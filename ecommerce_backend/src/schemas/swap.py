"""Swap schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import SwapStatus
from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class SwapBase(ORMBase):
    """Base Swap fields."""
    status: SwapStatus = Field(default=SwapStatus.proposed)
    notes: Optional[str] = None
    channel_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class SwapCreate(BaseModel):
    """Create Swap schema."""
    listing_id: UUID
    initiator_id: UUID
    counterparty_id: UUID
    notes: Optional[str] = None
    channel_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class SwapUpdate(BaseModel):
    """Update Swap schema."""
    status: Optional[SwapStatus] = None
    notes: Optional[str] = None
    channel_id: Optional[str] = Field(default=None, max_length=120)


# PUBLIC_INTERFACE
class SwapRead(SwapBase):
    """Read Swap schema."""
    id: UUID
    listing_id: UUID
    initiator_id: UUID
    counterparty_id: UUID
    created_at: datetime
    updated_at: datetime
