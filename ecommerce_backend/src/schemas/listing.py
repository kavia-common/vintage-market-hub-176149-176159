"""Listing schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import ListingStatus
from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class ListingBase(ORMBase):
    """Base Listing fields."""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(..., description="Listing price")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: ListingStatus = Field(default=ListingStatus.active)
    region_id: UUID
    category_id: UUID


# PUBLIC_INTERFACE
class ListingCreate(BaseModel):
    """Create Listing schema."""
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    price: Decimal
    currency: str = Field(default="USD", min_length=3, max_length=3)
    region_id: UUID
    category_id: UUID


# PUBLIC_INTERFACE
class ListingUpdate(BaseModel):
    """Update Listing schema."""
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    price: Optional[Decimal] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    status: Optional[ListingStatus] = None
    region_id: Optional[UUID] = None
    category_id: Optional[UUID] = None


# PUBLIC_INTERFACE
class ListingRead(ListingBase):
    """Read Listing schema."""
    id: UUID
    seller_id: UUID
    created_at: datetime
    updated_at: datetime
