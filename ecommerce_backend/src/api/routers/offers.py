from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from src.core.security import decode_token
from src.deps import db_session
from src.models import Listing, Offer, Negotiation
from src.models.enums import OfferStatus, NegotiationStatus
from src.schemas.offer import OfferRead

router = APIRouter(prefix="/offers", tags=["offers"])


class _TokenUser(BaseModel):
    """Internal helper schema to represent token-authenticated user identity for offers endpoints."""
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


# Request payloads for create/counter actions

class OfferCreatePayload(BaseModel):
    """Payload for creating an offer on a listing."""
    amount: Decimal = Field(..., description="Offer amount")


class OfferCounterPayload(BaseModel):
    """Payload for countering an existing offer (by seller)."""
    amount: Decimal = Field(..., description="Counter offer amount")


def _ensure_listing_active(listing: Listing) -> None:
    """Ensure listing is active for offers (basic guard)."""
    # We don't import ListingStatus here to avoid unused if status isn't enforced; model default is active.
    if getattr(listing, "status", None) and str(listing.status) not in ("active",):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create offer on inactive listing")


# PUBLIC_INTERFACE
@router.post(
    "/listings/{id}/offers",
    status_code=status.HTTP_201_CREATED,
    response_model=OfferRead,
    summary="Create offer on listing",
    description="Create a new offer for the specified listing as the authenticated buyer.",
    responses={
        201: {"description": "Offer created"},
        400: {"description": "Invalid input or listing not active"},
        401: {"description": "Not authenticated"},
        403: {"description": "Cannot offer on your own listing"},
        404: {"description": "Listing not found"},
    },
)
def create_offer_for_listing(
    id: UUID,
    payload: OfferCreatePayload,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> OfferRead:
    """Create a pending offer for a listing by the current user."""
    listing = db.get(Listing, id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.seller_id == token_user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create offer on your own listing")

    _ensure_listing_active(listing)

    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than 0")

    offer = Offer(amount=payload.amount, listing_id=listing.id, buyer_id=token_user.sub, status=OfferStatus.pending)
    db.add(offer)
    db.flush()
    # Ensure there is a negotiation channel for this offer
    if not offer.negotiation:
        neg = Negotiation(
            offer_id=offer.id,
            listing_id=listing.id,
            status=NegotiationStatus.open,
            last_message=f"Offer created at {offer.amount}",
        )
        db.add(neg)
    db.flush()
    db.refresh(offer)
    return OfferRead.model_validate(offer)


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[OfferRead],
    summary="List offers",
    description=(
        "List offers with optional filters. Query params:\n"
        "- status: filter by offer status\n"
        "- listing_id: filter by listing\n"
        "- mine: if true, restrict to offers where current user is buyer or seller of the listing"
    ),
    responses={
        200: {"description": "List of offers"},
        401: {"description": "Not authenticated when using mine=true"},
    },
)
def list_offers(
    status: Optional[OfferStatus] = Query(default=None),
    listing_id: Optional[UUID] = Query(default=None),
    mine: bool = Query(default=False, description="Show only offers related to me"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(db_session),
) -> List[OfferRead]:
    """Return offers filtered by status, listing and ownership."""
    stmt = select(Offer)

    filters = []
    if status is not None:
        filters.append(Offer.status == status)
    if listing_id is not None:
        filters.append(Offer.listing_id == listing_id)

    # Ownership filter requires auth; include offers where user is buyer or listing's seller.
    if mine:
        token_user = _auth_user(authorization=authorization)  # Reuse auth helper
        # Join-less filter using OR conditions via subqueries
        # Buyer-owned
        own_buyer = Offer.buyer_id == token_user.sub
        # Seller-owned (via listing seller_id)
        # Build exists condition by joining listing in where
        from sqlalchemy.orm import aliased
        L = aliased(Listing)
        # SQLAlchemy 2.0: filter with correlated subquery OR join
        # Simpler: include offers whose listing has seller_id = me
        # We'll add a join
        stmt = stmt.join(L, L.id == Offer.listing_id)
        filters.append(or_(own_buyer, L.seller_id == token_user.sub))

    if filters:
        stmt = stmt.where(and_(*filters))

    # Order newest first
    from sqlalchemy import desc
    stmt = stmt.order_by(desc(Offer.created_at))

    results = db.scalars(stmt).all()
    return [OfferRead.model_validate(r) for r in results]


# PUBLIC_INTERFACE
@router.get(
    "/{id}",
    response_model=OfferRead,
    summary="Get offer by id",
    description="Fetch an offer by UUID. Buyer or listing seller can view.",
    responses={
        200: {"description": "Offer found"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Offer not found"},
    },
)
def get_offer(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> OfferRead:
    """Return offer if current user is buyer or listing's seller."""
    offer = db.get(Offer, id)
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    listing = db.get(Listing, offer.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    if offer.buyer_id != token_user.sub and listing.seller_id != token_user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view offer")

    return OfferRead.model_validate(offer)


def _ensure_can_modify_offer_as_seller(offer: Offer, token_user: _TokenUser, db: Session) -> Listing:
    listing = db.get(Listing, offer.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.seller_id != token_user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the seller can perform this action")
    if offer.status in (OfferStatus.accepted, OfferStatus.rejected, OfferStatus.withdrawn, OfferStatus.expired):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offer is not modifiable in current status")
    return listing


# PUBLIC_INTERFACE
@router.post(
    "/{id}/counter",
    response_model=OfferRead,
    summary="Counter an offer (seller)",
    description="Seller counters a pending offer by updating the amount and keeping status pending.",
    responses={
        200: {"description": "Offer countered"},
        400: {"description": "Invalid amount or status transition"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - only seller can counter"},
        404: {"description": "Offer not found"},
    },
)
def counter_offer(
    id: UUID,
    payload: OfferCounterPayload,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> OfferRead:
    """Counter a pending offer as the listing's seller by setting a new amount."""
    offer = db.get(Offer, id)
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    listing = _ensure_can_modify_offer_as_seller(offer, token_user, db)

    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than 0")

    offer.amount = payload.amount
    # Status remains pending to allow buyer to accept/decline the counter
    db.add(offer)
    # Update/create a negotiation note
    if offer.negotiation:
        offer.negotiation.last_message = f"Seller countered to {offer.amount}"
    else:
        neg = Negotiation(
            offer_id=offer.id,
            listing_id=listing.id,
            status=NegotiationStatus.open,
            last_message=f"Seller countered to {offer.amount}",
        )
        db.add(neg)
    db.flush()
    db.refresh(offer)
    return OfferRead.model_validate(offer)


# PUBLIC_INTERFACE
@router.post(
    "/{id}/accept",
    response_model=OfferRead,
    summary="Accept an offer",
    description="Accept an offer. Seller may accept a buyer's pending offer; buyer may accept a seller counter if still pending.",
    responses={
        200: {"description": "Offer accepted"},
        400: {"description": "Invalid status transition"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Offer not found"},
    },
)
def accept_offer(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> OfferRead:
    """Accept a pending offer; allowed for seller or buyer depending on negotiation context."""
    offer = db.get(Offer, id)
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    listing = db.get(Listing, offer.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    # Only parties involved can accept: seller or buyer
    if token_user.sub not in (offer.buyer_id, listing.seller_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this offer")

    if offer.status != OfferStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending offers can be accepted")

    # Set accepted
    offer.status = OfferStatus.accepted
    # Close negotiation if exists
    if offer.negotiation:
        offer.negotiation.status = NegotiationStatus.closed
        offer.negotiation.last_message = "Offer accepted"

    db.add(offer)
    db.flush()
    db.refresh(offer)
    return OfferRead.model_validate(offer)


# PUBLIC_INTERFACE
@router.post(
    "/{id}/decline",
    response_model=OfferRead,
    summary="Decline an offer",
    description="Decline an offer. Either party may decline while pending.",
    responses={
        200: {"description": "Offer declined"},
        400: {"description": "Invalid status transition"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Offer not found"},
    },
)
def decline_offer(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> OfferRead:
    """Decline a pending offer; allowed for either party (buyer or seller)."""
    offer = db.get(Offer, id)
    if not offer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

    listing = db.get(Listing, offer.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    if token_user.sub not in (offer.buyer_id, listing.seller_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this offer")

    if offer.status != OfferStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending offers can be declined")

    offer.status = OfferStatus.rejected
    if offer.negotiation:
        offer.negotiation.status = NegotiationStatus.closed
        offer.negotiation.last_message = "Offer declined"

    db.add(offer)
    db.flush()
    db.refresh(offer)
    return OfferRead.model_validate(offer)
