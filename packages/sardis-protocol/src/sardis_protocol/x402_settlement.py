"""x402 settlement module - separates verification from on-chain settlement.

Implements:
- Settlement status tracking (VERIFIED -> SETTLING -> SETTLED)
- Store abstraction for settlement persistence
- X402Settler class for verify/settle operations
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from .x402 import X402Challenge, X402PaymentPayload, verify_payment_payload


class X402SettlementStatus(Enum):
    """Settlement status enum."""
    VERIFIED = "verified"
    SETTLING = "settling"
    SETTLED = "settled"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(slots=True)
class X402Settlement:
    """Settlement tracking for an x402 payment."""
    payment_id: str
    status: X402SettlementStatus
    challenge: X402Challenge | None = None
    payload: X402PaymentPayload | None = None
    tx_hash: str | None = None
    settled_at: datetime | None = None
    error: str | None = None


class X402SettlementStore(Protocol):
    """Protocol for settlement persistence."""

    async def save(self, settlement: X402Settlement) -> None:
        """Save a new settlement record."""
        ...

    async def get(self, payment_id: str) -> X402Settlement | None:
        """Retrieve settlement by payment_id."""
        ...

    async def update_status(
        self,
        payment_id: str,
        status: X402SettlementStatus,
        **kwargs,
    ) -> None:
        """Update settlement status and optional fields."""
        ...


class InMemorySettlementStore:
    """In-memory implementation of X402SettlementStore."""

    def __init__(self):
        self._settlements: dict[str, X402Settlement] = {}

    async def save(self, settlement: X402Settlement) -> None:
        """Save a new settlement record."""
        self._settlements[settlement.payment_id] = settlement

    async def get(self, payment_id: str) -> X402Settlement | None:
        """Retrieve settlement by payment_id."""
        return self._settlements.get(payment_id)

    async def update_status(
        self,
        payment_id: str,
        status: X402SettlementStatus,
        **kwargs,
    ) -> None:
        """Update settlement status and optional fields."""
        settlement = self._settlements.get(payment_id)
        if settlement is None:
            raise ValueError(f"settlement_not_found: {payment_id}")

        settlement.status = status
        for key, value in kwargs.items():
            if hasattr(settlement, key):
                setattr(settlement, key, value)


class X402Settler:
    """Manages x402 payment verification and settlement."""

    def __init__(
        self,
        store: X402SettlementStore,
        chain_executor: Any | None = None,
    ):
        self.store = store
        self.chain_executor = chain_executor

    async def verify(
        self,
        challenge: X402Challenge,
        payload: X402PaymentPayload,
    ) -> X402Settlement:
        """Verify payment payload against challenge. Does NOT touch blockchain."""
        verification = verify_payment_payload(payload, challenge)

        if not verification.accepted:
            settlement = X402Settlement(
                payment_id=payload.payment_id,
                status=X402SettlementStatus.FAILED,
                challenge=challenge,
                payload=payload,
                error=verification.reason,
            )
            await self.store.save(settlement)
            return settlement

        settlement = X402Settlement(
            payment_id=payload.payment_id,
            status=X402SettlementStatus.VERIFIED,
            challenge=challenge,
            payload=payload,
        )
        await self.store.save(settlement)
        return settlement

    async def settle(self, settlement: X402Settlement) -> X402Settlement:
        """Initiate on-chain settlement for a verified payment."""
        if settlement.status != X402SettlementStatus.VERIFIED:
            raise ValueError(
                f"cannot_settle: settlement must be VERIFIED, got {settlement.status.value}"
            )

        if self.chain_executor is None:
            raise ValueError("cannot_settle: chain_executor not configured")

        try:
            await self.store.update_status(
                settlement.payment_id,
                X402SettlementStatus.SETTLING,
            )

            from sardis_v2_core.mandates import PaymentMandate, VCProof
            import time

            challenge = settlement.challenge
            mandate = PaymentMandate(
                mandate_id=f"x402_{settlement.payment_id}",
                mandate_type="payment",
                issuer="x402",
                subject="x402",
                expires_at=int(time.time()) + 300,
                nonce=settlement.payment_id,
                proof=VCProof(
                    verification_method="x402",
                    created=datetime.now(timezone.utc).isoformat(),
                    proof_value="x402",
                ),
                domain="x402",
                purpose="checkout",
                chain=challenge.network,
                token=challenge.currency,
                amount_minor=int(challenge.amount),
                destination=challenge.payee_address,
                audit_hash=settlement.payment_id,
            )
            receipt = await self.chain_executor.dispatch_payment(mandate)
            tx_hash = receipt.tx_hash

            await self.store.update_status(
                settlement.payment_id,
                X402SettlementStatus.SETTLED,
                tx_hash=tx_hash,
                settled_at=datetime.now(timezone.utc),
            )

            updated = await self.store.get(settlement.payment_id)
            if updated is None:
                raise ValueError(f"settlement_lost: {settlement.payment_id}")
            return updated

        except Exception as exc:
            await self.store.update_status(
                settlement.payment_id,
                X402SettlementStatus.FAILED,
                error=str(exc),
            )
            updated = await self.store.get(settlement.payment_id)
            if updated is None:
                raise ValueError(f"settlement_lost: {settlement.payment_id}") from exc
            return updated

    async def check_settlement(self, payment_id: str) -> X402Settlement | None:
        """Check settlement status from store."""
        return await self.store.get(payment_id)


def _challenge_to_dict(c: X402Challenge) -> dict:
    return {
        "payment_id": c.payment_id,
        "resource_uri": c.resource_uri,
        "amount": c.amount,
        "currency": c.currency,
        "payee_address": c.payee_address,
        "network": c.network,
        "token_address": c.token_address,
        "expires_at": c.expires_at,
        "nonce": c.nonce,
    }


def _dict_to_challenge(d: dict) -> X402Challenge:
    return X402Challenge(**d)


def _payload_to_dict(p: X402PaymentPayload) -> dict:
    return {
        "payment_id": p.payment_id,
        "payer_address": p.payer_address,
        "amount": p.amount,
        "nonce": p.nonce,
        "signature": p.signature,
        "authorization": p.authorization,
    }


def _dict_to_payload(d: dict) -> X402PaymentPayload:
    return X402PaymentPayload(**d)


class DatabaseSettlementStore:
    """PostgreSQL implementation of X402SettlementStore."""

    async def save(self, settlement: X402Settlement) -> None:
        from sardis_v2_core.database import Database
        await Database.execute(
            """INSERT INTO x402_settlements (payment_id, status, challenge, payload, tx_hash, settled_at, error, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT (payment_id) DO UPDATE SET status=$2, challenge=$3, payload=$4, tx_hash=$5, settled_at=$6, error=$7""",
            settlement.payment_id,
            settlement.status.value,
            json.dumps(_challenge_to_dict(settlement.challenge)) if settlement.challenge else None,
            json.dumps(_payload_to_dict(settlement.payload)) if settlement.payload else None,
            settlement.tx_hash,
            settlement.settled_at,
            settlement.error,
        )

    async def get(self, payment_id: str) -> X402Settlement | None:
        from sardis_v2_core.database import Database
        row = await Database.fetchrow("SELECT * FROM x402_settlements WHERE payment_id = $1", payment_id)
        if not row:
            return None
        return X402Settlement(
            payment_id=row["payment_id"],
            status=X402SettlementStatus(row["status"]),
            challenge=_dict_to_challenge(json.loads(row["challenge"])) if row.get("challenge") else None,
            payload=_dict_to_payload(json.loads(row["payload"])) if row.get("payload") else None,
            tx_hash=row.get("tx_hash"),
            settled_at=row.get("settled_at"),
            error=row.get("error"),
        )

    async def update_status(
        self,
        payment_id: str,
        status: X402SettlementStatus,
        **kwargs,
    ) -> None:
        from sardis_v2_core.database import Database
        sets = ["status = $2"]
        args: list = [payment_id, status.value]
        idx = 3
        for key, value in kwargs.items():
            if key in ("tx_hash", "settled_at", "error"):
                sets.append(f"{key} = ${idx}")
                args.append(value)
                idx += 1
        await Database.execute(
            f"UPDATE x402_settlements SET {', '.join(sets)} WHERE payment_id = $1",
            *args,
        )


__all__ = [
    "X402SettlementStatus",
    "X402Settlement",
    "X402SettlementStore",
    "InMemorySettlementStore",
    "DatabaseSettlementStore",
    "X402Settler",
]
