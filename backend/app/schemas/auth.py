from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    name: str


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "user"  # "admin" or "user"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str = "Default Key"
    rate_limit_rpm: Optional[int] = 60
    monthly_limit_tokens: Optional[int] = 10_000_000
    expires_in_days: Optional[int] = None


class APIKeyCreateResponse(BaseModel):
    id: int
    name: str
    raw_key: str  # Only returned once upon creation!
    key_prefix: str
    rate_limit_rpm: int
    monthly_limit_tokens: int
    created_at: datetime
    expires_at: Optional[datetime] = None


class APIKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    rate_limit_rpm: int
    monthly_limit_tokens: int
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True
