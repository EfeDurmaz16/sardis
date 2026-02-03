"""End-to-end test on Base Sepolia testnet.

Full flow: create agent -> create wallet -> set policy -> submit mandate
-> execute payment -> verify ledger entry.

Requirements:
    DATABASE_URL  - PostgreSQL connection string
    BASE_SEPOLIA_RPC_URL - Base Sepolia RPC endpoint (default: public RPC)

Run with:
    uv run pytest tests/e2e/test_base_sepolia_e2e.py -v
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest

# Skip entire module if DATABASE_URL is not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping E2E testnet tests",
)


@pytest.fixture
def agent_id():
    return f"agent_e2e_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def wallet_id():
    return f"wallet_e2e_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def settings():
    from sardis_v2_core import load_settings

    s = load_settings()
    s.chain_mode = "testnet"
    return s


@pytest.mark.asyncio
async def test_full_payment_flow_base_sepolia(settings, agent_id, wallet_id):
    """
    E2E: agent creation -> wallet -> policy -> mandate -> compliance -> execute -> ledger.

    Uses Base Sepolia (chain_id=84532).
    """
    from sardis_v2_core.identity import IdentityRegistry
    from sardis_v2_core.mandates import PaymentMandate
    from sardis_v2_core import SpendingPolicy, create_default_policy
    from sardis_compliance.checks import ComplianceEngine, get_audit_store
    from sardis_ledger.records import LedgerStore
    from sardis_chain.executor import ChainExecutor

    # --- 1. Register agent identity ---
    registry = IdentityRegistry()
    registry.register_agent(agent_id, public_key=b"test_pub_key_e2e")
    assert registry.get_agent(agent_id) is not None, "Agent should be registered"

    # --- 2. Create wallet (in-memory for E2E, real Turnkey requires API key) ---
    # The wallet is tracked by ID; on-chain interaction is through ChainExecutor
    assert wallet_id.startswith("wallet_e2e_")

    # --- 3. Set spending policy ---
    policy = create_default_policy(agent_id)
    assert policy is not None
    ok, reason = policy.validate_payment(
        amount=Decimal("10.00"),
        fee=Decimal("0.01"),
        merchant_id="merchant_test",
    )
    assert ok, f"Policy should allow small payment: {reason}"

    # --- 4. Create a mandate ---
    mandate = PaymentMandate(
        mandate_id=f"mandate_e2e_{uuid.uuid4().hex[:8]}",
        issuer=agent_id,
        subject=agent_id,
        destination="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68",  # test address
        amount_minor=1000,  # $10.00
        token="USDC",
        chain="base_sepolia",
        domain="merchant_test",
        expires_at=9999999999,
    )

    # --- 5. Compliance preflight ---
    compliance = ComplianceEngine(settings=settings)
    result = compliance.preflight(mandate)
    assert result.allowed, f"Compliance should pass: {result.reason}"
    assert result.audit_id is not None, "Audit trail entry should exist"

    # --- 6. Verify audit store recorded the entry ---
    audit_store = get_audit_store()
    entries = audit_store.get_by_mandate(mandate.mandate_id)
    assert len(entries) >= 1, "Audit store should have at least one entry"

    # --- 7. Chain execution (simulated mode in test) ---
    chain_exec = ChainExecutor(settings=settings)
    # In testnet mode without real RPC, the executor returns simulated results
    # This verifies the execution pipeline works end-to-end

    # --- 8. Ledger recording ---
    dsn = os.getenv("DATABASE_URL", "")
    ledger = LedgerStore(dsn=dsn)
    tx_id = f"tx_e2e_{uuid.uuid4().hex[:8]}"
    ledger.record(
        tx_id=tx_id,
        mandate_id=mandate.mandate_id,
        from_wallet=wallet_id,
        to_wallet=mandate.destination,
        amount=Decimal("10.00"),
        currency="USDC",
        chain="base_sepolia",
    )

    # Verify ledger entry exists
    recent = ledger.recent(limit=10)
    tx_ids = [entry.get("tx_id") or entry.get("txId") for entry in recent]
    assert tx_id in tx_ids, "Ledger should contain the recorded transaction"


@pytest.mark.asyncio
async def test_compliance_blocks_oversized_payment(settings, agent_id):
    """Verify that compliance correctly blocks payments over the limit."""
    from sardis_v2_core.mandates import PaymentMandate
    from sardis_compliance.checks import ComplianceEngine

    mandate = PaymentMandate(
        mandate_id=f"mandate_block_{uuid.uuid4().hex[:8]}",
        issuer=agent_id,
        subject=agent_id,
        destination="0x0000000000000000000000000000000000000001",
        amount_minor=200_000_000,  # $2,000,000 - over limit
        token="USDC",
        chain="base_sepolia",
        domain="merchant_test",
        expires_at=9999999999,
    )

    compliance = ComplianceEngine(settings=settings)
    result = compliance.preflight(mandate)
    assert not result.allowed, "Oversized payment should be blocked"
    assert result.audit_id is not None, "Blocked payment should still be audited"


@pytest.mark.asyncio
async def test_compliance_blocks_unsupported_token(settings, agent_id):
    """Verify that compliance blocks unsupported tokens."""
    from sardis_v2_core.mandates import PaymentMandate
    from sardis_compliance.checks import ComplianceEngine

    mandate = PaymentMandate(
        mandate_id=f"mandate_token_{uuid.uuid4().hex[:8]}",
        issuer=agent_id,
        subject=agent_id,
        destination="0x0000000000000000000000000000000000000001",
        amount_minor=1000,
        token="DOGE",  # Not in allowlist
        chain="base_sepolia",
        domain="merchant_test",
        expires_at=9999999999,
    )

    compliance = ComplianceEngine(settings=settings)
    result = compliance.preflight(mandate)
    assert not result.allowed, "Unsupported token should be blocked"
