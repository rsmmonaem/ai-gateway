import json
import time
from datetime import datetime, timezone
from typing import Tuple
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import get_api_key_auth
from app.core.config import settings
from app.core.logging import logger
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.router.classifier import request_classifier
from app.router.engine import router_engine
from app.router.queue import concurrency_manager
from app.router.resilience import resilience_manager
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse, ChatMessage
from app.services.token_counter import count_chat_tokens, count_tokens_text
from app.services.usage_tracker import usage_tracker
from app.services.web_search import web_search_service

router = APIRouter(prefix="/chat", tags=["OpenAI - Chat Completions"])


@router.post("/completions")
async def create_chat_completion(
    chat_req: ChatCompletionRequest,
    raw_request: Request,
    auth: Tuple[User, APIKey] = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Universal OpenAI-compatible Chat Completions endpoint.
    Supports smart 'universal' model routing, web search context augmentation,
    fallback execution, non-buffering SSE streaming, and automatic token metrics tracking.
    """
    user, api_key = auth
    started_at = datetime.now(timezone.utc)
    t0 = time.time()
    req_id = getattr(raw_request.state, "request_id", f"req_{int(time.time()*1000)}")
    client_ip = raw_request.client.host if raw_request.client else "127.0.0.1"

    # Check for Web Search Intent
    target_cap = request_classifier.classify_request(chat_req)
    if target_cap == "web_search":
        user_query = ""
        for msg in reversed(chat_req.messages):
            if msg.role == "user" and isinstance(msg.content, str):
                user_query = msg.content
                break
        if user_query:
            logger.info(f"Web search intent detected for query: '{user_query}'. Performing search...")
            results = await web_search_service.search(user_query, max_results=3)
            search_context = web_search_service.format_search_context(results)
            if search_context:
                sys_msg = ChatMessage(role="system", content=f"System Web Search Context:\n{search_context}\nUse the web search results above when responding to the user's latest query.")
                chat_req.messages.insert(0, sys_msg)

    # 1. Resolve Primary Model and Secondary Fallback Candidates
    primary_def, primary_inst, primary_prov, fallback_candidates = await router_engine.resolve_model_candidates(
        requested_model=chat_req.model,
        user=user,
        db=db,
        request=chat_req,
    )

    primary_candidate = (primary_def, primary_inst, primary_prov)
    prompt_tokens = count_chat_tokens(chat_req.messages)

    if chat_req.stream:
        # --- Streaming Execution with Concurrency Queue ---
        await concurrency_manager.acquire(
            model_slug=primary_def.slug,
            backend=primary_def.backend,
            timeout=settings.DEFAULT_QUEUE_TIMEOUT_SECONDS,
        )

        async def event_generator():
            accumulated_text = []
            status_code = 200
            error_code = None
            try:
                if primary_inst:
                    primary_inst.active_requests += 1

                async for chunk_line in primary_prov.chat_completion_stream(chat_req):
                    if chunk_line.startswith("data: ") and not chunk_line.startswith("data: [DONE]"):
                        try:
                            payload_json = json.loads(chunk_line[6:].strip())
                            if "error" in payload_json:
                                status_code = 500
                                error_code = "stream_error"
                            choices = payload_json.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                piece = delta.get("content")
                                if piece:
                                    accumulated_text.append(piece)
                        except Exception:
                            pass

                    yield chunk_line

            except Exception as e:
                status_code = 500
                error_code = "stream_interrupted"
                yield f"data: {json.dumps({'error': {'message': str(e)}})}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                concurrency_manager.release(primary_def.slug, primary_def.backend)
                if primary_inst and primary_inst.active_requests > 0:
                    primary_inst.active_requests -= 1

                completed_at = datetime.now(timezone.utc)
                duration_ms = (time.time() - t0) * 1000
                full_reply = "".join(accumulated_text)
                completion_tokens = count_tokens_text(full_reply)

                prompt_str = (
                    json.dumps([m.model_dump() for m in chat_req.messages])
                    if settings.STORE_REQUEST_CONTENT
                    else None
                )

                await usage_tracker.record_usage(
                    request_id=req_id,
                    user_id=user.id,
                    api_key_id=api_key.id,
                    model=primary_def.slug,
                    provider=primary_def.provider,
                    backend=primary_def.backend,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    status_code=status_code,
                    pricing_input=primary_def.pricing_input,
                    pricing_output=primary_def.pricing_output,
                    error_code=error_code,
                    stream=True,
                    client_ip=client_ip,
                    prompt_content=prompt_str,
                    response_content=full_reply if settings.STORE_REQUEST_CONTENT else None,
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    else:
        # --- Non-Streaming Execution with Resilience (Retries + Fallback) ---
        await concurrency_manager.acquire(
            model_slug=primary_def.slug,
            backend=primary_def.backend,
            timeout=settings.DEFAULT_QUEUE_TIMEOUT_SECONDS,
        )

        try:
            response, used_def, used_inst, fallback_used = await resilience_manager.execute_chat_completion(
                request=chat_req,
                primary=primary_candidate,
                fallbacks=fallback_candidates,
            )

            comp_tokens = (
                response.usage.completion_tokens
                if response.usage and response.usage.completion_tokens > 0
                else count_tokens_text(response.choices[0].message.content if response.choices else "")
            )
            prompt_tokens_final = (
                response.usage.prompt_tokens
                if response.usage and response.usage.prompt_tokens > 0
                else prompt_tokens
            )

            completed_at = datetime.now(timezone.utc)
            duration_ms = (time.time() - t0) * 1000

            prompt_str = (
                json.dumps([m.model_dump() for m in chat_req.messages])
                if settings.STORE_REQUEST_CONTENT
                else None
            )
            reply_str = response.choices[0].message.content if response.choices else None

            await usage_tracker.record_usage(
                request_id=req_id,
                user_id=user.id,
                api_key_id=api_key.id,
                model=used_def.slug,
                provider=used_def.provider,
                backend=used_def.backend,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens_final,
                completion_tokens=comp_tokens,
                status_code=200,
                pricing_input=used_def.pricing_input,
                pricing_output=used_def.pricing_output,
                stream=False,
                client_ip=client_ip,
                prompt_content=prompt_str,
                response_content=reply_str if settings.STORE_REQUEST_CONTENT else None,
            )

            return response

        except Exception as e:
            status_code = getattr(e, "status_code", 500)
            error_code = str(type(e).__name__)
            duration_ms = (time.time() - t0) * 1000
            await usage_tracker.record_usage(
                request_id=req_id,
                user_id=user.id,
                api_key_id=api_key.id,
                model=primary_def.slug,
                provider=primary_def.provider,
                backend=primary_def.backend,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=0,
                status_code=status_code,
                error_code=error_code,
                stream=False,
                client_ip=client_ip,
            )
            raise e
        finally:
            concurrency_manager.release(primary_def.slug, primary_def.backend)
