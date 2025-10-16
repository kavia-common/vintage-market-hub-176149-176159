"""Offer schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import OfferStatus
from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class OfferBase(ORMBase):
    """Base Offer fields."""
    amount: Decimal
    status: OfferStatus = Field(default=OfferStatus.pending)


# PUBLIC_INTERFACE
class OfferCreate(BaseModel):
    """Create Offer schema."""
    listing_id: UUID
    buyer_id: UUID
    amount: Decimal


# PUBLIC_INTERFACE
class OfferUpdate(BaseModel):
    """Update Offer schema."""
    amount: Decimal | None = None
    status: OfferStatus | None = None


# PUBLIC_INTERFACE
class OfferRead(OfferBase):
    """Read Offer schema."""
    id: UUID
    listing_id: UUID
    buyer_id: UUID
    created_at: datetime
    updated_at: datetime
