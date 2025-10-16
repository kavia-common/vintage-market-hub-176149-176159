"""Category schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class CategoryBase(ORMBase):
    """Base Category fields."""
    name: str = Field(..., max_length=120)
    description: Optional[str] = Field(default=None)


# PUBLIC_INTERFACE
class CategoryCreate(BaseModel):
    """Create Category schema."""
    name: str = Field(..., max_length=120)
    description: Optional[str] = None


# PUBLIC_INTERFACE
class CategoryUpdate(BaseModel):
    """Update Category schema."""
    name: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = None


# PUBLIC_INTERFACE
class CategoryRead(CategoryBase):
    """Read Category schema."""
    id: UUID
    created_at: datetime
    updated_at: datetime
