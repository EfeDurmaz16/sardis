"""RecourseExecutorPort — swappable execution for a RecourseHold.

Sardis owns the *decision* (open / release / refund / dispute / resolve) and the
signed evidence — that is the moat and lives in :mod:`recourse_hold`.  This
module is the *execution* leg: moving (or claiming) the actual money.  It is
deliberately thin and **swappable**:

* opening a hold ≈ ``RefundProtocol.pay(to, amount, refundTo)`` — funds parked
  with a lockup and a refund address;
* releasing ≈ ``RefundProtocol.withdraw([paymentID])`` after the lockup, or a
  plain settlement to the recipient;
* refunding ≈ ``RefundProtocol.refundByRecipient/refundByArbiter`` — the
  reverse-transfer leg back to the payer.

Two implementations:

* :class:`NoopRecourseExecutor` — the default in dev/tests and whenever live
  escrow is not configured.  It records intent (synthetic tx hashes) and moves
  no real money — the hold's *state machine* is the source of truth.  This keeps
  the primitive **env-gated + mockable, no live keys needed**.
* :class:`RefundProtocolExecutor` — wraps the vendored Circle ``RefundProtocol``
  via an injected chain client.  Only used when ``SARDIS_RECOURSE_MODE=live``
  and a client is supplied; otherwise we fall back to the noop executor.

No vendor SDK or chain client is imported at module load — the live executor
takes its client by injection so importing this module never requires keys.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass
from typing import Any, Protocol

from .recourse_hold import RecourseHold

logger = logging.getLogger("sardis.recourse_executor")


@dataclass(slots=True)
class ExecutionRef:
    """Result of an execution leg: the on-chain (or synthetic) settlement ref."""

    ok: bool
    tx_hash: str | None = None
    escrow_payment_id: str | None = None
    escrow_contract: str | None = None
    provider: str = "noop"
    error: str | None = None


class RecourseExecutorPort(Protocol):
    """Swappable money-movement for recourse holds.  NEVER decides outcome."""

    async def open_hold(self, hold: RecourseHold) -> ExecutionRef:
        """Park funds/claim for the window (e.g. ``RefundProtocol.pay``)."""
        ...

    async def settle_release(self, hold: RecourseHold) -> ExecutionRef:
        """Settle to the recipient (e.g. ``withdraw`` after lockup)."""
        ...

    async def settle_refund(
        self, hold: RecourseHold, *, amount_minor: int
    ) -> ExecutionRef:
        """Reverse-transfer to the payer (e.g. ``refundByRecipient``)."""
        ...


def _synthetic_tx() -> str:
    return "0xrch_" + secrets.token_hex(16)


# ── Noop / mock executor (default, no keys) ────────────────────────────


class NoopRecourseExecutor:
    """Records intent, moves no real money.  The hold state machine is truth.

    Used in dev/tests and whenever live escrow is not configured.  Returns
    synthetic tx hashes so downstream audit fields are populated, but it does
    NOT touch a chain — fail-closed by construction (no money can leak).
    """

    provider = "noop"

    async def open_hold(self, hold: RecourseHold) -> ExecutionRef:
        logger.info(
            "recourse(noop): open hold %s amount_minor=%s %s payer=%s recipient=%s",
            hold.id, hold.amount_minor, hold.currency, hold.payer, hold.recipient,
        )
        return ExecutionRef(
            ok=True,
            tx_hash=_synthetic_tx(),
            escrow_payment_id=f"noop_{hold.id}",
            escrow_contract="noop",
            provider=self.provider,
        )

    async def settle_release(self, hold: RecourseHold) -> ExecutionRef:
        logger.info("recourse(noop): release hold %s -> recipient %s", hold.id, hold.recipient)
        return ExecutionRef(ok=True, tx_hash=_synthetic_tx(), provider=self.provider)

    async def settle_refund(
        self, hold: RecourseHold, *, amount_minor: int
    ) -> ExecutionRef:
        logger.info(
            "recourse(noop): refund hold %s amount_minor=%s -> payer %s",
            hold.id, amount_minor, hold.payer,
        )
        return ExecutionRef(ok=True, tx_hash=_synthetic_tx(), provider=self.provider)


# ── Live executor: vendored Circle RefundProtocol ──────────────────────


class RefundProtocolExecutor:
    """Wraps the vendored Circle ``RefundProtocol`` (Apache-2.0) for real money.

    The ``client`` is an injected, duck-typed chain client exposing:

    * ``pay(to, amount, refund_to) -> {"tx_hash", "payment_id"}``
    * ``withdraw(payment_ids) -> {"tx_hash"}``
    * ``refund_by_recipient(payment_id) -> {"tx_hash"}``

    Keeping it injected means importing this module never needs live keys; the
    engine only constructs this when ``SARDIS_RECOURSE_MODE=live`` and a client
    is provided.  If the client raises, we surface a failed ``ExecutionRef`` and
    let the engine keep the hold non-terminal (fail-closed — no state advance
    without a settled execution).
    """

    provider = "refund_protocol"

    def __init__(self, client: Any, *, contract_address: str | None = None) -> None:
        self._client = client
        self._contract = contract_address or os.getenv("SARDIS_REFUND_PROTOCOL_ADDRESS")

    async def open_hold(self, hold: RecourseHold) -> ExecutionRef:
        try:
            res = await self._client.pay(
                to=hold.recipient,
                amount=hold.amount_minor,
                refund_to=hold.payer,
            )
            return ExecutionRef(
                ok=True,
                tx_hash=res.get("tx_hash"),
                escrow_payment_id=str(res.get("payment_id")),
                escrow_contract=self._contract,
                provider=self.provider,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
            logger.error("recourse(refund_protocol): open failed for %s: %s", hold.id, exc)
            return ExecutionRef(ok=False, provider=self.provider, error=str(exc))

    async def settle_release(self, hold: RecourseHold) -> ExecutionRef:
        try:
            payment_id = hold.escrow_payment_id
            res = await self._client.withdraw(payment_ids=[payment_id])
            return ExecutionRef(ok=True, tx_hash=res.get("tx_hash"), provider=self.provider)
        except Exception as exc:  # noqa: BLE001
            logger.error("recourse(refund_protocol): release failed for %s: %s", hold.id, exc)
            return ExecutionRef(ok=False, provider=self.provider, error=str(exc))

    async def settle_refund(
        self, hold: RecourseHold, *, amount_minor: int
    ) -> ExecutionRef:
        try:
            res = await self._client.refund_by_recipient(payment_id=hold.escrow_payment_id)
            return ExecutionRef(ok=True, tx_hash=res.get("tx_hash"), provider=self.provider)
        except Exception as exc:  # noqa: BLE001
            logger.error("recourse(refund_protocol): refund failed for %s: %s", hold.id, exc)
            return ExecutionRef(ok=False, provider=self.provider, error=str(exc))


def resolve_default_executor(client: Any | None = None) -> RecourseExecutorPort:
    """Pick the executor from the environment.

    ``SARDIS_RECOURSE_MODE=live`` **and** a client -> :class:`RefundProtocolExecutor`.
    Anything else -> :class:`NoopRecourseExecutor` (env-gated, no keys needed).
    """
    mode = os.getenv("SARDIS_RECOURSE_MODE", "noop").strip().lower()
    if mode == "live" and client is not None:
        return RefundProtocolExecutor(client)
    if mode == "live" and client is None:
        logger.warning(
            "SARDIS_RECOURSE_MODE=live but no chain client supplied; "
            "falling back to NoopRecourseExecutor (no money will move)."
        )
    return NoopRecourseExecutor()


__all__ = [
    "ExecutionRef",
    "NoopRecourseExecutor",
    "RecourseExecutorPort",
    "RefundProtocolExecutor",
    "resolve_default_executor",
]
