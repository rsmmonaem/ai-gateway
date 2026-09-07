import json
import time
from typing import AsyncIterator, Optional, Tuple
import httpx
from fastapi import HTTPException

from app.core.logging import logger
from app.providers.base import InferenceProvider
from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionChoiceMessage,
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    CompletionUsage,
)
from app.services.token_counter import count_chat_tokens, count_tokens_text


class OpenAICompatibleProvider(InferenceProvider):
    """
    Adapter for any downstream inference engine implementing OpenAI's HTTP spec.
    Also provides a built-in mock mode for zero-dependency test verification.
    """

    @property
    def is_mock(self) -> bool:
        return "mock" in self.endpoint or "127.0.0.1:8000/v1/_mock" in self.endpoint

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        prompt_tokens = count_chat_tokens(request.messages)

        if self.is_mock:
            # Built-in mock response for testing without downloading models
            last_msg = request.messages[-1].content if request.messages else "Hello"
            reply_text = f"Mock response from {self.model_name} on Mac mini M4. Echo: {last_msg}"
            comp_tokens = count_tokens_text(reply_text)
            return ChatCompletionResponse(
                id=f"chatcmpl-mock-{int(time.time())}",
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatCompletionChoiceMessage(
                            role="assistant",
                            content=reply_text,
                        ),
                        finish_reason="stop",
                    )
                ],
                usage=CompletionUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=comp_tokens,
                    total_tokens=prompt_tokens + comp_tokens,
                ),
            )

        url = f"{self.endpoint}/v1/chat/completions"
        payload = request.model_dump(exclude_none=True)
        # Override model name with backend internal model name
        payload["model"] = self.model_name

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(url, json=payload)
            except httpx.ConnectError:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": {
                            "message": f"Cannot connect to backend endpoint '{self.endpoint}'. Is the model server running?",
                            "type": "server_error",
                            "param": None,
                            "code": "backend_unavailable",
                        }
                    },
                )
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": {
                            "message": f"Backend endpoint '{self.endpoint}' timed out after {self.timeout}s.",
                            "type": "server_error",
                            "param": None,
                            "code": "backend_timeout",
                        }
                    },
                )

        if resp.status_code != 200:
            raise HTTPException(
                status_code=resp.status_code,
                detail={
                    "error": {
                        "message": f"Backend returned error ({resp.status_code}): {resp.text}",
                        "type": "backend_error",
                        "param": None,
                        "code": "backend_error",
                    }
                },
            )

        data = resp.json()
        return ChatCompletionResponse(**data)

    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[str]:
        if self.is_mock:
            # Generate simulated stream tokens
            req_id = f"chatcmpl-mock-stream-{int(time.time())}"
            words = f"Mock streaming response from {self.model_name} on Mac mini M4. Unified Memory Metal active.".split(" ")
            for i, word in enumerate(words):
                chunk_data = {
                    "id": req_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": (" " if i > 0 else "") + word},
                            "finish_reason": None if i < len(words) - 1 else "stop",
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            yield "data: [DONE]\n\n"
            return

        url = f"{self.endpoint}/v1/chat/completions"
        payload = request.model_dump(exclude_none=True)
        payload["model"] = self.model_name
        payload["stream"] = True

        client = httpx.AsyncClient(timeout=self.timeout)
        try:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    yield f"data: {json.dumps({'error': {'message': f'Backend error {response.status_code}: {err_body.decode()}'}})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                async for line in response.aiter_lines():
                    if line:
                        yield f"{line}\n\n"
        except httpx.ConnectError:
            err_json = json.dumps({"error": {"message": f"Cannot connect to backend {self.endpoint}"}})
            yield f"data: {err_json}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            await client.aclose()

    async def completion(self, request: CompletionRequest) -> CompletionResponse:
        url = f"{self.endpoint}/v1/completions"
        payload = request.model_dump(exclude_none=True)
        payload["model"] = self.model_name

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return CompletionResponse(**resp.json())

    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        url = f"{self.endpoint}/v1/embeddings"
        payload = request.model_dump(exclude_none=True)
        payload["model"] = self.model_name

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return EmbeddingResponse(**resp.json())

    async def health_check(self) -> Tuple[bool, str, Optional[float]]:
        if self.is_mock:
            return True, "ONLINE (Mock Backend)", 1.2

        start = time.time()
        for check_path in ["/health", "/v1/health", "/v1/models", "/"]:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self.endpoint}{check_path}")
                    latency = round((time.time() - start) * 1000, 2)
                    if resp.status_code in (200, 404):
                        return True, "ONLINE", latency
            except Exception:
                continue

        return False, "OFFLINE", None
