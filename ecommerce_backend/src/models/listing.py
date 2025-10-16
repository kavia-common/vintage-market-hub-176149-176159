"""Listing model."""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
import uuid
from decimal import Decimal

from sqlalchemy import String, Text, Numeric, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import ListingStatus

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.region import Region
    from src.models.category import Category
    from src.models.offer import Offer
    from src.models.negotiation import Negotiation
    from src.models.swap import Swap
    from src.models.transaction import Transaction


class Listing(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a product listing offered by a seller."""

    __tablename__ = "listings"

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped["ListingStatus"] = mapped_column(Enum(ListingStatus), default=ListingStatus.active, nullable=False)

    # Foreign keys
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)

    # Relationships
    seller: Mapped["User"] = relationship(back_populates="listings")
    region: Mapped["Region"] = relationship(back_populates="listings")
    category: Mapped["Category"] = relationship(back_populates="listings")
    offers: Mapped[List["Offer"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    negotiations: Mapped[List["Negotiation"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    swaps: Mapped[List["Swap"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="listing")

    def __repr__(self) -> str:  # pragma: no cover
        return f"Listing(id={self.id}, title={self.title}, price={self.price} {self.currency})"

