import json
import time
import uuid
from datetime import datetime, timezone
from typing import Tuple

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import get_api_key_auth
from app.database.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.router.engine import RouterEngine
from app.router.queue import concurrency_manager
from app.schemas.anthropic import (
    AnthropicContentBlock,
    AnthropicMessagesRequest,
    AnthropicMessagesResponse,
    AnthropicUsage,
)
from app.schemas.openai import ChatCompletionRequest, ChatMessage
from app.services.token_counter import count_chat_tokens, count_tokens_text
from app.services.usage_tracker import usage_tracker
from app.core.config import settings

router = APIRouter(tags=["Anthropic Messages API"])
router_engine = RouterEngine()


def _convert_anthropic_to_openai(req: AnthropicMessagesRequest) -> ChatCompletionRequest:
    messages = []

    # 1. System Prompt
    if req.system:
        if isinstance(req.system, str):
            sys_text = req.system
        elif isinstance(req.system, list):
            sys_text = "\n\n".join([b.get("text", "") if isinstance(b, dict) else str(b) for b in req.system])
        else:
            sys_text = str(req.system)
        messages.append(ChatMessage(role="system", content=sys_text))

    # 2. Messages
    for m in req.messages:
        if isinstance(m.content, str):
            content_text = m.content
        elif isinstance(m.content, list):
            content_text = "".join([b.get("text", "") if isinstance(b, dict) else str(b) for b in m.content])
        else:
            content_text = str(m.content)
        messages.append(ChatMessage(role=m.role, content=content_text))

    return ChatCompletionRequest(
        model=req.model,
        messages=messages,
        max_tokens=req.max_tokens,
        temperature=req.temperature if req.temperature is not None else 1.0,
        stream=req.stream,
    )


@router.post("/messages")
@router.post("/v1/messages")
async def create_message(
    ant_req: AnthropicMessagesRequest,
    raw_request: Request,
    auth: Tuple[User, APIKey] = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Anthropic Messages API endpoint.
    Compatible with the official Anthropic Python and TypeScript SDKs.
    """
    user, api_key = auth
    started_at = datetime.now(timezone.utc)
    t0 = time.time()
    req_id = getattr(raw_request.state, "request_id", f"msg_{uuid.uuid4().hex[:20]}")
    client_ip = raw_request.client.host if raw_request.client else "127.0.0.1"

    # 1. Convert to internal OpenAI-style request
    chat_req = _convert_anthropic_to_openai(ant_req)

    # 2. Resolve Model & Provider
    model_def, instance, provider = await router_engine.resolve_model(
        requested_model=chat_req.model,
        user=user,
        db=db,
    )

    # 3. Queue / Concurrency Control
    await concurrency_manager.acquire(
        model_slug=model_def.slug,
        timeout=settings.DEFAULT_QUEUE_TIMEOUT_SECONDS,
    )

    prompt_tokens = count_chat_tokens(chat_req.messages)
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"

    if ant_req.stream:
        # --- Anthropic SSE Streaming Format ---
        async def event_generator():
            accumulated_text = []
            status_code = 200
            error_code = None
            try:
                if instance:
                    instance.active_requests += 1

                # Event 1: message_start
                start_payload = {
                    "type": "message_start",
                    "message": {
                        "id": msg_id,
                        "type": "message",
                        "role": "assistant",
                        "model": model_def.slug,
                        "content": [],
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": prompt_tokens, "output_tokens": 1},
                    },
                }
                yield f"event: message_start\ndata: {json.dumps(start_payload)}\n\n"

                # Event 2: content_block_start
                cb_start = {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                }
                yield f"event: content_block_start\ndata: {json.dumps(cb_start)}\n\n"

                # Stream deltas from provider
                async for chunk_line in provider.chat_completion_stream(chat_req):
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
                                    delta_payload = {
                                        "type": "content_block_delta",
                                        "index": 0,
                                        "delta": {"type": "text_delta", "text": piece},
                                    }
                                    yield f"event: content_block_delta\ndata: {json.dumps(delta_payload)}\n\n"
                        except Exception:
                            pass

                # Event: content_block_stop
                yield f"event: content_block_stop\ndata: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

                # Event: message_delta
                total_out = count_tokens_text("".join(accumulated_text))
                msg_delta = {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": total_out},
                }
                yield f"event: message_delta\ndata: {json.dumps(msg_delta)}\n\n"

                # Event: message_stop
                yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

            except Exception as e:
                status_code = 500
                error_code = "stream_interrupted"
                err_payload = {"type": "error", "error": {"type": "api_error", "message": str(e)}}
                yield f"event: error\ndata: {json.dumps(err_payload)}\n\n"
            finally:
                concurrency_manager.release(model_def.slug)
                if instance and instance.active_requests > 0:
                    instance.active_requests -= 1

                completed_at = datetime.now(timezone.utc)
                duration_ms = (time.time() - t0) * 1000
                full_reply = "".join(accumulated_text)
                completion_tokens = count_tokens_text(full_reply)

                await usage_tracker.record_usage(
                    request_id=req_id,
                    user_id=user.id,
                    api_key_id=api_key.id,
                    model=model_def.slug,
                    provider=model_def.provider,
                    backend=model_def.backend,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    status_code=status_code,
                    pricing_input=model_def.pricing_input,
                    pricing_output=model_def.pricing_output,
                    error_code=error_code,
                    stream=True,
                    client_ip=client_ip,
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
        # --- Non-Streaming Execution ---
        status_code = 200
        error_code = None
        full_reply = ""
        try:
            if instance:
                instance.active_requests += 1

            completion_resp = await provider.chat_completion(chat_req)
            choices = completion_resp.choices
            if choices and choices[0].message:
                full_reply = choices[0].message.content or ""

            completion_tokens = (
                completion_resp.usage.completion_tokens
                if completion_resp.usage
                else count_tokens_text(full_reply)
            )

            response_data = AnthropicMessagesResponse(
                id=msg_id,
                type="message",
                role="assistant",
                content=[AnthropicContentBlock(type="text", text=full_reply)],
                model=model_def.slug,
                stop_reason="end_turn",
                stop_sequence=None,
                usage=AnthropicUsage(
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                ),
            )
            return response_data

        except Exception as e:
            status_code = 500
            error_code = "execution_error"
            raise e
        finally:
            concurrency_manager.release(model_def.slug)
            if instance and instance.active_requests > 0:
                instance.active_requests -= 1

            completed_at = datetime.now(timezone.utc)
            duration_ms = (time.time() - t0) * 1000

            await usage_tracker.record_usage(
                request_id=req_id,
                user_id=user.id,
                api_key_id=api_key.id,
                model=model_def.slug,
                provider=model_def.provider,
                backend=model_def.backend,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=count_tokens_text(full_reply),
                status_code=status_code,
                pricing_input=model_def.pricing_input,
                pricing_output=model_def.pricing_output,
                error_code=error_code,
                stream=False,
                client_ip=client_ip,
            )
