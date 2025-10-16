"""Negotiation schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import NegotiationStatus
from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class NegotiationBase(ORMBase):
    """Base Negotiation fields."""
    status: NegotiationStatus = Field(default=NegotiationStatus.open)
    last_message: Optional[str] = None
    channel_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class NegotiationCreate(BaseModel):
    """Create Negotiation schema."""
    offer_id: UUID
    listing_id: UUID
    channel_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class NegotiationUpdate(BaseModel):
    """Update Negotiation schema."""
    status: Optional[NegotiationStatus] = None
    last_message: Optional[str] = None
    channel_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class NegotiationRead(NegotiationBase):
    """Read Negotiation schema."""
    id: UUID
    offer_id: UUID
    listing_id: UUID
    created_at: datetime
    updated_at: datetime
