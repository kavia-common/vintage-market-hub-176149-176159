"""SQLAlchemy Base and shared mixins."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    """Global declarative base for all models."""
    pass


class TimestampMixin:
    """Adds created_at and updated_at timestamp columns to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column named 'id'."""

    @declared_attr.directive
    def id(cls) -> Mapped[uuid.UUID]:
        # Use PostgreSQL UUID if available; fallback to CHAR(36) for portability.
        return mapped_column(
            UUID(as_uuid=True) if UUID is not None else String(36),
            primary_key=True,
            default=uuid.uuid4,
        )
