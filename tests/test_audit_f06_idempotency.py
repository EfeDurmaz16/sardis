"""Test that execute_chain() is idempotent on mandate_id."""
import time
import pytest
from unittest.mock import AsyncMock, Mock
from sardis_v2_core.orchestrator import PaymentOrchestrator
from sardis_v2_core.mandates import (
    MandateChain, PaymentMandate, IntentMandate, CartMandate, VCProof,
)


def _proof():
    return VCProof(
        verification_method="did:key:test",
        created=str(int(time.time())),
        proof_value="dGVzdA==",
    )


def _base(mid, mtype, purpose):
    return dict(
        mandate_id=mid,
        mandate_type=mtype,
        issuer="agent:test",
        subject="agent:test",
        expires_at=int(time.time()) + 3600,
        nonce="nonce-1",
        proof=_proof(),
        domain="example.com",
        purpose=purpose,
    )


def make_chain(payment_id="pay-1"):
    intent = IntentMandate(
        **_base("intent-1", "intent", "intent"),
        scope=["payment"],
        requested_amount=1000,
    )
    cart = CartMandate(
        **_base("cart-1", "cart", "cart"),
        line_items=[{"id": "item1", "price": 1000}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=1000,
        taxes_minor=0,
    )
    payment = PaymentMandate(
        **_base(payment_id, "payment", "checkout"),
        chain="base",
        token="USDC",
        amount_minor=1000,
        destination="0x1234567890123456789012345678901234567890",
        audit_hash="test-hash",
    )
    return MandateChain(intent=intent, cart=cart, payment=payment)


@pytest.fixture
def mock_components():
    wallet_manager = Mock(spec=["validate_policies"])
    wallet_manager.validate_policies = Mock(return_value=Mock(allowed=True))

    compliance = Mock()
    compliance.preflight = AsyncMock(return_value=Mock(
        allowed=True, provider="mock", rule_id="mock_rule",
    ))

    chain_executor = AsyncMock()
    chain_executor.dispatch_payment = AsyncMock(return_value=Mock(
        tx_hash="0xabc123", chain="base", block_number=12345,
        audit_anchor="anchor",
    ))

    ledger = Mock()
    ledger.append = Mock(return_value=Mock(tx_id="ledger_tx_001"))

    return dict(
        wallet_manager=wallet_manager,
        compliance=compliance,
        chain_executor=chain_executor,
        ledger=ledger,
    )


@pytest.mark.asyncio
async def test_idempotency_blocks_duplicate_execution(mock_components):
    """Calling execute_chain twice with same mandate_id only executes once."""
    orchestrator = PaymentOrchestrator(**mock_components)
    chain = make_chain()

    result1 = await orchestrator.execute_chain(chain)
    result2 = await orchestrator.execute_chain(chain)

    assert result1 is result2
    assert mock_components["chain_executor"].dispatch_payment.call_count == 1
    assert mock_components["ledger"].append.call_count == 1


@pytest.mark.asyncio
async def test_idempotency_different_mandates_execute_separately(mock_components):
    """Different mandate_ids execute separately."""
    orchestrator = PaymentOrchestrator(**mock_components)

    result1 = await orchestrator.execute_chain(make_chain("pay-1"))
    result2 = await orchestrator.execute_chain(make_chain("pay-2"))

    assert result1 is not result2
    assert result1.mandate_id == "pay-1"
    assert result2.mandate_id == "pay-2"
    assert mock_components["chain_executor"].dispatch_payment.call_count == 2


@pytest.mark.asyncio
async def test_idempotency_preserves_reconciliation_pending_status(mock_components):
    """Idempotency works even when ledger append fails."""
    mock_components["ledger"].append = Mock(side_effect=Exception("Ledger failure"))
    orchestrator = PaymentOrchestrator(**mock_components)
    chain = make_chain()

    result1 = await orchestrator.execute_chain(chain)
    assert result1.status == "reconciliation_pending"
    assert result1.ledger_tx_id == "PENDING_RECONCILIATION"

    result2 = await orchestrator.execute_chain(chain)
    assert result1 is result2
    assert mock_components["chain_executor"].dispatch_payment.call_count == 1
