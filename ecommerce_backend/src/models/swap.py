"""Swap model."""
from __future__ import annotations

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import SwapStatus

if TYPE_CHECKING:
    from src.models.listing import Listing
    from src.models.user import User


class Swap(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Swap proposal between two users regarding a listing."""

    __tablename__ = "swaps"

    status: Mapped[SwapStatus] = mapped_column(Enum(SwapStatus), default=SwapStatus.proposed, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, default=None)
    channel_id: Mapped[Optional[str]] = mapped_column(String(120), default=None, index=True)

    # Foreign keys
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    initiator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    counterparty_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    listing: Mapped["Listing"] = relationship(back_populates="swaps")
    initiator: Mapped["User"] = relationship(back_populates="swaps_initiated", foreign_keys=[initiator_id])
    counterparty: Mapped["User"] = relationship(back_populates="swaps_counterparty", foreign_keys=[counterparty_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"Swap(id={self.id}, status={self.status})"
