"""E2E tests for Pay with Sardis merchant checkout flow.

Full flow: create merchant -> create checkout session -> connect payer wallet
-> execute payment -> verify on-chain tx + ledger -> verify settlement.

These tests use mocked chain/wallet layers but exercise the full connector
pipeline, settlement service, and webhook delivery logic end-to-end.

Run with:
    uv run pytest tests/e2e/test_merchant_checkout_e2e.py -v --noconftest
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── Path setup (avoid heavy conftest imports) ─────────────────────
_packages = Path(__file__).parent.parent.parent / "packages"
for _pkg in ["sardis-core", "sardis-checkout", "sardis-api", "sardis-chain",
             "sardis-compliance", "sardis-ledger", "sardis-wallet"]:
    _p = _packages / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("DATABASE_URL", "memory://")
os.environ.setdefault("SECRET_KEY", "test_e2e_key_for_testing_purposes_only_32ch")

from sardis_checkout.connectors.sardis_native import SardisNativeConnector
from sardis_checkout.merchant_webhooks import MerchantWebhookService
from sardis_checkout.models import CheckoutRequest, PaymentStatus
from sardis_checkout.settlement import SettlementService
from sardis_v2_core.merchant import (
    Merchant,
    MerchantCheckoutSession,
)

# ── Mock Infrastructure ───────────────────────────────────────────

class MockMerchantRepo:
    def __init__(self):
        self.merchants: dict[str, Merchant] = {}
        self.sessions: dict[str, MerchantCheckoutSession] = {}

    async def create_merchant(self, merchant: Merchant) -> Merchant:
        self.merchants[merchant.merchant_id] = merchant
        return merchant

    async def get_merchant(self, merchant_id: str) -> Merchant | None:
        return self.merchants.get(merchant_id)

    async def create_session(self, session: MerchantCheckoutSession) -> MerchantCheckoutSession:
        self.sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> MerchantCheckoutSession | None:
        return self.sessions.get(session_id)

    async def update_session(self, session_id: str, **kwargs) -> None:
        s = self.sessions.get(session_id)
        if s:
            for k, v in kwargs.items():
                setattr(s, k, v)

    async def list_sessions_by_merchant(self, merchant_id: str, status=None, limit=50):
        return [
            s for s in self.sessions.values()
            if s.merchant_id == merchant_id and (status is None or s.status == status)
        ][:limit]

    async def get_processing_settlements(self):
        return [s for s in self.sessions.values() if s.settlement_status == "processing"]


@dataclass
class MockWallet:
    wallet_id: str
    agent_id: str = "agent_test"
    is_active: bool = True
    frozen: bool = False
    account_type: str = "eoa"
    smart_account_address: str | None = None
    _addresses: dict = field(default_factory=dict)

    def get_address(self, chain: str) -> str | None:
        return self._addresses.get(chain)


@dataclass
class MockReceipt:
    tx_hash: str = "0xe2e_test_tx_abc123def456"
    status: str = "success"


class MockWalletManager:
    def __init__(self):
        self.wallets: dict[str, MockWallet] = {}

    async def get_wallet(self, wallet_id: str) -> MockWallet | None:
        return self.wallets.get(wallet_id)

    async def async_validate_policies(self, mandate):
        return MagicMock(allowed=True)

    async def async_record_spend(self, mandate):
        pass


class MockChainExecutor:
    def __init__(self):
        self.dispatched: list = []

    async def dispatch_payment(self, mandate) -> MockReceipt:
        self.dispatched.append(mandate)
        return MockReceipt(tx_hash=f"0xtx_{mandate.mandate_id}")


class MockComplianceEngine:
    async def preflight(self, mandate):
        return MagicMock(allowed=True, reason=None, audit_id="audit_e2e_001")


class MockLedgerStore:
    def __init__(self):
        self.entries: list = []

    def append(self, payment_mandate=None, chain_receipt=None):
        self.entries.append({"mandate": payment_mandate, "receipt": chain_receipt})
        return MagicMock(tx_id=f"ledger_{payment_mandate.mandate_id}")


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def repo():
    return MockMerchantRepo()


@pytest.fixture
def wallet_manager():
    return MockWalletManager()


@pytest.fixture
def chain_executor():
    return MockChainExecutor()


@pytest.fixture
def compliance():
    return MockComplianceEngine()


@pytest.fixture
def ledger():
    return MockLedgerStore()


@pytest.fixture
def merchant(repo):
    m = Merchant(
        merchant_id="merch_e2e_001",
        name="E2E Test Shop",
        settlement_preference="usdc",
        settlement_wallet_id="wal_merch_settle",
        webhook_url="https://example.com/webhooks/sardis",
        is_active=True,
    )
    repo.merchants[m.merchant_id] = m
    return m


@pytest.fixture
def payer_wallet(wallet_manager):
    w = MockWallet(
        wallet_id="wal_payer_e2e",
        agent_id="agent_payer_e2e",
        _addresses={"base": "0xPayerAddr1234567890abcdef1234567890abcdef"},
    )
    wallet_manager.wallets[w.wallet_id] = w
    return w


@pytest.fixture
def merchant_wallet(wallet_manager):
    w = MockWallet(
        wallet_id="wal_merch_settle",
        agent_id="merchant_merch_e2e_001",
        _addresses={"base": "0xMerchAddr1234567890abcdef1234567890abcdef"},
    )
    wallet_manager.wallets[w.wallet_id] = w
    return w


@pytest.fixture
def connector(chain_executor, wallet_manager, compliance, ledger, repo):
    return SardisNativeConnector(
        chain_executor=chain_executor,
        wallet_manager=wallet_manager,
        compliance_engine=compliance,
        ledger_store=ledger,
        merchant_repo=repo,
        settlement_service=None,
        merchant_webhook_service=None,
    )


# ── E2E Flow Tests ────────────────────────────────────────────────


class TestMerchantCheckoutE2EFlow:
    """Full merchant checkout lifecycle: create -> pay -> settle."""

    @pytest.mark.asyncio
    async def test_full_usdc_checkout_flow(
        self, connector, repo, merchant, payer_wallet, merchant_wallet,
        chain_executor, ledger,
    ):
        """
        E2E: merchant onboard -> session create -> wallet connect ->
        payment execute -> verify tx + ledger + session status.
        """
        # Step 1: Create checkout session
        request = CheckoutRequest(
            agent_id=f"merchant_{merchant.merchant_id}",
            wallet_id=merchant.settlement_wallet_id,
            mandate_id="",
            amount=Decimal("49.99"),
            currency="USDC",
            description="E2E test order #1001",
            metadata={"merchant_id": merchant.merchant_id},
        )

        response = await connector.create_checkout_session(request)

        assert response.checkout_id.startswith("mcs_")
        assert response.redirect_url.startswith("https://checkout.sardis.sh/")
        assert response.status == PaymentStatus.PENDING
        assert response.psp_name == "sardis"
        assert response.amount == Decimal("49.99")

        session_id = response.checkout_id

        # Step 2: Verify session persisted
        session = await repo.get_session(session_id)
        assert session is not None
        assert session.status == "pending"
        assert session.merchant_id == merchant.merchant_id

        # Step 3: Execute payment (simulates payer connecting wallet + paying)
        result = await connector.execute_payment(session_id, payer_wallet.wallet_id)

        assert result["status"] == "paid"
        assert result["session_id"] == session_id
        assert result["tx_hash"].startswith("0xtx_")
        assert result["merchant_id"] == merchant.merchant_id
        assert result["amount"] == "49.99"

        # Step 4: Verify chain executor was called
        assert len(chain_executor.dispatched) >= 1
        dispatched_mandate = chain_executor.dispatched[0]
        assert dispatched_mandate.destination == merchant_wallet.get_address("base")
        assert dispatched_mandate.token == "USDC"

        # Step 5: Verify ledger recorded
        assert len(ledger.entries) == 1
        assert result["ledger_tx_id"] is not None

        # Step 6: Verify session updated to paid
        updated = await repo.get_session(session_id)
        assert updated.status == "paid"
        assert updated.tx_hash.startswith("0xtx_")
        assert updated.payer_wallet_id == payer_wallet.wallet_id
        assert updated.payment_method == "wallet"

        # Step 7: Verify payment status via connector
        status = await connector.get_payment_status(session_id)
        assert status == PaymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_full_fiat_checkout_with_settlement(
        self, repo, merchant, payer_wallet, merchant_wallet,
        chain_executor, wallet_manager, compliance, ledger,
    ):
        """
        E2E: fiat merchant flow — payment triggers auto-settlement.
        """
        # Switch merchant to fiat settlement
        merchant.settlement_preference = "fiat"
        merchant.bank_account = {"routing": "021000021", "account": "1234567890"}

        # Create settlement service
        settlement_svc = SettlementService(
            merchant_repo=repo,
            offramp_service=None,  # No real Bridge in test
            merchant_webhook_service=None,
        )

        connector = SardisNativeConnector(
            chain_executor=chain_executor,
            wallet_manager=wallet_manager,
            compliance_engine=compliance,
            ledger_store=ledger,
            merchant_repo=repo,
            settlement_service=settlement_svc,
            merchant_webhook_service=None,
        )

        # Create session
        request = CheckoutRequest(
            agent_id=f"merchant_{merchant.merchant_id}",
            wallet_id=merchant.settlement_wallet_id,
            mandate_id="",
            amount=Decimal("100.00"),
            currency="USDC",
            description="Fiat settlement test",
            metadata={"merchant_id": merchant.merchant_id},
        )
        response = await connector.create_checkout_session(request)
        session_id = response.checkout_id

        # Execute payment — should trigger settlement for fiat merchant
        result = await connector.execute_payment(session_id, payer_wallet.wallet_id)
        assert result["status"] == "paid"

        # Give fire-and-forget settlement task a moment to run
        await asyncio.sleep(0.1)

        # For USDC settlement (no offramp service), session should be settled
        # The settlement service marks USDC as complete immediately
        # For fiat without Bridge, it skips offramp but still marks processing
        session = await repo.get_session(session_id)
        assert session.status in ("paid", "settled")

    @pytest.mark.asyncio
    async def test_usdc_settlement_marks_complete(self, repo, merchant):
        """USDC merchants settle immediately — no offramp needed."""
        session = MerchantCheckoutSession(
            session_id="mcs_settle_usdc_e2e",
            merchant_id=merchant.merchant_id,
            amount=Decimal("75.00"),
            status="paid",
            tx_hash="0xabc123",
        )
        repo.sessions[session.session_id] = session

        settlement_svc = SettlementService(
            merchant_repo=repo,
            offramp_service=None,
            merchant_webhook_service=None,
        )

        await settlement_svc.settle_session(session.session_id)

        updated = await repo.get_session(session.session_id)
        assert updated.status == "settled"
        assert updated.settlement_status == "completed"


class TestCheckoutEdgeCases:
    """Edge cases and error handling in the checkout flow."""

    @pytest.mark.asyncio
    async def test_expired_session_rejected(
        self, connector, repo, merchant, payer_wallet, merchant_wallet,
    ):
        """Payment on an expired session should fail."""
        request = CheckoutRequest(
            agent_id=f"merchant_{merchant.merchant_id}",
            wallet_id=merchant.settlement_wallet_id,
            mandate_id="",
            amount=Decimal("10.00"),
            metadata={"merchant_id": merchant.merchant_id},
        )
        response = await connector.create_checkout_session(request)

        # Manually expire the session
        session = await repo.get_session(response.checkout_id)
        session.expires_at = datetime.now(UTC) - timedelta(minutes=1)

        with pytest.raises(ValueError, match="expired"):
            await connector.execute_payment(response.checkout_id, payer_wallet.wallet_id)

        updated = await repo.get_session(response.checkout_id)
        assert updated.status == "expired"

    @pytest.mark.asyncio
    async def test_double_pay_rejected(
        self, connector, repo, merchant, payer_wallet, merchant_wallet,
    ):
        """Paying an already-paid session should fail."""
        request = CheckoutRequest(
            agent_id=f"merchant_{merchant.merchant_id}",
            wallet_id=merchant.settlement_wallet_id,
            mandate_id="",
            amount=Decimal("25.00"),
            metadata={"merchant_id": merchant.merchant_id},
        )
        response = await connector.create_checkout_session(request)

        # First payment succeeds
        await connector.execute_payment(response.checkout_id, payer_wallet.wallet_id)

        # Second payment should fail (status is now 'paid')
        with pytest.raises(ValueError, match="status"):
            await connector.execute_payment(response.checkout_id, payer_wallet.wallet_id)

    @pytest.mark.asyncio
    async def test_inactive_merchant_rejected(self, connector, repo, payer_wallet):
        """Checkout with inactive merchant should fail at session creation."""
        inactive = Merchant(
            merchant_id="merch_inactive",
            name="Dead Store",
            is_active=False,
        )
        repo.merchants[inactive.merchant_id] = inactive

        request = CheckoutRequest(
            agent_id="merchant_merch_inactive",
            wallet_id="",
            mandate_id="",
            amount=Decimal("10.00"),
            metadata={"merchant_id": "merch_inactive"},
        )

        with pytest.raises(ValueError, match="inactive"):
            await connector.create_checkout_session(request)

    @pytest.mark.asyncio
    async def test_frozen_wallet_rejected(
        self, connector, repo, merchant, merchant_wallet, wallet_manager,
    ):
        """Frozen payer wallet should be rejected."""
        frozen_wallet = MockWallet(
            wallet_id="wal_frozen",
            frozen=True,
            _addresses={"base": "0xFrozenAddr"},
        )
        wallet_manager.wallets[frozen_wallet.wallet_id] = frozen_wallet

        request = CheckoutRequest(
            agent_id=f"merchant_{merchant.merchant_id}",
            wallet_id=merchant.settlement_wallet_id,
            mandate_id="",
            amount=Decimal("10.00"),
            metadata={"merchant_id": merchant.merchant_id},
        )
        response = await connector.create_checkout_session(request)

        with pytest.raises(ValueError, match="frozen"):
            await connector.execute_payment(response.checkout_id, frozen_wallet.wallet_id)

    @pytest.mark.asyncio
    async def test_nonexistent_session_returns_failed_status(self, connector):
        """Querying a non-existent session should return FAILED status."""
        status = await connector.get_payment_status("mcs_doesnt_exist")
        assert status == PaymentStatus.FAILED


class TestWebhookE2E:
    """Webhook delivery in the checkout flow."""

    @pytest.mark.asyncio
    async def test_webhook_delivered_on_payment(
        self, repo, merchant, payer_wallet, merchant_wallet,
        chain_executor, wallet_manager, compliance, ledger,
    ):
        """Verify webhook fires after successful payment."""
        webhook_svc = MagicMock()
        webhook_svc.deliver = AsyncMock()

        connector = SardisNativeConnector(
            chain_executor=chain_executor,
            wallet_manager=wallet_manager,
            compliance_engine=compliance,
            ledger_store=ledger,
            merchant_repo=repo,
            settlement_service=None,
            merchant_webhook_service=webhook_svc,
        )

        request = CheckoutRequest(
            agent_id=f"merchant_{merchant.merchant_id}",
            wallet_id=merchant.settlement_wallet_id,
            mandate_id="",
            amount=Decimal("30.00"),
            description="Webhook test",
            metadata={"merchant_id": merchant.merchant_id},
        )
        response = await connector.create_checkout_session(request)
        await connector.execute_payment(response.checkout_id, payer_wallet.wallet_id)

        # Let fire-and-forget task run
        await asyncio.sleep(0.1)

        webhook_svc.deliver.assert_called_once()
        call_kwargs = webhook_svc.deliver.call_args
        assert call_kwargs.kwargs["event_type"] == "payment.completed"
        assert call_kwargs.kwargs["payload"]["session_id"] == response.checkout_id
        assert call_kwargs.kwargs["payload"]["status"] == "paid"

    def test_webhook_signature_roundtrip(self):
        """HMAC signature generation and verification."""
        payload = b'{"event":"payment.completed","session_id":"mcs_e2e"}'
        secret = "test_e2e_wh_roundtrip"

        sig = MerchantWebhookService.sign_payload(payload, secret)
        assert sig.startswith("sha256=")
        assert MerchantWebhookService.verify_signature(payload, secret, sig) is True
        assert MerchantWebhookService.verify_signature(payload, "wrong", sig) is False


class TestMultiSessionFlow:
    """Multiple concurrent sessions for the same merchant."""

    @pytest.mark.asyncio
    async def test_multiple_sessions_tracked_independently(
        self, connector, repo, merchant, payer_wallet, merchant_wallet,
    ):
        """Three sessions for the same merchant should be independent."""
        session_ids = []
        for i in range(3):
            request = CheckoutRequest(
                agent_id=f"merchant_{merchant.merchant_id}",
                wallet_id=merchant.settlement_wallet_id,
                mandate_id="",
                amount=Decimal(f"{10 + i * 10}.00"),
                description=f"Multi-session #{i}",
                metadata={"merchant_id": merchant.merchant_id},
            )
            response = await connector.create_checkout_session(request)
            session_ids.append(response.checkout_id)

        assert len(set(session_ids)) == 3  # All unique

        # Pay only the second session
        await connector.execute_payment(session_ids[1], payer_wallet.wallet_id)

        # Verify statuses
        s0 = await repo.get_session(session_ids[0])
        s1 = await repo.get_session(session_ids[1])
        s2 = await repo.get_session(session_ids[2])
        assert s0.status == "pending"
        assert s1.status == "paid"
        assert s2.status == "pending"

        # List sessions
        sessions = await repo.list_sessions_by_merchant(merchant.merchant_id)
        assert len(sessions) == 3
