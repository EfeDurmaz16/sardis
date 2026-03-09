"""Tests for CPN collect(), CPN webhooks, and settlement routing via CPN."""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_v2_core.cpn_funding_adapter import CircleCPNFundingAdapter
from sardis_v2_core.funding import FundingRequest, FundingResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(
    *,
    base_url: str = "https://api.circle-test.io",
    collection_path: str = "/v1/cpn/collections",
) -> CircleCPNFundingAdapter:
    return CircleCPNFundingAdapter(
        api_key="test-api-key",
        base_url=base_url,
        payout_path="/v1/cpn/payouts",
        status_path="/v1/cpn/payments/{payment_id}",
        collection_path=collection_path,
    )


def _make_request(
    amount: str = "100.00",
    currency: str = "USD",
    description: str = "Test collection",
) -> FundingRequest:
    return FundingRequest(
        amount=Decimal(amount),
        currency=currency,
        description=description,
    )


# ---------------------------------------------------------------------------
# 1. CircleCPNFundingAdapter.collect()
# ---------------------------------------------------------------------------

class TestCircleCPNCollect:
    @respx.mock
    @pytest.mark.asyncio
    async def test_collect_returns_funding_result(self) -> None:
        """collect() parses the Circle response into a FundingResult."""
        adapter = _make_adapter()
        respx.post("https://api.circle-test.io/v1/cpn/collections").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "col_abc123",
                    "amount": "100.00",
                    "currency": "USD",
                    "status": "processing",
                    "metadata": {"session_id": "sess_1"},
                },
            )
        )

        result = await adapter.collect(_make_request())

        assert isinstance(result, FundingResult)
        assert result.transfer_id == "col_abc123"
        assert result.amount == Decimal("100.00")
        assert result.currency == "USD"
        assert result.status == "processing"
        assert result.provider == "circle_cpn"
        assert result.rail == "fiat"

    @respx.mock
    @pytest.mark.asyncio
    async def test_collect_uses_collection_id_field(self) -> None:
        """collect() prefers the 'collection_id' field when 'id' is absent."""
        adapter = _make_adapter()
        respx.post("https://api.circle-test.io/v1/cpn/collections").mock(
            return_value=httpx.Response(
                200,
                json={"collection_id": "col_xyz", "amount": "50.00", "currency": "USD", "status": "pending"},
            )
        )

        result = await adapter.collect(_make_request(amount="50.00"))

        assert result.transfer_id == "col_xyz"

    @respx.mock
    @pytest.mark.asyncio
    async def test_collect_raises_on_missing_id(self) -> None:
        """collect() raises RuntimeError when the response contains no transfer ID."""
        adapter = _make_adapter()
        respx.post("https://api.circle-test.io/v1/cpn/collections").mock(
            return_value=httpx.Response(200, json={"status": "processing"})
        )

        with pytest.raises(RuntimeError, match="circle_cpn_missing_collection_id"):
            await adapter.collect(_make_request())

    @respx.mock
    @pytest.mark.asyncio
    async def test_collect_http_error_propagates(self) -> None:
        """collect() propagates HTTP errors from the upstream API."""
        adapter = _make_adapter()
        respx.post("https://api.circle-test.io/v1/cpn/collections").mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )

        with pytest.raises(httpx.HTTPStatusError):
            await adapter.collect(_make_request())

    @respx.mock
    @pytest.mark.asyncio
    async def test_collect_with_connected_account(self) -> None:
        """collect() includes connected_account_id in the POST body when provided."""
        adapter = _make_adapter()
        captured: list[dict] = []

        async def _capture(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "col_1", "amount": "25.00", "currency": "USD", "status": "processing"})

        respx.post("https://api.circle-test.io/v1/cpn/collections").mock(side_effect=_capture)

        req = FundingRequest(
            amount=Decimal("25.00"),
            currency="USD",
            description="Test",
            connected_account_id="acct_merchant_1",
        )
        await adapter.collect(req)

        assert captured[0]["connected_account_id"] == "acct_merchant_1"

    def test_collect_respects_custom_collection_path(self) -> None:
        """The collection_path constructor parameter is stored on the adapter."""
        adapter = _make_adapter(collection_path="/v2/cpn/inbound")
        assert adapter._collection_path == "/v2/cpn/inbound"

    def test_constructor_default_collection_path(self) -> None:
        """collection_path defaults to /v1/cpn/collections."""
        adapter = _make_adapter()
        assert adapter._collection_path == "/v1/cpn/collections"


# ---------------------------------------------------------------------------
# 2. CPN webhook handler
# ---------------------------------------------------------------------------

def _make_cpn_app(secret: str = "webhook-secret") -> tuple[FastAPI, TestClient]:
    """Build a minimal FastAPI app with the CPN webhook router mounted."""
    import os
    os.environ["CIRCLE_CPN_WEBHOOK_SECRET"] = secret

    from sardis_api.routers.cpn_webhooks import router

    app = FastAPI()
    app.include_router(router)
    return app, TestClient(app, raise_server_exceptions=False)


def _cpn_signature(body: bytes, secret: str = "webhook-secret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestCPNWebhookRouter:
    def _post(
        self,
        client: TestClient,
        payload: dict,
        secret: str = "webhook-secret",
        override_sig: str | None = None,
    ) -> Any:
        body = json.dumps(payload).encode()
        sig = override_sig if override_sig is not None else _cpn_signature(body, secret)
        return client.post(
            "/cpn/webhooks",
            content=body,
            headers={"Content-Type": "application/json", "Circle-Signature": sig},
        )

    def test_payment_completed_returns_200(self) -> None:
        _, client = _make_cpn_app()
        resp = self._post(client, {"type": "cpn.payment.completed", "id": "evt_1", "data": {"id": "pay_1"}})
        assert resp.status_code == 200
        assert resp.json() == {"received": True}

    def test_payment_failed_returns_200(self) -> None:
        _, client = _make_cpn_app()
        resp = self._post(
            client,
            {"type": "cpn.payment.failed", "id": "evt_2", "data": {"id": "pay_2", "failureReason": "insufficient_funds"}},
        )
        assert resp.status_code == 200

    def test_collection_completed_returns_200(self) -> None:
        _, client = _make_cpn_app()
        resp = self._post(client, {"type": "cpn.collection.completed", "id": "evt_3", "data": {"id": "col_1"}})
        assert resp.status_code == 200

    def test_collection_failed_returns_200(self) -> None:
        _, client = _make_cpn_app()
        resp = self._post(client, {"type": "cpn.collection.failed", "id": "evt_4", "data": {"collectionId": "col_2"}})
        assert resp.status_code == 200

    def test_unhandled_event_type_returns_200(self) -> None:
        """Unknown event types are logged but still return 200."""
        _, client = _make_cpn_app()
        resp = self._post(client, {"type": "cpn.some.future_event", "id": "evt_5", "data": {}})
        assert resp.status_code == 200

    def test_invalid_signature_returns_400(self) -> None:
        _, client = _make_cpn_app()
        resp = self._post(client, {"type": "cpn.payment.completed", "id": "evt_6", "data": {}}, override_sig="badsig")
        assert resp.status_code == 400

    def test_missing_signature_header_returns_400(self) -> None:
        _, client = _make_cpn_app()
        body = json.dumps({"type": "cpn.payment.completed"}).encode()
        resp = client.post("/cpn/webhooks", content=body, headers={"Content-Type": "application/json"})
        assert resp.status_code == 400

    def test_invalid_json_returns_400(self) -> None:
        _, client = _make_cpn_app()
        body = b"not-json"
        sig = _cpn_signature(body)
        resp = client.post(
            "/cpn/webhooks",
            content=body,
            headers={"Content-Type": "application/json", "Circle-Signature": sig},
        )
        assert resp.status_code == 400

    def test_wrong_secret_returns_400(self) -> None:
        _, client = _make_cpn_app(secret="correct-secret")
        resp = self._post(
            client,
            {"type": "cpn.payment.completed", "id": "e", "data": {}},
            secret="wrong-secret",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 3. SettlementService CPN routing
# ---------------------------------------------------------------------------

@dataclass
class _FakeMerchant:
    merchant_id: str
    settlement_preference: str
    webhook_url: str | None = None
    bank_account: dict = field(default_factory=dict)
    settlement_wallet_id: str | None = None
    cpn_account_id: str | None = None


@dataclass
class _FakeSession:
    session_id: str
    merchant_id: str
    status: str
    amount: Decimal
    currency: str
    settlement_status: str = "pending"
    offramp_id: str | None = None


class _FakeMerchantRepo:
    def __init__(self, merchant: _FakeMerchant, session: _FakeSession) -> None:
        self._merchant = merchant
        self._session = session
        self.updates: list[dict] = []

    async def get_session(self, session_id: str) -> _FakeSession | None:
        return self._session if self._session.session_id == session_id else None

    async def get_merchant(self, merchant_id: str) -> _FakeMerchant | None:
        return self._merchant if self._merchant.merchant_id == merchant_id else None

    async def update_session(self, session_id: str, **kwargs: Any) -> None:
        self.updates.append({"session_id": session_id, **kwargs})
        for k, v in kwargs.items():
            if hasattr(self._session, k):
                object.__setattr__(self._session, k, v)  # type: ignore[misc]


class _FakeCPNAdapter:
    def __init__(self, transfer_id: str = "cpn_transfer_1") -> None:
        self._transfer_id = transfer_id
        self.fund_calls: list[FundingRequest] = []

    async def fund(self, request: FundingRequest) -> FundingResult:
        self.fund_calls.append(request)
        return FundingResult(
            provider="circle_cpn",
            rail="fiat",
            transfer_id=self._transfer_id,
            amount=request.amount,
            currency=request.currency,
            status="processing",
        )


class TestSettlementServiceCPN:
    @pytest.mark.asyncio
    async def test_cpn_settlement_calls_fund_and_sets_processing(self) -> None:
        """settle_session() calls cpn_adapter.fund() and marks session as processing."""
        from sardis_checkout.settlement import SettlementService

        merchant = _FakeMerchant(
            merchant_id="m1",
            settlement_preference="cpn",
            cpn_account_id="cpn_acct_1",
        )
        session = _FakeSession(
            session_id="sess_1",
            merchant_id="m1",
            status="paid",
            amount=Decimal("99.00"),
            currency="USD",
        )
        repo = _FakeMerchantRepo(merchant, session)
        cpn = _FakeCPNAdapter()

        svc = SettlementService(merchant_repo=repo, cpn_adapter=cpn)
        await svc.settle_session("sess_1")

        assert len(cpn.fund_calls) == 1
        call = cpn.fund_calls[0]
        assert call.amount == Decimal("99.00")
        assert call.currency == "USD"

        update = repo.updates[-1]
        assert update["settlement_status"] == "processing"
        assert update["offramp_id"] == "cpn_transfer_1"

    @pytest.mark.asyncio
    async def test_cpn_settlement_delivers_webhook(self) -> None:
        """settle_session() delivers 'settlement.initiated' webhook on CPN path."""
        from sardis_checkout.settlement import SettlementService

        merchant = _FakeMerchant(
            merchant_id="m2",
            settlement_preference="cpn",
            webhook_url="https://merchant.example.com/webhook",
        )
        session = _FakeSession(
            session_id="sess_2",
            merchant_id="m2",
            status="paid",
            amount=Decimal("50.00"),
            currency="USD",
        )
        repo = _FakeMerchantRepo(merchant, session)
        cpn = _FakeCPNAdapter(transfer_id="cpn_t2")

        webhook_svc = MagicMock()
        webhook_svc.deliver = AsyncMock()

        svc = SettlementService(merchant_repo=repo, cpn_adapter=cpn, merchant_webhook_service=webhook_svc)
        await svc.settle_session("sess_2")

        webhook_svc.deliver.assert_called_once()
        call_kwargs = webhook_svc.deliver.call_args.kwargs
        assert call_kwargs["event_type"] == "settlement.initiated"
        assert call_kwargs["payload"]["settlement_method"] == "cpn"
        assert call_kwargs["payload"]["transfer_id"] == "cpn_t2"

    @pytest.mark.asyncio
    async def test_cpn_settlement_no_adapter_marks_failed(self) -> None:
        """settle_session() marks settlement as failed when no CPN adapter is configured."""
        from sardis_checkout.settlement import SettlementService

        merchant = _FakeMerchant(merchant_id="m3", settlement_preference="cpn")
        session = _FakeSession(
            session_id="sess_3",
            merchant_id="m3",
            status="paid",
            amount=Decimal("10.00"),
            currency="USD",
        )
        repo = _FakeMerchantRepo(merchant, session)

        svc = SettlementService(merchant_repo=repo)  # no cpn_adapter
        await svc.settle_session("sess_3")

        assert any(u.get("settlement_status") == "failed" for u in repo.updates)

    @pytest.mark.asyncio
    async def test_usdc_settlement_not_affected(self) -> None:
        """USDC settlement still completes independently of CPN adapter presence."""
        from sardis_checkout.settlement import SettlementService

        merchant = _FakeMerchant(merchant_id="m4", settlement_preference="usdc")
        session = _FakeSession(
            session_id="sess_4",
            merchant_id="m4",
            status="paid",
            amount=Decimal("200.00"),
            currency="USD",
        )
        repo = _FakeMerchantRepo(merchant, session)
        cpn = _FakeCPNAdapter()

        svc = SettlementService(merchant_repo=repo, cpn_adapter=cpn)
        await svc.settle_session("sess_4")

        # CPN adapter should never have been called
        assert len(cpn.fund_calls) == 0
        assert any(u.get("settlement_status") == "completed" for u in repo.updates)

    @pytest.mark.asyncio
    async def test_cpn_fund_exception_marks_failed(self) -> None:
        """If cpn_adapter.fund() raises, settlement_status is set to failed."""
        from sardis_checkout.settlement import SettlementService

        class _BrokenCPNAdapter:
            async def fund(self, request: FundingRequest) -> FundingResult:
                raise RuntimeError("circle_cpn_upstream_error")

        merchant = _FakeMerchant(merchant_id="m5", settlement_preference="cpn")
        session = _FakeSession(
            session_id="sess_5",
            merchant_id="m5",
            status="paid",
            amount=Decimal("75.00"),
            currency="USD",
        )
        repo = _FakeMerchantRepo(merchant, session)

        svc = SettlementService(merchant_repo=repo, cpn_adapter=_BrokenCPNAdapter())
        await svc.settle_session("sess_5")

        assert any(u.get("settlement_status") == "failed" for u in repo.updates)
