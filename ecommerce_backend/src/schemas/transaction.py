"""Transaction schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import TransactionStatus
from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class TransactionBase(ORMBase):
    """Base Transaction fields."""
    amount: Decimal
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: TransactionStatus = Field(default=TransactionStatus.pending)
    provider: str = Field(default="stripe", max_length=50)
    provider_payment_intent_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class TransactionCreate(BaseModel):
    """Create Transaction schema."""
    listing_id: Optional[UUID] = None
    buyer_id: Optional[UUID] = None
    amount: Decimal
    currency: str = Field(default="USD", min_length=3, max_length=3)
    provider: str = Field(default="stripe", max_length=50)
    provider_payment_intent_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class TransactionUpdate(BaseModel):
    """Update Transaction schema."""
    status: Optional[TransactionStatus] = None
    provider_payment_intent_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class TransactionRead(TransactionBase):
    """Read Transaction schema."""
    id: UUID
    listing_id: Optional[UUID] = None
    buyer_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
