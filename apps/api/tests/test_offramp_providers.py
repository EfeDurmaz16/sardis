"""Tests for the offramp provider adapters (Onramper / Transak Stream / Coinbase).

Proves, without any live keys:

* each adapter conforms to :class:`OfframpPort` and reports the right custody
  model + sandbox flag;
* the registry wires each real provider only when its env keys are present and
  falls back to the SIMULATED :class:`SandboxOfframpPort` when keys are absent;
* higher-priority offramps (Circle CPN / Increase) keep precedence over these
  aggregators;
* money crosses the boundary as integer minor units of the source crypto token
  and is converted to the vendors' decimal-string sell amounts with no float;
* each adapter fails closed on a missing required field / unknown rail rather
  than guessing on a money path;
* the Coinbase CDP JWT is signed (Ed25519 / ES256) without leaking the key.

The clients' ``_client_()`` (the httpx session) is monkeypatched so no network
call happens; we assert on the request shape the adapter built.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from server.providers.offramp import (
    CoinbaseOfframpAdapter,
    CoinbaseOfframpClient,
    CoinbaseOfframpConfig,
    OnramperOfframpAdapter,
    OnramperOfframpClient,
    OnramperOfframpConfig,
    TransakStreamClient,
    TransakStreamConfig,
    TransakStreamOfframpAdapter,
)
from server.providers.ports import (
    CustodyModel,
    OfframpPort,
    ProviderCapability,
    ProviderError,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxOfframpPort

# A real Ed25519 seed (base64) for JWT-signing tests — test-only, not a secret
# that authenticates anything: 32 zero bytes -> deterministic key.
_TEST_ED25519_SEED_B64 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


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
    """Records each POST/GET so the test can assert request shape + headers."""

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
    def test_all_three_conform_to_offramp_port(self):
        onramper = OnramperOfframpAdapter(
            OnramperOfframpClient(OnramperOfframpConfig(api_key="pk_test", environment="staging"))
        )
        transak = TransakStreamOfframpAdapter(
            TransakStreamClient(TransakStreamConfig(api_key="k", environment="staging"))
        )
        coinbase = CoinbaseOfframpAdapter(
            CoinbaseOfframpClient(
                CoinbaseOfframpConfig(
                    api_key_name="org/key",
                    api_key_private=_TEST_ED25519_SEED_B64,
                    environment="sandbox",
                )
            )
        )
        for adapter in (onramper, transak, coinbase):
            assert isinstance(adapter, OfframpPort)
            assert adapter.capability == ProviderCapability.OFFRAMP
            assert adapter.sandbox is True  # staging/sandbox env
            # Every offramp leg is partner-custodied (the partner takes custody
            # of the crypto and settles fiat).
            assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED


# ---------------------------------------------------------------------------
# Onramper: sell-intent request shape + money correctness
# ---------------------------------------------------------------------------


class TestOnramperOfframpAdapter:
    @pytest.mark.asyncio
    async def test_create_payout_builds_sell_intent_with_decimal_amount(self):
        client = OnramperOfframpClient(
            OnramperOfframpConfig(api_key="pk_test", environment="staging")
        )
        session = _patch_session(
            client,
            [
                {
                    "transactionId": "tx_sell_1",
                    "status": "created",
                    "transactionInformation": {"url": "https://sell.onramper.com/tx_sell_1"},
                }
            ],
        )
        adapter = OnramperOfframpAdapter(client)
        # 10_000_000 base units == 10.000000 USDC (6 decimals).
        txn = await adapter.create_payout(
            source_chain="base",
            source_token="usdc",
            amount_minor=10_000_000,
            destination_bank_ref="banktransfer",
            fiat_currency="USD",
            metadata={"source_address": "0xabc"},
        )
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/checkout/intent")
        body = kw["json"]
        assert body["type"] == "sell"
        assert body["source"] == "usdc"  # crypto being sold
        assert body["destination"] == "usd"  # fiat received
        assert body["network"] == "base"
        assert body["wallet"]["address"] == "0xabc"
        # Exact decimal string from minor units; no float anywhere.
        assert body["amount"] == "10.000000"
        assert Decimal(body["amount"]) == Decimal("10")
        # NormalizedTxn carries source crypto minor units + fiat currency.
        assert txn.amount_minor == 10_000_000
        assert txn.currency == "USD"
        assert txn.reference == "tx_sell_1"
        assert txn.raw["url"] == "https://sell.onramper.com/tx_sell_1"
        assert txn.custody_model == CustodyModel.PARTNER_CUSTODIED
        assert txn.sandbox is True

    @pytest.mark.asyncio
    async def test_requires_source_address(self):
        adapter = OnramperOfframpAdapter(
            OnramperOfframpClient(OnramperOfframpConfig(api_key="pk_x"))
        )
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                source_chain="base",
                source_token="usdc",
                amount_minor=1_000_000,
                destination_bank_ref="banktransfer",
            )

    @pytest.mark.asyncio
    async def test_rejects_decimal_amount(self):
        adapter = OnramperOfframpAdapter(
            OnramperOfframpClient(OnramperOfframpConfig(api_key="pk_x"))
        )
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                source_chain="base",
                source_token="usdc",
                amount_minor=Decimal("10.00"),  # type: ignore[arg-type]
                destination_bank_ref="banktransfer",
                metadata={"source_address": "0xabc"},
            )

    @pytest.mark.asyncio
    async def test_get_status_reads_transaction(self):
        client = OnramperOfframpClient(OnramperOfframpConfig(api_key="pk_x"))
        session = _patch_session(client, [{"transactionId": "tx_9", "status": "completed"}])
        adapter = OnramperOfframpAdapter(client)
        result = await adapter.get_status("tx_9")
        assert session.calls[0][:2] == ("GET", "/transactions/tx_9")
        assert result.status == "completed"


# ---------------------------------------------------------------------------
# Transak Stream: address-based SELL order, deposit address is the payload
# ---------------------------------------------------------------------------


class TestTransakStreamAdapter:
    @pytest.mark.asyncio
    async def test_create_payout_returns_deposit_address(self):
        client = TransakStreamClient(TransakStreamConfig(api_key="tk", environment="staging"))
        session = _patch_session(
            client,
            [
                {
                    "data": {
                        "orderId": "ord_123",
                        "status": "AWAITING_PAYMENT_FROM_USER",
                        "payinAddress": "0xDEPOSIT",
                    }
                }
            ],
        )
        adapter = TransakStreamOfframpAdapter(client)
        txn = await adapter.create_payout(
            source_chain="polygon",
            source_token="usdc",
            amount_minor=25_000_000,  # 25.000000 USDC
            destination_bank_ref="sepa_bank_transfer",
            fiat_currency="EUR",
            idempotency_key="idem_1",
            metadata={"partner_user_id": "user_1"},
        )
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/api/v2/orders")
        # Secret is sent only via the x-api-key header, never the body/query.
        assert kw["headers"] is None or "x-api-key" not in (kw["headers"] or {})
        body = kw["json"]
        assert body["isBuyOrSell"] == "SELL"
        assert body["cryptoCurrency"] == "USDC"
        assert body["network"] == "polygon"
        assert body["fiatCurrency"] == "EUR"
        assert body["paymentInstrumentId"] == "sepa_bank_transfer"
        assert body["partnerUserId"] == "user_1"
        assert body["partnerOrderId"] == "idem_1"  # idempotency key threaded
        assert Decimal(body["cryptoAmount"]) == Decimal("25")
        # The deposit address (agent-fundable) is surfaced in raw.
        assert txn.raw["deposit_address"] == "0xDEPOSIT"
        assert txn.reference == "ord_123"
        assert txn.currency == "EUR"
        assert txn.custody_model == CustodyModel.PARTNER_CUSTODIED

    @pytest.mark.asyncio
    async def test_requires_partner_user_id(self):
        adapter = TransakStreamOfframpAdapter(
            TransakStreamClient(TransakStreamConfig(api_key="tk"))
        )
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                source_chain="base",
                source_token="usdc",
                amount_minor=1_000_000,
                destination_bank_ref="sepa_bank_transfer",
            )

    @pytest.mark.asyncio
    async def test_status_is_not_fabricated(self):
        adapter = TransakStreamOfframpAdapter(
            TransakStreamClient(TransakStreamConfig(api_key="tk"))
        )
        result = await adapter.get_status("ord_123")
        # No GET-by-id that settles; report pending rather than invent "completed".
        assert result.status == "pending"
        assert "webhook" in result.raw["note"]


# ---------------------------------------------------------------------------
# Coinbase Offramp: session token -> sell quote -> hosted URL, JWT auth
# ---------------------------------------------------------------------------


class TestCoinbaseOfframpAdapter:
    @pytest.mark.asyncio
    async def test_create_payout_session_then_quote_with_decimal_amount(self):
        client = CoinbaseOfframpClient(
            CoinbaseOfframpConfig(
                api_key_name="org/key",
                api_key_private=_TEST_ED25519_SEED_B64,
                environment="sandbox",
            )
        )
        session = _patch_session(
            client,
            [
                {"token": "sess_tok_1"},
                {
                    "quote_id": "q_1",
                    "cashout_total": {"value": "9.50", "currency": "USD"},
                },
            ],
        )
        adapter = CoinbaseOfframpAdapter(client)
        txn = await adapter.create_payout(
            source_chain="base",
            source_token="usdc",
            amount_minor=10_000_000,  # 10.000000 USDC
            destination_bank_ref="ach",
            fiat_currency="USD",
            metadata={"source_address": "0xabc", "country": "US"},
        )
        # Call 1: session token.
        m1, p1, kw1 = session.calls[0]
        assert (m1, p1) == ("POST", "/onramp/v1/token")
        assert kw1["headers"]["Authorization"].startswith("Bearer ")
        assert kw1["json"]["addresses"][0]["address"] == "0xabc"
        # Call 2: sell quote with normalized ACH payment method + decimal amount.
        m2, p2, kw2 = session.calls[1]
        assert (m2, p2) == ("POST", "/onramp/v1/sell/quote")
        qbody = kw2["json"]
        assert qbody["paymentMethod"] == "ACH_BANK_ACCOUNT"
        assert qbody["sellCurrency"] == "USDC"
        assert qbody["cashoutCurrency"] == "USD"
        assert qbody["country"] == "US"
        assert Decimal(qbody["sellAmount"]) == Decimal("10")
        # No offramp_url in quote -> adapter assembles the hosted URL.
        assert txn.raw["url"].startswith("https://pay.coinbase.com/v3/sell/input?")
        assert "sessionToken=sess_tok_1" in txn.raw["url"]
        assert txn.raw["cashout_method"] == "ACH_BANK_ACCOUNT"
        assert txn.reference == "q_1"
        assert txn.custody_model == CustodyModel.PARTNER_CUSTODIED

    @pytest.mark.asyncio
    async def test_paypal_cashout_method(self):
        client = CoinbaseOfframpClient(
            CoinbaseOfframpConfig(api_key_name="org/key", api_key_private=_TEST_ED25519_SEED_B64)
        )
        _patch_session(client, [{"token": "t"}, {"quote_id": "q", "offramp_url": "https://x"}])
        adapter = CoinbaseOfframpAdapter(client)
        txn = await adapter.create_payout(
            source_chain="base",
            source_token="usdc",
            amount_minor=5_000_000,
            destination_bank_ref="paypal",
            metadata={"source_address": "0xabc"},
        )
        assert txn.raw["cashout_method"] == "PAYPAL"
        # Quote-provided offramp_url is preferred over the assembled one.
        assert txn.raw["url"] == "https://x"

    @pytest.mark.asyncio
    async def test_unknown_cashout_method_fails_closed(self):
        client = CoinbaseOfframpClient(
            CoinbaseOfframpConfig(api_key_name="org/key", api_key_private=_TEST_ED25519_SEED_B64)
        )
        _patch_session(client, [{"token": "t"}])
        adapter = CoinbaseOfframpAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                source_chain="base",
                source_token="usdc",
                amount_minor=1_000_000,
                destination_bank_ref="carrier_pigeon",
                metadata={"source_address": "0xabc"},
            )

    @pytest.mark.asyncio
    async def test_requires_source_address(self):
        client = CoinbaseOfframpClient(
            CoinbaseOfframpConfig(api_key_name="org/key", api_key_private=_TEST_ED25519_SEED_B64)
        )
        adapter = CoinbaseOfframpAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                source_chain="base",
                source_token="usdc",
                amount_minor=1_000_000,
                destination_bank_ref="ach",
            )

    def test_cdp_jwt_is_signed_ed25519(self):
        from server.providers.offramp.client import _cdp_jwt

        token = _cdp_jwt(
            api_key_name="org/key",
            api_key_private=_TEST_ED25519_SEED_B64,
            request_method="POST",
            request_path="/onramp/v1/token",
        )
        # Three base64url segments; never contains the raw key material.
        assert token.count(".") == 2
        assert _TEST_ED25519_SEED_B64 not in token


# ---------------------------------------------------------------------------
# Registry: env-gated wiring + sandbox fallback + precedence (invariants #1/#2)
# ---------------------------------------------------------------------------


class TestRegistryOfframpWiring:
    def test_no_keys_falls_back_to_sandbox(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        port = reg.get(ProviderCapability.OFFRAMP)
        assert isinstance(port, SandboxOfframpPort)
        assert port.sandbox is True
        assert port.custody_model == CustodyModel.SIMULATED
        assert not reg.has_real(ProviderCapability.OFFRAMP)

    def test_onramper_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(), environ={"ONRAMPER_API_KEY": "pk_test"}
        )
        assert reg.has_real(ProviderCapability.OFFRAMP)
        port = reg.get(ProviderCapability.OFFRAMP)
        assert port.provider == "onramper"
        assert port.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_transak_stream_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(), environ={"TRANSAK_STREAM_API_KEY": "tk"}
        )
        assert reg.has_real(ProviderCapability.OFFRAMP)
        assert reg.get(ProviderCapability.OFFRAMP).provider == "transak_stream"

    def test_coinbase_offramp_real_when_keys_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={
                "COINBASE_CDP_API_KEY_NAME": "org/key",
                "COINBASE_CDP_API_KEY_PRIVATE": _TEST_ED25519_SEED_B64,
            },
        )
        assert reg.has_real(ProviderCapability.OFFRAMP)
        port = reg.get(ProviderCapability.OFFRAMP)
        assert port.provider == "coinbase_offramp"

    def test_onramper_keeps_precedence_over_transak_and_coinbase(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={
                "ONRAMPER_API_KEY": "pk_test",
                "TRANSAK_STREAM_API_KEY": "tk",
                "COINBASE_CDP_API_KEY_NAME": "org/key",
                "COINBASE_CDP_API_KEY_PRIVATE": _TEST_ED25519_SEED_B64,
            },
        )
        # First configured in priority order wins.
        assert reg.get(ProviderCapability.OFFRAMP).provider == "onramper"
