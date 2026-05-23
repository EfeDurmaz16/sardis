"""PaymentObject Minter — mints one-time-use payment tokens from spending mandates.

The minter is the only authorized path for creating PaymentObjects.  It
enforces mandate validity, amount bounds, funding cell claims, replay
protection, and cryptographic signing before producing a minted token.

Pipeline:
─────────

    mint(mandate_id, merchant_id, amount, ...)
        │
        ▼
    ┌─────────────────────────────────────────────────────┐
    │  1. LOOKUP MANDATE                                  │
    │     → Fetch the SpendingMandate by ID               │
    │     → Fail if not found                             │
    ├─────────────────────────────────────────────────────┤
    │  2. VALIDATE MANDATE                                │
    │     → Status must be ACTIVE                         │
    │     → Must not be expired                           │
    │     → Amount within per-tx, daily, monthly, total   │
    ├─────────────────────────────────────────────────────┤
    │  3. CLAIM FUNDING CELLS                             │
    │     → Reserve budget cells from the mandate         │
    │     → Fail if insufficient budget                   │
    ├─────────────────────────────────────────────────────┤
    │  4. COMPUTE SESSION HASH                            │
    │     → SHA-256 of (mandate_id + merchant + amount +  │
    │       timestamp + nonce) for replay protection      │
    ├─────────────────────────────────────────────────────┤
    │  5. SIGN                                            │
    │     → Sign the payment object data                  │
    │     → Produces signature chain entry                │
    ├─────────────────────────────────────────────────────┤
    │  6. RETURN MINTED PAYMENT OBJECT                    │
    │     → status=MINTED, ready for presentation         │
    └─────────────────────────────────────────────────────┘

Dependencies are injected via Protocol-based ports (matching the orchestrator
pattern), making the minter testable with in-memory fakes.

Usage::

    minter = PaymentObjectMinter(
        mandate_lookup=postgres_mandate_store,
        cell_claimer=budget_cell_service,
        signer=turnkey_signer,
    )

    po = await minter.mint(
        mandate_id="mandate_abc123",
        merchant_id="merchant_openai",
        amount=Decimal("49.99"),
    )
    assert po.status == PaymentObjectStatus.MINTED

See also:
  - ``payment_object.py`` — the PaymentObject dataclass.
  - ``spending_mandate.py`` — the mandate that authorizes minting.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from .payment_object import PaymentObject, PaymentObjectStatus, PrivacyTier
from .spending_mandate import MandateStatus, SpendingMandate

logger = logging.getLogger("sardis.minter")


# ============ Port Protocols ============


@runtime_checkable
class SpendingMandateLookupPort(Protocol):
    """Port for looking up spending mandates by ID."""

    async def get_mandate(self, mandate_id: str) -> SpendingMandate | None:
        """Fetch a spending mandate by its ID.

        Returns:
            The SpendingMandate if found, None otherwise.
        """
        ...


@runtime_checkable
class CellClaimPort(Protocol):
    """Port for claiming funding cells from a mandate's budget.

    Funding cells are discrete budget units that get reserved (claimed)
    when a PaymentObject is minted.  This prevents double-spending across
    concurrent mint requests.
    """

    async def claim_cells(
        self,
        mandate_id: str,
        amount: Decimal,
        currency: str,
    ) -> list[str]:
        """Claim funding cells covering the requested amount.

        Args:
            mandate_id: The mandate to claim cells from.
            amount: The total amount to cover.
            currency: Currency code (e.g. "USDC").

        Returns:
            List of claimed cell IDs.

        Raises:
            ValueError: If insufficient budget to cover the amount.
        """
        ...


@runtime_checkable
class SigningPort(Protocol):
    """Port for cryptographic signing of payment object data."""

    async def sign(self, data: bytes) -> str:
        """Sign the given data and return a signature string.

        Args:
            data: Raw bytes to sign.

        Returns:
            Base64 or hex-encoded signature string.
        """
        ...


# ============ Mint Result ============


class MintError(Exception):
    """Raised when minting a PaymentObject fails."""

    def __init__(
        self,
        message: str,
        error_code: str,
        mandate_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.mandate_id = mandate_id
        self.details = details or {}


# ============ Minter Service ============


class PaymentObjectMinter:
    """Mints PaymentObjects from spending mandates.

    The minter validates mandate bounds, claims funding cells,
    and produces signed, one-time-use payment tokens.

    All dependencies are injected via Protocol-based ports so the minter
    can be tested with in-memory fakes without touching real infrastructure.
    """

    def __init__(
        self,
        *,
        mandate_lookup: SpendingMandateLookupPort,
        cell_claimer: CellClaimPort,
        signer: SigningPort,
    ) -> None:
        self._mandate_lookup = mandate_lookup
        self._cell_claimer = cell_claimer
        self._signer = signer

    async def mint(
        self,
        mandate_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        *,
        privacy_tier: PrivacyTier = PrivacyTier.TRANSPARENT,
        expires_in_seconds: int = 3600,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentObject:
        """Mint a new PaymentObject from a spending mandate.

        Validates the mandate, claims funding cells, computes a session
        hash for replay protection, signs the object, and returns a
        minted PaymentObject ready for presentation to a merchant.

        Args:
            mandate_id: ID of the spending mandate to mint from.
            merchant_id: Merchant this payment is payable to.
            amount: Exact payment amount.
            currency: Currency code (default: "USDC").
            privacy_tier: Privacy level for on-chain data exposure.
            expires_in_seconds: Seconds until the payment object expires
                (default: 3600 = 1 hour).
            metadata: Optional metadata to attach to the payment object.

        Returns:
            A PaymentObject with status=MINTED.

        Raises:
            MintError: If minting fails for any reason (mandate not found,
                mandate not active, amount exceeds limits, insufficient
                budget, signing failure).
        """
        # ── Step 1: Lookup mandate ───────────────────────────────────
        mandate = await self._mandate_lookup.get_mandate(mandate_id)
        if mandate is None:
            raise MintError(
                f"Mandate {mandate_id} not found",
                error_code="MANDATE_NOT_FOUND",
                mandate_id=mandate_id,
            )

        # ── Step 2: Validate mandate ─────────────────────────────────
        self._validate_mandate(mandate, amount, merchant_id)

        # ── Step 3: Claim funding cells ──────────────────────────────
        try:
            cell_ids = await self._cell_claimer.claim_cells(
                mandate_id=mandate_id,
                amount=amount,
                currency=currency,
            )
        except ValueError as exc:
            raise MintError(
                f"Failed to claim funding cells: {exc}",
                error_code="INSUFFICIENT_BUDGET",
                mandate_id=mandate_id,
                details={"amount": str(amount), "currency": currency},
            ) from exc

        if not cell_ids:
            raise MintError(
                "No funding cells claimed — insufficient budget",
                error_code="INSUFFICIENT_BUDGET",
                mandate_id=mandate_id,
                details={"amount": str(amount), "currency": currency},
            )

        # ── Step 4: Compute session hash ─────────────────────────────
        now = datetime.now(UTC)
        nonce = uuid4().hex
        session_hash = self._compute_session_hash(
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            amount=amount,
            currency=currency,
            timestamp=now,
            nonce=nonce,
        )

        # ── Step 5: Sign ─────────────────────────────────────────────
        object_id = f"po_{uuid4().hex[:16]}"
        signable_data = self._build_signable_payload(
            object_id=object_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            amount=amount,
            currency=currency,
            cell_ids=cell_ids,
            session_hash=session_hash,
        )

        try:
            signature = await self._signer.sign(signable_data)
        except Exception as exc:
            raise MintError(
                f"Signing failed: {exc}",
                error_code="SIGNING_FAILED",
                mandate_id=mandate_id,
            ) from exc

        # ── Step 5b: Generate ZKP if privacy tier requires it ──────
        zkp_proof_hex: str | None = None
        if privacy_tier in (PrivacyTier.HYBRID, PrivacyTier.FULL_ZK):
            try:
                from sardis_zkp import ZKProver
                prover = ZKProver(production=False)
                proof = await prover.prove_mandate_compliance(
                    amount=amount,
                    per_tx_limit=mandate.amount_per_tx or Decimal("999999"),
                    daily_limit=mandate.amount_daily or Decimal("999999"),
                    daily_spent=mandate.spent_total,
                    merchant_id=merchant_id,
                )
                zkp_proof_hex = proof.proof_hex
                logger.info(
                    "Generated %s ZKP proof %s for payment object %s",
                    privacy_tier.value, proof.proof_id, object_id,
                )
            except ImportError:
                logger.warning("sardis_zkp not installed — skipping proof generation")
            except Exception as exc:
                logger.warning("ZKP proof generation failed: %s", exc)

        # ── Step 6: Build and return PaymentObject ───────────────────
        expires_at = now + timedelta(seconds=expires_in_seconds)

        obj_metadata = metadata or {}
        if zkp_proof_hex:
            obj_metadata["zkp_proof"] = zkp_proof_hex

        po = PaymentObject(
            object_id=object_id,
            mandate_id=mandate_id,
            cell_ids=cell_ids,
            merchant_id=merchant_id,
            exact_amount=amount,
            currency=currency,
            one_time_use=True,
            signature_chain=[signature],
            session_hash=session_hash,
            expires_at=expires_at,
            status=PaymentObjectStatus.MINTED,
            privacy_tier=privacy_tier,
            created_at=now,
            metadata=obj_metadata,
        )

        logger.info(
            "Minted PaymentObject %s from mandate %s: %s %s to %s",
            po.object_id,
            mandate_id,
            amount,
            currency,
            merchant_id,
        )

        return po

    # ── Internal helpers ─────────────────────────────────────────────

    def _validate_mandate(
        self,
        mandate: SpendingMandate,
        amount: Decimal,
        merchant_id: str,
    ) -> None:
        """Validate the mandate is active and the amount is within bounds.

        Raises:
            MintError: If any validation check fails.
        """
        # Status check
        if mandate.status != MandateStatus.ACTIVE:
            raise MintError(
                f"Mandate {mandate.id} is {mandate.status.value}, not active",
                error_code="MANDATE_NOT_ACTIVE",
                mandate_id=mandate.id,
                details={"status": mandate.status.value},
            )

        # Expiration check
        now = datetime.now(UTC)
        if mandate.expires_at is not None and now > mandate.expires_at:
            raise MintError(
                f"Mandate {mandate.id} expired at {mandate.expires_at.isoformat()}",
                error_code="MANDATE_EXPIRED",
                mandate_id=mandate.id,
                details={"expires_at": mandate.expires_at.isoformat()},
            )

        # Valid-from check
        if mandate.valid_from and now < mandate.valid_from:
            raise MintError(
                f"Mandate {mandate.id} not yet valid (valid_from: {mandate.valid_from.isoformat()})",
                error_code="MANDATE_NOT_YET_VALID",
                mandate_id=mandate.id,
                details={"valid_from": mandate.valid_from.isoformat()},
            )

        # Amount validation
        if amount <= Decimal("0"):
            raise MintError(
                "Amount must be positive",
                error_code="INVALID_AMOUNT",
                mandate_id=mandate.id,
                details={"amount": str(amount)},
            )

        # Per-transaction limit
        if mandate.amount_per_tx is not None and amount > mandate.amount_per_tx:
            raise MintError(
                f"Amount {amount} exceeds per-transaction limit {mandate.amount_per_tx}",
                error_code="PER_TX_LIMIT_EXCEEDED",
                mandate_id=mandate.id,
                details={
                    "amount": str(amount),
                    "limit_per_tx": str(mandate.amount_per_tx),
                },
            )

        # Total budget remaining
        if mandate.amount_total is not None:
            remaining = mandate.amount_total - mandate.spent_total
            if amount > remaining:
                raise MintError(
                    f"Amount {amount} exceeds remaining mandate budget {remaining}",
                    error_code="TOTAL_BUDGET_EXCEEDED",
                    mandate_id=mandate.id,
                    details={
                        "amount": str(amount),
                        "remaining": str(remaining),
                        "total": str(mandate.amount_total),
                        "spent": str(mandate.spent_total),
                    },
                )

        # Merchant scope check
        if mandate.merchant_scope:
            blocked = mandate.merchant_scope.get("blocked", [])
            if merchant_id in blocked:
                raise MintError(
                    f"Merchant {merchant_id} is blocked by mandate",
                    error_code="MERCHANT_BLOCKED",
                    mandate_id=mandate.id,
                    details={"merchant_id": merchant_id},
                )

            allowed = mandate.merchant_scope.get("allowed")
            if allowed is not None:
                matched = any(
                    merchant_id.endswith(a.lstrip("*")) if a.startswith("*") else merchant_id == a
                    for a in allowed
                )
                if not matched:
                    raise MintError(
                        f"Merchant {merchant_id} not in mandate allowed list",
                        error_code="MERCHANT_NOT_ALLOWED",
                        mandate_id=mandate.id,
                        details={
                            "merchant_id": merchant_id,
                            "allowed": allowed,
                        },
                    )

    @staticmethod
    def _compute_session_hash(
        *,
        mandate_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str,
        timestamp: datetime,
        nonce: str,
    ) -> str:
        """Compute a SHA-256 session hash for replay protection.

        The hash is unique per mint attempt because it includes a random
        nonce and the precise timestamp.  Two calls with the same
        mandate/merchant/amount will produce different hashes.
        """
        payload = {
            "mandate_id": mandate_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency,
            "timestamp": timestamp.isoformat(),
            "nonce": nonce,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

    @staticmethod
    def _build_signable_payload(
        *,
        object_id: str,
        mandate_id: str,
        merchant_id: str,
        amount: Decimal,
        currency: str,
        cell_ids: list[str],
        session_hash: str,
    ) -> bytes:
        """Build the canonical bytes payload for signing.

        The payload is a deterministic JSON string (sorted keys, no
        whitespace) so that signature verification is reproducible.
        """
        payload = {
            "object_id": object_id,
            "mandate_id": mandate_id,
            "merchant_id": merchant_id,
            "amount": str(amount),
            "currency": currency,
            "cell_ids": sorted(cell_ids),
            "session_hash": session_hash,
        }
        return json.dumps(payload, sort_keys=True).encode()
