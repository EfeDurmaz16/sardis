"""Tests for x402 upto scheme — streaming micropayments."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sardis_protocol.x402_upto import UptoSession, build_permit2_typed_data


@pytest.mark.asyncio
async def test_incremental_consumption():
    """Test consuming amounts incrementally."""
    session = UptoSession(max_amount=Decimal("10"))

    c1 = await session.consume("3")
    assert c1.cumulative == "3"
    assert c1.remaining == "7"

    c2 = await session.consume("5")
    assert c2.cumulative == "8"
    assert c2.remaining == "2"


@pytest.mark.asyncio
async def test_exceed_max_rejected():
    """Consuming beyond max_amount raises ValueError."""
    session = UptoSession(max_amount=Decimal("5"))

    await session.consume("3")

    with pytest.raises(ValueError, match="upto_exceed_max"):
        await session.consume("3")  # 3 + 3 = 6 > 5


@pytest.mark.asyncio
async def test_finalize_settles_consumed():
    """Finalizing returns the total consumed amount."""
    session = UptoSession(max_amount=Decimal("100"), payment_id="x402_test")

    await session.consume("25")
    await session.consume("30")

    settlement = await session.finalize()
    assert settlement.total_consumed == "55"
    assert settlement.max_amount == "100"
    assert settlement.payment_id == "x402_test"


@pytest.mark.asyncio
async def test_finalize_twice_raises():
    """Cannot finalize a session that's already finalized."""
    session = UptoSession(max_amount=Decimal("10"))
    await session.consume("5")
    await session.finalize()

    with pytest.raises(ValueError, match="already_finalized"):
        await session.finalize()


@pytest.mark.asyncio
async def test_consume_after_finalize_raises():
    """Cannot consume from a finalized session."""
    session = UptoSession(max_amount=Decimal("10"))
    await session.consume("5")
    await session.finalize()

    with pytest.raises(ValueError, match="finalized"):
        await session.consume("1")


@pytest.mark.asyncio
async def test_get_remaining():
    """get_remaining() returns correct remaining amount."""
    session = UptoSession(max_amount=Decimal("10"))
    assert session.get_remaining() == "10"

    await session.consume("3")
    assert session.get_remaining() == "7"


def test_build_permit2_typed_data():
    """Permit2 typed data has correct structure."""
    data = build_permit2_typed_data(
        token="0x" + "a" * 40,
        spender="0x" + "b" * 40,
        amount=1000000,
        nonce=1,
        deadline=9999999999,
    )

    assert data["primaryType"] == "PermitSingle"
    assert "PermitDetails" in data["types"]
    assert data["domain"]["name"] == "Permit2"
    assert data["message"]["details"]["token"] == "0x" + "a" * 40
    assert data["message"]["details"]["amount"] == "1000000"
