"""Domain enumerations for statuses and types."""
from __future__ import annotations

import enum


class ListingStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    sold = "sold"
    archived = "archived"


class OfferStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"
    expired = "expired"


class NegotiationStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    cancelled = "cancelled"


class SwapStatus(str, enum.Enum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"
    completed = "completed"
    cancelled = "cancelled"


class TransactionStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"
