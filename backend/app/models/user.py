from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)  # admin or user
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # active or disabled
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    api_keys: Mapped[List["APIKey"]] = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    usage_records: Mapped[List["UsageRecord"]] = relationship("UsageRecord", back_populates="user")
    permissions: Mapped[List["UserModelPermission"]] = relationship("UserModelPermission", back_populates="user", cascade="all, delete-orphan")
