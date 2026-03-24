"""Tests for refund flow — full, partial, error cases."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_v2_core.refund import Refund, RefundService, RefundStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_payment(**overrides) -> dict:
    base = {
        "payment_id": "pay_test123",
        "org_id": "org_test",
        "amount": Decimal("100.00"),
        "currency": "USDC",
        "status": "completed",
        "chain": "base",
        "token": "USDC",
        "from_address": "0xSender",
        "to_address": "0xReceiver",
        "tx_hash": "0xoriginal",
        "refund_id": None,
    }
    base.update(overrides)
    return base


class FakeDB:
    """In-memory fake database for testing."""

    def __init__(self, payments: dict | None = None):
        self._payments = payments or {}
        self._refunds: dict[str, Refund] = {}

    async def get_pool(self):
        return self

    def acquire(self):
        return _FakeConn(self)


class _FakeConn:
    def __init__(self, db: FakeDB):
        self._db = db

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def fetchrow(self, query: str, *args):
        if "FROM payments" in query:
            payment_id = args[0]
            return self._db._payments.get(payment_id)
        if "FROM refunds" in query:
            payment_id = args[0]
            for r in self._db._refunds.values():
                if r.payment_id == payment_id:
                    return {
                        "refund_id": r.refund_id,
                        "payment_id": r.payment_id,
                        "org_id": r.org_id,
                        "amount": r.amount,
                        "currency": r.currency,
                        "reason": r.reason,
                        "status": r.status.value,
                        "reverse_tx_hash": r.reverse_tx_hash,
                        "error": r.error,
                        "created_at": r.created_at,
                        "completed_at": r.completed_at,
                    }
            return None
        return None

    async def execute(self, query: str, *args):
        # Capture refund saves
        if "INSERT INTO refunds" in query:
            refund_id = args[0]
            self._db._refunds[refund_id] = Refund(
                refund_id=refund_id,
                payment_id=args[1],
                org_id=args[2],
                amount=args[3],
                currency=args[4],
                reason=args[5],
                status=RefundStatus(args[6]),
                reverse_tx_hash=args[7],
                error=args[8],
                created_at=args[9],
                completed_at=args[10],
            )
        if "UPDATE payments" in query:
            payment_id = args[0]
            if payment_id in self._db._payments:
                self._db._payments[payment_id]["status"] = "refunded"
                self._db._payments[payment_id]["refund_id"] = args[1]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_full_refund():
    """Full refund of a completed payment should succeed."""
    payment = _make_payment()
    db = FakeDB(payments={payment["payment_id"]: payment})
    notification_svc = AsyncMock()

    svc = RefundService(database=db, notification_service=notification_svc)
    refund = await svc.initiate_refund(
        payment_id="pay_test123",
        org_id="org_test",
        reason="Customer requested refund",
    )

    assert refund.status == RefundStatus.COMPLETED
    assert refund.amount == Decimal("100.00")
    assert refund.reverse_tx_hash is not None
    assert refund.reverse_tx_hash.startswith("0xsim_")
    assert refund.completed_at is not None

    # Notification should be sent
    notification_svc.send.assert_called_once()
    call_args = notification_svc.send.call_args
    assert call_args.kwargs["event_type"] == "payment.refunded"


@pytest.mark.asyncio
async def test_successful_partial_refund():
    """Partial refund with amount < original should succeed."""
    payment = _make_payment()
    db = FakeDB(payments={payment["payment_id"]: payment})

    svc = RefundService(database=db)
    refund = await svc.initiate_refund(
        payment_id="pay_test123",
        org_id="org_test",
        reason="Partial refund for returned item",
        amount=Decimal("30.00"),
    )

    assert refund.status == RefundStatus.COMPLETED
    assert refund.amount == Decimal("30.00")


@pytest.mark.asyncio
async def test_refund_nonexistent_payment():
    """Refunding a payment that doesn't exist should raise ValueError."""
    db = FakeDB(payments={})

    svc = RefundService(database=db)
    with pytest.raises(ValueError, match="not found"):
        await svc.initiate_refund(
            payment_id="pay_nonexistent",
            org_id="org_test",
            reason="test",
        )


@pytest.mark.asyncio
async def test_refund_already_refunded():
    """Refunding an already-refunded payment should raise ValueError."""
    payment = _make_payment(refund_id="rfd_existing")
    db = FakeDB(payments={payment["payment_id"]: payment})

    svc = RefundService(database=db)
    with pytest.raises(ValueError, match="already been refunded"):
        await svc.initiate_refund(
            payment_id="pay_test123",
            org_id="org_test",
            reason="test",
        )


@pytest.mark.asyncio
async def test_refund_amount_exceeds_original():
    """Refund amount greater than original should raise ValueError."""
    payment = _make_payment()
    db = FakeDB(payments={payment["payment_id"]: payment})

    svc = RefundService(database=db)
    with pytest.raises(ValueError, match="exceeds"):
        await svc.initiate_refund(
            payment_id="pay_test123",
            org_id="org_test",
            reason="test",
            amount=Decimal("200.00"),
        )


@pytest.mark.asyncio
async def test_refund_non_completed_payment():
    """Refunding a payment that isn't completed should raise ValueError."""
    payment = _make_payment(status="pending")
    db = FakeDB(payments={payment["payment_id"]: payment})

    svc = RefundService(database=db)
    with pytest.raises(ValueError, match="only completed payments"):
        await svc.initiate_refund(
            payment_id="pay_test123",
            org_id="org_test",
            reason="test",
        )


@pytest.mark.asyncio
async def test_get_refund():
    """get_refund should return persisted refund record."""
    payment = _make_payment()
    db = FakeDB(payments={payment["payment_id"]: payment})

    svc = RefundService(database=db)
    refund = await svc.initiate_refund(
        payment_id="pay_test123",
        org_id="org_test",
        reason="test refund",
    )

    fetched = await svc.get_refund("pay_test123", "org_test")
    assert fetched is not None
    assert fetched.refund_id == refund.refund_id
    assert fetched.amount == Decimal("100.00")


@pytest.mark.asyncio
async def test_refund_triggers_failure_notification():
    """When reverse tx fails, payment.refund_failed notification should be sent."""
    payment = _make_payment()
    db = FakeDB(payments={payment["payment_id"]: payment})
    notification_svc = AsyncMock()

    # Mock chain executor that fails
    chain_executor = AsyncMock(side_effect=RuntimeError("chain unavailable"))

    svc = RefundService(
        database=db,
        chain_executor=chain_executor,
        notification_service=notification_svc,
    )
    # Set live mode to use the chain executor
    svc._chain_mode = "live"

    with pytest.raises(RuntimeError, match="chain unavailable"):
        await svc.initiate_refund(
            payment_id="pay_test123",
            org_id="org_test",
            reason="test",
        )

    # Should have sent refund_failed notification
    notification_svc.send.assert_called_once()
    call_args = notification_svc.send.call_args
    assert call_args.kwargs["event_type"] == "payment.refund_failed"
