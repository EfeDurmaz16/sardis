"""Tests for the cross-chain bridge adapters (Squid / CCTP v2).

Proves, without any live keys:

* each adapter conforms to :class:`BridgePort`, reports ``NON_CUSTODIAL``
  custody and the right sandbox flag;
* the registry wires each real provider only when its env keys/flags are
  present, and falls back to the SIMULATED :class:`SandboxBridgePort` when
  absent (invariants #1 and #2);
* money crosses the boundary as integer minor units and is sent to the vendors
  as exact base-unit strings (no float anywhere);
* ``quote`` -> ``build_execution`` returns the already-shaped transaction the
  CustodyPort signs, and ``build_execution`` fails closed on an unknown ref;
* Squid carries the integrator id and binds the route to from/to addresses at
  build time; CCTP encodes a correct ``depositForBurn`` and computes maxFee
  with Decimal arithmetic;
* adapters fail closed on bad input (non-int amount, unknown chain/domain).

The Squid client's ``_client_()`` (the httpx session) is monkeypatched so no
network call happens; we assert on the request shape the adapter built.  CCTP's
calldata encoding is pure (no I/O) so it is asserted directly.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from server.providers.bridge import (
    CCTP_TOKEN_MESSENGER_V2,
    CctpBridgeAdapter,
    CctpClient,
    CctpConfig,
    SquidBridgeAdapter,
    SquidClient,
    SquidConfig,
)
from server.providers.bridge.client import _DEPOSIT_FOR_BURN_SELECTOR
from server.providers.ports import (
    BridgePort,
    CustodyModel,
    ProviderCapability,
    ProviderError,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxBridgePort


def _dev_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=False, database_url="", circle_cpn=SimpleNamespace())


# ---------------------------------------------------------------------------
# Fake httpx response/session so no network call happens.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:  # pragma: no cover - happy path
        return None

    def json(self):
        return self._payload


class _FakeSession:
    """Records the last POST/GET so the test can assert request shape."""

    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    async def get(self, path: str, *, params=None, headers=None) -> _FakeResponse:
        self.calls.append(("GET", path, {"params": params, "headers": headers}))
        return self._next()

    async def post(self, path: str, *, json=None, headers=None) -> _FakeResponse:
        self.calls.append(("POST", path, {"json": json, "headers": headers}))
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


# ---------------------------------------------------------------------------
# Port conformance + custody models
# ---------------------------------------------------------------------------


class TestPortConformance:
    def test_both_conform_to_bridge_port(self):
        squid = SquidBridgeAdapter(
            SquidClient(SquidConfig(integrator_id="sardis", environment="staging"))
        )
        cctp = CctpBridgeAdapter(CctpClient(CctpConfig(environment="sandbox")))
        for adapter in (squid, cctp):
            assert isinstance(adapter, BridgePort)
            assert adapter.capability == ProviderCapability.BRIDGE
            assert adapter.sandbox is True  # staging/sandbox env
            # Bridges are non-custodial: the user signs/burns from their wallet.
            assert adapter.custody_model == CustodyModel.NON_CUSTODIAL

    def test_provider_names(self):
        assert SquidBridgeAdapter(SquidClient(SquidConfig(integrator_id="x"))).provider == "squid"
        assert CctpBridgeAdapter(CctpClient(CctpConfig())).provider == "cctp"

    def test_squid_requires_integrator_id(self):
        with pytest.raises(ValueError):
            SquidClient(SquidConfig(integrator_id=""))


# ---------------------------------------------------------------------------
# Squid: integrator id header, exact amount, quote->build rebinds addresses
# ---------------------------------------------------------------------------


class TestSquidAdapter:
    @pytest.mark.asyncio
    async def test_build_execution_sends_integrator_and_addresses(self):
        client = SquidClient(SquidConfig(integrator_id="sardis-int", environment="staging"))
        session = _patch_session(
            client,
            [
                {
                    "route": {
                        "quoteId": "q_123",
                        "estimate": {
                            "fromAmount": "1000000",
                            "toAmount": "998500",
                            "toAmountMin": "990000",
                        },
                        "transactionRequest": {
                            "target": "0xSquidRouter",
                            "data": "0xdeadbeef",
                            "value": "0",
                            "gasLimit": "500000",
                            "chainId": "8453",
                        },
                    }
                }
            ],
        )
        adapter = SquidBridgeAdapter(client)
        # 1_000_000 base units == 1 USDC (6 decimals). Base -> Tempo (pathUSD).
        q = await adapter.quote(
            from_chain="8453",
            to_chain="4217",
            token="0xUSDC",
            amount_minor=1_000_000,
        )
        # quote() does not hit the network (route is bound to addresses at build).
        assert session.calls == []
        assert q.status == "quoted"
        assert q.custody_model == CustodyModel.NON_CUSTODIAL

        ref = q.raw["quote_ref"]
        built = await adapter.build_execution(
            quote_ref=ref,
            sender_address="0xSender",
            recipient_address="0xRecipient",
        )
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/v2/route")
        body = kw["json"]
        # Exact base-unit string from minor units; no float.
        assert body["fromAmount"] == "1000000"
        assert isinstance(body["fromAmount"], str)
        assert body["fromChain"] == "8453"
        assert body["toChain"] == "4217"
        assert body["fromAddress"] == "0xSender"
        assert body["toAddress"] == "0xRecipient"
        # Integrator id rides on the client headers (asserted in header test).
        # The already-shaped tx is returned for the CustodyPort.
        assert built.status == "ready"
        assert built.raw["transaction"]["to"] == "0xSquidRouter"
        assert built.raw["transaction"]["data"] == "0xdeadbeef"
        assert built.raw["receive_amount"] == "998500"
        assert built.raw["receive_amount_min"] == "990000"
        # quoteId is surfaced for Squid Intents status tracking.
        assert built.raw["quote_id"] == "q_123"
        assert built.reference == "q_123"

    @pytest.mark.asyncio
    async def test_integrator_id_on_client_headers(self):
        client = SquidClient(SquidConfig(integrator_id="sardis-int", environment="staging"))
        session = await client._client_()
        assert session.headers["x-integrator-id"] == "sardis-int"
        await client.close()

    @pytest.mark.asyncio
    async def test_rejects_non_int_amount(self):
        adapter = SquidBridgeAdapter(SquidClient(SquidConfig(integrator_id="x")))
        with pytest.raises(ProviderError):
            await adapter.quote(
                from_chain="8453",
                to_chain="4217",
                token="0xUSDC",
                amount_minor=Decimal("1.0"),  # type: ignore[arg-type]
            )

    @pytest.mark.asyncio
    async def test_build_execution_unknown_ref_fails_closed(self):
        adapter = SquidBridgeAdapter(SquidClient(SquidConfig(integrator_id="x")))
        with pytest.raises(ProviderError):
            await adapter.build_execution(
                quote_ref="nope", sender_address="0xS", recipient_address="0xR"
            )


# ---------------------------------------------------------------------------
# CCTP v2: domain resolution, Decimal maxFee, depositForBurn calldata, fast/std
# ---------------------------------------------------------------------------


class TestCctpAdapter:
    @pytest.mark.asyncio
    async def test_fast_quote_fetches_fee_and_computes_maxfee_with_decimal(self):
        client = CctpClient(CctpConfig(environment="sandbox", fast=True))
        # /v2/burn/USDC/fees -> minimumFee "0.05" (== 5 bps).
        session = _patch_session(client, [[{"minimumFee": "0.05"}]])
        adapter = CctpBridgeAdapter(client)
        # 100 USDC == 100_000_000 base units. minimumFee "0.05" -> bps-hundredths
        # int 5 (Circle reference: "0"+"05"); protocolFee = amount*5/1e6 = 500;
        # +20% buffer = 600 (matches Circle's reference arithmetic exactly).
        q = await adapter.quote(
            from_chain="ethereum",
            to_chain="base",
            token="0xUSDC",
            amount_minor=100_000_000,
        )
        method, path, _ = session.calls[0]
        assert (method, path) == ("GET", "/v2/burn/USDC/fees/0/6")  # eth=0, base=6
        assert q.raw["source_domain"] == 0
        assert q.raw["destination_domain"] == 6
        assert q.raw["fast"] is True
        assert q.raw["finality"] == 1000
        # maxFee computed exactly with Decimal (no float): 100e6*5/1e6*1.2 = 600.
        assert q.raw["max_fee"] == "600"
        # Recipient receives amount - maxFee.
        assert q.raw["receive_amount"] == str(100_000_000 - 600)

    @pytest.mark.asyncio
    async def test_standard_transfer_zero_fee_no_network(self):
        client = CctpClient(CctpConfig(environment="sandbox", fast=False))
        session = _patch_session(client, [])
        adapter = CctpBridgeAdapter(client)
        q = await adapter.quote(
            from_chain="base",
            to_chain="arbitrum",
            token="0xUSDC",
            amount_minor=5_000_000,
        )
        # Standard transfer has no protocol fee, so no fee endpoint is called.
        assert session.calls == []
        assert q.raw["fast"] is False
        assert q.raw["finality"] == 2000
        assert q.raw["max_fee"] == "0"
        assert q.raw["receive_amount"] == "5000000"

    @pytest.mark.asyncio
    async def test_build_execution_encodes_deposit_for_burn(self):
        client = CctpClient(CctpConfig(environment="sandbox", fast=False))
        _patch_session(client, [])
        adapter = CctpBridgeAdapter(client)
        q = await adapter.quote(
            from_chain="base",
            to_chain="arbitrum",
            token="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Base USDC
            amount_minor=1_000_000,
        )
        built = await adapter.build_execution(
            quote_ref=q.raw["quote_ref"],
            sender_address="0xSender0000000000000000000000000000000000",
            recipient_address="0x1111111111111111111111111111111111111111",
        )
        tx = built.raw["transaction"]
        # Burn tx targets the canonical TokenMessengerV2.
        assert tx["to"] == CCTP_TOKEN_MESSENGER_V2
        assert tx["value"] == "0"
        data = tx["data"]
        # Correct 7-arg V2 selector.
        assert data.startswith(_DEPOSIT_FOR_BURN_SELECTOR)
        assert _DEPOSIT_FOR_BURN_SELECTOR == "0x8e0250ee"
        body = data[len(_DEPOSIT_FOR_BURN_SELECTOR) :]
        # 7 static 32-byte words.
        assert len(body) == 7 * 64
        words = [body[i : i + 64] for i in range(0, len(body), 64)]
        # word0 amount == 1_000_000.
        assert int(words[0], 16) == 1_000_000
        # word1 destinationDomain == arbitrum (3).
        assert int(words[1], 16) == 3
        # word2 mintRecipient is the left-padded recipient address.
        assert words[2].endswith("1111111111111111111111111111111111111111")
        # word3 burnToken left-padded.
        assert words[3].endswith("833589fcd6edb6e08f4c7c32d4f71b54bda02913")
        # word4 destinationCaller == 0 (any caller may mint).
        assert int(words[4], 16) == 0
        # word5 maxFee == 0 (standard).
        assert int(words[5], 16) == 0
        # word6 minFinalityThreshold == 2000 (standard).
        assert int(words[6], 16) == 2000

    @pytest.mark.asyncio
    async def test_unknown_chain_fails_closed(self):
        adapter = CctpBridgeAdapter(CctpClient(CctpConfig()))
        with pytest.raises(ProviderError):
            await adapter.quote(
                from_chain="dogechain",
                to_chain="base",
                token="0xUSDC",
                amount_minor=1_000_000,
            )

    @pytest.mark.asyncio
    async def test_get_attestation_404_is_pending(self):
        client = CctpClient(CctpConfig(environment="sandbox"))
        _patch_session(client, [_FakeResponse(None, status_code=404)])
        att = await client.get_attestation(source_domain=0, transaction_hash="0xabc")
        assert att["status"] == "pending_confirmations"

    @pytest.mark.asyncio
    async def test_get_attestation_complete_returns_message(self):
        client = CctpClient(CctpConfig(environment="sandbox"))
        _patch_session(
            client,
            [{"messages": [{"message": "0xMSG", "attestation": "0xATT", "status": "complete"}]}],
        )
        att = await client.get_attestation(source_domain=0, transaction_hash="0xabc")
        assert att["status"] == "complete"
        assert att["message"] == "0xMSG"
        assert att["attestation"] == "0xATT"

    def test_selector_matches_signature(self):
        # The selector is derived from the V2 signature, not a magic literal.
        from eth_utils import keccak

        sig = "depositForBurn(uint256,uint32,bytes32,address,bytes32,uint256,uint32)"
        expected = "0x" + keccak(text=sig).hex()[:8]
        assert expected == _DEPOSIT_FOR_BURN_SELECTOR


# ---------------------------------------------------------------------------
# Registry: env-gated wiring + sandbox fallback (invariants #1 and #2)
# ---------------------------------------------------------------------------


class TestRegistryBridgeWiring:
    def test_no_keys_falls_back_to_sandbox(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        port = reg.get(ProviderCapability.BRIDGE)
        assert isinstance(port, SandboxBridgePort)
        assert port.sandbox is True
        assert port.custody_model == CustodyModel.SIMULATED
        assert not reg.has_real(ProviderCapability.BRIDGE)

    def test_squid_real_when_integrator_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(), environ={"SQUID_INTEGRATOR_ID": "sardis-int"}
        )
        assert reg.has_real(ProviderCapability.BRIDGE)
        port = reg.get(ProviderCapability.BRIDGE)
        assert port.provider == "squid"
        assert port.custody_model == CustodyModel.NON_CUSTODIAL

    def test_cctp_real_when_enabled(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={"CCTP_ENABLED": "true"})
        assert reg.has_real(ProviderCapability.BRIDGE)
        assert reg.get(ProviderCapability.BRIDGE).provider == "cctp"

    def test_squid_keeps_precedence_over_cctp(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"SQUID_INTEGRATOR_ID": "sardis-int", "CCTP_ENABLED": "true"},
        )
        assert reg.get(ProviderCapability.BRIDGE).provider == "squid"

    def test_cctp_disabled_by_default_even_keyless(self):
        # CCTP is keyless but must be opt-in so the dev default stays sandbox.
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        assert not reg.has_real(ProviderCapability.BRIDGE)
        assert isinstance(reg.get(ProviderCapability.BRIDGE), SandboxBridgePort)
