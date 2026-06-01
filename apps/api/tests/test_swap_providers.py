"""Tests for the swap provider adapters (LI.FI / 0x v2 / Jupiter).

Proves, without any live keys:

* each adapter conforms to :class:`SwapPort`, reports ``NON_CUSTODIAL`` custody
  and the right sandbox flag;
* the registry wires each real provider only when its env keys/flags are
  present, and falls back to the SIMULATED :class:`SandboxSwapPort` when absent;
* money crosses the boundary as integer minor units and is sent to the vendors
  as exact base-unit strings (no float anywhere);
* each adapter captures its integrator-fee (revenue) param;
* ``quote`` -> ``build_execution`` returns the already-shaped transaction the
  CustodyPort signs, and ``build_execution`` fails closed on an unknown ref;
* adapters fail closed on bad input (non-int amount, wrong chain).

The clients' ``_client_()`` (the httpx session) is monkeypatched so no network
call happens; we assert on the request shape the adapter built.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from server.providers.ports import (
    CustodyModel,
    ProviderCapability,
    ProviderError,
    SwapPort,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxSwapPort
from server.providers.swap import (
    JupiterClient,
    JupiterConfig,
    JupiterSwapAdapter,
    LifiClient,
    LifiConfig,
    LifiSwapAdapter,
    ZeroExClient,
    ZeroExConfig,
    ZeroExSwapAdapter,
)


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

    async def get(self, path: str, *, params=None, headers=None) -> _FakeResponse:
        self.calls.append(("GET", path, {"params": params, "headers": headers}))
        return _FakeResponse(self._responses.pop(0))

    async def post(self, path: str, *, json=None, headers=None) -> _FakeResponse:
        self.calls.append(("POST", path, {"json": json, "headers": headers}))
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
    def test_all_three_conform_to_swap_port(self):
        lifi = LifiSwapAdapter(LifiClient(LifiConfig(environment="staging")))
        zerox = ZeroExSwapAdapter(ZeroExClient(ZeroExConfig(api_key="zx", environment="sandbox")))
        jupiter = JupiterSwapAdapter(JupiterClient(JupiterConfig(environment="sandbox")))
        for adapter in (lifi, zerox, jupiter):
            assert isinstance(adapter, SwapPort)
            assert adapter.capability == ProviderCapability.SWAP
            assert adapter.sandbox is True  # staging/sandbox env
            # Swaps are non-custodial: the user signs from their own wallet.
            assert adapter.custody_model == CustodyModel.NON_CUSTODIAL

    def test_provider_names(self):
        assert LifiSwapAdapter(LifiClient(LifiConfig())).provider == "lifi"
        assert ZeroExSwapAdapter(ZeroExClient(ZeroExConfig(api_key="x"))).provider == "zerox"
        assert JupiterSwapAdapter(JupiterClient(JupiterConfig())).provider == "jupiter"


# ---------------------------------------------------------------------------
# LI.FI: integrator fee capture, money correctness, quote->build, fail-closed
# ---------------------------------------------------------------------------


class TestLifiAdapter:
    @pytest.mark.asyncio
    async def test_quote_sends_integrator_fee_and_exact_amount(self):
        client = LifiClient(LifiConfig(environment="staging", integrator="sardis", fee=0.003))
        session = _patch_session(
            client,
            [
                {
                    "id": "lifi_route_1",
                    "estimate": {
                        "fromAmount": "1000000",
                        "toAmount": "997000",
                        "toAmountMin": "992000",
                        "approvalAddress": "0xSpender",
                    },
                    "transactionRequest": {
                        "to": "0xRouter",
                        "data": "0xabcd",
                        "value": "0",
                        "gasLimit": "210000",
                        "chainId": 8453,
                    },
                }
            ],
        )
        adapter = LifiSwapAdapter(client)
        # 1_000_000 base units == 1 USDC (6 decimals).
        result = await adapter.quote(
            chain="base",
            sell_token="0xUSDC",
            buy_token="0xWETH",
            sell_amount_minor=1_000_000,
        )
        method, path, kw = session.calls[0]
        assert (method, path) == ("GET", "/v1/quote")
        params = kw["params"]
        # Exact base-unit string from minor units; no float.
        assert params["fromAmount"] == "1000000"
        assert isinstance(params["fromAmount"], str)
        # Same-chain swap: from == to chain.
        assert params["fromChain"] == "base"
        assert params["toChain"] == "base"
        # Integrator-fee (revenue) params captured.
        assert params["integrator"] == "sardis"
        assert params["fee"] == 0.003
        assert result.status == "quoted"
        assert result.custody_model == CustodyModel.NON_CUSTODIAL
        assert result.raw["buy_amount"] == "997000"
        assert result.raw["buy_amount_min"] == "992000"

    @pytest.mark.asyncio
    async def test_build_execution_rebinds_to_real_taker(self):
        client = LifiClient(LifiConfig(environment="staging", fee=0.003))
        session = _patch_session(
            client,
            [
                {  # initial indicative quote
                    "id": "lifi_route_1",
                    "estimate": {"fromAmount": "1000000", "toAmount": "997000"},
                    "transactionRequest": {"to": "0xR", "data": "0x01", "chainId": 8453},
                },
                {  # re-quote bound to the taker
                    "id": "lifi_route_1",
                    "estimate": {
                        "fromAmount": "1000000",
                        "toAmount": "997000",
                        "toAmountMin": "992000",
                        "approvalAddress": "0xSpender",
                    },
                    "transactionRequest": {
                        "to": "0xRouter",
                        "data": "0xtakerbound",
                        "value": "0",
                        "chainId": 8453,
                    },
                },
            ],
        )
        adapter = LifiSwapAdapter(client)
        q = await adapter.quote(
            chain="base", sell_token="0xUSDC", buy_token="0xWETH", sell_amount_minor=1_000_000
        )
        ref = q.raw["quote_ref"]
        built = await adapter.build_execution(quote_ref=ref, taker_address="0xTaker")
        # Second GET carries the real taker as fromAddress.
        assert session.calls[1][2]["params"]["fromAddress"] == "0xTaker"
        assert built.status == "ready"
        assert built.raw["transaction"]["to"] == "0xRouter"
        assert built.raw["transaction"]["data"] == "0xtakerbound"
        assert built.raw["allowance_spender"] == "0xSpender"

    @pytest.mark.asyncio
    async def test_rejects_non_int_amount(self):
        adapter = LifiSwapAdapter(LifiClient(LifiConfig()))
        with pytest.raises(ProviderError):
            await adapter.quote(
                chain="base",
                sell_token="0xUSDC",
                buy_token="0xWETH",
                sell_amount_minor=Decimal("1.0"),  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_build_execution_unknown_ref_fails_closed(self):
        adapter = LifiSwapAdapter(LifiClient(LifiConfig()))
        with pytest.raises(ProviderError):
            await adapter.build_execution(quote_ref="nope", taker_address="0xT")


# ---------------------------------------------------------------------------
# 0x v2: swapFeeBps capture, taker required at build, calldata returned
# ---------------------------------------------------------------------------


class TestZeroExAdapter:
    @pytest.mark.asyncio
    async def test_build_execution_sends_fee_and_taker_returns_calldata(self):
        client = ZeroExClient(
            ZeroExConfig(
                api_key="zx_test",
                environment="sandbox",
                swap_fee_bps=30,
                swap_fee_recipient="0xFeeWallet",
            )
        )
        session = _patch_session(
            client,
            [
                {
                    "blockNumber": "20264713",
                    "buyAmount": "300433569",
                    "minBuyAmount": "297405770",
                    "sellAmount": "100000000",
                    "issues": {"allowance": {"spender": "0xAllowanceHolder"}},
                    "transaction": {
                        "to": "0x7f6c",
                        "data": "0x1fff991f",
                        "gas": "221184",
                        "gasPrice": "1877540000",
                        "value": "0",
                    },
                }
            ],
        )
        adapter = ZeroExSwapAdapter(client)
        q = await adapter.quote(
            chain="ethereum",
            sell_token="0xUSDC",
            buy_token="0xDAI",
            sell_amount_minor=100_000_000,
        )
        # quote() does not hit the network for 0x (taker needed); no calls yet.
        assert session.calls == []
        ref = q.raw["quote_ref"]
        built = await adapter.build_execution(quote_ref=ref, taker_address="0xTaker")
        method, path, kw = session.calls[0]
        assert (method, path) == ("GET", "/swap/allowance-holder/quote")
        params = kw["params"]
        assert params["chainId"] == 1  # ethereum resolved
        assert params["sellAmount"] == "100000000"  # exact, string
        assert params["taker"] == "0xTaker"  # required in v2
        # Integrator-fee (revenue) params captured; fee token defaults to buy.
        assert params["swapFeeBps"] == 30
        assert params["swapFeeRecipient"] == "0xFeeWallet"
        assert params["swapFeeToken"] == "0xDAI"
        # Calldata returned for the CustodyPort to sign.
        assert built.raw["transaction"]["to"] == "0x7f6c"
        assert built.raw["transaction"]["data"] == "0x1fff991f"
        assert built.raw["allowance_spender"] == "0xAllowanceHolder"
        assert built.raw["buy_amount"] == "300433569"

    @pytest.mark.asyncio
    async def test_numeric_chain_id_passthrough(self):
        client = ZeroExClient(ZeroExConfig(api_key="zx"))
        session = _patch_session(
            client,
            [{"buyAmount": "1", "sellAmount": "1", "issues": {}, "transaction": {}}],
        )
        adapter = ZeroExSwapAdapter(client)
        q = await adapter.quote(
            chain="42161", sell_token="0xA", buy_token="0xB", sell_amount_minor=5
        )
        await adapter.build_execution(quote_ref=q.raw["quote_ref"], taker_address="0xT")
        assert session.calls[0][2]["params"]["chainId"] == 42161

    @pytest.mark.asyncio
    async def test_unknown_chain_fails_closed(self):
        adapter = ZeroExSwapAdapter(ZeroExClient(ZeroExConfig(api_key="zx")))
        with pytest.raises(ProviderError):
            await adapter.quote(
                chain="dogechain", sell_token="0xA", buy_token="0xB", sell_amount_minor=1
            )

    def test_fee_omitted_when_unconfigured(self):
        client = ZeroExClient(ZeroExConfig(api_key="zx"))
        params = client._fee_params(
            sell_token="0xA",
            buy_token="0xB",
            swap_fee_bps=None,
            swap_fee_recipient=None,
            swap_fee_token=None,
        )
        assert params == {}


# ---------------------------------------------------------------------------
# Jupiter: platformFeeBps capture, Solana-only, quote echo at build
# ---------------------------------------------------------------------------


class TestJupiterAdapter:
    @pytest.mark.asyncio
    async def test_quote_sends_platform_fee_and_build_echoes_quote(self):
        client = JupiterClient(JupiterConfig(environment="sandbox", platform_fee_bps=30))
        session = _patch_session(
            client,
            [
                {
                    "inAmount": "1000000",
                    "outAmount": "25000000",
                    "otherAmountThreshold": "24875000",
                    "routePlan": [{"swapInfo": {}}],
                },
                {
                    "swapTransaction": "BASE64TX",
                    "lastValidBlockHeight": 123456,
                },
            ],
        )
        adapter = JupiterSwapAdapter(client)
        q = await adapter.quote(
            chain="solana",
            sell_token="EPjF...USDC",
            buy_token="So111...SOL",
            sell_amount_minor=1_000_000,
        )
        method, path, kw = session.calls[0]
        assert (method, path) == ("GET", "/swap/v1/quote")
        params = kw["params"]
        assert params["amount"] == "1000000"  # exact base-unit string
        assert params["inputMint"] == "EPjF...USDC"
        assert params["platformFeeBps"] == 30  # revenue param captured
        assert q.raw["buy_amount"] == "25000000"

        ref = q.raw["quote_ref"]
        built = await adapter.build_execution(quote_ref=ref, taker_address="SoLPubKey")
        m2, p2, kw2 = session.calls[1]
        assert (m2, p2) == ("POST", "/swap/v1/swap")
        body = kw2["json"]
        # The exact quote response is echoed back (Jupiter requirement).
        assert body["quoteResponse"]["outAmount"] == "25000000"
        assert body["userPublicKey"] == "SoLPubKey"
        assert built.raw["swap_transaction"] == "BASE64TX"

    @pytest.mark.asyncio
    async def test_non_solana_chain_fails_closed(self):
        adapter = JupiterSwapAdapter(JupiterClient(JupiterConfig()))
        with pytest.raises(ProviderError):
            await adapter.quote(
                chain="base", sell_token="A", buy_token="B", sell_amount_minor=1_000_000
            )

    def test_keyless_uses_lite_host(self):
        keyless = JupiterClient(JupiterConfig())
        assert keyless._base_url == "https://lite-api.jup.ag"
        keyed = JupiterClient(JupiterConfig(api_key="jk"))
        assert keyed._base_url == "https://api.jup.ag"


# ---------------------------------------------------------------------------
# Registry: env-gated wiring + sandbox fallback (invariants #1 and #2)
# ---------------------------------------------------------------------------


class TestRegistrySwapWiring:
    def test_no_keys_falls_back_to_sandbox(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        port = reg.get(ProviderCapability.SWAP)
        assert isinstance(port, SandboxSwapPort)
        assert port.sandbox is True
        assert port.custody_model == CustodyModel.SIMULATED
        assert not reg.has_real(ProviderCapability.SWAP)

    def test_lifi_real_when_enabled(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(), environ={"LIFI_ENABLED": "true", "LIFI_FEE": "0.003"}
        )
        assert reg.has_real(ProviderCapability.SWAP)
        port = reg.get(ProviderCapability.SWAP)
        assert port.provider == "lifi"
        assert port.custody_model == CustodyModel.NON_CUSTODIAL

    def test_lifi_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={"LIFI_API_KEY": "lk"})
        assert reg.get(ProviderCapability.SWAP).provider == "lifi"

    def test_zerox_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={"ZEROX_API_KEY": "zx"})
        assert reg.has_real(ProviderCapability.SWAP)
        assert reg.get(ProviderCapability.SWAP).provider == "zerox"

    def test_jupiter_real_when_enabled(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={"JUPITER_ENABLED": "1"})
        assert reg.get(ProviderCapability.SWAP).provider == "jupiter"

    def test_lifi_keeps_precedence_over_others(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={
                "LIFI_API_KEY": "lk",
                "ZEROX_API_KEY": "zx",
                "JUPITER_ENABLED": "true",
            },
        )
        assert reg.get(ProviderCapability.SWAP).provider == "lifi"
