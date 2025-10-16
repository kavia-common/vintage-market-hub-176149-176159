"""User model."""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # Import only for type checking to resolve forward refs without runtime circular imports
    from src.models.listing import Listing
    from src.models.offer import Offer
    from src.models.swap import Swap
    from src.models.transaction import Transaction

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a registered platform user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    listings: Mapped[List["Listing"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    offers: Mapped[List["Offer"]] = relationship(back_populates="buyer", cascade="all, delete-orphan")
    swaps_initiated: Mapped[List["Swap"]] = relationship(
        back_populates="initiator", foreign_keys="Swap.initiator_id", cascade="all, delete-orphan"
    )
    swaps_counterparty: Mapped[List["Swap"]] = relationship(
        back_populates="counterparty", foreign_keys="Swap.counterparty_id", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="buyer")

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"User(id={self.id}, email={self.email}, username={self.username})"
