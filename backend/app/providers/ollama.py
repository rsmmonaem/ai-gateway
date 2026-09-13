import json
import time
from typing import AsyncIterator, List, Optional, Tuple
import httpx
from fastapi import HTTPException

from app.providers.base import InferenceProvider
from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionChoiceMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    CompletionResponse,
    CompletionUsage,
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingUsage,
)
from app.services.token_counter import count_chat_tokens, count_tokens_text


class OllamaProvider(InferenceProvider):
    """
    Adapter for Ollama (0.34.0) running natively on macOS with Apple Silicon M5 Metal GPU acceleration.
    Translates OpenAI request/response formats to/from Ollama REST API.
    """

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        url = f"{self.endpoint}/api/chat"
        prompt_tokens = count_chat_tokens(request.messages)

        messages_payload = []
        for msg in request.messages:
            content_str = ""
            if isinstance(msg.content, str):
                content_str = msg.content
            elif isinstance(msg.content, list):
                # Extract text parts
                text_parts = [p.get("text", "") for p in msg.content if isinstance(p, dict) and p.get("type") == "text"]
                content_str = "\n".join(text_parts)
            messages_payload.append({"role": msg.role, "content": content_str})

        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if request.stop is not None:
            options["stop"] = [request.stop] if isinstance(request.stop, str) else request.stop
        if request.frequency_penalty is not None:
            options["repeat_penalty"] = 1.0 + request.frequency_penalty
        if request.presence_penalty is not None:
            options["presence_penalty"] = request.presence_penalty

        payload = {
            "model": self.model_name,
            "messages": messages_payload,
            "stream": False,
            "options": options,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, json=payload)
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": {
                            "message": f"Could not connect to Ollama at {self.endpoint}. Is Ollama running?",
                            "type": "server_error",
                            "code": "ollama_offline",
                        }
                    },
                )
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={"error": {"message": f"Ollama timed out after {self.timeout}s.", "code": "timeout"}},
                )

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        data = resp.json()
        content = data.get("message", {}).get("content", "")
        prompt_t = data.get("prompt_eval_count", prompt_tokens)
        comp_t = data.get("eval_count", count_tokens_text(content))

        return ChatCompletionResponse(
            id=f"chatcmpl-ollama-{int(time.time())}",
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionChoiceMessage(
                        role="assistant",
                        content=content,
                    ),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=prompt_t,
                completion_tokens=comp_t,
                total_tokens=prompt_t + comp_t,
            ),
        )

    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[str]:
        url = f"{self.endpoint}/api/chat"
        messages_payload = []
        for msg in request.messages:
            content_str = ""
            if isinstance(msg.content, str):
                content_str = msg.content
            elif isinstance(msg.content, list):
                text_parts = [p.get("text", "") for p in msg.content if isinstance(p, dict) and p.get("type") == "text"]
                content_str = "\n".join(text_parts)
            messages_payload.append({"role": msg.role, "content": content_str})

        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens

        payload = {
            "model": self.model_name,
            "messages": messages_payload,
            "stream": True,
            "options": options,
        }

        client = httpx.AsyncClient(timeout=self.timeout)
        try:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    err_text = await response.aread()
                    yield f"data: {json.dumps({'error': {'message': f'Ollama error: {err_text.decode()}'}})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                req_id = f"chatcmpl-ollama-{int(time.time())}"
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk_obj = json.loads(line)
                        content_piece = chunk_obj.get("message", {}).get("content", "")
                        done = chunk_obj.get("done", False)

                        sse_chunk = {
                            "id": req_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": request.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": content_piece} if content_piece else {},
                                    "finish_reason": "stop" if done else None,
                                }
                            ],
                        }
                        yield f"data: {json.dumps(sse_chunk)}\n\n"
                    except Exception:
                        continue

            yield "data: [DONE]\n\n"
        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': {'message': 'Connection to Ollama failed'}})}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await client.aclose()

    async def completion(self, request: CompletionRequest) -> CompletionResponse:
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": request.prompt if isinstance(request.prompt, str) else "\n".join(request.prompt),
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            data = resp.json()
            return CompletionResponse(
                id=f"cmpl-ollama-{int(time.time())}",
                model=request.model,
                choices=[CompletionChoice(text=data.get("response", ""), index=0, finish_reason="stop")],
            )

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        url = f"{self.endpoint}/api/embeddings"
        prompts: List[str] = [request.input] if isinstance(request.input, str) else request.input
        results: List[EmbeddingData] = []
        total_tokens = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for idx, prompt in enumerate(prompts):
                payload = {"model": self.model_name, "prompt": prompt}
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise HTTPException(status_code=resp.status_code, detail=resp.text)
                data = resp.json()
                vec = data.get("embedding", [])
                t_count = count_tokens_text(prompt)
                total_tokens += t_count
                results.append(EmbeddingData(embedding=vec, index=idx))

        return EmbeddingResponse(
            data=results,
            model=request.model,
            usage=EmbeddingUsage(prompt_tokens=total_tokens, total_tokens=total_tokens),
        )

    async def health_check(self) -> Tuple[bool, str, Optional[float]]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"{self.endpoint}/api/tags")
                latency = round((time.time() - start) * 1000, 2)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    has_model = any(self.model_name in m.get("name", "") for m in models)
                    status_str = "ONLINE (Model Loaded)" if has_model else "ONLINE (Backend ready)"
                    return True, status_str, latency
        except Exception:
            pass
        return False, "OFFLINE", None
