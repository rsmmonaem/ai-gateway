from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Tuple
from app.schemas.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)


class InferenceProvider(ABC):
    """
    Abstract interface for local and remote AI inference backends.
    All providers normalize their input/output to standard OpenAI-compatible formats.
    """

    def __init__(self, endpoint: str, model_name: str, timeout: float = 300.0):
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    @abstractmethod
    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Execute a non-streaming chat completion."""
        pass

    @abstractmethod
    async def chat_completion_stream(
        self, request: ChatCompletionRequest
    ) -> AsyncIterator[str]:
        """Execute a streaming chat completion yielding SSE 'data: ...' strings."""
        pass

    @abstractmethod
    async def completion(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a text completion."""
        pass

    @abstractmethod
    async def embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Execute an embedding request."""
        pass

    @abstractmethod
    async def health_check(self) -> Tuple[bool, str, Optional[float]]:
        """
        Check health of this model backend.
        Returns: (is_healthy, status_message, latency_ms)
        """
        pass
