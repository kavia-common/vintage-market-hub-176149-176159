"""Transaction model."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from src.models.enums import TransactionStatus

if TYPE_CHECKING:
    from src.models.listing import Listing
    from src.models.user import User


class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a payment transaction for a listing."""

    __tablename__ = "transactions"

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), default=TransactionStatus.pending, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="stripe", nullable=False)
    provider_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(120), default=None, index=True)

    # Foreign keys
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    listing: Mapped[Optional["Listing"]] = relationship(back_populates="transactions")
    buyer: Mapped[Optional["User"]] = relationship(back_populates="transactions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"Transaction(id={self.id}, status={self.status}, amount={self.amount} {self.currency})"
