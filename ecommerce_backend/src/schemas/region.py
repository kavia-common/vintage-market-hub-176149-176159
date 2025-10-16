"""Region schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class RegionBase(ORMBase):
    """Base Region fields."""
    name: str = Field(..., max_length=120)
    code: str = Field(..., max_length=20)


# PUBLIC_INTERFACE
class RegionCreate(BaseModel):
    """Create Region schema."""
    name: str = Field(..., max_length=120)
    code: str = Field(..., max_length=20)


# PUBLIC_INTERFACE
class RegionUpdate(BaseModel):
    """Update Region schema."""
    name: str | None = Field(default=None, max_length=120)
    code: str | None = Field(default=None, max_length=20)


# PUBLIC_INTERFACE
class RegionRead(RegionBase):
    """Read Region schema."""
    id: UUID
    created_at: datetime
    updated_at: datetime
