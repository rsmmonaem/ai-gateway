from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="Default Key", nullable=False)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    monthly_limit_tokens: Mapped[int] = mapped_column(BigInteger, default=10_000_000, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < datetime.now(timezone.utc):
            return False
        return True
