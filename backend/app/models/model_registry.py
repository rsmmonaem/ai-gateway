from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ModelDefinition(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Display Name e.g. "Kimi 7B Instruct"
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)  # e.g. "kimi-7b"
    aliases: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Comma separated e.g. "kimi,kimi-fast"
    provider: Mapped[str] = mapped_column(String(100), default="local", nullable=False)  # e.g. "local-mlx", "local-ollama"
    backend: Mapped[str] = mapped_column(String(50), nullable=False)  # "mlx", "ollama", "llamacpp", "openai_compatible"
    backend_model_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Target model tag/id on engine
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)  # e.g. "http://127.0.0.1:8081"
    context_length: Mapped[int] = mapped_column(Integer, default=32768, nullable=False)
    supports_chat: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_completion: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_embeddings: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_coding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_reasoning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    pricing_input: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # USD per 1M tokens
    pricing_output: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # USD per 1M tokens
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    instances: Mapped[List["ModelInstance"]] = relationship(
        "ModelInstance", back_populates="model", cascade="all, delete-orphan"
    )


class ModelInstance(Base):
    __tablename__ = "model_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    instance_name: Mapped[str] = mapped_column(String(100), default="instance-1", nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    health_status: Mapped[str] = mapped_column(String(50), default="ONLINE", nullable=False)  # ONLINE, OFFLINE, DEGRADED
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    model: Mapped["ModelDefinition"] = relationship("ModelDefinition", back_populates="instances")
