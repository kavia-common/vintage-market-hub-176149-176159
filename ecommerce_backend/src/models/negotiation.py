"""Negotiation model."""
from __future__ import annotations

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Enum, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import NegotiationStatus

if TYPE_CHECKING:
    from src.models.offer import Offer
    from src.models.listing import Listing


class Negotiation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Negotiation session linked to an offer and listing."""

    __tablename__ = "negotiations"

    status: Mapped[NegotiationStatus] = mapped_column(Enum(NegotiationStatus), default=NegotiationStatus.open, nullable=False)
    last_message: Mapped[Optional[str]] = mapped_column(Text, default=None)
    channel_id: Mapped[Optional[str]] = mapped_column(String(120), default=None, index=True)  # for chat reference

    # Foreign keys
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, unique=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    offer: Mapped["Offer"] = relationship(back_populates="negotiation")
    listing: Mapped["Listing"] = relationship(back_populates="negotiations")

    def __repr__(self) -> str:  # pragma: no cover
        return f"Negotiation(id={self.id}, status={self.status})"
