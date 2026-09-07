import time
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


# --- Error Schemas ---
class OpenAIErrorDetail(BaseModel):
    message: str
    type: str = "invalid_request_error"
    param: Optional[str] = None
    code: Optional[str] = None


class OpenAIErrorResponse(BaseModel):
    error: OpenAIErrorDetail


# --- Chat Completion Schemas ---
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    user: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    extra_body: Optional[Dict[str, Any]] = None


class CompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionChoiceMessage(BaseModel):
    role: str = "assistant"
    content: Optional[str] = ""
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionChoiceMessage
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[CompletionUsage] = None
    system_fingerprint: Optional[str] = "fp_local_gateway"


# --- Streaming Schemas ---
class ChatCompletionDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChunkChoice(BaseModel):
    index: int = 0
    delta: ChatCompletionDelta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChunkChoice]
    usage: Optional[CompletionUsage] = None


# --- Text Completion Schemas (/v1/completions) ---
class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    stream: bool = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = 16
    stop: Optional[Union[str, List[str]]] = None


class CompletionChoice(BaseModel):
    text: str
    index: int = 0
    finish_reason: Optional[str] = "stop"


class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[CompletionChoice]
    usage: Optional[CompletionUsage] = None


# --- Embeddings Schemas (/v1/embeddings) ---
class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]
    user: Optional[str] = None


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int = 0


class EmbeddingUsage(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: EmbeddingUsage


# --- Models List Schemas (/v1/models) ---
class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "local"
    context_length: Optional[int] = None
    description: Optional[str] = None


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelObject]
