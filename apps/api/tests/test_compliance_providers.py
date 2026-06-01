"""Tests for the compliance adapters (Didit KYC/KYB + Didit/OpenSanctions KYT).

Proves, without any live keys:

* :class:`DiditKycAdapter` conforms to :class:`KycPort`; :class:`DiditKytAdapter`
  and :class:`OpenSanctionsKytAdapter` conform to :class:`KytPort`; all report
  ``PARTNER_CUSTODIED`` custody and the right sandbox flag (invariant #1);
* the registry wires each real provider only when its env key is present, in the
  documented precedence (OpenSanctions preferred for KYT; Didit backs KYC and
  the KYT fallback), and falls back to the SIMULATED sandbox ports when no key
  is set (invariant #2);
* KYT is required-in-production: with no real KYT provider in prod, the registry
  fails CLOSED rather than handing back a sandbox screening port (invariant #5);
* Didit webhook verification is HMAC-SHA256 over the RAW body with an
  ``X-Timestamp`` freshness guard, and fails CLOSED on a missing secret / stale
  timestamp / bad signature (the brief's fail-CLOSED on screening);
* a screening transport/auth failure raises :class:`ProviderError` so the moat
  fails closed;
* the request shapes match the researched 2026 APIs (Didit ``POST /v3/session/``
  + ``/decision/`` + ``/v3/aml/``; OpenSanctions ``POST /match/{scope}`` with
  ``Authorization: ApiKey`` and the ``queries`` wrapper).

Each client's ``_client_()`` (the httpx session) is monkeypatched so no network
call happens; we assert on the request shape the adapter built and on the
normalized verdict.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from types import SimpleNamespace

import pytest

from server.providers.compliance import (
    DiditClient,
    DiditConfig,
    DiditKycAdapter,
    DiditKytAdapter,
    OpenSanctionsClient,
    OpenSanctionsConfig,
    OpenSanctionsKytAdapter,
)
from server.providers.ports import (
    CustodyModel,
    KycPort,
    KytPort,
    ProviderCapability,
    ProviderError,
    ProviderNotConfigured,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxKycPort, SandboxKytPort


def _dev_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=False, database_url="", circle_cpn=SimpleNamespace())


def _prod_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=True, database_url="", circle_cpn=SimpleNamespace())


# ---------------------------------------------------------------------------
# Fake httpx response/session so no network call happens.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    async def get(self, path: str, *, params=None, headers=None) -> _FakeResponse:
        self.calls.append(("GET", path, {"params": params, "headers": headers}))
        return self._next()

    async def post(self, path: str, *, json=None, data=None, params=None, headers=None):
        self.calls.append(
            ("POST", path, {"json": json, "data": data, "params": params, "headers": headers})
        )
        return self._next()

    def _next(self) -> _FakeResponse:
        item = self._responses.pop(0)
        if isinstance(item, _FakeResponse):
            return item
        return _FakeResponse(item)


def _patch_session(client, responses) -> _FakeSession:
    session = _FakeSession(responses)

    async def _client_():
        return session

    client._client_ = _client_  # type: ignore[assignment]
    return session


def _raising_session(exc: Exception):
    class _Boom:
        async def get(self, *a, **k):
            raise exc

        async def post(self, *a, **k):
            raise exc

    return _Boom()


# ---------------------------------------------------------------------------
# Port conformance + custody models
# ---------------------------------------------------------------------------


class TestPortConformance:
    def test_didit_kyc_conforms(self):
        adapter = DiditKycAdapter(DiditClient(DiditConfig(api_key="dk", environment="sandbox")))
        assert isinstance(adapter, KycPort)
        assert adapter.capability == ProviderCapability.KYC
        assert adapter.provider == "didit"
        assert adapter.sandbox is True
        assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_didit_kyt_conforms(self):
        adapter = DiditKytAdapter(DiditClient(DiditConfig(api_key="dk", environment="sandbox")))
        assert isinstance(adapter, KytPort)
        assert adapter.capability == ProviderCapability.KYT
        assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_opensanctions_kyt_conforms(self):
        adapter = OpenSanctionsKytAdapter(
            OpenSanctionsClient(OpenSanctionsConfig(api_key="ok", environment="sandbox"))
        )
        assert isinstance(adapter, KytPort)
        assert adapter.capability == ProviderCapability.KYT
        assert adapter.provider == "opensanctions"
        assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_clients_require_a_key(self):
        with pytest.raises(ValueError):
            DiditClient(DiditConfig(api_key=""))
        with pytest.raises(ValueError):
            OpenSanctionsClient(OpenSanctionsConfig(api_key=""))


# ---------------------------------------------------------------------------
# Didit KYC/KYB session + decision (request shape vs 2026 API)
# ---------------------------------------------------------------------------


class TestDiditKyc:
    @pytest.mark.asyncio
    async def test_create_kyc_session_builds_v3_request(self):
        client = DiditClient(
            DiditConfig(api_key="dk", kyc_workflow_id="wf_kyc", environment="sandbox")
        )
        session = _patch_session(
            client,
            [
                {
                    "session_id": "sess_1",
                    "session_token": "tok",
                    "url": "https://v/x",
                    "status": "Not Started",
                }
            ],
        )
        adapter = DiditKycAdapter(client)
        result = await adapter.create_session(subject_ref="user_1", kind="kyc")
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/v3/session/")
        assert kw["json"]["workflow_id"] == "wf_kyc"
        assert kw["json"]["vendor_data"] == "user_1"
        assert result.reference == "sess_1"
        assert result.status == "not_started"
        assert result.raw["verification_url"] == "https://v/x"
        assert result.custody_model == CustodyModel.PARTNER_CUSTODIED

    @pytest.mark.asyncio
    async def test_create_kyb_uses_kyb_workflow(self):
        client = DiditClient(
            DiditConfig(api_key="dk", kyb_workflow_id="wf_kyb", environment="sandbox")
        )
        session = _patch_session(client, [{"session_id": "s2", "status": "In Progress"}])
        adapter = DiditKycAdapter(client)
        result = await adapter.create_session(subject_ref="biz_1", kind="kyb")
        assert session.calls[0][2]["json"]["workflow_id"] == "wf_kyb"
        assert result.status == "pending"
        assert result.raw["kind"] == "kyb"

    @pytest.mark.asyncio
    async def test_kyb_without_workflow_fails_closed(self):
        client = DiditClient(DiditConfig(api_key="dk", environment="sandbox"))
        _patch_session(client, [{}])
        adapter = DiditKycAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.create_session(subject_ref="biz_1", kind="kyb")

    @pytest.mark.asyncio
    async def test_get_status_maps_decision(self):
        client = DiditClient(DiditConfig(api_key="dk", environment="sandbox"))
        session = _patch_session(client, [{"status": "Approved"}])
        adapter = DiditKycAdapter(client)
        result = await adapter.get_status("sess_1")
        method, path, _ = session.calls[0]
        assert (method, path) == ("GET", "/v3/session/sess_1/decision/")
        assert result.status == "approved"

    @pytest.mark.asyncio
    async def test_get_status_detects_kyb_from_key_people(self):
        client = DiditClient(DiditConfig(api_key="dk", environment="sandbox"))
        _patch_session(client, [{"status": "Approved", "key_people_checks": [{"x": 1}]}])
        adapter = DiditKycAdapter(client)
        result = await adapter.get_status("sess_1")
        assert result.raw["kind"] == "kyb"


# ---------------------------------------------------------------------------
# Didit webhook verification — HMAC over RAW body, freshness, fail-closed
# ---------------------------------------------------------------------------


class TestDiditWebhook:
    def _sign(self, secret: str, body: bytes) -> str:
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def test_valid_signature_passes(self):
        client = DiditClient(DiditConfig(api_key="dk", webhook_secret="whsec"))
        body = b'{"session_id":"s","status":"Approved"}'
        ts = str(int(time.time()))
        headers = {"X-Signature": self._sign("whsec", body), "X-Timestamp": ts}
        assert client.verify_webhook(body=body, headers=headers) is True

    def test_case_insensitive_headers(self):
        client = DiditClient(DiditConfig(api_key="dk", webhook_secret="whsec"))
        body = b'{"a":1}'
        ts = str(int(time.time()))
        headers = {"x-signature": self._sign("whsec", body), "x-timestamp": ts}
        assert client.verify_webhook(body=body, headers=headers) is True

    def test_missing_secret_fails_closed(self):
        client = DiditClient(DiditConfig(api_key="dk", webhook_secret=None))
        body = b"{}"
        headers = {"X-Signature": "deadbeef", "X-Timestamp": str(int(time.time()))}
        assert client.verify_webhook(body=body, headers=headers) is False

    def test_bad_signature_fails_closed(self):
        client = DiditClient(DiditConfig(api_key="dk", webhook_secret="whsec"))
        body = b'{"a":1}'
        headers = {"X-Signature": "0" * 64, "X-Timestamp": str(int(time.time()))}
        assert client.verify_webhook(body=body, headers=headers) is False

    def test_stale_timestamp_fails_closed(self):
        client = DiditClient(DiditConfig(api_key="dk", webhook_secret="whsec"))
        body = b'{"a":1}'
        old = str(int(time.time()) - 10_000)
        headers = {"X-Signature": self._sign("whsec", body), "X-Timestamp": old}
        assert client.verify_webhook(body=body, headers=headers) is False

    def test_missing_headers_fails_closed(self):
        client = DiditClient(DiditConfig(api_key="dk", webhook_secret="whsec"))
        assert client.verify_webhook(body=b"{}", headers={}) is False


# ---------------------------------------------------------------------------
# Didit AML (KYT counterparty) screening
# ---------------------------------------------------------------------------


class TestDiditKyt:
    @pytest.mark.asyncio
    async def test_screen_counterparty_builds_aml_request(self):
        client = DiditClient(DiditConfig(api_key="dk", environment="sandbox"))
        session = _patch_session(
            client,
            [{"request_id": "req_1", "aml": {"status": "Clear", "total_hits": 0, "hits": []}}],
        )
        adapter = DiditKytAdapter(client)
        result = await adapter.screen_counterparty(name="John Doe")
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/v3/aml/")
        assert kw["json"]["entity_type"] == "person"
        assert kw["json"]["name"] == "John Doe"
        assert result.status == "clear"
        assert result.reference == "req_1"
        assert result.custody_model == CustodyModel.PARTNER_CUSTODIED

    @pytest.mark.asyncio
    async def test_confirmed_hit_is_reported_as_hit(self):
        client = DiditClient(DiditConfig(api_key="dk", environment="sandbox"))
        _patch_session(
            client,
            [
                {
                    "request_id": "r",
                    "aml": {
                        "status": "In Review",
                        "total_hits": 1,
                        "hits": [
                            {
                                "id": "h1",
                                "match": True,
                                "score": 1,
                                "caption": "X",
                                "datasets": ["OFAC"],
                            }
                        ],
                    },
                }
            ],
        )
        adapter = DiditKytAdapter(client)
        result = await adapter.screen_counterparty(name="Bad Actor")
        assert result.status == "hit"
        assert result.raw["total_hits"] == 1
        assert result.raw["hits"][0]["match"] is True

    @pytest.mark.asyncio
    async def test_transport_failure_raises_provider_error(self):
        client = DiditClient(DiditConfig(api_key="dk", environment="sandbox"))

        async def _client_():
            return _raising_session(RuntimeError("boom"))

        client._client_ = _client_  # type: ignore[assignment]
        adapter = DiditKytAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.screen_counterparty(name="X")


# ---------------------------------------------------------------------------
# OpenSanctions match (KYT) — request shape, auth header, verdict
# ---------------------------------------------------------------------------


class TestOpenSanctions:
    @pytest.mark.asyncio
    async def test_screen_counterparty_builds_match_request(self):
        client = OpenSanctionsClient(
            OpenSanctionsConfig(api_key="ok", scope="default", environment="sandbox")
        )
        session = _patch_session(
            client,
            [{"responses": {"cp": {"results": [], "total": {"value": 0}}}}],
        )
        adapter = OpenSanctionsKytAdapter(client)
        result = await adapter.screen_counterparty(name="Acme Corp", metadata={"schema": "Company"})
        method, path, kw = session.calls[0]
        assert method == "POST"
        assert path == "/match/default"
        assert kw["json"]["queries"]["cp"]["schema"] == "Company"
        assert kw["json"]["queries"]["cp"]["properties"]["name"] == ["Acme Corp"]
        assert kw["params"]["threshold"] == 0.7
        assert result.status == "clear"

    @pytest.mark.asyncio
    async def test_auth_header_is_apikey(self):
        client = OpenSanctionsClient(OpenSanctionsConfig(api_key="topsecret"))
        # Build the real httpx client to inspect the header it sets.
        session = await client._client_()
        try:
            assert session.headers["Authorization"] == "ApiKey topsecret"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_confirmed_match_is_hit(self):
        client = OpenSanctionsClient(OpenSanctionsConfig(api_key="ok", environment="sandbox"))
        _patch_session(
            client,
            [
                {
                    "responses": {
                        "cp": {
                            "results": [
                                {
                                    "id": "Q1",
                                    "score": 0.95,
                                    "match": True,
                                    "caption": "Sanctioned Co",
                                    "datasets": ["us_ofac_sdn"],
                                    "topics": ["sanction"],
                                }
                            ],
                            "total": {"value": 1},
                        }
                    }
                }
            ],
        )
        adapter = OpenSanctionsKytAdapter(client)
        result = await adapter.screen_counterparty(name="Sanctioned Co")
        assert result.status == "hit"
        assert result.raw["hits"][0]["datasets"] == ["us_ofac_sdn"]

    @pytest.mark.asyncio
    async def test_unconfirmed_candidate_is_review(self):
        client = OpenSanctionsClient(OpenSanctionsConfig(api_key="ok", environment="sandbox"))
        _patch_session(
            client,
            [
                {
                    "responses": {
                        "cp": {
                            "results": [
                                {"id": "Q2", "score": 0.72, "match": False, "caption": "Maybe"}
                            ],
                            "total": {"value": 1},
                        }
                    }
                }
            ],
        )
        adapter = OpenSanctionsKytAdapter(client)
        result = await adapter.screen_counterparty(name="Maybe")
        assert result.status == "review"

    @pytest.mark.asyncio
    async def test_screen_address_uses_cryptowallet_schema(self):
        client = OpenSanctionsClient(OpenSanctionsConfig(api_key="ok", environment="sandbox"))
        session = _patch_session(
            client, [{"responses": {"addr": {"results": [], "total": {"value": 0}}}}]
        )
        adapter = OpenSanctionsKytAdapter(client)
        addr = "0x" + "ab" * 20
        result = await adapter.screen_address(address=addr, chain="base")
        body = session.calls[0][2]["json"]
        assert body["queries"]["addr"]["schema"] == "CryptoWallet"
        assert addr in body["queries"]["addr"]["properties"]["publicKey"]
        assert result.status == "clear"

    @pytest.mark.asyncio
    async def test_transport_failure_raises_provider_error(self):
        client = OpenSanctionsClient(OpenSanctionsConfig(api_key="ok", environment="sandbox"))

        async def _client_():
            return _raising_session(RuntimeError("boom"))

        client._client_ = _client_  # type: ignore[assignment]
        adapter = OpenSanctionsKytAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.screen_address(address="0xdead")


# ---------------------------------------------------------------------------
# Registry: env-gated wiring + sandbox fallback + precedence + fail-closed
# ---------------------------------------------------------------------------


class TestRegistryComplianceWiring:
    def test_no_keys_falls_back_to_sandbox_in_dev(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        assert isinstance(reg.get(ProviderCapability.KYC), SandboxKycPort)
        assert isinstance(reg.get(ProviderCapability.KYT), SandboxKytPort)
        assert not reg.has_real(ProviderCapability.KYC)
        assert not reg.has_real(ProviderCapability.KYT)

    def test_kyt_required_in_production_fails_closed(self):
        # KYT is required-in-production: no real provider -> fail closed.
        reg = ProviderRegistry.from_settings(_prod_settings(), environ={})
        with pytest.raises(ProviderNotConfigured):
            reg.get(ProviderCapability.KYT)
        # KYC is NOT required-in-production -> sandbox fallback is allowed.
        assert isinstance(reg.get(ProviderCapability.KYC), SandboxKycPort)

    def test_didit_key_wires_kyc_and_kyt_fallback(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={"DIDIT_API_KEY": "dk"})
        assert reg.has_real(ProviderCapability.KYC)
        assert reg.get(ProviderCapability.KYC).provider == "didit"
        assert reg.has_real(ProviderCapability.KYT)
        assert reg.get(ProviderCapability.KYT).provider == "didit"

    def test_opensanctions_preferred_for_kyt(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"DIDIT_API_KEY": "dk", "OPENSANCTIONS_API_KEY": "ok"},
        )
        # Didit still backs KYC; OpenSanctions takes KYT precedence.
        assert reg.get(ProviderCapability.KYC).provider == "didit"
        assert reg.get(ProviderCapability.KYT).provider == "opensanctions"

    def test_opensanctions_satisfies_prod_kyt_requirement(self):
        reg = ProviderRegistry.from_settings(
            _prod_settings(), environ={"OPENSANCTIONS_API_KEY": "ok"}
        )
        assert reg.get(ProviderCapability.KYT).provider == "opensanctions"

    def test_kyc_kyt_accessors_return_ports(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        assert isinstance(reg.kyc(), KycPort)
        assert isinstance(reg.kyt(), KytPort)
