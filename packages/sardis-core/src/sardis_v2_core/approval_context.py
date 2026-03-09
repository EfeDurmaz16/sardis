"""First-class approval context for binding payment execution to approval.

The ApprovalContext captures the full context at the moment a payment was
approved — origin, cart, action, policy — so that execution can verify
the approved object == the executed object.

This addresses the core security concern: "payments inside browser agents
only become safe when the approval context is stronger than the page context."
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApprovalContext:
    """Cryptographic binding between approval and execution.

    Every field contributes to approval_context_hash. If any field changes
    between approval and execution, the hash mismatch blocks the payment.
    """

    # Origin binding (where the payment was initiated)
    top_origin: str = ""          # top-level page origin (e.g. "https://shop.example.com")
    frame_origin: str = ""        # iframe origin if embedded (e.g. "https://checkout.sardis.sh")
    page_url_hash: str = ""       # SHA-256 of full page URL (privacy-preserving)

    # Session binding
    session_id: str = ""          # checkout session or agent session ID
    nonce: str = ""               # one-time nonce for replay prevention

    # Merchant binding
    merchant_domain: str = ""     # merchant domain for cross-referencing AP2 cart

    # Cart/action binding
    cart_hash: str = ""           # SHA-256 of canonical cart (line items, totals)
    action_description_hash: str = ""  # SHA-256 of what the agent says it's paying for

    # Policy binding
    policy_hash: str = ""         # SHA-256 of the policy snapshot at approval time

    # Payment binding
    amount: str = ""              # exact amount approved (string for precision)
    token: str = ""               # token approved (e.g. "USDC")
    chain: str = ""               # chain approved (e.g. "base")
    destination: str = ""         # recipient address approved

    # Timing
    expires_at: int = 0           # unix timestamp — approval expires after this
    approved_at: int = 0          # unix timestamp — when approval was granted

    def compute_hash(self) -> str:
        """Compute the canonical hash of this approval context.

        This hash is what gets checked at execution time. If anything
        changes between approval and execution, the hash won't match.
        """
        canonical = json.dumps(
            {
                "top_origin": self.top_origin,
                "frame_origin": self.frame_origin,
                "page_url_hash": self.page_url_hash,
                "session_id": self.session_id,
                "nonce": self.nonce,
                "merchant_domain": self.merchant_domain,
                "cart_hash": self.cart_hash,
                "action_description_hash": self.action_description_hash,
                "policy_hash": self.policy_hash,
                "amount": self.amount,
                "token": self.token,
                "chain": self.chain,
                "destination": self.destination,
                "expires_at": self.expires_at,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def is_expired(self) -> bool:
        """Check if this approval has expired."""
        if self.expires_at <= 0:
            return False  # no expiry set
        return int(time.time()) > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "top_origin": self.top_origin,
            "frame_origin": self.frame_origin,
            "page_url_hash": self.page_url_hash,
            "session_id": self.session_id,
            "nonce": self.nonce,
            "merchant_domain": self.merchant_domain,
            "cart_hash": self.cart_hash,
            "action_description_hash": self.action_description_hash,
            "policy_hash": self.policy_hash,
            "amount": self.amount,
            "token": self.token,
            "chain": self.chain,
            "destination": self.destination,
            "expires_at": self.expires_at,
            "approved_at": self.approved_at,
            "approval_context_hash": self.compute_hash(),
        }


def hash_value(value: str) -> str:
    """SHA-256 hash a string value for privacy-preserving binding."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_cart(line_items: list[dict], subtotal: str, taxes: str, currency: str) -> str:
    """Compute canonical cart hash from cart data."""
    sorted_items = sorted(line_items, key=lambda x: (x.get("item_id", ""), x.get("name", "")))
    canonical = json.dumps(
        {"line_items": sorted_items, "subtotal": subtotal, "taxes": taxes, "currency": currency},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_approval_context(
    approved: ApprovalContext,
    execution_hash: str,
) -> tuple[bool, str]:
    """Verify that execution matches the approved context.

    Args:
        approved: The ApprovalContext created at approval time.
        execution_hash: The hash provided at execution time.

    Returns:
        (is_valid, error_message). error_message is empty on success.
    """
    if approved.is_expired():
        return False, "approval_context_expired"

    computed = approved.compute_hash()
    if computed != execution_hash:
        return False, "approval_context_hash_mismatch"

    return True, ""
