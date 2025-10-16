from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from src.core.security import decode_token
from src.deps import db_session
from src.models import Listing, Swap, User
from src.models.enums import SwapStatus
from src.schemas.swap import SwapRead

router = APIRouter(prefix="/swaps", tags=["swaps"])


class _TokenUser(BaseModel):
    """Internal helper schema to represent token-authenticated user identity for swaps."""
    sub: UUID


def _auth_user(authorization: str | None = Header(default=None)) -> _TokenUser:
    """Extract current user UUID from Bearer access token, raising 401 on problems."""
    from uuid import UUID as _UUID
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
        user_id = _UUID(str(sub))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return _TokenUser(sub=user_id)


# Request payloads

class SwapCreatePayload(BaseModel):
    """Payload for creating a swap between two listings and users."""
    proposer_listing_id: UUID = Field(..., description="Listing owned by proposer (current user)")
    recipient_listing_id: UUID = Field(..., description="Listing owned by the recipient user")
    notes: Optional[str] = Field(default=None, description="Optional note for the proposal")


def _validate_swap_parties(db: Session, proposer_id: UUID, proposer_listing_id: UUID, recipient_listing_id: UUID) -> tuple[Listing, Listing, User, User]:
    """Validate listings exist and are owned by the appropriate users.

    Returns:
    - proposer_listing, recipient_listing, proposer_user, recipient_user
    """
    proposer_listing = db.get(Listing, proposer_listing_id)
    if not proposer_listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposer listing not found")
    recipient_listing = db.get(Listing, recipient_listing_id)
    if not recipient_listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient listing not found")
    if proposer_listing.seller_id != proposer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must own the proposer listing")
    if recipient_listing.seller_id == proposer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot propose swap with your own listing")

    proposer_user = db.get(User, proposer_id)
    if not proposer_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposer user not found")
    recipient_user = db.get(User, recipient_listing.seller_id)
    if not recipient_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient user not found")

    return proposer_listing, recipient_listing, proposer_user, recipient_user


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=SwapRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a swap proposal",
    description="Create a swap where the current user (initiator) proposes to swap their listing with another user's listing.",
    responses={
        201: {"description": "Swap proposal created"},
        400: {"description": "Invalid state or attempting to swap with self"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - ownership violation"},
        404: {"description": "Listing or user not found"},
    },
)
def create_swap(
    payload: SwapCreatePayload,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> SwapRead:
    """Create a swap proposal ensuring ownership and valid counterparties."""
    proposer_listing, recipient_listing, _proposer_user, recipient_user = _validate_swap_parties(
        db, token_user.sub, payload.proposer_listing_id, payload.recipient_listing_id
    )

    # We store swap on the recipient's listing to let them manage decision on their item
    swap = Swap(
        listing_id=recipient_listing.id,
        initiator_id=token_user.sub,
        counterparty_id=recipient_user.id,
        status=SwapStatus.proposed,
        notes=(payload.notes or ""),
    )
    db.add(swap)
    db.flush()
    db.refresh(swap)
    return SwapRead.model_validate(swap)


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[SwapRead],
    summary="List swaps",
    description=(
        "List swaps with optional filters.\n"
        "Query params:\n"
        "- mine: if true, show swaps where you are initiator or counterparty\n"
        "- status: filter by swap status"
    ),
    responses={
        200: {"description": "List of swaps"},
        401: {"description": "Not authenticated when using mine=true"},
    },
)
def list_swaps(
    mine: bool = Query(default=False, description="Show only swaps involving me"),
    status: Optional[SwapStatus] = Query(default=None, description="Filter by status"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(db_session),
) -> List[SwapRead]:
    """Return swaps filtered by ownership and status."""
    stmt = select(Swap)
    filters = []
    if status is not None:
        filters.append(Swap.status == status)

    if mine:
        token_user = _auth_user(authorization=authorization)
        # Involve swaps where user is initiator or counterparty
        filters.append(or_(Swap.initiator_id == token_user.sub, Swap.counterparty_id == token_user.sub))

    if filters:
        stmt = stmt.where(and_(*filters))
    from sqlalchemy import desc
    stmt = stmt.order_by(desc(Swap.created_at))

    results = db.scalars(stmt).all()
    return [SwapRead.model_validate(r) for r in results]


# PUBLIC_INTERFACE
@router.get(
    "/{id}",
    response_model=SwapRead,
    summary="Get swap by id",
    description="Fetch a swap by UUID. Only the initiator or counterparty can view.",
    responses={
        200: {"description": "Swap found"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Swap not found"},
    },
)
def get_swap(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> SwapRead:
    """Return a swap if current user is initiator or counterparty."""
    swap = db.get(Swap, id)
    if not swap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap not found")
    if token_user.sub not in (swap.initiator_id, swap.counterparty_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view swap")
    return SwapRead.model_validate(swap)


def _ensure_can_decide_swap(swap: Swap, token_user: _TokenUser) -> None:
    """Ensure only the counterparty can accept/decline the swap."""
    if token_user.sub != swap.counterparty_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the recipient can decide this swap")
    if swap.status != SwapStatus.proposed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only proposed swaps can be decided")


# PUBLIC_INTERFACE
@router.post(
    "/{id}/accept",
    response_model=SwapRead,
    summary="Accept a swap proposal",
    description="Counterparty accepts a proposed swap.",
    responses={
        200: {"description": "Swap accepted"},
        400: {"description": "Invalid status transition"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - only counterparty can accept"},
        404: {"description": "Swap not found"},
    },
)
def accept_swap(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> SwapRead:
    """Accept a swap; only the counterparty can accept a proposed swap."""
    swap = db.get(Swap, id)
    if not swap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap not found")
    _ensure_can_decide_swap(swap, token_user)

    swap.status = SwapStatus.accepted
    db.add(swap)
    db.flush()
    db.refresh(swap)
    return SwapRead.model_validate(swap)


# PUBLIC_INTERFACE
@router.post(
    "/{id}/decline",
    response_model=SwapRead,
    summary="Decline a swap proposal",
    description="Counterparty declines a proposed swap.",
    responses={
        200: {"description": "Swap declined"},
        400: {"description": "Invalid status transition"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - only counterparty can decline"},
        404: {"description": "Swap not found"},
    },
)
def decline_swap(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> SwapRead:
    """Decline a swap; only the counterparty can decline a proposed swap."""
    swap = db.get(Swap, id)
    if not swap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap not found")
    _ensure_can_decide_swap(swap, token_user)

    swap.status = SwapStatus.rejected
    db.add(swap)
    db.flush()
    db.refresh(swap)
    return SwapRead.model_validate(swap)
