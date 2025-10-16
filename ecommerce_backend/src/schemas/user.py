"""User Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.schemas.base import ORMBase


# PUBLIC_INTERFACE
class UserBase(ORMBase):
    """Base attributes shared by User schemas."""
    email: EmailStr = Field(..., description="Unique email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(default=None, description="Full name of the user")
    is_active: bool = Field(default=True, description="Is the user active")
    is_superuser: bool = Field(default=False, description="Is the user an administrator")


# PUBLIC_INTERFACE
class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


# PUBLIC_INTERFACE
class UserUpdate(BaseModel):
    """Schema for updating user details."""
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    password: Optional[str] = Field(default=None, min_length=8)
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# PUBLIC_INTERFACE
class UserRead(UserBase):
    """Schema for reading user data."""
    id: UUID
    created_at: datetime
    updated_at: datetime
