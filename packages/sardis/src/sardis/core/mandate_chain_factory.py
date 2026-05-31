"""Single typed factory for building a :class:`MandateChain`.

This is the one supported way to construct a ``MandateChain`` for
:meth:`sardis.core.orchestrator.PaymentOrchestrator.execute_chain`.  Callers
should stop building intent/cart/payment mandates ad-hoc (duck-typing or
``type(...)``-based construction) and use :func:`build_mandate_chain` instead.

Design notes
------------
* **Decimal money only — never float.**  Callers pass a human-readable amount
  (``Decimal`` / ``str`` / ``int``) plus the token's ``decimals``.  The minor
  units stored on the mandates are computed with :class:`decimal.Decimal`
  arithmetic; no float ever touches the money path.
* The real domain model (``packages/sardis/src/sardis/core/mandates.py``)
  carries money as integer *minor units* (``amount_minor``) and the currency as
  the ``token`` / ``currency`` field.  This factory bridges the Decimal public
  contract to that representation.
* ``MandateChain.__post_init__`` enforces invariants: all three mandates must
  share the same ``subject`` (the agent id), the payment amount must not exceed
  the cart total, and expirations must be ordered intent <= cart <= payment.
  The factory satisfies all of these by construction.

Synthesized fields (NOT cryptographic)
--------------------------------------
``MandateBase`` requires a ``proof`` (``VCProof``).  Like the existing internal
execution paths (e.g. ``apps/api/server/routes/authority/mvp.py``), this
factory synthesizes an **internal system proof** for orchestrator routing.  It
is explicitly *not* a verifiable cryptographic AP2 proof.  Adopt this factory
only on internal execution paths where the inbound mandate has already been
verified, or where the chain is constructed first-party (a2a / ap2 / pay).
"""
from __future__ import annotations

import hashlib
import time
import uuid
from decimal import Decimal

from .mandates import CartMandate, IntentMandate, MandateChain, PaymentMandate, VCProof

# Default token precision.  USDC / EURC use 6 decimals on the chains Sardis
# supports; callers can override via ``decimals`` for other tokens.
DEFAULT_TOKEN_DECIMALS = 6

# How long, in seconds, a freshly built chain stays valid.
_DEFAULT_TTL_SECONDS = 300


def _to_minor_units(amount: Decimal | str | int, decimals: int) -> int:
    """Convert a human-readable amount to integer minor units using Decimal.

    ``float`` is intentionally rejected to keep the money path float-free.
    """
    if isinstance(amount, float):
        raise TypeError(
            "amount must be Decimal | str | int, not float — float money is forbidden"
        )
    value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    scaled = value * (Decimal(10) ** decimals)
    minor = scaled.to_integral_value()
    if minor != scaled:
        raise ValueError(
            f"amount {amount!r} has more precision than {decimals} decimals allow"
        )
    return int(minor)


def build_mandate_chain(
    *,
    agent_id: str,
    amount: Decimal | str | int,
    currency: str,
    counterparty: str,
    wallet_id: str | None = None,
    mandate_id: str | None = None,
    chain: str = "base",
    decimals: int = DEFAULT_TOKEN_DECIMALS,
    purpose: str = "",
    merchant_domain: str | None = None,
    issuer: str | None = None,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> MandateChain:
    """Build a typed :class:`MandateChain` ready for ``execute_chain``.

    Parameters
    ----------
    agent_id:
        The acting agent.  Used as the ``subject`` on all three mandates (the
        chain's consistency check requires a single shared subject).
    amount:
        Money as ``Decimal`` / ``str`` / ``int`` (never ``float``).  Converted
        to integer minor units with ``decimals`` precision.
    currency:
        Token symbol (e.g. ``"USDC"``).  Stored as ``token`` on the payment and
        ``currency`` on the cart.
    counterparty:
        Destination address / merchant the payment pays to.
    wallet_id:
        Optional execution hint selecting the signing wallet.
    mandate_id:
        Optional payment mandate id.  Generated (``md_<uuid>``) when omitted.
    chain:
        Target settlement chain (defaults to ``"base"``).
    decimals:
        Token precision for the minor-unit conversion (defaults to 6).
    purpose:
        Optional human-readable description of the intent.
    merchant_domain:
        Optional merchant domain binding; defaults to ``counterparty``.
    issuer:
        Optional mandate issuer; defaults to the agent id.
    ttl_seconds:
        Validity window; expirations are ordered intent <= cart <= payment.
    """
    amount_minor = _to_minor_units(amount, decimals)

    pay_id = mandate_id or f"md_{uuid.uuid4().hex}"
    short = pay_id[:16]
    iss = issuer or agent_id
    merchant = merchant_domain or counterparty
    now = int(time.time())

    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    verification_method = f"did:sardis:{agent_id}#key-1"
    attestation = hashlib.sha256(
        f"{verification_method}:{created}:{pay_id}".encode()
    ).hexdigest()
    # Internal system proof for orchestrator routing — NOT a cryptographic AP2 proof.
    proof = VCProof(
        verification_method=verification_method,
        created=created,
        proof_purpose="internal_system_execution",
        proof_value=attestation,
    )

    nonce = uuid.uuid4().hex

    intent = IntentMandate(
        mandate_id=f"intent_{short}",
        mandate_type="intent",
        issuer=iss,
        subject=agent_id,
        expires_at=now + ttl_seconds,
        nonce=f"intent_{nonce}",
        proof=proof,
        domain=merchant,
        purpose="intent",
        requested_amount=amount_minor,
        natural_language_description=purpose,
    )
    cart = CartMandate(
        mandate_id=f"cart_{short}",
        mandate_type="cart",
        issuer=iss,
        subject=agent_id,
        # Ordered: intent <= cart <= payment.
        expires_at=now + ttl_seconds,
        nonce=f"cart_{nonce}",
        proof=proof,
        domain=merchant,
        purpose="cart",
        line_items=[{"description": purpose or "payment", "amount_minor": amount_minor}],
        merchant_domain=merchant,
        currency=currency,
        subtotal_minor=amount_minor,
        taxes_minor=0,
    )
    payment = PaymentMandate(
        mandate_id=pay_id,
        mandate_type="payment",
        issuer=iss,
        subject=agent_id,
        expires_at=now + ttl_seconds,
        nonce=f"payment_{nonce}",
        proof=proof,
        domain=merchant,
        purpose="checkout",
        chain=chain,
        token=currency,
        amount_minor=amount_minor,
        destination=counterparty,
        audit_hash=attestation,
        wallet_id=wallet_id,
        merchant_domain=merchant,
    )

    return MandateChain(intent=intent, cart=cart, payment=payment)


__all__ = ["build_mandate_chain", "DEFAULT_TOKEN_DECIMALS"]
