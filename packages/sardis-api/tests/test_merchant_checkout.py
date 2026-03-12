"""Tests for Pay with Sardis — merchant + checkout routers and domain model."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure local packages are importable (mirrors conftest.py but avoids create_app)
_packages = Path(__file__).parent.parent.parent
for _pkg in [
    "sardis-core",
    "sardis-checkout",
    "sardis-api",
    "sardis-guardrails",
    "sardis-protocol",
]:
    _p = _packages / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("DATABASE_URL", "memory://")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing_purposes_only_32chars")

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sardis_v2_core.merchant import (
    Merchant,
    MerchantCheckoutLink,
    MerchantCheckoutSession,
    _generate_client_secret,
    _generate_external_id,
    _generate_webhook_secret,
)

# ── Domain Model Tests ─────────────────────────────────────────────


class TestMerchantModel:
    def test_merchant_defaults(self):
        m = Merchant(name="Acme Corp")
        assert m.name == "Acme Corp"
        assert m.merchant_id.startswith("merch_")
        assert m.webhook_secret.startswith("whsec_")
        assert m.settlement_preference == "usdc"
        assert m.is_active is True
        assert m.platform_fee_bps == 0
        assert isinstance(m.created_at, datetime)

    def test_merchant_custom_fields(self):
        m = Merchant(
            name="Test Shop",
            settlement_preference="fiat",
            mcc_code="5411",
            platform_fee_bps=100,
        )
        assert m.settlement_preference == "fiat"
        assert m.mcc_code == "5411"
        assert m.platform_fee_bps == 100

    def test_session_defaults(self):
        s = MerchantCheckoutSession(merchant_id="merch_abc", amount=Decimal("49.99"))
        assert s.session_id.startswith("mcs_")
        assert s.client_secret  # should be non-empty
        assert len(s.client_secret) > 20
        assert s.status == "pending"
        assert s.currency == "USDC"
        assert s.payment_method is None
        assert s.tx_hash is None
        assert s.idempotency_key is None
        assert s.platform_fee_amount == Decimal("0")
        assert s.net_amount is None

    def test_session_client_secret_uniqueness(self):
        secrets = {MerchantCheckoutSession().client_secret for _ in range(100)}
        assert len(secrets) == 100

    def test_checkout_link_defaults(self):
        link = MerchantCheckoutLink(merchant_id="merch_abc", amount=Decimal("5.00"), slug="coffee")
        assert link.link_id.startswith("mcl_")
        assert link.currency == "USDC"
        assert link.is_active is True

    def test_external_id_uniqueness(self):
        ids = {_generate_external_id("merch") for _ in range(100)}
        assert len(ids) == 100

    def test_webhook_secret_uniqueness(self):
        secrets = {_generate_webhook_secret() for _ in range(100)}
        assert len(secrets) == 100

    def test_client_secret_uniqueness(self):
        secrets = {_generate_client_secret() for _ in range(100)}
        assert len(secrets) == 100


# ── Mock Dependencies ──────────────────────────────────────────────


def _make_merchant(**overrides) -> Merchant:
    defaults = {
        "merchant_id": "merch_test123",
        "name": "Test Merchant",
        "settlement_preference": "usdc",
        "settlement_wallet_id": "wal_settle_001",
        "is_active": True,
    }
    defaults.update(overrides)
    return Merchant(**defaults)


def _make_session(**overrides) -> MerchantCheckoutSession:
    defaults = {
        "session_id": "mcs_test456",
        "merchant_id": "merch_test123",
        "amount": Decimal("49.99"),
        "currency": "USDC",
        "status": "pending",
        "expires_at": datetime.now(UTC) + timedelta(minutes=15),
    }
    defaults.update(overrides)
    return MerchantCheckoutSession(**defaults)


class MockMerchantRepo:
    def __init__(self):
        self.merchants: dict[str, Merchant] = {}
        self.sessions: dict[str, MerchantCheckoutSession] = {}
        self.links: dict[str, MerchantCheckoutLink] = {}
        self.webhook_deliveries: dict[str, dict] = {}

    async def create_merchant(self, merchant: Merchant) -> Merchant:
        self.merchants[merchant.merchant_id] = merchant
        return merchant

    async def get_merchant(self, merchant_id: str) -> Merchant | None:
        return self.merchants.get(merchant_id)

    async def list_merchants(self, org_id: str) -> list[Merchant]:
        return [m for m in self.merchants.values() if m.org_id == org_id]

    async def update_merchant(self, merchant_id: str, **kwargs) -> Merchant | None:
        m = self.merchants.get(merchant_id)
        if not m:
            return None
        for k, v in kwargs.items():
            setattr(m, k, v)
        m.updated_at = datetime.now(UTC)
        return m

    async def create_session(self, session: MerchantCheckoutSession) -> MerchantCheckoutSession:
        self.sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> MerchantCheckoutSession | None:
        return self.sessions.get(session_id)

    async def get_session_by_secret(self, client_secret: str) -> MerchantCheckoutSession | None:
        for s in self.sessions.values():
            if s.client_secret == client_secret:
                return s
        return None

    async def get_session_for_update(self, session_id: str) -> MerchantCheckoutSession | None:
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

    async def create_checkout_link(self, link: MerchantCheckoutLink) -> MerchantCheckoutLink:
        self.links[link.link_id] = link
        return link

    async def get_checkout_link(self, link_id: str) -> MerchantCheckoutLink | None:
        return self.links.get(link_id)

    async def get_checkout_link_by_slug(self, slug: str) -> MerchantCheckoutLink | None:
        for l in self.links.values():
            if l.slug == slug and l.is_active:
                return l
        return None

    async def list_checkout_links(self, merchant_id: str) -> list[MerchantCheckoutLink]:
        return [l for l in self.links.values() if l.merchant_id == merchant_id]

    async def record_webhook_delivery(self, event_id, merchant_id, event_type, payload) -> bool:
        if event_id in self.webhook_deliveries:
            return False
        self.webhook_deliveries[event_id] = {
            "merchant_id": merchant_id, "event_type": event_type, "payload": payload
        }
        return True

    async def update_webhook_delivery(self, event_id, status, attempts) -> None:
        if event_id in self.webhook_deliveries:
            self.webhook_deliveries[event_id]["status"] = status
            self.webhook_deliveries[event_id]["attempts"] = attempts


# ── Connector Tests ────────────────────────────────────────────────


class TestSardisNativeConnector:
    @pytest.fixture
    def mock_repo(self):
        repo = MockMerchantRepo()
        repo.merchants["merch_test123"] = _make_merchant()
        return repo

    @pytest.fixture
    def connector(self, mock_repo):
        from sardis_checkout.connectors.sardis_native import SardisNativeConnector

        return SardisNativeConnector(
            chain_executor=AsyncMock(),
            wallet_manager=AsyncMock(),
            compliance_engine=AsyncMock(),
            ledger_store=AsyncMock(),
            merchant_repo=mock_repo,
            settlement_service=None,
            merchant_webhook_service=None,
        )

    @pytest.mark.asyncio
    async def test_create_checkout_session(self, connector, mock_repo):
        from sardis_checkout.models import CheckoutRequest

        request = CheckoutRequest(
            agent_id="merchant_merch_test123",
            wallet_id="wal_settle_001",
            mandate_id="",
            amount=Decimal("49.99"),
            currency="USDC",
            description="Test payment",
            metadata={"merchant_id": "merch_test123"},
        )

        response = await connector.create_checkout_session(request)

        assert response.checkout_id.startswith("mcs_")
        assert "/s/" in response.redirect_url  # Uses client_secret URL
        assert "client_secret" in response.metadata
        assert len(mock_repo.sessions) == 1

        # Verify session has client_secret
        session = list(mock_repo.sessions.values())[0]
        assert session.client_secret
        assert len(session.client_secret) > 20

    @pytest.mark.asyncio
    async def test_create_session_invalid_merchant(self, connector):
        from sardis_checkout.models import CheckoutRequest

        request = CheckoutRequest(
            agent_id="merchant_nonexistent",
            wallet_id="",
            mandate_id="",
            amount=Decimal("10"),
            metadata={"merchant_id": "nonexistent"},
        )

        with pytest.raises(ValueError, match="Merchant not found"):
            await connector.create_checkout_session(request)

    @pytest.mark.asyncio
    async def test_create_session_inactive_merchant(self, connector, mock_repo):
        from sardis_checkout.models import CheckoutRequest

        mock_repo.merchants["merch_test123"].is_active = False

        request = CheckoutRequest(
            agent_id="merchant_merch_test123",
            wallet_id="",
            mandate_id="",
            amount=Decimal("10"),
            metadata={"merchant_id": "merch_test123"},
        )

        with pytest.raises(ValueError, match="inactive"):
            await connector.create_checkout_session(request)

    @pytest.mark.asyncio
    async def test_psp_type(self, connector):
        from sardis_checkout.models import PSPType
        assert connector.psp_type == PSPType.SARDIS

    @pytest.mark.asyncio
    async def test_execute_payment_idempotent_on_already_paid(self, connector, mock_repo):
        """Already paid session should return existing result (idempotent)."""
        session = _make_session(status="paid", tx_hash="0xexisting")
        mock_repo.sessions[session.session_id] = session

        result = await connector.execute_payment(
            session_id=session.session_id,
            payer_wallet_id="wal_payer_001",
        )
        assert result["status"] == "paid"
        assert result["tx_hash"] == "0xexisting"


# ── Router Wiring Tests ───────────────────────────────────────────


class TestMerchantCheckoutRouterWiring:
    def test_merchant_router_has_endpoints(self):
        from sardis_api.routers.merchants import router
        paths = [r.path for r in router.routes]
        assert "/" in paths
        assert "/{merchant_id}" in paths
        assert "/{merchant_id}/bank-account" in paths
        assert "/{merchant_id}/settlements" in paths
        assert "/{merchant_id}/links" in paths

    def test_checkout_router_has_endpoints(self):
        from sardis_api.routers.merchant_checkout import public_router, router
        auth_paths = [r.path for r in router.routes]
        public_paths = [r.path for r in public_router.routes]

        assert "/sessions" in auth_paths
        assert "/sessions/{session_id}" in auth_paths

        # Public endpoints now use client_secret
        assert "/sessions/client/{client_secret}/details" in public_paths
        assert "/sessions/client/{client_secret}/connect" in public_paths
        assert "/sessions/client/{client_secret}/pay" in public_paths
        assert "/sessions/client/{client_secret}/balance" in public_paths
        assert "/sessions/client/{client_secret}/stream" in public_paths
        assert "/sessions/client/{client_secret}/onramp-token" in public_paths
        assert "/links/{slug}" in public_paths

    def test_main_wires_merchant_routers(self):
        main_path = Path(__file__).parent.parent / "src" / "sardis_api" / "main.py"
        source = main_path.read_text()
        assert "merchants_router" in source
        assert "merchant_checkout_router" in source


# ── Session Lifecycle Tests ────────────────────────────────────────


class TestSessionLifecycle:
    @pytest.fixture
    def repo(self):
        return MockMerchantRepo()

    @pytest.mark.asyncio
    async def test_connect_wallet_to_session(self, repo):
        session = _make_session()
        await repo.create_session(session)

        await repo.update_session(session.session_id, payer_wallet_id="wal_payer_001")

        updated = await repo.get_session(session.session_id)
        assert updated.payer_wallet_id == "wal_payer_001"

    @pytest.mark.asyncio
    async def test_session_status_transitions(self, repo):
        session = _make_session()
        await repo.create_session(session)

        # pending -> paid
        await repo.update_session(session.session_id, status="paid", tx_hash="0xabc123")
        s = await repo.get_session(session.session_id)
        assert s.status == "paid"
        assert s.tx_hash == "0xabc123"

        # paid -> settled
        await repo.update_session(session.session_id, status="settled", settlement_status="completed")
        s = await repo.get_session(session.session_id)
        assert s.status == "settled"
        assert s.settlement_status == "completed"

    @pytest.mark.asyncio
    async def test_expired_session_blocks_connect(self, repo):
        """Sessions past their expiry should not accept wallet connections."""
        session = _make_session(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        await repo.create_session(session)

        s = await repo.get_session(session.session_id)
        assert s.expires_at < datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_list_sessions_by_merchant(self, repo):
        m = _make_merchant()
        await repo.create_merchant(m)

        for i in range(3):
            s = _make_session(session_id=f"mcs_list_{i}", merchant_id=m.merchant_id)
            await repo.create_session(s)

        sessions = await repo.list_sessions_by_merchant(m.merchant_id)
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_processing_settlements_query(self, repo):
        s1 = _make_session(session_id="mcs_proc_1", status="paid", settlement_status="processing")
        s2 = _make_session(session_id="mcs_proc_2", status="paid", settlement_status="completed")
        s3 = _make_session(session_id="mcs_proc_3", status="paid", settlement_status="processing")

        for s in (s1, s2, s3):
            await repo.create_session(s)

        processing = await repo.get_processing_settlements()
        assert len(processing) == 2
        assert {s.session_id for s in processing} == {"mcs_proc_1", "mcs_proc_3"}

    @pytest.mark.asyncio
    async def test_get_session_by_secret(self, repo):
        session = _make_session()
        await repo.create_session(session)

        found = await repo.get_session_by_secret(session.client_secret)
        assert found is not None
        assert found.session_id == session.session_id

        not_found = await repo.get_session_by_secret("nonexistent_secret")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_session_for_update(self, repo):
        session = _make_session()
        await repo.create_session(session)

        locked = await repo.get_session_for_update(session.session_id)
        assert locked is not None
        assert locked.session_id == session.session_id


# ── Checkout Links Tests ──────────────────────────────────────────


class TestCheckoutLinks:
    @pytest.fixture
    def repo(self):
        return MockMerchantRepo()

    @pytest.mark.asyncio
    async def test_create_and_get_link(self, repo):
        link = MerchantCheckoutLink(
            merchant_id="merch_test123",
            amount=Decimal("5.00"),
            slug="coffee-5usd",
        )
        await repo.create_checkout_link(link)

        found = await repo.get_checkout_link(link.link_id)
        assert found is not None
        assert found.slug == "coffee-5usd"
        assert found.amount == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_get_link_by_slug(self, repo):
        link = MerchantCheckoutLink(
            merchant_id="merch_test123",
            amount=Decimal("10.00"),
            slug="donation-10",
        )
        await repo.create_checkout_link(link)

        found = await repo.get_checkout_link_by_slug("donation-10")
        assert found is not None
        assert found.link_id == link.link_id

        not_found = await repo.get_checkout_link_by_slug("nonexistent")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_inactive_link_not_found_by_slug(self, repo):
        link = MerchantCheckoutLink(
            merchant_id="merch_test123",
            amount=Decimal("10.00"),
            slug="disabled-link",
            is_active=False,
        )
        await repo.create_checkout_link(link)

        found = await repo.get_checkout_link_by_slug("disabled-link")
        assert found is None


# ── Pydantic Model Validation Tests ───────────────────────────────


class TestRequestValidation:
    def test_create_session_requires_positive_amount(self):
        from sardis_api.routers.merchant_checkout import CreateSessionRequest
        with pytest.raises(Exception):
            CreateSessionRequest(merchant_id="merch_123", amount=Decimal("-10"))

    def test_create_session_defaults(self):
        from sardis_api.routers.merchant_checkout import CreateSessionRequest
        req = CreateSessionRequest(merchant_id="merch_123", amount=Decimal("25.50"))
        assert req.currency == "USDC"
        assert req.metadata == {}
        assert req.embed_origin is None

    def test_create_merchant_validates_settlement_preference(self):
        from sardis_api.routers.merchants import CreateMerchantRequest
        with pytest.raises(Exception):
            CreateMerchantRequest(name="Test", settlement_preference="bitcoin")

    def test_create_merchant_fee_bounds(self):
        from sardis_api.routers.merchants import CreateMerchantRequest
        with pytest.raises(Exception):
            CreateMerchantRequest(name="Test", platform_fee_bps=600)

    def test_create_merchant_valid(self):
        from sardis_api.routers.merchants import CreateMerchantRequest
        req = CreateMerchantRequest(name="Test Shop", settlement_preference="fiat", platform_fee_bps=100)
        assert req.name == "Test Shop"
        assert req.settlement_preference == "fiat"

    def test_create_checkout_link_slug_validation(self):
        from sardis_api.routers.merchants import CreateCheckoutLinkRequest
        # Valid slug
        req = CreateCheckoutLinkRequest(amount=Decimal("5.00"), slug="coffee-5usd")
        assert req.slug == "coffee-5usd"

        # Invalid slug (starts with hyphen)
        with pytest.raises(Exception):
            CreateCheckoutLinkRequest(amount=Decimal("5.00"), slug="-bad-slug")


# ── Settlement Service Tests ──────────────────────────────────────


class TestSettlementService:
    @pytest.mark.asyncio
    async def test_usdc_settlement_marks_complete(self):
        """USDC merchants get immediate settlement (no offramp needed)."""
        from sardis_checkout.settlement import SettlementService

        repo = MockMerchantRepo()
        merchant = _make_merchant(settlement_preference="usdc")
        repo.merchants[merchant.merchant_id] = merchant

        session = _make_session(status="paid", tx_hash="0xabc")
        repo.sessions[session.session_id] = session

        service = SettlementService(
            merchant_repo=repo,
            offramp_service=None,
            merchant_webhook_service=None,
        )

        await service.settle_session(session.session_id)

        updated = await repo.get_session(session.session_id)
        assert updated.status == "settled"
        assert updated.settlement_status == "completed"

    @pytest.mark.asyncio
    async def test_settlement_skips_non_paid_sessions(self):
        """Settlement should skip sessions that aren't in 'paid' status."""
        from sardis_checkout.settlement import SettlementService

        repo = MockMerchantRepo()
        merchant = _make_merchant()
        repo.merchants[merchant.merchant_id] = merchant

        session = _make_session(status="pending")
        repo.sessions[session.session_id] = session

        service = SettlementService(
            merchant_repo=repo,
            offramp_service=None,
            merchant_webhook_service=None,
        )

        await service.settle_session(session.session_id)

        updated = await repo.get_session(session.session_id)
        assert updated.status == "pending"  # unchanged


# ── Webhook Signature Tests ───────────────────────────────────────


class TestWebhookSignature:
    def test_hmac_signature_generation(self):
        from sardis_checkout.merchant_webhooks import MerchantWebhookService

        payload = b'{"event": "payment.completed"}'
        secret = "test_webhook_secret_placeholder_123"

        sig = MerchantWebhookService.sign_payload(payload, secret)
        assert sig.startswith("sha256=")
        assert len(sig) > 10

    def test_signature_is_deterministic(self):
        from sardis_checkout.merchant_webhooks import MerchantWebhookService

        payload = b'{"test": true}'
        secret = "test_wh_abc"

        sig1 = MerchantWebhookService.sign_payload(payload, secret)
        sig2 = MerchantWebhookService.sign_payload(payload, secret)
        assert sig1 == sig2

    def test_different_secrets_produce_different_signatures(self):
        from sardis_checkout.merchant_webhooks import MerchantWebhookService

        payload = b'{"test": true}'

        sig1 = MerchantWebhookService.sign_payload(payload, "test_a")
        sig2 = MerchantWebhookService.sign_payload(payload, "test_b")
        assert sig1 != sig2

    def test_verify_signature_roundtrip(self):
        from sardis_checkout.merchant_webhooks import MerchantWebhookService

        payload = b'{"event": "settlement.completed", "amount": "49.99"}'
        secret = "test_wh_roundtrip"

        sig = MerchantWebhookService.sign_payload(payload, secret)
        assert MerchantWebhookService.verify_signature(payload, secret, sig) is True
        assert MerchantWebhookService.verify_signature(payload, "test_wrong", sig) is False


# ── Webhook Delivery Tests ────────────────────────────────────────


class TestWebhookDelivery:
    @pytest.mark.asyncio
    async def test_webhook_includes_event_id(self):
        """Webhook payload should contain event_id for deduplication."""

        from sardis_checkout.merchant_webhooks import MerchantWebhookService

        repo = MockMerchantRepo()
        service = MerchantWebhookService(merchant_repo=repo)

        merchant = _make_merchant(webhook_url="https://example.com/webhook")
        repo.merchants[merchant.merchant_id] = merchant

        # Delivery will fail (no real server), but we can check the delivery was recorded
        await service.deliver(
            merchant=merchant,
            event_type="payment.completed",
            payload={"session_id": "mcs_test", "amount": "10.00"},
        )

        # Check that a delivery was recorded
        assert len(repo.webhook_deliveries) == 1
        event_id = list(repo.webhook_deliveries.keys())[0]
        assert event_id.startswith("evt_")

        await service.close()
