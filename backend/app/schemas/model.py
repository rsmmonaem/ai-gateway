from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ModelCreate(BaseModel):
    name: str
    slug: str
    aliases: Optional[str] = None
    provider: str = "local"
    backend: str  # "mlx", "ollama", "llamacpp", "openai_compatible"
    backend_model_name: str
    endpoint: str
    context_length: int = 32768
    supports_chat: bool = True
    supports_completion: bool = True
    supports_embeddings: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    enabled: bool = True
    priority: int = 100
    pricing_input: float = 0.0
    pricing_output: float = 0.0
    description: Optional[str] = None


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[str] = None
    backend_model_name: Optional[str] = None
    endpoint: Optional[str] = None
    context_length: Optional[int] = None
    supports_chat: Optional[bool] = None
    supports_completion: Optional[bool] = None
    supports_embeddings: Optional[bool] = None
    supports_tools: Optional[bool] = None
    supports_vision: Optional[bool] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    pricing_input: Optional[float] = None
    pricing_output: Optional[float] = None
    description: Optional[str] = None


class ModelInstanceOut(BaseModel):
    id: int
    instance_name: str
    endpoint: str
    health_status: str
    last_health_check: Optional[datetime] = None
    active_requests: int
    total_requests: int
    avg_latency_ms: float
    enabled: bool

    class Config:
        from_attributes = True


class ModelOut(BaseModel):
    id: int
    name: str
    slug: str
    aliases: Optional[str] = None
    provider: str
    backend: str
    backend_model_name: str
    endpoint: str
    context_length: int
    supports_chat: bool
    supports_completion: bool
    supports_embeddings: bool
    supports_tools: bool
    supports_vision: bool
    enabled: bool
    priority: int
    pricing_input: float
    pricing_output: float
    description: Optional[str] = None
    instances: List[ModelInstanceOut] = []

    class Config:
        from_attributes = True


class ModelTestRequest(BaseModel):
    prompt: str = "Hello, are you online? Respond with a single short sentence."
    max_tokens: int = 30


class ModelTestResponse(BaseModel):
    connected: bool
    status: str
    ttft_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    response_text: Optional[str] = None
    backend: str
    error: Optional[str] = None
