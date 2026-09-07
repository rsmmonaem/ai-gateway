from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserModelPermission(Base):
    __tablename__ = "user_model_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "model_id", name="uq_user_model"),)

    user: Mapped["User"] = relationship("User", back_populates="permissions")
