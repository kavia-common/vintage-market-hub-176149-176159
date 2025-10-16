"""Pydantic schemas base classes."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ORMBase(BaseModel):
    """Base model enabling ORM mode."""

    model_config = ConfigDict(from_attributes=True)


class UUIDSchema(BaseModel):
    """Schema with an id UUID field."""

    id: UUID = Field(..., description="Resource identifier")
