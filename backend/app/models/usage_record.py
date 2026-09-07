from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    backend: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stream: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    client_ip: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )

    # Optional prompt/response storage (only stored if STORE_REQUEST_CONTENT=True)
    prompt_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="usage_records")
