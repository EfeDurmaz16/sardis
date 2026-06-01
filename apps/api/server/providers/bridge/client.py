"""Thin clients for the cross-chain bridge providers Sardis routes through.

Two providers live here, each researched against its CURRENT (2026) API.

Squid (intent-based aggregation; live on Tempo day-one, pathUSD)
---------------------------------------------------------------
Researched via WebSearch + Squid dev docs
(``docs.squidrouter.com/api-and-sdk-integration/api``,
``docs.squidrouter.com/api-and-sdk-integration/key-concepts/track-status``,
``squidrouter.com/blog/squid-live-on-tempo-blockchain-payments``):

* **Base URL:** ``https://v2.api.squidrouter.com`` (single multichain host; no
  separate sandbox host — a non-prod deployment is a Sardis-side label so a
  result is never mistaken for a settled production movement).
* **Auth:** ``x-integrator-id: <id>`` header on EVERY GET and POST.  Never
  hardcoded; arrives from env via the registry.
* **Route (quote + tx):** ``POST /v2/route`` — body ``fromChain``, ``toChain``
  (chain ids as strings), ``fromToken``, ``toToken`` (token addresses),
  ``fromAmount`` (smallest units, string), ``fromAddress``, ``toAddress``,
  ``slippage`` (percent number, e.g. ``1``).  Response ``route.estimate``
  (``toAmount`` / ``toAmountMin``), ``route.quoteId`` (REQUIRED for status
  tracking / Squid Intents), and ``route.transactionRequest``
  (``target``/``to``, ``data``, ``value``, ``gasLimit``) — the already-shaped
  tx the CustodyPort signs.  ``requestId`` is returned in a response header.
* **Status:** ``GET /v2/status`` — query ``transactionId`` (source tx hash),
  ``requestId``, ``fromChainId``, ``toChainId``, ``quoteId`` (mandatory for
  Intents).  After executing an Intents tx you MUST call status with quoteId.
* **Tempo / pathUSD:** Squid is live on Tempo (chain id 4217) from day-one;
  ``toToken`` = pathUSD bridges any-chain -> Tempo.  Routing via Axelar / CCTP /
  LayerZero under the hood.

CCTP v2 (Circle native USDC burn/mint — canonical, non-custodial)
----------------------------------------------------------------
Researched via WebSearch + Circle docs + context7
``/circlefin/circle-cctp-crosschain-transfer``
(``developers.circle.com/cctp/technical-guide``,
``developers.circle.com/cctp/evm-smart-contracts``):

* **Contracts (same across EVM mainnet V2):** TokenMessengerV2
  ``0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d``; MessageTransmitterV2
  ``0x81D40F21F12A8F0E3252Bccb954D722d4c464B64``.
* **Burn:** ``TokenMessengerV2.depositForBurn(uint256 amount, uint32
  destinationDomain, bytes32 mintRecipient, address burnToken, bytes32
  destinationCaller, uint256 maxFee, uint32 minFinalityThreshold)``.  The port
  ABI-encodes the calldata; the CustodyPort signs + broadcasts it.  No client
  here ever holds, authorizes, or settles funds — burn/mint is canonical and
  fully non-custodial (the user burns from their own wallet, Circle mints to
  the recipient).
* **Finality:** ``minFinalityThreshold`` 1000 = Fast (confirmed-level
  attestation, on-chain fee); 2000 = Standard (finalized, fee 0).
* **Fee:** ``GET /v2/burn/USDC/fees/{srcDomain}/{dstDomain}`` -> ``[{
  "minimumFee": "<bps-hundredths>" }]`` (e.g. ``"0.05"`` == 5 bps).  ``maxFee``
  = amount * bps / 1e6, +20% buffer (mirrors Circle's reference).
* **Attestation:** ``GET /v2/messages/{srcDomain}?transactionHash=<burnTx>`` ->
  ``{messages:[{message, attestation, status}]}``; ``status == "complete"``
  yields the ``message`` + ``attestation`` the recipient submits to
  ``MessageTransmitterV2.receiveMessage`` on the destination chain.
* **Iris hosts:** mainnet ``https://iris-api.circle.com``; sandbox
  ``https://iris-api-sandbox.circle.com``.
* **Domain ids:** Ethereum 0, Avalanche 1, Optimism 2, Arbitrum 3, Solana 5,
  Base 6, Polygon PoS 7, Unichain 10, Linea 11.

No secret hardcoded.  Money is exact integer base-unit strings (no float).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- Squid -----------------------------------------------------------------
_SQUID_BASE = "https://v2.api.squidrouter.com"

# -- CCTP v2 ---------------------------------------------------------------
_IRIS_PROD_BASE = "https://iris-api.circle.com"
_IRIS_SANDBOX_BASE = "https://iris-api-sandbox.circle.com"

#: TokenMessengerV2 / MessageTransmitterV2 are the SAME address on every EVM
#: mainnet V2 deployment.
CCTP_TOKEN_MESSENGER_V2 = "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d"
CCTP_MESSAGE_TRANSMITTER_V2 = "0x81D40F21F12A8F0E3252Bccb954D722d4c464B64"

#: 7-arg CCTP v2 ``depositForBurn`` signature.  The selector is derived from
#: this string (single source of truth) via keccak, falling back to the
#: verified literal if ``eth_utils`` is unavailable at import.
_DEPOSIT_FOR_BURN_SIG = "depositForBurn(uint256,uint32,bytes32,address,bytes32,uint256,uint32)"
#: keccak256(_DEPOSIT_FOR_BURN_SIG)[:4] == 0x8e0250ee (verified against eth_utils).
_DEPOSIT_FOR_BURN_SELECTOR_FALLBACK = "0x8e0250ee"


def _function_selector(signature: str) -> str:
    try:
        from eth_utils import keccak  # type: ignore[import-untyped]

        return "0x" + keccak(text=signature).hex()[:8]
    except Exception:  # noqa: BLE001 - keep encoding usable without eth_utils
        return _DEPOSIT_FOR_BURN_SELECTOR_FALLBACK


_DEPOSIT_FOR_BURN_SELECTOR = _function_selector(_DEPOSIT_FOR_BURN_SIG)

#: CCTP v2 domain ids (Circle docs).  Chain *name* -> domain id.
CCTP_DOMAINS: dict[str, int] = {
    "ethereum": 0,
    "mainnet": 0,
    "avalanche": 1,
    "optimism": 2,
    "arbitrum": 3,
    "solana": 5,
    "base": 6,
    "polygon": 7,
    "unichain": 10,
    "linea": 11,
}

#: Min finality thresholds: Fast (confirmed) vs Standard (finalized).
CCTP_FINALITY_FAST = 1000
CCTP_FINALITY_STANDARD = 2000

#: Fast-fee safety buffer (Circle reference uses +20%).
_FAST_FEE_BUFFER_NUM = 120
_FAST_FEE_BUFFER_DEN = 100

_DEFAULT_TIMEOUT = 20.0


def _is_sandbox_env(environment: str) -> bool:
    return environment.strip().lower() in {
        "sandbox",
        "staging",
        "test",
        "development",
        "dev",
    }


@dataclass
class BridgeQuote:
    """Normalized bridge quote.  Money as exact base-unit strings (never float).

    ``transaction`` is the already-shaped instruction the CustodyPort signs:
    Squid -> ``{to,data,value,gasLimit,chainId}``; CCTP -> the encoded
    ``depositForBurn`` call ``{to,data,value,chainId}``.
    """

    quote_id: str
    send_amount: str
    receive_amount: str
    #: Slippage / fee-protected minimum the recipient is guaranteed to receive.
    receive_amount_min: str | None = None
    transaction: dict[str, Any] = field(default_factory=dict)
    #: Token the sender must approve before the bridge can pull it (EVM), if any.
    allowance_spender: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


# =========================================================================
# Squid
# =========================================================================


@dataclass(frozen=True)
class SquidConfig:
    """Resolved Squid runtime.  The integrator id is never logged.

    ``integrator_id`` is required by Squid on every request and is also the
    attribution / fee-tracking key.
    """

    integrator_id: str
    environment: str = "production"
    #: Default slippage percent applied to a route unless overridden per-call.
    slippage_percent: float = 1.0
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        # Squid has a single multichain host; "sandbox" is a Sardis-side label.
        return _is_sandbox_env(self.environment)


class SquidClient:
    """``POST /v2/route`` + ``GET /v2/status`` over httpx."""

    def __init__(self, config: SquidConfig) -> None:
        if not config.integrator_id:
            raise ValueError("Squid integrator id is required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=_SQUID_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    # Required on every Squid request.
                    "x-integrator-id": self._config.integrator_id,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_route(
        self,
        *,
        from_chain: str,
        to_chain: str,
        from_token: str,
        to_token: str,
        from_amount: str,
        from_address: str,
        to_address: str,
        slippage: float | None = None,
    ) -> BridgeQuote:
        """``POST /v2/route`` — cross-chain route with quoteId + transactionRequest."""
        body: dict[str, Any] = {
            "fromChain": from_chain,
            "toChain": to_chain,
            "fromToken": from_token,
            "toToken": to_token,
            "fromAmount": from_amount,
            "fromAddress": from_address,
            "toAddress": to_address,
            "slippage": slippage if slippage is not None else self._config.slippage_percent,
        }
        client = await self._client_()
        resp = await client.post("/v2/route", json=body)
        resp.raise_for_status()
        data = resp.json()
        route = data.get("route") or {}
        estimate = route.get("estimate") or {}
        tx = route.get("transactionRequest") or {}
        return BridgeQuote(
            quote_id=str(route.get("quoteId") or ""),
            send_amount=str(estimate.get("fromAmount", from_amount)),
            receive_amount=str(estimate.get("toAmount", "")),
            receive_amount_min=(
                str(estimate.get("toAmountMin"))
                if estimate.get("toAmountMin") is not None
                else None
            ),
            transaction={
                # Squid uses "target" in v2; keep "to" alias for the CustodyPort.
                "to": tx.get("target") or tx.get("to"),
                "data": tx.get("data"),
                "value": tx.get("value"),
                "gasLimit": tx.get("gasLimit"),
                "chainId": tx.get("chainId") or from_chain,
            },
            allowance_spender=tx.get("target") or tx.get("to"),
            raw=data,
        )

    async def get_status(
        self,
        *,
        transaction_id: str,
        request_id: str | None = None,
        from_chain_id: str | None = None,
        to_chain_id: str | None = None,
        quote_id: str | None = None,
    ) -> dict[str, Any]:
        """``GET /v2/status`` — track an executed route by source tx hash."""
        params: dict[str, Any] = {"transactionId": transaction_id}
        if request_id:
            params["requestId"] = request_id
        if from_chain_id:
            params["fromChainId"] = from_chain_id
        if to_chain_id:
            params["toChainId"] = to_chain_id
        if quote_id:
            params["quoteId"] = quote_id
        client = await self._client_()
        resp = await client.get("/v2/status", params=params)
        resp.raise_for_status()
        return resp.json()


# =========================================================================
# CCTP v2 (Circle native USDC)
# =========================================================================


def _evm_address_to_bytes32(address: str) -> str:
    """Left-pad a 20-byte EVM address to a 32-byte hex word (no 0x doubling)."""
    clean = address.lower().removeprefix("0x")
    return "0x" + clean.rjust(64, "0")


def _uint_to_word(value: int) -> str:
    """Encode an unsigned int as a 32-byte ABI word (hex, no 0x)."""
    if value < 0:
        raise ValueError("negative values cannot be ABI-encoded as uint")
    return f"{value:064x}"


@dataclass(frozen=True)
class CctpConfig:
    """Resolved CCTP v2 runtime.

    CCTP is canonical / permissionless; no API key is needed — only the Iris
    host (mainnet vs sandbox) and whether Fast transfer is the default.
    """

    environment: str = "production"
    #: When True, default new transfers to Fast (confirmed) finality.
    fast: bool = True
    #: Optional per-call USDC token address override per chain (else caller
    #: passes ``burn_token`` explicitly — the orchestrator already knows it).
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


class CctpClient:
    """Builds ``depositForBurn`` calldata + polls the Iris attestation API.

    The client never signs or broadcasts: it encodes the already-authorized
    burn instruction (returned for the CustodyPort) and reads attestation
    status from Iris.  Burn/mint is fully non-custodial.
    """

    def __init__(self, config: CctpConfig) -> None:
        self._config = config
        self._base_url = _IRIS_SANDBOX_BASE if config.is_sandbox else _IRIS_PROD_BASE
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    @property
    def fast(self) -> bool:
        return self._config.fast

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._config.timeout_seconds,
                headers={"Accept": "application/json"},
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    @staticmethod
    def domain_for(chain: str) -> int:
        """Resolve a chain name (or numeric domain) to a CCTP domain id."""
        s = chain.strip().lower()
        if s.isdigit():
            return int(s)
        domain = CCTP_DOMAINS.get(s)
        if domain is None:
            raise ValueError(f"unknown CCTP chain {chain!r}; pass a numeric domain id")
        return domain

    async def get_min_fee_bps_hundredths(
        self, *, source_domain: int, destination_domain: int
    ) -> Decimal:
        """``GET /v2/burn/USDC/fees/{src}/{dst}`` -> minimumFee (bps-hundredths).

        Returns the fee as a :class:`~decimal.Decimal` of basis-point-hundredths
        (Circle returns e.g. ``"0.05"`` meaning 5 bps).  Never float.
        """
        client = await self._client_()
        resp = await client.get(f"/v2/burn/USDC/fees/{source_domain}/{destination_domain}")
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, list) and payload:
            entry = payload[0]
        elif isinstance(payload, dict):
            entry = payload
        else:
            entry = {}
        minimum = entry.get("minimumFee", "0")
        return Decimal(str(minimum))

    def compute_max_fee(self, *, amount_minor: int, bps_hundredths: Decimal) -> int:
        """maxFee = amount * (bps-hundredths/100) bps /1e4, +20% buffer.

        Mirrors Circle's reference exactly with :class:`~decimal.Decimal`
        arithmetic (never float).  ``bps_hundredths`` is what the fee endpoint
        returns (e.g. ``Decimal("0.05")`` == 5 bps).
        """
        # bps-hundredths -> integer of hundredths (e.g. "0.05" -> 5).
        scaled = (bps_hundredths * Decimal(100)).to_integral_value()
        # protocolFee = amount * scaled / 1_000_000  (bps * 1e4 denom).
        protocol_fee = (Decimal(amount_minor) * scaled) / Decimal(1_000_000)
        buffered = (protocol_fee * Decimal(_FAST_FEE_BUFFER_NUM)) / Decimal(_FAST_FEE_BUFFER_DEN)
        # Round up to the next whole base unit so the on-chain maxFee is never
        # short of the protocol fee.
        from decimal import ROUND_CEILING

        return int(buffered.to_integral_value(rounding=ROUND_CEILING))

    def build_deposit_for_burn_calldata(
        self,
        *,
        amount_minor: int,
        destination_domain: int,
        mint_recipient: str,
        burn_token: str,
        max_fee: int,
        min_finality_threshold: int,
        destination_caller: str | None = None,
    ) -> str:
        """ABI-encode ``depositForBurn(...)`` for the source-chain TokenMessengerV2.

        Returns ``0x``-prefixed calldata.  Pure encoding — no signing, no
        broadcast; the CustodyPort signs this and submits it to
        :data:`CCTP_TOKEN_MESSENGER_V2`.  All 7 V2 args are static 32-byte
        words, so no dynamic offset handling is needed.
        """
        if amount_minor <= 0:
            raise ValueError("amount_minor must be positive")
        if max_fee < 0:
            raise ValueError("max_fee must be non-negative")
        recipient_word = _evm_address_to_bytes32(mint_recipient).removeprefix("0x")
        caller_word = (
            _evm_address_to_bytes32(destination_caller).removeprefix("0x")
            if destination_caller
            else "0" * 64  # zero == any caller may mint (standard pattern)
        )
        token_word = _evm_address_to_bytes32(burn_token).removeprefix("0x")
        words = (
            _uint_to_word(amount_minor)
            + _uint_to_word(destination_domain)
            + recipient_word
            + token_word
            + caller_word
            + _uint_to_word(max_fee)
            + _uint_to_word(min_finality_threshold)
        )
        return _DEPOSIT_FOR_BURN_SELECTOR + words

    async def get_attestation(self, *, source_domain: int, transaction_hash: str) -> dict[str, Any]:
        """``GET /v2/messages/{srcDomain}?transactionHash=`` -> first message.

        Returns ``{message, attestation, status}``; ``status == "complete"``
        means the recipient can submit ``message`` + ``attestation`` to
        ``MessageTransmitterV2.receiveMessage`` on the destination chain.  A 404
        means the burn is not yet indexed (caller polls).
        """
        client = await self._client_()
        resp = await client.get(
            f"/v2/messages/{source_domain}",
            params={"transactionHash": transaction_hash},
        )
        if resp.status_code == 404:
            return {"status": "pending_confirmations"}
        resp.raise_for_status()
        data = resp.json()
        messages = data.get("messages") or []
        return messages[0] if messages else {"status": "pending_confirmations"}
