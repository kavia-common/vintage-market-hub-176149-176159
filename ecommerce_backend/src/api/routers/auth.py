from __future__ import annotations

from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.deps import db_session
from src.models import User
from src.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response schemas for auth
class TokenPair(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="User password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


# PUBLIC_INTERFACE
@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, username, full_name, and password.",
    responses={
        201: {"description": "User created"},
        400: {"description": "Email or username already registered"},
    },
)
def register_user(payload: UserCreate, db: Session = Depends(db_session)) -> UserRead:
    """Register a new user.

    Validates uniqueness of email and username, hashes the password using bcrypt,
    and stores the new user in the database.

    Parameters:
    - payload: UserCreate with email, username, password, and optional full_name.

    Returns:
    - UserRead: Created user details (without password).
    """
    # Check if email or username already taken
    existing_email = db.scalar(select(User).where(User.email == payload.email))
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    existing_username = db.scalar(select(User).where(User.username == payload.username))
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    hashed = get_password_hash(payload.password)
    user = User(email=payload.email, username=payload.username, full_name=payload.full_name, hashed_password=hashed)
    db.add(user)
    db.flush()  # assign id
    db.refresh(user)

    return UserRead.model_validate(user)


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login and obtain tokens",
    description="Authenticate with email and password to receive access and refresh tokens.",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid email or password"},
    },
)
def login(payload: LoginRequest, db: Session = Depends(db_session)) -> TokenPair:
    """Authenticate user and issue JWT tokens.

    Parameters:
    - payload: LoginRequest with email and password.

    Returns:
    - TokenPair: access_token and refresh_token.
    """
    settings = get_settings()
    user: Optional[User] = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Optional: check active flag
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    access = create_access_token(subject=str(user.id), expires_delta=access_expires, additional_claims={"email": user.email})
    refresh = create_refresh_token(subject=str(user.id), expires_delta=refresh_expires)

    return TokenPair(access_token=access, refresh_token=refresh)


# PUBLIC_INTERFACE
@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Refresh tokens",
    description="Exchange a valid refresh token for a new access and refresh token pair.",
    responses={
        200: {"description": "Token refresh successful"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
def refresh_tokens(body: RefreshRequest) -> TokenPair:
    """Refresh the JWT token pair using a refresh token.

    Parameters:
    - body: RefreshRequest containing a refresh_token.

    Returns:
    - TokenPair: New access and refresh tokens.
    """
    settings = get_settings()
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    new_access = create_access_token(subject=sub, expires_delta=access_expires)
    new_refresh = create_refresh_token(subject=sub, expires_delta=refresh_expires)

    return TokenPair(access_token=new_access, refresh_token=new_refresh)


# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user",
    description="Return the current authenticated user's profile using the Authorization Bearer access token.",
    responses={
        200: {"description": "Current user returned"},
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
    },
)
def read_me(
    authorization: str | None = Header(default=None),
    db: Session = Depends(db_session),
) -> UserRead:
    """Return the current user derived from the Bearer access token.

    Parameters:
    - Authorization header: 'Bearer <access_token>'

    Returns:
    - UserRead: Current user profile.
    """
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
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Find the user by UUID subject
    try:
        user_id = UUID(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserRead.model_validate(user)
