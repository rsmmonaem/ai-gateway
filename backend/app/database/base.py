from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime


class Base(DeclarativeBase):
    """Base class for all database models with common timestamp helpers."""
    pass
