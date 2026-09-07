from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class UsageRecordOut(BaseModel):
    id: int
    request_id: str
    user_id: int
    api_key_id: Optional[int] = None
    model: str
    provider: str
    backend: str
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    status_code: int
    error_code: Optional[str] = None
    stream: bool
    client_ip: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UsageStatsSummary(BaseModel):
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_total_cost: float
    avg_latency_ms: float
    error_rate_percent: float
    requests_today: int
    tokens_today: int
    active_models_count: int
    total_users_count: int
    active_keys_count: int
