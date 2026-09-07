from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class AnthropicContentBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str = ""


class AnthropicMessageParam(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, List[Dict[str, Any]]]


class AnthropicMessagesRequest(BaseModel):
    model: str
    messages: List[AnthropicMessageParam]
    max_tokens: int = Field(default=1024, ge=1)
    system: Optional[Union[str, List[Dict[str, Any]]]] = None
    metadata: Optional[Dict[str, Any]] = None
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=0)


class AnthropicUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class AnthropicMessagesResponse(BaseModel):
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[AnthropicContentBlock]
    model: str
    stop_reason: Optional[str] = "end_turn"
    stop_sequence: Optional[str] = None
    usage: AnthropicUsage
