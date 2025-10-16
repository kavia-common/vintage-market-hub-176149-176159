from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.security import decode_token
from src.deps import db_session
from src.models import Listing, Transaction
from src.models.enums import TransactionStatus
from src.schemas.transaction import TransactionRead
from src.services.payments import create_payment_intent

router = APIRouter(prefix="/transactions", tags=["transactions"])


class _TokenUser(BaseModel):
    """Internal helper schema to represent token-authenticated user identity for transactions."""
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


class CheckoutRequest(BaseModel):
    """Request schema for initiating a checkout/payment intent."""
    listing_id: Optional[UUID] = Field(default=None, description="Listing being purchased (optional)")
    amount: Decimal = Field(..., description="Total amount for the transaction")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency (ISO code)")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata to attach to payment intent")


class CheckoutResponse(BaseModel):
    """Response schema for checkout containing provider info and Transaction read model."""
    provider: str = Field(..., description="Payment provider used")
    client_secret: Optional[str] = Field(default=None, description="Client secret for payment confirmation (if applicable)")
    payment_intent_id: str = Field(..., description="Provider payment intent identifier")
    transaction: TransactionRead


# PUBLIC_INTERFACE
@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create a payment intent and Transaction",
    description=(
        "Initiate a checkout by creating a payment intent with the configured provider (Stripe if configured, "
        "else mock). Persists a Transaction with status 'pending' and returns client_secret if available."
    ),
    responses={
        200: {"description": "Payment intent created"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        404: {"description": "Listing not found"},
    },
)
def checkout(
    payload: CheckoutRequest,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> CheckoutResponse:
    """Create a provider payment intent and persist a Transaction record."""
    # Optional listing validation
    listing_obj: Optional[Listing] = None
    if payload.listing_id:
        listing_obj = db.get(Listing, payload.listing_id)
        if not listing_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than 0")

    # Convert Decimal dollars to cents (or assume cents provided logically)
    amount_cents = int(Decimal(payload.amount) * 100)

    # Create provider payment intent
    meta = payload.metadata or {}
    if listing_obj:
        meta.setdefault("listing_id", str(listing_obj.id))
    meta.setdefault("buyer_id", str(token_user.sub))

    intent = create_payment_intent(amount_cents=amount_cents, currency=payload.currency.lower(), metadata=meta)

    # Persist Transaction
    settings = get_settings()
    txn = Transaction(
        amount=payload.amount,
        currency=payload.currency.upper(),
        status=TransactionStatus.pending,
        provider=(settings.PAYMENT_PROVIDER or "stripe").lower(),
        provider_payment_intent_id=intent.payment_intent_id,
        listing_id=listing_obj.id if listing_obj else None,
        buyer_id=token_user.sub,
    )
    db.add(txn)
    db.flush()
    db.refresh(txn)

    return CheckoutResponse(
        provider=intent.provider,
        client_secret=intent.client_secret,
        payment_intent_id=intent.payment_intent_id,
        transaction=TransactionRead.model_validate(txn),
    )


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[TransactionRead],
    summary="List transactions",
    description=(
        "List transactions with optional filters. "
        "Query params: mine=true (only my transactions), status, listing_id"
    ),
    responses={200: {"description": "List of transactions"}},
)
def list_transactions(
    mine: bool = Query(default=False, description="Show only current user's transactions"),
    status: Optional[TransactionStatus] = Query(default=None, description="Filter by transaction status"),
    listing_id: Optional[UUID] = Query(default=None, description="Filter by listing id"),
    authorization: str | None = Header(default=None),
    db: Session = Depends(db_session),
) -> List[TransactionRead]:
    """Return transactions filtered by ownership and status."""
    stmt = select(Transaction)
    filters = []
    if status is not None:
        filters.append(Transaction.status == status)
    if listing_id is not None:
        filters.append(Transaction.listing_id == listing_id)
    if mine:
        token_user = _auth_user(authorization=authorization)
        filters.append(Transaction.buyer_id == token_user.sub)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.order_by(desc(Transaction.created_at))
    results = db.scalars(stmt).all()
    return [TransactionRead.model_validate(r) for r in results]


# PUBLIC_INTERFACE
@router.get(
    "/{id}",
    response_model=TransactionRead,
    summary="Get transaction by id",
    description="Fetch a transaction by UUID. Only buyer can view their transaction.",
    responses={
        200: {"description": "Transaction found"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Transaction not found"},
    },
)
def get_transaction(
    id: UUID,
    token_user: _TokenUser = Depends(_auth_user),
    db: Session = Depends(db_session),
) -> TransactionRead:
    """Return a transaction if the current user is the buyer."""
    txn = db.get(Transaction, id)
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if txn.buyer_id != token_user.sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view transaction")
    return TransactionRead.model_validate(txn)
