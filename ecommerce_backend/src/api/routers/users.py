from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.deps import db_session
from src.core.security import decode_token
from src.models import User
from src.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


class _TokenUser(BaseModel):
    """Internal helper schema to represent token-authenticated user identity."""
    sub: UUID


def _get_current_user_id(authorization: str | None = Header(default=None)) -> _TokenUser:
    """Extract current user UUID from Bearer access token, raising 401 on problems."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    sub = payload.get("sub")
    try:
        user_id = UUID(str(sub))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return _TokenUser(sub=user_id)


# Request/Response Schemas

# PUBLIC_INTERFACE
class UserPublic(UserRead):
    """Public view of a user profile."""
    # In future we could hide fields here; currently reusing UserRead for simplicity.


# PUBLIC_INTERFACE
class UserProfileUpdate(BaseModel):
    """Payload to update current user's profile."""
    username: Optional[str] = Field(default=None, min_length=3, max_length=50, description="New username")
    full_name: Optional[str] = Field(default=None, description="Full name")
    bio: Optional[str] = Field(default=None, description="Short user bio")  # Stub: not persisted yet
    region_id: Optional[UUID] = Field(default=None, description="Preferred region id")  # Stub: not persisted yet
    avatar_url: Optional[str] = Field(default=None, description="URL to avatar image")  # Stub: not persisted yet


# Routes

# PUBLIC_INTERFACE
@router.get(
    "/{id}",
    response_model=UserPublic,
    summary="Get user by id",
    description="Public endpoint to fetch a user profile by its UUID.",
    responses={
        200: {"description": "User found"},
        404: {"description": "User not found"},
    },
)
def get_user_by_id(id: UUID, db: Session = Depends(db_session)) -> UserPublic:
    """Return a public user profile by UUID.

    Parameters:
    - id: UUID of the user.

    Returns:
    - UserPublic: Public user profile.
    """
    user = db.get(User, id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserPublic.model_validate(user)


# PUBLIC_INTERFACE
@router.patch(
    "/me",
    response_model=UserPublic,
    summary="Update current user's profile",
    description=(
        "Authenticated endpoint to update selected profile fields. "
        "Currently supports updating username and full_name in the database. "
        "Fields bio, region_id, and avatar_url are accepted but not persisted yet (stubs)."
    ),
    responses={
        200: {"description": "Profile updated"},
        400: {"description": "Invalid input or username already taken"},
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
    },
)
def update_me(
    payload: UserProfileUpdate,
    token_user: _TokenUser = Depends(_get_current_user_id),
    db: Session = Depends(db_session),
) -> UserPublic:
    """Update the current authenticated user's profile.

    Parameters:
    - payload: UserProfileUpdate with optional fields.
    - Authorization: Bearer access token.

    Returns:
    - UserPublic: Updated user profile.
    """
    user = db.get(User, token_user.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Enforce ownership: token subject must match user being updated (already ensured by selecting by sub)
    # Handle username uniqueness if changed
    if payload.username and payload.username != user.username:
        # Check if username exists
        from sqlalchemy import select  # local import to avoid polluting module namespace
        existing = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
        user.username = payload.username

    if payload.full_name is not None:
        user.full_name = payload.full_name

    # Stubs accepted but not stored yet
    # payload.bio, payload.region_id, payload.avatar_url

    db.add(user)
    db.flush()
    db.refresh(user)
    return UserPublic.model_validate(user)


# PUBLIC_INTERFACE
@router.post(
    "/me/avatar",
    summary="Upload avatar (stub)",
    description=(
        "Upload an avatar image for the current user. "
        "This is a stub endpoint that accepts a file but does not store it. "
        "Future implementation will persist to configured storage and update avatar_url."
    ),
    responses={
        200: {"description": "Avatar uploaded (stub)"},
        400: {"description": "Invalid file"},
        401: {"description": "Not authenticated"},
    },
)
def upload_avatar_stub(
    file: UploadFile = File(...),
    token_user: _TokenUser = Depends(_get_current_user_id),
) -> dict:
    """Accept an avatar file for the current user. Currently a no-op stub.

    Parameters:
    - file: UploadFile image content.
    - Authorization: Bearer access token.

    Returns:
    - dict: Status and filename acknowledging receipt.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")
    # In a future iteration, validate content-type, store to storage provider, update user's avatar_url.
    return {"status": "ok", "filename": file.filename, "note": "Avatar upload is a stub and not persisted yet."}
