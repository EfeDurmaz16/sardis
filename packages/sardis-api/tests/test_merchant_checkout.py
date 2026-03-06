"""Tests for Pay with Sardis — merchant + checkout routers and domain model."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure local packages are importable (mirrors conftest.py but avoids create_app)
_packages = Path(__file__).parent.parent.parent
for _pkg in ["sardis-core", "sardis-checkout", "sardis-api"]:
    _p = _packages / _pkg / "src"
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("DATABASE_URL", "memory://")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing_purposes_only_32chars")

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_v2_core.merchant import (
    Merchant,
    MerchantCheckoutSession,
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
        assert s.status == "pending"
        assert s.currency == "USDC"
        assert s.payment_method is None
        assert s.tx_hash is None

    def test_external_id_uniqueness(self):
        ids = {_generate_external_id("merch") for _ in range(100)}
        assert len(ids) == 100

    def test_webhook_secret_uniqueness(self):
        secrets = {_generate_webhook_secret() for _ in range(100)}
        assert len(secrets) == 100


# ── Mock Dependencies ──────────────────────────────────────────────


def _make_merchant(**overrides) -> Merchant:
    defaults = dict(
        merchant_id="merch_test123",
        name="Test Merchant",
        settlement_preference="usdc",
        settlement_wallet_id="wal_settle_001",
        is_active=True,
    )
    defaults.update(overrides)
    return Merchant(**defaults)


def _make_session(**overrides) -> MerchantCheckoutSession:
    defaults = dict(
        session_id="mcs_test456",
        merchant_id="merch_test123",
        amount=Decimal("49.99"),
        currency="USDC",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    defaults.update(overrides)
    return MerchantCheckoutSession(**defaults)


class MockMerchantRepo:
    def __init__(self):
        self.merchants: dict[str, Merchant] = {}
        self.sessions: dict[str, MerchantCheckoutSession] = {}

    async def create_merchant(self, merchant: Merchant) -> Merchant:
        self.merchants[merchant.merchant_id] = merchant
        return merchant

    async def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        return self.merchants.get(merchant_id)

    async def list_merchants(self, org_id: str) -> list[Merchant]:
        return [m for m in self.merchants.values() if m.org_id == org_id]

    async def update_merchant(self, merchant_id: str, **kwargs) -> Optional[Merchant]:
        m = self.merchants.get(merchant_id)
        if not m:
            return None
        for k, v in kwargs.items():
            setattr(m, k, v)
        m.updated_at = datetime.now(timezone.utc)
        return m

    async def create_session(self, session: MerchantCheckoutSession) -> MerchantCheckoutSession:
        self.sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> Optional[MerchantCheckoutSession]:
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
        assert response.redirect_url.startswith("https://checkout.sardis.sh/")
        assert len(mock_repo.sessions) == 1

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


# ── Router Wiring Tests ───────────────────────────────────────────


class TestMerchantCheckoutRouterWiring:
    def test_merchant_router_has_endpoints(self):
        from sardis_api.routers.merchants import router
        paths = [r.path for r in router.routes]
        assert "/" in paths
        assert "/{merchant_id}" in paths
        assert "/{merchant_id}/bank-account" in paths
        assert "/{merchant_id}/settlements" in paths

    def test_checkout_router_has_endpoints(self):
        from sardis_api.routers.merchant_checkout import router, public_router
        auth_paths = [r.path for r in router.routes]
        public_paths = [r.path for r in public_router.routes]

        assert "/sessions" in auth_paths
        assert "/sessions/{session_id}" in auth_paths

        assert "/sessions/{session_id}/details" in public_paths
        assert "/sessions/{session_id}/connect" in public_paths
        assert "/sessions/{session_id}/pay" in public_paths
        assert "/sessions/{session_id}/balance" in public_paths

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

        # pending → paid
        await repo.update_session(session.session_id, status="paid", tx_hash="0xabc123")
        s = await repo.get_session(session.session_id)
        assert s.status == "paid"
        assert s.tx_hash == "0xabc123"

        # paid → settled
        await repo.update_session(session.session_id, status="settled", settlement_status="completed")
        s = await repo.get_session(session.session_id)
        assert s.status == "settled"
        assert s.settlement_status == "completed"

    @pytest.mark.asyncio
    async def test_expired_session_blocks_connect(self, repo):
        """Sessions past their expiry should not accept wallet connections."""
        session = _make_session(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        await repo.create_session(session)

        s = await repo.get_session(session.session_id)
        assert s.expires_at < datetime.now(timezone.utc)

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
