"""Tests for the onramp provider adapters (Onramper / Transak / Daimo Pay).

Proves, without any live keys:

* each adapter conforms to :class:`OnrampPort` and reports the right custody
  model + sandbox flag;
* the registry wires each real provider only when its env keys are present,
  and falls back to the SIMULATED sandbox impl when keys are absent;
* money crosses the boundary as integer minor units and is converted to the
  vendors' decimal-string fields with no float (exact ``Decimal``);
* the Daimo adapter fails closed on an unknown destination chain rather than
  guessing a chain id on a money path.

The clients' ``_client_()`` (the httpx session) is monkeypatched so no network
call happens; we assert on the request shape the adapter built.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from server.providers.onramp import (
    DaimoClient,
    DaimoConfig,
    DaimoOnrampAdapter,
    OnramperClient,
    OnramperConfig,
    OnramperOnrampAdapter,
    TransakClient,
    TransakConfig,
    TransakOnrampAdapter,
)
from server.providers.ports import (
    CustodyModel,
    OnrampPort,
    ProviderCapability,
    ProviderError,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxOnrampPort


def _dev_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=False, database_url="", circle_cpn=SimpleNamespace())


# ---------------------------------------------------------------------------
# Fake httpx response/session so no network call happens.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - happy path
        return None

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    """Records the last POST/GET so the test can assert request shape."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    async def post(self, path: str, *, json=None, headers=None) -> _FakeResponse:
        self.calls.append(("POST", path, {"json": json, "headers": headers}))
        return _FakeResponse(self._responses.pop(0))

    async def get(self, path: str, *, headers=None) -> _FakeResponse:
        self.calls.append(("GET", path, {"headers": headers}))
        return _FakeResponse(self._responses.pop(0))


def _patch_session(client, responses: list[dict]) -> _FakeSession:
    session = _FakeSession(responses)

    async def _client_():
        return session

    client._client_ = _client_  # type: ignore[assignment]
    return session


# ---------------------------------------------------------------------------
# Port conformance + custody models
# ---------------------------------------------------------------------------


class TestPortConformance:
    def test_all_three_conform_to_onramp_port(self):
        fake_key = "pk_" + "test"
        onramper = OnramperOnrampAdapter(
            OnramperClient(OnramperConfig(api_key=fake_key, environment="staging"))
        )
        transak = TransakOnrampAdapter(
            TransakClient(TransakConfig(api_key="k", api_secret="s", environment="staging"))
        )
        daimo = DaimoOnrampAdapter(DaimoClient(DaimoConfig(api_key="k", environment="sandbox")))
        for adapter in (onramper, transak, daimo):
            assert isinstance(adapter, OnrampPort)
            assert adapter.capability == ProviderCapability.ONRAMP
            assert adapter.sandbox is True  # staging/sandbox env

    def test_custody_models(self):
        onramper = OnramperOnrampAdapter(OnramperClient(OnramperConfig(api_key="pk_x")))
        transak = TransakOnrampAdapter(TransakClient(TransakConfig(api_key="k", api_secret="s")))
        daimo = DaimoOnrampAdapter(DaimoClient(DaimoConfig(api_key="k")))
        assert onramper.custody_model == CustodyModel.PARTNER_CUSTODIED
        assert transak.custody_model == CustodyModel.PARTNER_CUSTODIED
        # Daimo settles straight to the destination wallet; Sardis never holds.
        assert daimo.custody_model == CustodyModel.NON_CUSTODIAL


# ---------------------------------------------------------------------------
# Onramper: request shape + money correctness
# ---------------------------------------------------------------------------


class TestOnramperAdapter:
    @pytest.mark.asyncio
    async def test_create_session_builds_buy_intent_with_decimal_amount(self):
        client = OnramperClient(OnramperConfig(api_key="pk_test", environment="staging"))
        session = _patch_session(
            client,
            [
                {
                    "transactionId": "tx_1",
                    "status": "created",
                    "transactionInformation": {"url": "https://buy.onramper.com/tx_1"},
                }
            ],
        )
        adapter = OnramperOnrampAdapter(client)
        # 125_00 cents == $125.00
        result = await adapter.create_session(
            wallet_address="0xabc",
            chain="base",
            crypto_currency="usdc",
            fiat_currency="USD",
            amount_minor=12_500,
        )
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/checkout/intent")
        body = kw["json"]
        # Exact decimal string from minor units; no float anywhere.
        assert body["amount"] == "125"
        assert Decimal(body["amount"]) == Decimal("125.00")
        assert body["type"] == "buy"
        assert body["source"] == "usd"
        assert body["destination"] == "usdc"
        assert body["network"] == "base"
        assert body["wallet"]["address"] == "0xabc"
        assert result.reference == "tx_1"
        assert result.raw["url"] == "https://buy.onramper.com/tx_1"
        assert result.custody_model == CustodyModel.PARTNER_CUSTODIED
        assert result.sandbox is True

    @pytest.mark.asyncio
    async def test_requires_amount(self):
        adapter = OnramperOnrampAdapter(OnramperClient(OnramperConfig(api_key="pk_x")))
        with pytest.raises(ProviderError):
            await adapter.create_session(wallet_address="0xabc", chain="base")

    def test_signing_only_when_secret_present(self):
        unsigned = OnramperClient(OnramperConfig(api_key="pk_x"))
        assert unsigned._sign_wallet("0xabc", None) == {}
        signed = OnramperClient(OnramperConfig(api_key="pk_x", signing_secret="shh"))
        out = signed._sign_wallet("0xabc", None)
        assert set(out) == {"signature", "signContent"}
        assert out["signContent"] == "0xabc"


# ---------------------------------------------------------------------------
# Transak: two-step mint, secret stays server-side
# ---------------------------------------------------------------------------


class TestTransakAdapter:
    @pytest.mark.asyncio
    async def test_mints_widget_url_two_step(self):
        client = TransakClient(TransakConfig(api_key="pk", api_secret="sk", environment="staging"))
        session = _patch_session(
            client,
            [
                {"data": {"accessToken": "at_123"}},
                {"data": {"widgetUrl": "https://global-stg.transak.com/?sessionId=abc"}},
            ],
        )
        adapter = TransakOnrampAdapter(client)
        result = await adapter.create_session(
            wallet_address="0xdef",
            chain="base",
            crypto_currency="usdc",
            amount_minor=5_000,  # $50.00
        )
        # Step 1: secret passed in api-secret header, never query string.
        m1, u1, kw1 = session.calls[0]
        assert m1 == "POST"
        assert kw1["headers"]["api-secret"] == "sk"
        assert kw1["json"] == {"apiKey": "pk"}
        # Step 2: access-token header, widgetParams with decimal fiatAmount.
        m2, u2, kw2 = session.calls[1]
        assert kw2["headers"]["access-token"] == "at_123"
        wp = kw2["json"]["widgetParams"]
        assert Decimal(wp["fiatAmount"]) == Decimal("50.00")
        assert wp["walletAddress"] == "0xdef"
        assert wp["cryptoCurrencyCode"] == "USDC"
        assert wp["network"] == "base"
        assert result.raw["url"].startswith("https://")
        assert result.status == "created"

    @pytest.mark.asyncio
    async def test_amount_optional(self):
        client = TransakClient(TransakConfig(api_key="pk", api_secret="sk"))
        session = _patch_session(
            client,
            [
                {"data": {"accessToken": "at"}},
                {"data": {"widgetUrl": "https://x"}},
            ],
        )
        adapter = TransakOnrampAdapter(client)
        await adapter.create_session(wallet_address="0xdef", chain="base")
        wp = session.calls[1][2]["json"]["widgetParams"]
        assert "fiatAmount" not in wp  # user picks amount in-widget


# ---------------------------------------------------------------------------
# Daimo: exact USDC amount, chain/token resolution, fail-closed
# ---------------------------------------------------------------------------


class TestDaimoAdapter:
    @pytest.mark.asyncio
    async def test_create_payment_exact_usdc_amount(self):
        client = DaimoClient(DaimoConfig(api_key="k", environment="sandbox"))
        session = _patch_session(
            client,
            [
                {
                    "id": "pay_1",
                    "url": "https://pay.daimo.com/checkout?id=pay_1",
                    "payment": {"id": "pay_1", "status": "payment_unpaid"},
                }
            ],
        )
        adapter = DaimoOnrampAdapter(client)
        # 10_000_000 base units == 10.000000 USDC (6 decimals)
        result = await adapter.create_session(
            wallet_address="0x3a321372E8a9755cD2CA6114eB8dA32A14F8100b",
            chain="base",
            crypto_currency="usdc",
            amount_minor=10_000_000,
        )
        body = session.calls[0][2]["json"]
        dest = body["destination"]
        # Precise, padded decimal string for USDC (6 decimals); no float.
        assert dest["amountUnits"] == "10.000000"
        assert Decimal(dest["amountUnits"]) == Decimal("10")
        assert dest["chainId"] == 8453  # base
        assert dest["tokenAddress"] == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
        assert dest["destinationAddress"].startswith("0x")
        assert result.reference == "pay_1"
        assert result.raw["url"] == "https://pay.daimo.com/checkout?id=pay_1"
        assert result.custody_model == CustodyModel.NON_CUSTODIAL

    @pytest.mark.asyncio
    async def test_unknown_chain_fails_closed(self):
        adapter = DaimoOnrampAdapter(DaimoClient(DaimoConfig(api_key="k")))
        with pytest.raises(ProviderError):
            await adapter.create_session(
                wallet_address="0xabc",
                chain="dogechain",
                amount_minor=1_000_000,
            )

    @pytest.mark.asyncio
    async def test_explicit_chain_id_and_token_override(self):
        client = DaimoClient(DaimoConfig(api_key="k"))
        session = _patch_session(
            client, [{"id": "p2", "url": "https://x", "payment": {"status": "payment_unpaid"}}]
        )
        adapter = DaimoOnrampAdapter(client)
        await adapter.create_session(
            wallet_address="0xabc",
            chain="some-l2",
            crypto_currency="usdc",
            amount_minor=1_000_000,
            metadata={"chain_id": 999, "token_address": "0xToken"},
        )
        dest = session.calls[0][2]["json"]["destination"]
        assert dest["chainId"] == 999
        assert dest["tokenAddress"] == "0xToken"

    @pytest.mark.asyncio
    async def test_rejects_decimal_amount(self):
        adapter = DaimoOnrampAdapter(DaimoClient(DaimoConfig(api_key="k")))
        with pytest.raises(ProviderError):
            await adapter.create_session(
                wallet_address="0xabc",
                chain="base",
                amount_minor=Decimal("10.00"),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Registry: env-gated wiring + sandbox fallback (invariants #1 and #2)
# ---------------------------------------------------------------------------


class TestRegistryOnrampWiring:
    def test_no_keys_falls_back_to_sandbox(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        port = reg.get(ProviderCapability.ONRAMP)
        assert isinstance(port, SandboxOnrampPort)
        assert port.sandbox is True
        assert port.custody_model == CustodyModel.SIMULATED
        assert not reg.has_real(ProviderCapability.ONRAMP)

    def test_onramper_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(), environ={"ONRAMPER_API_KEY": "pk_" + "test"}
        )
        assert reg.has_real(ProviderCapability.ONRAMP)
        port = reg.get(ProviderCapability.ONRAMP)
        assert port.provider == "onramper"
        assert port.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_transak_real_when_keys_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"TRANSAK_API_KEY": "tk", "TRANSAK_API_SECRET": "ts"},
        )
        assert reg.has_real(ProviderCapability.ONRAMP)
        assert reg.get(ProviderCapability.ONRAMP).provider == "transak"

    def test_daimo_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={"DAIMO_PAY_API_KEY": "dk"})
        assert reg.has_real(ProviderCapability.ONRAMP)
        port = reg.get(ProviderCapability.ONRAMP)
        assert port.provider == "daimo"
        assert port.custody_model == CustodyModel.NON_CUSTODIAL

    def test_conduit_keeps_precedence_over_new_onramps(self):
        # Conduit configured + Onramper configured -> Conduit wins (precedence).
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={
                "CONDUIT_API_KEY": "ck",
                "CONDUIT_API_SECRET": "cs",
                "CONDUIT_SANDBOX": "true",
                "ONRAMPER_API_KEY": "pk_test",
            },
        )
        assert reg.get(ProviderCapability.ONRAMP).provider == "conduit"
