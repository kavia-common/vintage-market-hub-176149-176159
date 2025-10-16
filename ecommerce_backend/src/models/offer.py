"""Offer model."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import OfferStatus

if TYPE_CHECKING:
    from src.models.listing import Listing
    from src.models.user import User
    from src.models.negotiation import Negotiation


class Offer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Offer submitted by a buyer for a listing."""

    __tablename__ = "offers"

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OfferStatus] = mapped_column(Enum(OfferStatus), default=OfferStatus.pending, nullable=False)

    # Foreign keys
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    listing: Mapped["Listing"] = relationship(back_populates="offers")
    buyer: Mapped["User"] = relationship(back_populates="offers")
    negotiation: Mapped["Negotiation"] = relationship(back_populates="offer", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"Offer(id={self.id}, listing={self.listing_id}, amount={self.amount}, status={self.status})"
