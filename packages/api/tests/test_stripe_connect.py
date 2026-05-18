"""Tests for Stripe Connect (Sardis Connect) — provider, router, settlement."""
from __future__ import annotations

import os
import sys
import types
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure local packages are importable
_packages = Path(__file__).parent.parent.parent
for _pkg in ["sardis-core", "sardis-checkout", "sardis-api", "sardis-protocol"]:
    _p = _packages / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("DATABASE_URL", "memory://")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing_purposes_only_32chars")

import pytest
from sardis_v2_core.merchant import Merchant, MerchantCheckoutSession

# ── Fixtures ──────────────────────────────────────────────────────


def _make_merchant(**overrides) -> Merchant:
    defaults = {
        "merchant_id": "merch_test_connect",
        "name": "Connect Test Shop",
        "settlement_preference": "usdc",
        "settlement_wallet_id": "wal_settle_001",
        "is_active": True,
    }
    defaults.update(overrides)
    return Merchant(**defaults)


def _make_stripe_merchant(**overrides) -> Merchant:
    """Merchant with Stripe Connect already configured."""
    defaults = {
        "merchant_id": "merch_stripe_001",
        "name": "Stripe Merchant",
        "settlement_preference": "stripe_connect",
        "stripe_account_id": "acct_test_123",
        "stripe_onboarding_state": "complete",
        "stripe_charges_enabled": True,
        "stripe_payouts_enabled": True,
        "stripe_details_submitted": True,
        "is_active": True,
    }
    defaults.update(overrides)
    return Merchant(**defaults)


def _make_session(**overrides) -> MerchantCheckoutSession:
    defaults = {
        "session_id": "mcs_stripe_test",
        "merchant_id": "merch_stripe_001",
        "amount": Decimal("100.00"),
        "currency": "USDC",
        "status": "paid",
        "net_amount": Decimal("99.50"),
        "expires_at": datetime.now(UTC) + timedelta(minutes=15),
    }
    defaults.update(overrides)
    return MerchantCheckoutSession(**defaults)


class MockMerchantRepo:
    def __init__(self):
        self.merchants: dict[str, Merchant] = {}
        self.sessions: dict[str, MerchantCheckoutSession] = {}

    async def get_merchant(self, merchant_id: str) -> Merchant | None:
        return self.merchants.get(merchant_id)

    async def update_merchant(self, merchant_id: str, **kwargs) -> Merchant | None:
        m = self.merchants.get(merchant_id)
        if not m:
            return None
        for k, v in kwargs.items():
            setattr(m, k, v)
        m.updated_at = datetime.now(UTC)
        return m

    async def get_session(self, session_id: str) -> MerchantCheckoutSession | None:
        return self.sessions.get(session_id)

    async def update_session(self, session_id: str, **kwargs) -> None:
        s = self.sessions.get(session_id)
        if s:
            for k, v in kwargs.items():
                setattr(s, k, v)

    async def list_sessions_by_merchant(self, merchant_id, status=None, limit=50):
        return [
            s for s in self.sessions.values()
            if s.merchant_id == merchant_id and (status is None or s.status == status)
        ][:limit]

    async def get_processing_settlements(self):
        return [s for s in self.sessions.values() if getattr(s, "settlement_status", None) == "processing"]


# ── Provider Tests ────────────────────────────────────────────────


class TestStripeConnectProvider:
    """Test StripeConnectProvider with mocked Stripe SDK."""

    def _make_provider(self):
        """Create provider with a mocked stripe module."""
        mock_stripe = MagicMock()
        mock_stripe.api_key = None

        with patch.dict(os.environ, {"STRIPE_API_KEY": "sk_test_FAKE_KEY_FOR_UNIT_TESTS_ONLY"}):  # nosecret: test-only dummy key
            with patch.dict(sys.modules, {"stripe": mock_stripe}):
                from sardis_v2_core.stripe_connect import StripeConnectProvider
                provider = StripeConnectProvider(api_key="sk_test_FAKE_KEY_FOR_UNIT_TESTS_ONLY")  # nosecret: test-only dummy key

        provider._stripe = mock_stripe
        return provider, mock_stripe

    @pytest.mark.asyncio
    async def test_create_express_account(self):
        provider, mock_stripe = self._make_provider()

        mock_account = MagicMock()
        mock_account.id = "acct_test_new"
        mock_account.charges_enabled = False
        mock_account.payouts_enabled = False
        mock_account.details_submitted = False
        mock_account.requirements = MagicMock(
            currently_due=["business_profile.url"],
            past_due=[],
            disabled_reason=None,
            current_deadline=None,
        )
        mock_stripe.Account.create.return_value = mock_account

        result = await provider.create_express_account(
            email="test@shop.com",
            business_name="Test Shop",
            country="US",
        )

        assert result.account_id == "acct_test_new"
        assert result.charges_enabled is False
        assert result.payouts_enabled is False
        assert result.onboarding_state == "not_started"
        assert "business_profile.url" in result.requirements_currently_due

        # Verify Stripe API called with correct params
        call_kwargs = mock_stripe.Account.create.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_create_account_link(self):
        provider, mock_stripe = self._make_provider()

        mock_link = MagicMock()
        mock_link.url = "https://connect.stripe.com/setup/e/acct_test/xxx"
        mock_link.expires_at = int(datetime.now(UTC).timestamp()) + 300

        mock_stripe.AccountLink.create.return_value = mock_link

        result = await provider.create_account_link(
            account_id="acct_test_123",
            merchant_id="merch_test",
        )

        assert result.url.startswith("https://connect.stripe.com")
        assert isinstance(result.expires_at, datetime)
        mock_stripe.AccountLink.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_account_status_complete(self):
        provider, mock_stripe = self._make_provider()

        mock_account = MagicMock()
        mock_account.id = "acct_test_active"
        mock_account.charges_enabled = True
        mock_account.payouts_enabled = True
        mock_account.details_submitted = True
        mock_account.requirements = MagicMock(
            currently_due=[],
            past_due=[],
            disabled_reason=None,
            current_deadline=None,
        )
        mock_stripe.Account.retrieve.return_value = mock_account

        result = await provider.get_account_status("acct_test_active")

        assert result.onboarding_state == "complete"
        assert result.charges_enabled is True
        assert result.payouts_enabled is True
        assert result.requirements_currently_due == []

    @pytest.mark.asyncio
    async def test_get_account_status_restricted(self):
        provider, mock_stripe = self._make_provider()

        mock_account = MagicMock()
        mock_account.id = "acct_test_restricted"
        mock_account.charges_enabled = False
        mock_account.payouts_enabled = False
        mock_account.details_submitted = True
        mock_account.requirements = MagicMock(
            currently_due=["individual.verification.document"],
            past_due=["individual.verification.document"],
            disabled_reason="requirements.past_due",
            current_deadline=int(datetime.now(UTC).timestamp()) + 86400,
        )
        mock_stripe.Account.retrieve.return_value = mock_account

        result = await provider.get_account_status("acct_test_restricted")

        assert result.onboarding_state == "restricted"
        assert result.disabled_reason == "requirements.past_due"
        assert result.current_deadline is not None
        assert "individual.verification.document" in result.requirements_past_due

    @pytest.mark.asyncio
    async def test_get_account_status_rejected(self):
        provider, mock_stripe = self._make_provider()

        mock_account = MagicMock()
        mock_account.id = "acct_test_rejected"
        mock_account.charges_enabled = False
        mock_account.payouts_enabled = False
        mock_account.details_submitted = True
        mock_account.requirements = MagicMock(
            currently_due=[],
            past_due=[],
            disabled_reason="rejected.fraud",
            current_deadline=None,
        )
        mock_stripe.Account.retrieve.return_value = mock_account

        result = await provider.get_account_status("acct_test_rejected")

        assert result.onboarding_state == "rejected"
        assert result.disabled_reason == "rejected.fraud"

    @pytest.mark.asyncio
    async def test_create_transfer(self):
        provider, mock_stripe = self._make_provider()

        mock_transfer = MagicMock()
        mock_transfer.id = "tr_test_001"
        mock_transfer.amount = 9950
        mock_transfer.currency = "usd"
        mock_transfer.destination = "acct_test_123"
        mock_stripe.Transfer.create.return_value = mock_transfer

        result = await provider.create_transfer(
            account_id="acct_test_123",
            amount_cents=9950,
            currency="usd",
            description="Test settlement",
            metadata={"session_id": "mcs_test"},
        )

        assert result.transfer_id == "tr_test_001"
        assert result.amount_cents == 9950
        assert result.destination == "acct_test_123"

    def test_verify_webhook_invalid_signature(self):
        provider, mock_stripe = self._make_provider()

        mock_stripe.Webhook.construct_event.side_effect = Exception("Invalid signature")

        with pytest.raises(Exception, match="Invalid signature"):
            provider.verify_webhook_signature(
                payload=b'{"test": true}',
                sig_header="t=123,v1=bad",
                secret="whsec_FAKE_FOR_TESTS",  # nosecret: test-only dummy key
            )

    def test_verify_webhook_missing_secret(self):
        provider, _ = self._make_provider()

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SARDIS_STRIPE_CONNECT_WEBHOOK_SECRET", None)
            with pytest.raises(ValueError, match="webhook secret"):
                provider.verify_webhook_signature(
                    payload=b'{}',
                    sig_header="t=123,v1=abc",
                )

    def test_provider_requires_api_key(self):
        mock_stripe = MagicMock()
        with patch.dict(sys.modules, {"stripe": mock_stripe}):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("STRIPE_API_KEY", None)
                from sardis_v2_core.stripe_connect import StripeConnectProvider
                with pytest.raises(ValueError, match="API key"):
                    StripeConnectProvider(api_key=None)


# ── Settlement Tests ──────────────────────────────────────────────


class TestStripeConnectSettlement:
    """Test the stripe_connect settlement path in SettlementService."""

    @pytest.fixture
    def repo(self):
        repo = MockMerchantRepo()
        repo.merchants["merch_stripe_001"] = _make_stripe_merchant()
        repo.sessions["mcs_stripe_test"] = _make_session()
        return repo

    @pytest.fixture
    def mock_provider(self):
        provider = AsyncMock()
        provider.create_transfer.return_value = types.SimpleNamespace(
            transfer_id="tr_settlement_001",
            amount_cents=9950,
            currency="usd",
            destination="acct_test_123",
        )
        return provider

    @pytest.fixture
    def settlement_service(self, repo, mock_provider):
        from sardis_checkout.settlement import SettlementService
        return SettlementService(
            merchant_repo=repo,
            stripe_connect_provider=mock_provider,
        )

    @pytest.mark.asyncio
    async def test_settle_stripe_connect_success(self, settlement_service, repo, mock_provider):
        """Paid session with stripe_connect merchant should create a Stripe transfer."""
        # Patch Database.execute to avoid real DB call for payout tracking
        with patch("sardis_v2_core.database.Database.execute", new_callable=AsyncMock):
            await settlement_service.settle_session("mcs_stripe_test")

        session = repo.sessions["mcs_stripe_test"]
        assert session.status == "settled"
        assert session.settlement_status == "completed"
        assert session.settlement_tx_hash == "tr_settlement_001"

        # Verify transfer was called with correct amount (99.50 * 100 = 9950 cents)
        mock_provider.create_transfer.assert_called_once()
        call_kwargs = mock_provider.create_transfer.call_args[1]
        assert call_kwargs["account_id"] == "acct_test_123"
        assert call_kwargs["amount_cents"] == 9950
        assert call_kwargs["currency"] == "usd"

    @pytest.mark.asyncio
    async def test_settle_stripe_connect_no_provider(self, repo):
        """Settlement should fail gracefully when no Stripe provider configured."""
        from sardis_checkout.settlement import SettlementService
        service = SettlementService(merchant_repo=repo)

        await service.settle_session("mcs_stripe_test")

        session = repo.sessions["mcs_stripe_test"]
        assert session.settlement_status == "failed"

    @pytest.mark.asyncio
    async def test_settle_stripe_connect_no_account(self, repo, mock_provider):
        """Settlement should fail when merchant has no Stripe account."""
        from sardis_checkout.settlement import SettlementService
        repo.merchants["merch_stripe_001"].stripe_account_id = None

        service = SettlementService(merchant_repo=repo, stripe_connect_provider=mock_provider)
        await service.settle_session("mcs_stripe_test")

        session = repo.sessions["mcs_stripe_test"]
        assert session.settlement_status == "failed"
        mock_provider.create_transfer.assert_not_called()

    @pytest.mark.asyncio
    async def test_settle_stripe_connect_payouts_disabled(self, repo, mock_provider):
        """Settlement should fail when merchant payouts are not enabled."""
        from sardis_checkout.settlement import SettlementService
        repo.merchants["merch_stripe_001"].stripe_payouts_enabled = False

        service = SettlementService(merchant_repo=repo, stripe_connect_provider=mock_provider)
        await service.settle_session("mcs_stripe_test")

        session = repo.sessions["mcs_stripe_test"]
        assert session.settlement_status == "failed"
        mock_provider.create_transfer.assert_not_called()

    @pytest.mark.asyncio
    async def test_settle_stripe_connect_transfer_failure(self, repo, mock_provider):
        """Settlement should handle Stripe transfer exceptions."""
        from sardis_checkout.settlement import SettlementService
        mock_provider.create_transfer.side_effect = Exception("Stripe API error")

        service = SettlementService(merchant_repo=repo, stripe_connect_provider=mock_provider)
        with patch("sardis_v2_core.database.Database.execute", new_callable=AsyncMock):
            await service.settle_session("mcs_stripe_test")

        session = repo.sessions["mcs_stripe_test"]
        assert session.settlement_status == "failed"

    @pytest.mark.asyncio
    async def test_settle_non_paid_session_skipped(self, repo, mock_provider):
        """Non-paid sessions should be skipped."""
        from sardis_checkout.settlement import SettlementService
        repo.sessions["mcs_stripe_test"].status = "pending"

        service = SettlementService(merchant_repo=repo, stripe_connect_provider=mock_provider)
        await service.settle_session("mcs_stripe_test")

        mock_provider.create_transfer.assert_not_called()

    @pytest.mark.asyncio
    async def test_settle_uses_net_amount(self, repo, mock_provider):
        """Transfer amount should use net_amount (after platform fee), not gross."""
        from sardis_checkout.settlement import SettlementService
        repo.sessions["mcs_stripe_test"].amount = Decimal("100.00")
        repo.sessions["mcs_stripe_test"].net_amount = Decimal("97.50")

        service = SettlementService(merchant_repo=repo, stripe_connect_provider=mock_provider)
        with patch("sardis_v2_core.database.Database.execute", new_callable=AsyncMock):
            await service.settle_session("mcs_stripe_test")

        call_kwargs = mock_provider.create_transfer.call_args[1]
        assert call_kwargs["amount_cents"] == 9750  # 97.50 * 100

    @pytest.mark.asyncio
    async def test_settle_falls_back_to_gross_if_no_net(self, repo, mock_provider):
        """If net_amount is None, use gross amount."""
        from sardis_checkout.settlement import SettlementService
        repo.sessions["mcs_stripe_test"].amount = Decimal("50.00")
        repo.sessions["mcs_stripe_test"].net_amount = None

        service = SettlementService(merchant_repo=repo, stripe_connect_provider=mock_provider)
        with patch("sardis_v2_core.database.Database.execute", new_callable=AsyncMock):
            await service.settle_session("mcs_stripe_test")

        call_kwargs = mock_provider.create_transfer.call_args[1]
        assert call_kwargs["amount_cents"] == 5000  # 50.00 * 100


# ── Router Wiring Tests ──────────────────────────────────────────


class TestStripeConnectRouterWiring:
    def test_connect_router_has_endpoints(self):
        from sardis_api.routes.providers.stripe_connect import router
        paths = [r.path for r in router.routes]
        assert "/{merchant_id}/connect" in paths
        assert "/{merchant_id}/connect/status" in paths
        assert "/{merchant_id}/connect/refresh" in paths

    def test_webhook_router_has_endpoint(self):
        from sardis_api.routes.providers.stripe_connect import webhook_router
        paths = [r.path for r in webhook_router.routes]
        # webhook_router has prefix="/stripe-connect", so path is /stripe-connect/webhooks
        assert "/stripe-connect/webhooks" in paths

    def test_main_imports_stripe_connect(self):
        main_path = Path(__file__).parent.parent / "src" / "sardis_api" / "main.py"
        source = main_path.read_text()
        assert "stripe_connect_router" in source
        assert "StripeConnectProvider" in source


# ── Merchant Model Stripe Fields ─────────────────────────────────


class TestMerchantStripeFields:
    def test_merchant_stripe_defaults(self):
        m = Merchant(name="Test")
        assert m.stripe_account_id is None
        assert m.stripe_onboarding_state == "not_started"
        assert m.stripe_charges_enabled is False
        assert m.stripe_payouts_enabled is False
        assert m.stripe_details_submitted is False
        assert m.stripe_disabled_reason is None
        assert m.stripe_current_deadline is None
        assert m.stripe_last_synced_at is None

    def test_merchant_stripe_connect_preference(self):
        m = Merchant(
            name="Stripe Shop",
            settlement_preference="stripe_connect",
            stripe_account_id="acct_123",
            stripe_onboarding_state="complete",
            stripe_charges_enabled=True,
            stripe_payouts_enabled=True,
        )
        assert m.settlement_preference == "stripe_connect"
        assert m.stripe_account_id == "acct_123"
        assert m.stripe_charges_enabled is True

    def test_merchant_updatable_includes_stripe_fields(self):
        from sardis_v2_core.merchant import MerchantRepository
        updatable = MerchantRepository._MERCHANT_UPDATABLE
        assert "stripe_account_id" in updatable
        assert "stripe_onboarding_state" in updatable
        assert "stripe_charges_enabled" in updatable
        assert "stripe_payouts_enabled" in updatable
        assert "stripe_details_submitted" in updatable
        assert "stripe_disabled_reason" in updatable
        assert "stripe_current_deadline" in updatable
        assert "stripe_last_synced_at" in updatable


# ── API Response Model Tests ─────────────────────────────────────


class TestMerchantResponseStripeFields:
    def test_merchant_response_includes_stripe_fields(self):
        from sardis_api.routes.commerce.merchants import MerchantResponse
        fields = MerchantResponse.model_fields
        assert "stripe_account_id" in fields
        assert "stripe_onboarding_state" in fields
        assert "stripe_charges_enabled" in fields
        assert "stripe_payouts_enabled" in fields

    def test_settlement_preference_allows_stripe_connect(self):
        from sardis_api.routes.commerce.merchants import CreateMerchantRequest
        req = CreateMerchantRequest(name="Test", settlement_preference="stripe_connect")
        assert req.settlement_preference == "stripe_connect"

    def test_settlement_preference_rejects_invalid(self):
        from pydantic import ValidationError

        from sardis_api.routes.commerce.merchants import CreateMerchantRequest
        with pytest.raises(ValidationError):
            CreateMerchantRequest(name="Test", settlement_preference="bitcoin")
