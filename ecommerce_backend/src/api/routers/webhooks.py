from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.deps import db_session
from src.models import Transaction
from src.models.enums import TransactionStatus
from src.services.payments import verify_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookAck(BaseModel):
    """Acknowledgement payload for webhook processing."""
    received: bool = Field(..., description="Whether the webhook was received and processed")
    verified: bool = Field(..., description="Whether the webhook payload signature was verified")
    action: Optional[str] = Field(default=None, description="Action/status applied to the transaction")
    transaction_id: Optional[str] = Field(default=None, description="Transaction UUID affected (if any)")
    note: Optional[str] = Field(default=None, description="Additional notes")


def _map_stripe_event_to_status(event: Dict[str, Any]) -> tuple[Optional[str], Optional[TransactionStatus]]:
    """Map incoming Stripe-like event types to TransactionStatus."""
    etype = str(event.get("type") or "")
    data = event.get("data", {}) or {}
    obj = data.get("object", {}) if isinstance(data, dict) else {}

    intent_id = obj.get("id") or obj.get("payment_intent")
    mapped_status: Optional[TransactionStatus] = None
    if etype in ("payment_intent.succeeded",):
        mapped_status = TransactionStatus.succeeded
    elif etype in ("payment_intent.payment_failed", "charge.failed"):
        mapped_status = TransactionStatus.failed
    elif etype in ("charge.refunded", "charge.refund.updated"):
        mapped_status = TransactionStatus.refunded
    # Return provider payment intent id and mapped status
    return (intent_id, mapped_status)


# PUBLIC_INTERFACE
@router.post(
    "/payments",
    response_model=WebhookAck,
    summary="Payment provider webhook",
    description=(
        "Endpoint for payment provider webhooks (Stripe or mock). "
        "Verifies signature when possible and updates Transaction status based on the event."
    ),
    responses={
        200: {"description": "Webhook processed"},
        400: {"description": "Invalid payload"},
    },
)
async def payments_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(db_session),
) -> WebhookAck:
    """Handle payment webhooks and update Transaction records accordingly.

    Expected events (Stripe-like):
    - payment_intent.succeeded -> TransactionStatus.succeeded
    - payment_intent.payment_failed or charge.failed -> TransactionStatus.failed
    - charge.refunded -> TransactionStatus.refunded
    """
    raw = await request.body()
    verified, event = verify_webhook(raw_body=raw, signature=stripe_signature)

    # Try to map to a transaction via provider_payment_intent_id
    pi_id, new_status = _map_stripe_event_to_status(event)

    action = None
    txn_affected: Optional[Transaction] = None

    if pi_id:
        txn_affected = db.scalar(select(Transaction).where(Transaction.provider_payment_intent_id == pi_id))
        if txn_affected and new_status:
            txn_affected.status = new_status
            db.add(txn_affected)
            db.flush()
            action = f"set_status_{new_status.value}"
        elif txn_affected:
            action = "no_status_change"
        else:
            action = "transaction_not_found"

    return WebhookAck(
        received=True,
        verified=verified,
        action=action,
        transaction_id=str(txn_affected.id) if txn_affected else None,
        note="Processed webhook event",
    )
