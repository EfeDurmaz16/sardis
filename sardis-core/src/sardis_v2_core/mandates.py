"""Typed AP2 mandate models reused by adapters and SDKs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Sequence

from pydantic import BaseModel

MandateType = Literal["intent", "cart", "payment"]


class VCProof(BaseModel):
    type: Literal["DataIntegrityProof"] = "DataIntegrityProof"
    verification_method: str
    created: str
    proof_purpose: str = "assertionMethod"
    proof_value: str


@dataclass(slots=True)
class MandateBase:
    mandate_id: str
    mandate_type: MandateType
    issuer: str
    subject: str
    expires_at: int
    nonce: str
    proof: VCProof
    domain: str
    purpose: Literal["intent", "browsing", "cart", "checkout"]

    def is_expired(self) -> bool:
        return self.expires_at <= int(time.time())


@dataclass(slots=True)
class IntentMandate(MandateBase):
    scope: Sequence[str] = field(default_factory=list)
    requested_amount: int | None = None  # in minor units (e.g., cents)


@dataclass(slots=True)
class CartMandate(MandateBase):
    line_items: Sequence[dict]
    merchant_domain: str
    currency: str
    subtotal_minor: int
    taxes_minor: int


@dataclass(slots=True)
class PaymentMandate(MandateBase):
    chain: str
    token: str
    amount_minor: int
    destination: str
    audit_hash: str


@dataclass(slots=True)
class MandateChain:
    """Verified AP2 mandate chain linking Intent -> Cart -> Payment."""

    intent: IntentMandate
    cart: CartMandate
    payment: PaymentMandate


__all__ = [
    "IntentMandate",
    "CartMandate",
    "PaymentMandate",
    "VCProof",
    "MandateChain",
]
