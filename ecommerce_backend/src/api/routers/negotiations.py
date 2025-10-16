from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.core.security import decode_token
from src.deps import db_session
from src.models import Listing, Offer, Negotiation
from src.models.enums import NegotiationStatus, OfferStatus
from src.schemas.negotiation import NegotiationRead

router = APIRouter(prefix="/offers", tags=["negotiations"])


class _TokenUser(BaseModel):
    """Internal helper schema to represent token-authenticated user identity for negotiations."""
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


class NegotiationPostPayload(BaseModel):
    """Payload to post into a negotiation thread - message and/or counter offer."""
    message: Optional[str] = Field(default=None, description="Message content")
    counter_amount: Optional[float] = Field(default=None, description="Optional counter offer amount")


def _get_offer_and_listing(db: Session, offer_id: UUID) -> tuple[Offer, Listing]:
    offer = db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    listing = db.get(Listing, offer.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return offer, listing


def _ensure_party(offer: Offer, listing: Listing, user_id: UUID) -> None:
    if user_id not in (offer.buyer_id, listing.seller_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this negotiation")


# PUBLIC_INTERFACE
@router.get(
    "/{id}/negotiations",
    response_model=List[NegotiationRead],
    summary="Get negotiations for offer",
    description="Returns the single negotiation session for an offer if exists.",
    responses={
        200: {"description": "Negotiations returned"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Offer not found"},
    },
)
def get_negotiations_for_offer(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> List[NegotiationRead]:
    """Return the negotiation tied to an offer if the requester is a party."""
    offer, listing = _get_offer_and_listing(db, id)
    _ensure_party(offer, listing, token_user.sub)

    if offer.negotiation:
        return [NegotiationRead.model_validate(offer.negotiation)]
    return []


# PUBLIC_INTERFACE
@router.post(
    "/{id}/negotiations",
    response_model=NegotiationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Post negotiation update",
    description="Post a message and/or counter into the negotiation thread for an offer.",
    responses={
        201: {"description": "Negotiation entry posted"},
        400: {"description": "Invalid state or payload"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Offer not found"},
    },
)
def post_negotiation_for_offer(
    id: UUID,
    payload: NegotiationPostPayload,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> NegotiationRead:
    """Create or update the negotiation associated with an offer by posting a message and optionally a counter."""
    offer, listing = _get_offer_and_listing(db, id)
    _ensure_party(offer, listing, token_user.sub)

    if offer.status != OfferStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer is not negotiable in current status")

    note_parts: list[str] = []
    if payload.message:
        note_parts.append(payload.message.strip())
    if payload.counter_amount is not None:
        if payload.counter_amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Counter must be > 0")
        # Allow either party to counter; keep status pending
        offer.amount = payload.counter_amount
        db.add(offer)
        note_parts.append(f"Countered to {offer.amount}")

    if not note_parts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide message or counter_amount")

    if offer.negotiation:
        neg = offer.negotiation
        neg.status = NegotiationStatus.open
        neg.last_message = " | ".join(note_parts)
    else:
        neg = Negotiation(
            offer_id=offer.id,
            listing_id=listing.id,
            status=NegotiationStatus.open,
            last_message=" | ".join(note_parts),
        )
        db.add(neg)

    db.flush()
    db.refresh(neg)
    return NegotiationRead.model_validate(neg)
