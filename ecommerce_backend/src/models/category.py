"""Category model."""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.listing import Listing

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Item category (e.g., clothing, furniture, accessories)."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)

    listings: Mapped[List["Listing"]] = relationship(back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover
        return f"Category(id={self.id}, name={self.name})"
