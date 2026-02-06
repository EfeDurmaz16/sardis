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
    # AP2 ecosystem visibility signals:
    # - agent presence should always be explicit
    # - modality distinguishes human-present vs human-not-present flows
    ai_agent_presence: bool = True
    transaction_modality: Literal["human_present", "human_not_present"] = "human_present"
    # Execution-only hint (not part of AP2 signature payload).
    # When present, chain executors should use this to select the signing wallet.
    wallet_id: str | None = None
    # Merchant domain binding (distinct from identity `domain`).
    # In AP2, this should match the CartMandate.merchant_domain.
    merchant_domain: str | None = None


@dataclass(slots=True)
class MandateChain:
    """Verified AP2 mandate chain linking Intent -> Cart -> Payment."""

    intent: IntentMandate
    cart: CartMandate
    payment: PaymentMandate

    def __post_init__(self):
        """Validate mandate chain consistency."""
        # All mandates must reference the same agent_id
        agent_ids = {self.intent.subject, self.cart.subject, self.payment.subject}
        if len(agent_ids) != 1:
            raise ValueError(
                f"All mandates must reference the same agent_id. "
                f"Found: intent={self.intent.subject}, cart={self.cart.subject}, payment={self.payment.subject}"
            )

        # Payment amount must be within cart total bounds
        cart_total = self.cart.subtotal_minor + self.cart.taxes_minor
        if self.payment.amount_minor > cart_total:
            raise ValueError(
                f"Payment amount ({self.payment.amount_minor}) exceeds cart total ({cart_total})"
            )

        # If intent has requested_amount, payment must not exceed it
        if self.intent.requested_amount is not None and self.payment.amount_minor > self.intent.requested_amount:
            raise ValueError(
                f"Payment amount ({self.payment.amount_minor}) exceeds intent requested amount ({self.intent.requested_amount})"
            )

        # Timestamps must be ordered: intent.expires_at <= cart.expires_at <= payment.expires_at
        # This ensures the chain was created in logical order
        if not (self.intent.expires_at <= self.cart.expires_at <= self.payment.expires_at):
            raise ValueError(
                f"Mandate expiration timestamps must be ordered (intent <= cart <= payment). "
                f"Found: intent={self.intent.expires_at}, cart={self.cart.expires_at}, payment={self.payment.expires_at}"
            )


__all__ = [
    "IntentMandate",
    "CartMandate",
    "PaymentMandate",
    "VCProof",
    "MandateChain",
]
