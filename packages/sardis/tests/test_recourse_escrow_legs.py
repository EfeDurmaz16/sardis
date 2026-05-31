"""Tests for the RecourseHold *execution legs* — the money-movement that backs
the escrow/dispute surface, exercised through a recording **mock escrow** and the
vendored Circle ``RefundProtocol`` mapping.

The state-machine invariants are pinned in ``test_recourse_hold.py``. This file
pins the part the dossier called out: that a hold actually *moves money* (lightly)
down a single fail-closed path, with signed evidence on every transition and no
double-move:

* a dispute holds the contested funds (mock escrow ``open_hold`` fired);
* resolve-refund reverse-transfers to the *payer* (``settle_refund`` fired with
  the held amount, destination = payer);
* resolve-release settles to the *recipient* (``settle_release`` fired);
* every settling transition is invoked exactly once — no double-move;
* the ``RefundProtocolExecutor`` maps open/release/refund onto the vendored
  contract's ``pay`` / ``withdraw`` / ``refundByRecipient`` calls.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from sardis.core.recourse_engine import RecourseEngine
from sardis.core.recourse_executor import (
    ExecutionRef,
    RecourseExecutorPort,
    RefundProtocolExecutor,
)
from sardis.core.recourse_hold import RecourseStatus, Resolution
from sardis.core.recourse_hold_repository import InMemoryRecourseHoldStore

SECRET = "test-recourse-escrow-secret"
HELD_MINOR = 100_000_000  # 100 USDC @ 6dp
PAYER = "0x" + "aa" * 20
RECIPIENT = "0x" + "bb" * 20


class RecordingEscrowExecutor:
    """Mock escrow leg: records every call + its parties/amounts, moves no chain
    money. Lets a test assert the *right* leg fired toward the *right* party with
    the *right* minor-units — i.e. the hold actually moved money (lightly)."""

    provider = "mock_escrow"

    def __init__(self) -> None:
        self.opens: list[tuple[str, int, str]] = []  # (recipient, amount, payer)
        self.releases: list[str] = []  # recipient settled to
        self.refunds: list[tuple[str, int]] = []  # (payer, amount)

    async def open_hold(self, hold) -> ExecutionRef:
        self.opens.append((hold.recipient, hold.amount_minor, hold.payer))
        return ExecutionRef(
            ok=True,
            tx_hash="0xopen",
            escrow_payment_id=f"escrow_{hold.id}",
            escrow_contract="0xRefundProtocol",
            provider=self.provider,
        )

    async def settle_release(self, hold) -> ExecutionRef:
        self.releases.append(hold.recipient)
        return ExecutionRef(ok=True, tx_hash="0xrelease", provider=self.provider)

    async def settle_refund(self, hold, *, amount_minor: int) -> ExecutionRef:
        self.refunds.append((hold.payer, int(amount_minor)))
        return ExecutionRef(ok=True, tx_hash="0xrefund", provider=self.provider)


def _engine(executor: RecourseExecutorPort):
    store = InMemoryRecourseHoldStore()
    return RecourseEngine(store=store, executor=executor, signing_secret=SECRET), store


async def _open(eng):
    return await eng.open_hold(
        payment_ref="po_escrow_001",
        mandate_id="mdt_escrow_001",
        agent_id="agent_escrow",
        amount=Decimal(HELD_MINOR) / Decimal(10**6),
        amount_minor=HELD_MINOR,
        currency="USDC",
        payer=PAYER,
        recipient=RECIPIENT,
        window_seconds=3600,
        policy_hash="pol",
        mandate_hash="mdt",
    )


# ── the contested-funds hold moves money down one path ──────────────────


@pytest.mark.asyncio
async def test_dispute_holds_contested_funds():
    """Opening a hold parks the contested funds via the escrow leg; filing a
    dispute moves no further money (auto-release paused)."""
    exe = RecordingEscrowExecutor()
    eng, _ = _engine(exe)
    hold = await _open(eng)

    # The escrow leg fired once, toward the recipient, for the full held amount,
    # refundable to the payer.
    assert exe.opens == [(RECIPIENT, HELD_MINOR, PAYER)]

    disputed = await eng.dispute(hold.id, actor="payer", reason="not delivered")
    assert disputed.status == RecourseStatus.DISPUTED
    # No settlement leg fired on dispute — funds are simply held/contested.
    assert exe.releases == []
    assert exe.refunds == []
    assert disputed.evidence.verify(secret=SECRET)


@pytest.mark.asyncio
async def test_resolve_refund_returns_to_payer():
    """resolve(REFUND) reverse-transfers the held amount to the *payer* and
    settles the hold terminal, with signed evidence."""
    exe = RecordingEscrowExecutor()
    eng, _ = _engine(exe)
    hold = await _open(eng)
    await eng.dispute(hold.id, actor="payer", reason="not as described")

    resolved = await eng.resolve(hold.id, resolution=Resolution.REFUND, actor="admin")

    assert resolved.status == RecourseStatus.RESOLVED
    assert resolved.resolution == Resolution.REFUND
    # Exactly one refund leg, to the payer, for the full held amount.
    assert exe.refunds == [(PAYER, HELD_MINOR)]
    assert exe.releases == []
    assert resolved.refunded_minor == HELD_MINOR
    assert resolved.settle_tx_hash == "0xrefund"
    assert resolved.evidence.verify(secret=SECRET)


@pytest.mark.asyncio
async def test_resolve_release_settles_to_recipient():
    """resolve(RELEASE) settles the held amount to the *recipient*, signed."""
    exe = RecordingEscrowExecutor()
    eng, _ = _engine(exe)
    hold = await _open(eng)
    await eng.dispute(hold.id, actor="payer", reason="changed mind")

    resolved = await eng.resolve(hold.id, resolution=Resolution.RELEASE, actor="admin")

    assert resolved.status == RecourseStatus.RESOLVED
    assert resolved.resolution == Resolution.RELEASE
    # Exactly one release leg, to the recipient; no money returned to payer.
    assert exe.releases == [RECIPIENT]
    assert exe.refunds == []
    assert resolved.refunded_minor == 0
    assert resolved.settle_tx_hash == "0xrelease"
    assert resolved.evidence.verify(secret=SECRET)


@pytest.mark.asyncio
async def test_no_double_move_across_legs():
    """A resolved hold cannot be settled again down either path — the money
    moved exactly once."""
    exe = RecordingEscrowExecutor()
    eng, _ = _engine(exe)
    hold = await _open(eng)
    await eng.dispute(hold.id, actor="payer")
    await eng.resolve(hold.id, resolution=Resolution.REFUND, actor="admin")

    with pytest.raises(Exception):
        await eng.resolve(hold.id, resolution=Resolution.RELEASE, actor="admin")
    with pytest.raises(Exception):
        await eng.release(hold.id)
    with pytest.raises(Exception):
        await eng.refund(hold.id)

    # Still exactly one money-movement, the original refund.
    assert exe.refunds == [(PAYER, HELD_MINOR)]
    assert exe.releases == []


@pytest.mark.asyncio
async def test_resolve_refund_partial_caps_at_held():
    """A partial resolve-refund moves only the requested minor-units to the payer;
    over-held is rejected before any leg fires (fail-closed)."""
    exe = RecordingEscrowExecutor()
    eng, _ = _engine(exe)
    hold = await _open(eng)
    await eng.dispute(hold.id, actor="payer")

    # Over the held amount -> rejected, no leg fired.
    with pytest.raises(Exception):
        await eng.resolve(
            hold.id,
            resolution=Resolution.REFUND,
            actor="admin",
            amount_minor=HELD_MINOR + 1,
        )
    assert exe.refunds == []

    # Partial within the held amount -> single refund leg for that amount.
    resolved = await eng.resolve(
        hold.id, resolution=Resolution.REFUND, actor="admin", amount_minor=40_000_000
    )
    assert resolved.status == RecourseStatus.RESOLVED
    assert exe.refunds == [(PAYER, 40_000_000)]


# ── vendored Circle RefundProtocol mapping ──────────────────────────────


class _FakeRefundProtocolClient:
    """Duck-typed chain client capturing the vendored-contract calls the
    RefundProtocolExecutor makes (no chain, no keys)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def pay(self, *, to, amount, refund_to):
        self.calls.append(("pay", to, amount, refund_to))
        return {"tx_hash": "0xpay", "payment_id": 42}

    async def withdraw(self, *, payment_ids):
        self.calls.append(("withdraw", tuple(payment_ids)))
        return {"tx_hash": "0xwithdraw"}

    async def refund_by_recipient(self, *, payment_id):
        self.calls.append(("refund_by_recipient", payment_id))
        return {"tx_hash": "0xrefund"}


@pytest.mark.asyncio
async def test_refund_protocol_executor_maps_contract_calls():
    """The live executor wraps the vendored Circle RefundProtocol:
    open->pay(to, amount, refundTo), release->withdraw([paymentID]),
    refund->refundByRecipient(paymentID)."""
    client = _FakeRefundProtocolClient()
    exe = RefundProtocolExecutor(client, contract_address="0xRefundProtocol")
    eng, _ = _engine(exe)

    hold = await _open(eng)
    # open_hold mapped to RefundProtocol.pay(to=recipient, amount, refundTo=payer)
    assert ("pay", RECIPIENT, HELD_MINOR, PAYER) in client.calls
    assert hold.escrow_payment_id == "42"
    assert hold.escrow_contract == "0xRefundProtocol"

    await eng.dispute(hold.id, actor="payer")
    await eng.resolve(hold.id, resolution=Resolution.RELEASE, actor="admin")
    # release mapped to withdraw([paymentID])
    assert ("withdraw", ("42",)) in client.calls


@pytest.mark.asyncio
async def test_refund_protocol_executor_refund_maps_to_recipient_call():
    client = _FakeRefundProtocolClient()
    exe = RefundProtocolExecutor(client, contract_address="0xRefundProtocol")
    eng, _ = _engine(exe)

    hold = await _open(eng)
    await eng.dispute(hold.id, actor="payer")
    await eng.resolve(hold.id, resolution=Resolution.REFUND, actor="admin")
    assert ("refund_by_recipient", "42") in client.calls


@pytest.mark.asyncio
async def test_refund_protocol_open_failure_keeps_hold_held():
    """If the vendored contract call raises on open, the hold records the error
    but stays held (fail-closed — the sweep can retry, nothing irreversibly
    moved)."""

    class _Boom(_FakeRefundProtocolClient):
        async def pay(self, *, to, amount, refund_to):
            raise RuntimeError("rpc down")

    exe = RefundProtocolExecutor(_Boom())
    eng, store = _engine(exe)
    hold = await _open(eng)
    assert hold.status == RecourseStatus.HELD
    persisted = await store.get(hold.id)
    assert persisted.metadata.get("open_error") == "rpc down"
