"""Region model."""
from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.listing import Listing

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Region(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Geographical region to scope listings and interactions."""

    __tablename__ = "regions"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    listings: Mapped[List["Listing"]] = relationship(back_populates="region")

    def __repr__(self) -> str:  # pragma: no cover
        return f"Region(id={self.id}, code={self.code}, name={self.name})"
