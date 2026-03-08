"""Tests for the receipt store — save, get, verify, list."""

import pytest

from sardis_v2_core.execution_receipt import ExecutionReceipt, build_receipt
from sardis_v2_core.receipt_store import InMemoryReceiptStore


@pytest.mark.asyncio
async def test_save_and_get_roundtrip():
    """Save a receipt and retrieve it by ID."""
    store = InMemoryReceiptStore()
    receipt = build_receipt(
        intent={"test": "data"},
        tx_hash="0xabc123",
        chain="base",
        org_id="org_1",
        agent_id="agent_1",
        amount="100.00",
        currency="USDC",
    )

    await store.save(receipt)
    retrieved = await store.get(receipt.receipt_id)

    assert retrieved is not None
    assert retrieved.receipt_id == receipt.receipt_id
    assert retrieved.tx_hash == "0xabc123"
    assert retrieved.org_id == "org_1"


@pytest.mark.asyncio
async def test_get_by_tx_hash():
    """Retrieve a receipt by transaction hash."""
    store = InMemoryReceiptStore()
    receipt = build_receipt(
        tx_hash="0xdeadbeef",
        chain="base",
        org_id="org_1",
        agent_id="agent_1",
        amount="50.00",
        currency="USDC",
    )
    await store.save(receipt)

    retrieved = await store.get_by_tx_hash("0xdeadbeef")
    assert retrieved is not None
    assert retrieved.receipt_id == receipt.receipt_id


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none():
    """Getting a nonexistent receipt returns None."""
    store = InMemoryReceiptStore()
    assert await store.get("nonexistent") is None
    assert await store.get_by_tx_hash("0xnope") is None


@pytest.mark.asyncio
async def test_verify_valid_receipt():
    """Verify a valid receipt returns True."""
    store = InMemoryReceiptStore()
    receipt = build_receipt(
        tx_hash="0xvalid",
        chain="base",
        org_id="org_1",
        agent_id="agent_1",
        amount="100.00",
        currency="USDC",
    )
    await store.save(receipt)

    assert await store.verify(receipt.receipt_id) is True


@pytest.mark.asyncio
async def test_verify_tampered_receipt():
    """Tampered receipt fails verification."""
    store = InMemoryReceiptStore()
    receipt = build_receipt(
        tx_hash="0xtamper",
        chain="base",
        org_id="org_1",
        agent_id="agent_1",
        amount="100.00",
        currency="USDC",
    )
    await store.save(receipt)

    # Tamper with the stored receipt
    receipt.amount = "999999.00"

    assert await store.verify(receipt.receipt_id) is False


@pytest.mark.asyncio
async def test_verify_nonexistent_returns_false():
    """Verifying a nonexistent receipt returns False."""
    store = InMemoryReceiptStore()
    assert await store.verify("nonexistent") is False


@pytest.mark.asyncio
async def test_list_by_agent():
    """List receipts for a specific agent."""
    store = InMemoryReceiptStore()
    for i in range(5):
        receipt = build_receipt(
            tx_hash=f"0xagent_{i}",
            chain="base",
            org_id="org_1",
            agent_id="agent_A",
            amount=str(i * 10),
            currency="USDC",
        )
        await store.save(receipt)

    # Add one for a different agent
    other = build_receipt(
        tx_hash="0xother",
        chain="base",
        org_id="org_1",
        agent_id="agent_B",
        amount="99",
        currency="USDC",
    )
    await store.save(other)

    results = await store.list_by_agent("agent_A")
    assert len(results) == 5
    assert all(r.agent_id == "agent_A" for r in results)


@pytest.mark.asyncio
async def test_list_by_org():
    """List receipts for a specific org."""
    store = InMemoryReceiptStore()
    for i in range(3):
        receipt = build_receipt(
            tx_hash=f"0xorg_{i}",
            chain="base",
            org_id="org_X",
            agent_id=f"agent_{i}",
            amount="10",
            currency="USDC",
        )
        await store.save(receipt)

    results = await store.list_by_org("org_X")
    assert len(results) == 3


@pytest.mark.asyncio
async def test_duplicate_save_raises():
    """Saving the same receipt twice raises ValueError."""
    store = InMemoryReceiptStore()
    receipt = build_receipt(
        tx_hash="0xdup",
        chain="base",
        org_id="org_1",
        agent_id="agent_1",
        amount="10",
        currency="USDC",
    )
    await store.save(receipt)

    with pytest.raises(ValueError, match="already exists"):
        await store.save(receipt)
