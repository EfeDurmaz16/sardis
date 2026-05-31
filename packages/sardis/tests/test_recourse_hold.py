"""Tests for the Programmable Recourse primitive (RecourseHold).

Pins the fail-closed contract of the thin recourse engine:

* a recourse-windowed payment opens a durable, signed RecourseHold (held);
* release on window expiry settles to the recipient;
* refund within the window returns funds to the payer (<= held);
* a second release is blocked (no double-release);
* a refund over the held amount is blocked;
* dispute -> resolve goes down exactly one path (refund OR release);
* every transition carries verifiable signed evidence.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from sardis.core.recourse_engine import RecourseEngine
from sardis.core.recourse_executor import ExecutionRef, NoopRecourseExecutor
from sardis.core.recourse_hold import (
    RecourseAmountError,
    RecourseStateError,
    RecourseStatus,
    Resolution,
    build_recourse_hold,
)
from sardis.core.recourse_hold_repository import InMemoryRecourseHoldStore

SECRET = "test-recourse-secret"


def _engine(executor=None):
    store = InMemoryRecourseHoldStore()
    eng = RecourseEngine(store=store, executor=executor, signing_secret=SECRET)
    return eng, store


async def _open(eng, *, amount_minor=100_000_000, window_seconds=3600):
    return await eng.open_hold(
        payment_ref="po_rch_001",
        mandate_id="mdt_rch_001",
        agent_id="agent_rch",
        amount=Decimal(amount_minor) / Decimal(10**6),
        amount_minor=amount_minor,
        currency="USDC",
        payer="0x" + "aa" * 20,
        recipient="0x" + "bb" * 20,
        window_seconds=window_seconds,
        policy_hash="pol_hash",
        mandate_hash="mdt_hash",
    )


# ── domain-level state machine ─────────────────────────────────────────


def test_build_hold_starts_held_with_window():
    hold = build_recourse_hold(
        payment_ref="po_x", mandate_id="m", agent_id="a",
        amount=Decimal("100"), amount_minor=100_000_000, currency="USDC",
        payer="payer", recipient="recip", window_seconds=3600,
    )
    assert hold.id.startswith("rch_")
    assert hold.status == RecourseStatus.HELD
    assert hold.refundable_minor == 100_000_000
    assert hold.expires_at > hold.opened_at


def test_zero_window_rejected():
    with pytest.raises(ValueError):
        build_recourse_hold(
            payment_ref="p", mandate_id="m", agent_id="a", amount="1",
            amount_minor=1_000_000, currency="USDC", payer="x", recipient="y",
            window_seconds=0,
        )


def test_release_signs_evidence_and_is_terminal():
    hold = build_recourse_hold(
        payment_ref="p", mandate_id="m", agent_id="a", amount="100",
        amount_minor=100_000_000, currency="USDC", payer="x", recipient="y",
        window_seconds=3600,
    )
    ev = hold.release(secret=SECRET)
    assert hold.status == RecourseStatus.RELEASED
    assert hold.resolution == Resolution.RELEASE
    assert ev.decision == "released"
    assert ev.verify(secret=SECRET)
    assert hold.is_terminal()


def test_double_release_blocked():
    hold = build_recourse_hold(
        payment_ref="p", mandate_id="m", agent_id="a", amount="100",
        amount_minor=100_000_000, currency="USDC", payer="x", recipient="y",
        window_seconds=3600,
    )
    hold.release(secret=SECRET)
    with pytest.raises(RecourseStateError):
        hold.release(secret=SECRET)


def test_refund_over_amount_blocked():
    hold = build_recourse_hold(
        payment_ref="p", mandate_id="m", agent_id="a", amount="100",
        amount_minor=100_000_000, currency="USDC", payer="x", recipient="y",
        window_seconds=3600,
    )
    with pytest.raises(RecourseAmountError):
        hold.refund(amount_minor=100_000_001, secret=SECRET)


def test_refund_then_release_blocked():
    hold = build_recourse_hold(
        payment_ref="p", mandate_id="m", agent_id="a", amount="100",
        amount_minor=100_000_000, currency="USDC", payer="x", recipient="y",
        window_seconds=3600,
    )
    hold.refund(secret=SECRET)
    assert hold.status == RecourseStatus.REFUNDED
    with pytest.raises(RecourseStateError):
        hold.release(secret=SECRET)


def test_resolve_requires_dispute_first():
    hold = build_recourse_hold(
        payment_ref="p", mandate_id="m", agent_id="a", amount="100",
        amount_minor=100_000_000, currency="USDC", payer="x", recipient="y",
        window_seconds=3600,
    )
    # Cannot resolve a hold that is not disputed.
    with pytest.raises(RecourseStateError):
        hold.resolve(resolution=Resolution.REFUND, actor="arb", secret=SECRET)


def test_dispute_resolve_single_path():
    hold = build_recourse_hold(
        payment_ref="p", mandate_id="m", agent_id="a", amount="100",
        amount_minor=100_000_000, currency="USDC", payer="x", recipient="y",
        window_seconds=3600,
    )
    hold.dispute(actor="payer", reason="not delivered", secret=SECRET)
    assert hold.status == RecourseStatus.DISPUTED
    ev = hold.resolve(resolution=Resolution.REFUND, actor="arbiter", secret=SECRET)
    assert hold.status == RecourseStatus.RESOLVED
    assert hold.resolution == Resolution.REFUND
    assert ev.decision == "resolved_refund"
    assert ev.verify(secret=SECRET)
    # A second resolution is blocked.
    with pytest.raises(RecourseStateError):
        hold.resolve(resolution=Resolution.RELEASE, actor="arbiter", secret=SECRET)


# ── engine-level (store + executor) ────────────────────────────────────


@pytest.mark.asyncio
async def test_engine_open_persists_and_records_execution():
    eng, store = _engine()
    hold = await _open(eng)
    assert hold.status == RecourseStatus.HELD
    persisted = await store.get(hold.id)
    assert persisted is not None
    assert persisted.open_tx_hash  # noop executor recorded a synthetic tx
    assert persisted.escrow_payment_id


@pytest.mark.asyncio
async def test_engine_release_settles_to_recipient():
    eng, store = _engine()
    hold = await _open(eng)
    released = await eng.release(hold.id)
    assert released.status == RecourseStatus.RELEASED
    assert released.resolution == Resolution.RELEASE
    assert released.settle_tx_hash
    assert released.evidence.verify(secret=SECRET)


@pytest.mark.asyncio
async def test_engine_refund_within_window():
    eng, store = _engine()
    hold = await _open(eng)
    refunded = await eng.refund(hold.id, amount_minor=40_000_000)
    assert refunded.status == RecourseStatus.REFUNDED
    assert refunded.resolution == Resolution.REFUND
    assert refunded.refunded_minor == 40_000_000
    assert refunded.evidence.verify(secret=SECRET)


@pytest.mark.asyncio
async def test_engine_double_release_blocked():
    eng, store = _engine()
    hold = await _open(eng)
    await eng.release(hold.id)
    with pytest.raises(RecourseStateError):
        await eng.release(hold.id)


@pytest.mark.asyncio
async def test_engine_refund_over_amount_blocked():
    eng, store = _engine()
    hold = await _open(eng, amount_minor=50_000_000)
    with pytest.raises(RecourseAmountError):
        await eng.refund(hold.id, amount_minor=50_000_001)
    # Still held — fail-closed, nothing moved.
    persisted = await store.get(hold.id)
    assert persisted.status == RecourseStatus.HELD


@pytest.mark.asyncio
async def test_engine_failed_execution_keeps_hold_non_terminal():
    """If the executor reports failure on release, the hold must NOT advance."""

    class _FailingReleaseExecutor(NoopRecourseExecutor):
        async def settle_release(self, hold):
            return ExecutionRef(ok=False, provider="noop", error="boom")

    eng, store = _engine(executor=_FailingReleaseExecutor())
    hold = await _open(eng)
    with pytest.raises(RuntimeError):
        await eng.release(hold.id)
    # The persisted row is still held (the in-domain advance was never saved).
    persisted = await store.get(hold.id)
    assert persisted.status == RecourseStatus.HELD


@pytest.mark.asyncio
async def test_engine_sweep_releases_only_expired():
    eng, store = _engine()
    fresh = await _open(eng, window_seconds=3600)
    # Manually craft an already-expired held hold directly in the store.
    expired = build_recourse_hold(
        payment_ref="po_exp", mandate_id="m2", agent_id="a", amount="10",
        amount_minor=10_000_000, currency="USDC", payer="x", recipient="y",
        window_seconds=1,
    )
    expired.expires_at = datetime.now(UTC) - timedelta(seconds=10)
    await store.create(expired)

    released = await eng.sweep_expired()
    assert expired.id in released
    assert fresh.id not in released
    assert (await store.get(expired.id)).status == RecourseStatus.RELEASED
    assert (await store.get(fresh.id)).status == RecourseStatus.HELD


@pytest.mark.asyncio
async def test_engine_dispute_pauses_auto_release():
    eng, store = _engine()
    hold = await _open(eng, window_seconds=1)
    await eng.dispute(hold.id, actor="payer", reason="late")
    # Force the window past expiry.
    disputed = await store.get(hold.id)
    disputed.expires_at = datetime.now(UTC) - timedelta(seconds=10)
    await store.save(disputed)
    # Sweep must NOT release a disputed hold.
    released = await eng.sweep_expired()
    assert hold.id not in released
    assert (await store.get(hold.id)).status == RecourseStatus.DISPUTED
    # Resolve it explicitly to release.
    resolved = await eng.resolve(hold.id, resolution=Resolution.RELEASE, actor="arbiter")
    assert resolved.status == RecourseStatus.RESOLVED
    assert resolved.resolution == Resolution.RELEASE
