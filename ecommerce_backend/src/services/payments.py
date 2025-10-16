from __future__ import annotations

import hmac
import json
import os
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Dict, Optional, Tuple

from src.core.config import get_settings

try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None  # Stripe optional; we handle gracefully


@dataclass
class PaymentIntentResult:
    """Result of creating a payment intent."""
    provider: str
    payment_intent_id: str
    client_secret: Optional[str]
    amount_cents: int
    currency: str
    is_mock: bool = False


# PUBLIC_INTERFACE
def create_payment_intent(amount_cents: int, currency: str = "usd", metadata: Optional[Dict[str, Any]] = None) -> PaymentIntentResult:
    """Create a payment intent with the configured provider.

    Will use Stripe if STRIPE_SECRET_KEY is set and stripe lib is available.
    Otherwise, returns a mock intent suitable for local/testing.

    Parameters:
    - amount_cents: integer amount in cents (e.g., 1299 = $12.99)
    - currency: ISO currency code, defaults to "usd"
    - metadata: additional provider metadata

    Returns:
    - PaymentIntentResult: info including provider id and client_secret (when available)
    """
    settings = get_settings()
    provider = (settings.PAYMENT_PROVIDER or "stripe").lower()

    # If we have Stripe configuration and library, use it
    if provider == "stripe" and stripe is not None and settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        meta = metadata or {}
        intent = stripe.PaymentIntent.create(
            amount=int(amount_cents),
            currency=currency,
            metadata=meta,
            automatic_payment_methods={"enabled": True},
        )
        return PaymentIntentResult(
            provider="stripe",
            payment_intent_id=intent.get("id"),
            client_secret=intent.get("client_secret"),
            amount_cents=int(intent.get("amount")),
            currency=intent.get("currency"),
            is_mock=False,
        )

    # Fallback mock intent (test mode)
    mock_id = f"pi_mock_{abs(hash((amount_cents, currency, json.dumps(metadata or {}, sort_keys=True)))) % 10_000_000}"
    client_secret = f"{mock_id}_secret_mock"
    return PaymentIntentResult(
        provider=provider or "mock",
        payment_intent_id=mock_id,
        client_secret=client_secret,
        amount_cents=int(amount_cents),
        currency=currency,
        is_mock=True,
    )


# PUBLIC_INTERFACE
def verify_webhook(raw_body: bytes, signature: str | None) -> Tuple[bool, Dict[str, Any]]:
    """Verify and parse a payment webhook payload.

    For Stripe:
      - If STRIPE_WEBHOOK_SECRET and stripe installed, verify signature using stripe.Webhook.
      - If missing secret or library, accept payload in TEST MODE (unverified).

    For mock mode:
      - Accept the payload as-is and return parsed JSON if possible.

    Parameters:
    - raw_body: raw request body bytes
    - signature: signature header (e.g., Stripe-Signature)

    Returns:
    - (verified, event_dict): verified indicates cryptographic verification succeeded;
      event_dict contains at least "type" and "data" keys for downstream processing.
    """
    settings = get_settings()
    provider = (settings.PAYMENT_PROVIDER or "stripe").lower()

    # Stripe verification path
    if provider == "stripe":
        payload = raw_body.decode("utf-8") if isinstance(raw_body, (bytes, bytearray)) else str(raw_body)
        # If fully configured and library available -> verify cryptographically
        if stripe is not None and settings.STRIPE_WEBHOOK_SECRET:
            try:
                event = stripe.Webhook.construct_event(payload=payload, sig_header=signature or "", secret=settings.STRIPE_WEBHOOK_SECRET)
                # Convert to plain dict
                event_dict = event if isinstance(event, dict) else getattr(event, "to_dict", lambda: json.loads(json.dumps(event, default=str)))()
                return True, event_dict
            except Exception:
                # Invalid signature or parse error
                try:
                    parsed = json.loads(payload)
                except Exception:
                    parsed = {"raw": payload}
                return False, parsed

        # Test mode: accept unverified payload but mark unverified
        try:
            parsed = json.loads(payload)
        except Exception:
            parsed = {"raw": payload}
        return False, parsed

    # Generic/mock provider: attempt to parse JSON and simulate verification using a weak HMAC if signature set
    body = raw_body if isinstance(raw_body, (bytes, bytearray)) else str(raw_body).encode("utf-8")
    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception:
        parsed = {"raw": body.decode("utf-8", errors="ignore")}
    # If an env MOCK_WEBHOOK_SECRET exists, simulate HMAC check
    mock_secret = os.getenv("MOCK_WEBHOOK_SECRET")
    if mock_secret and signature:
        digest = hmac.new(mock_secret.encode("utf-8"), msg=body, digestmod=sha256).hexdigest()
        return hmac.compare_digest(digest, signature), parsed
    # Otherwise unverified but accepted in test mode
    return False, parsed
