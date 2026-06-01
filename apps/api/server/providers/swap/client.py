"""Thin HTTP clients for the same-chain / cross-token swap providers Sardis
aggregates.

Three providers live here, each researched against its CURRENT (2026) API:

LI.FI (pure-REST DEX + bridge aggregation; Solana live)
-------------------------------------------------------
Researched via WebSearch + context7 ``/websites/li_fi``
(``docs.li.fi/api-reference/get-a-quote-for-a-token-transfer``,
``docs.li.fi/li.fi-api/solana``, ``docs.li.fi/monetization-take-fees``):

* **Auth:** ``x-lifi-api-key: <key>`` header (optional for low rate limits;
  required for production rate limits + fee withdrawal).  Never hardcoded.
* **Base URLs:** production ``https://li.quest``; staging
  ``https://staging.li.quest``.
* **Quote:** ``GET /v1/quote`` — returns a ``Step`` whose ``estimate`` carries
  ``toAmount`` / ``toAmountMin`` (min incl. slippage) and whose
  ``transactionRequest`` (``to``, ``data``, ``value``, ``gasLimit``,
  ``gasPrice``, ``chainId``) can be signed/broadcast directly.
* **Query params:** ``fromChain``, ``toChain`` (chain id or key),
  ``fromToken``, ``toToken`` (address or symbol), ``fromAmount`` (smallest
  units, string), ``fromAddress``, optional ``toAddress``, ``slippage``
  (decimal, e.g. ``0.005`` = 0.5%), ``integrator`` (tracking id), ``fee``
  (integrator fee fraction, e.g. ``0.003`` = 0.3% — the REVENUE param;
  deducted from the user's input and collected in LI.FI's FeeCollection
  sub-contract).
* **Solana:** native SOL is the System Program address
  ``11111111111111111111111111111111``.  Routing via Mayan/Allbridge/Jupiter
  + native CCTP.

0x / Uniswap Trading API — Swap API v2 (same-chain EVM best price)
------------------------------------------------------------------
Researched via WebSearch + context7 ``/websites/0x``
(``docs.0x.org/api-reference/openapi-json/swap/allowanceholder-getquote``,
``docs.0x.org/docs/upgrading/upgrading-to-swap-v2``):

* **Auth:** TWO required headers — ``0x-api-key: <key>`` and
  ``0x-version: v2``.
* **Base URL:** ``https://api.0x.org`` (multichain via ``chainId`` param;
  no separate sandbox host — non-prod is a Sardis-side label).
* **Price (indicative):** ``GET /swap/allowance-holder/price``.
* **Quote (firm, with calldata):** ``GET /swap/allowance-holder/quote`` —
  ``taker`` is REQUIRED in v2 so the API can return ``transaction`` calldata
  and ``issues``.
* **Query params:** ``chainId``, ``sellToken``, ``buyToken``, ``sellAmount``
  (base units), ``taker``, optional ``slippageBps``, and the REVENUE params
  ``swapFeeBps`` (basis points), ``swapFeeRecipient``, ``swapFeeToken`` (the
  token the fee is taken in — must be buy or sell token).
* **Response:** ``buyAmount``, ``sellAmount``, ``minBuyAmount``,
  ``fees.integratorFee`` (the captured fee), ``issues.allowance`` (with
  ``spender`` to approve), and ``transaction`` (``to``, ``data``, ``gas``,
  ``gasPrice``, ``value``).
* Native asset sentinel is ``0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE``.

Jupiter (Solana best-price swap)
--------------------------------
Researched via WebSearch + the official docs
(``dev.jup.ag``/``developers.jup.ag/docs/swap/add-fees-to-swap``,
``hub.jup.ag/docs/swap-api``):

* **Auth:** ``x-api-key: <key>`` header.
* **Base URLs:** keyed ``https://api.jup.ag``; free/lite
  ``https://lite-api.jup.ag`` (no key, lower limits — used as the non-prod /
  keyless default so dev runs without a key).
* **Quote:** ``GET /swap/v1/quote`` — params ``inputMint``, ``outputMint``,
  ``amount`` (base units), ``slippageBps``, and the REVENUE param
  ``platformFeeBps`` (basis points).  Returns ``inAmount``, ``outAmount``,
  ``otherAmountThreshold`` (slippage-protected min/max).
* **Build swap tx:** ``POST /swap/v1/swap`` with body ``{quoteResponse,
  userPublicKey, feeAccount}`` — ``feeAccount`` is the SPL token account that
  receives the ``platformFeeBps`` fee (mint must be part of the swap pair).
  Returns a base64 ``swapTransaction`` the wallet signs.

Custody: every swap client is **non-custodial** — the client only returns a
quote and the already-shaped transaction (EVM calldata / Solana serialized tx)
for the orchestrator's CustodyPort to sign + broadcast.  No swap client ever
holds, authorizes, initiates, or settles funds.  No policy / KYA / sanctions /
mandate checks happen here (those live in the moat).  No secret is hardcoded;
credentials arrive via the registry from env.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- LI.FI -----------------------------------------------------------------
_LIFI_PROD_BASE = "https://li.quest"
_LIFI_STAGING_BASE = "https://staging.li.quest"
#: LI.FI native-SOL sentinel (System Program address).
LIFI_SOLANA_NATIVE = "11111111111111111111111111111111"

# -- 0x Swap API v2 --------------------------------------------------------
_ZEROX_BASE = "https://api.0x.org"
_ZEROX_API_VERSION = "v2"
#: 0x native-asset sentinel (checksummed).
ZEROX_NATIVE = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

# -- Jupiter ---------------------------------------------------------------
_JUPITER_KEYED_BASE = "https://api.jup.ag"
_JUPITER_LITE_BASE = "https://lite-api.jup.ag"

_DEFAULT_TIMEOUT = 20.0


def _is_sandbox_env(environment: str) -> bool:
    return environment.strip().lower() in {
        "sandbox",
        "staging",
        "test",
        "development",
        "dev",
    }


# =========================================================================
# LI.FI
# =========================================================================


@dataclass(frozen=True)
class LifiConfig:
    """Resolved LI.FI runtime.  The API key is never logged.

    ``integrator`` is the partner string LI.FI attributes fees to; ``fee`` is
    the default integrator fee fraction (e.g. ``0.003`` = 0.3%) captured on
    every quote unless overridden per-call.
    """

    #: Optional — LI.FI quotes work keyless at low rate limits, but a key is
    #: required for production limits and to withdraw collected integrator fees.
    api_key: str | None = None
    environment: str = "production"
    integrator: str = "sardis"
    #: Default integrator-fee fraction (revenue).  0.003 == 0.3%.
    fee: float | None = None
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


@dataclass
class SwapQuote:
    """Normalized swap quote, money as exact base-unit strings (never float)."""

    quote_id: str
    sell_amount: str
    buy_amount: str
    #: Slippage-protected minimum the taker is guaranteed to receive.
    buy_amount_min: str | None
    #: Pre-shaped transaction the CustodyPort signs.  EVM: ``{to,data,value,
    #: gasLimit,gasPrice,chainId}``.  Solana: ``{swapTransaction}`` (base64).
    transaction: dict[str, Any] = field(default_factory=dict)
    #: Allowance the taker must grant before executing (EVM), if any.
    allowance_spender: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class LifiClient:
    """``GET /v1/quote`` over httpx with integrator-fee capture."""

    def __init__(self, config: LifiConfig) -> None:
        self._config = config
        self._base_url = _LIFI_STAGING_BASE if config.is_sandbox else _LIFI_PROD_BASE
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            if self._config.api_key:
                headers["x-lifi-api-key"] = self._config.api_key
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._config.timeout_seconds,
                headers=headers,
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_quote(
        self,
        *,
        from_chain: str,
        to_chain: str,
        from_token: str,
        to_token: str,
        from_amount: str,
        from_address: str,
        to_address: str | None = None,
        slippage: float | None = None,
        fee: float | None = None,
    ) -> SwapQuote:
        """``GET /v1/quote`` — returns a Step with estimate + transactionRequest.

        ``fee`` (integrator-fee fraction) is the revenue param; it falls back to
        the config default when not supplied per-call.
        """
        params: dict[str, Any] = {
            "fromChain": from_chain,
            "toChain": to_chain,
            "fromToken": from_token,
            "toToken": to_token,
            "fromAmount": from_amount,
            "fromAddress": from_address,
            "integrator": self._config.integrator,
        }
        if to_address:
            params["toAddress"] = to_address
        if slippage is not None:
            params["slippage"] = slippage
        effective_fee = fee if fee is not None else self._config.fee
        if effective_fee is not None:
            params["fee"] = effective_fee

        client = await self._client_()
        resp = await client.get("/v1/quote", params=params)
        resp.raise_for_status()
        data = resp.json()
        estimate = data.get("estimate") or {}
        tx = data.get("transactionRequest") or {}
        return SwapQuote(
            quote_id=str(data.get("id") or data.get("tool") or ""),
            sell_amount=str(estimate.get("fromAmount", from_amount)),
            buy_amount=str(estimate.get("toAmount", "")),
            buy_amount_min=(
                str(estimate.get("toAmountMin"))
                if estimate.get("toAmountMin") is not None
                else None
            ),
            transaction={
                "to": tx.get("to"),
                "data": tx.get("data"),
                "value": tx.get("value"),
                "gasLimit": tx.get("gasLimit"),
                "gasPrice": tx.get("gasPrice"),
                "chainId": tx.get("chainId"),
            },
            allowance_spender=estimate.get("approvalAddress"),
            raw=data,
        )


# =========================================================================
# 0x Swap API v2 (allowance-holder)
# =========================================================================


@dataclass(frozen=True)
class ZeroExConfig:
    """Resolved 0x Swap API v2 runtime.  The API key is never logged."""

    api_key: str
    environment: str = "production"
    #: Default integrator fee in basis points (revenue).  30 == 0.30%.
    swap_fee_bps: int | None = None
    #: Address that receives the integrator fee.
    swap_fee_recipient: str | None = None
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        # 0x has a single multichain host; "sandbox" is a Sardis-side label so a
        # non-prod deployment never reports a result as a settled production
        # movement.  The network path is identical.
        return _is_sandbox_env(self.environment)


class ZeroExClient:
    """``GET /swap/allowance-holder/quote`` (+ ``/price``) over httpx."""

    def __init__(self, config: ZeroExConfig) -> None:
        if not config.api_key:
            raise ValueError("0x API key is required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=_ZEROX_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    # Both headers are REQUIRED in v2.
                    "0x-api-key": self._config.api_key,
                    "0x-version": _ZEROX_API_VERSION,
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _fee_params(
        self,
        *,
        sell_token: str,
        buy_token: str,
        swap_fee_bps: int | None,
        swap_fee_recipient: str | None,
        swap_fee_token: str | None,
    ) -> dict[str, Any]:
        bps = swap_fee_bps if swap_fee_bps is not None else self._config.swap_fee_bps
        recipient = swap_fee_recipient or self._config.swap_fee_recipient
        if bps is None or recipient is None:
            return {}
        # The fee token must be one of the swap pair; default to the buy token.
        token = swap_fee_token or buy_token
        if token not in {sell_token, buy_token}:
            token = buy_token
        return {
            "swapFeeBps": bps,
            "swapFeeRecipient": recipient,
            "swapFeeToken": token,
        }

    async def get_quote(
        self,
        *,
        chain_id: int,
        sell_token: str,
        buy_token: str,
        sell_amount: str,
        taker: str,
        slippage_bps: int | None = None,
        swap_fee_bps: int | None = None,
        swap_fee_recipient: str | None = None,
        swap_fee_token: str | None = None,
    ) -> SwapQuote:
        """``GET /swap/allowance-holder/quote`` — firm quote with calldata.

        ``taker`` is required in v2.  Fee params capture the integrator fee
        (revenue).
        """
        params: dict[str, Any] = {
            "chainId": chain_id,
            "sellToken": sell_token,
            "buyToken": buy_token,
            "sellAmount": sell_amount,
            "taker": taker,
        }
        if slippage_bps is not None:
            params["slippageBps"] = slippage_bps
        params.update(
            self._fee_params(
                sell_token=sell_token,
                buy_token=buy_token,
                swap_fee_bps=swap_fee_bps,
                swap_fee_recipient=swap_fee_recipient,
                swap_fee_token=swap_fee_token,
            )
        )

        client = await self._client_()
        resp = await client.get("/swap/allowance-holder/quote", params=params)
        resp.raise_for_status()
        data = resp.json()
        tx = data.get("transaction") or {}
        issues = data.get("issues") or {}
        allowance = issues.get("allowance") or {}
        return SwapQuote(
            quote_id=str(data.get("blockNumber") or ""),
            sell_amount=str(data.get("sellAmount", sell_amount)),
            buy_amount=str(data.get("buyAmount", "")),
            buy_amount_min=(
                str(data.get("minBuyAmount")) if data.get("minBuyAmount") is not None else None
            ),
            transaction={
                "to": tx.get("to"),
                "data": tx.get("data"),
                "value": tx.get("value"),
                "gas": tx.get("gas"),
                "gasPrice": tx.get("gasPrice"),
                "chainId": chain_id,
            },
            allowance_spender=(allowance.get("spender") if isinstance(allowance, dict) else None),
            raw=data,
        )


# =========================================================================
# Jupiter (Solana)
# =========================================================================


@dataclass(frozen=True)
class JupiterConfig:
    """Resolved Jupiter runtime.  The API key is never logged.

    When ``api_key`` is set the keyed host ``api.jup.ag`` is used; otherwise the
    keyless lite host ``lite-api.jup.ag`` (lower rate limits) so dev runs work
    without a key.
    """

    api_key: str | None = None
    environment: str = "production"
    #: Default platform fee in basis points (revenue).  30 == 0.30%.
    platform_fee_bps: int | None = None
    #: SPL token account that receives the platform fee (mint in swap pair).
    fee_account: str | None = None
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


class JupiterClient:
    """``GET /swap/v1/quote`` + ``POST /swap/v1/swap`` over httpx."""

    def __init__(self, config: JupiterConfig) -> None:
        self._config = config
        # Keyed host requires the key; lite host is keyless.
        self._base_url = _JUPITER_KEYED_BASE if config.api_key else _JUPITER_LITE_BASE
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            if self._config.api_key:
                headers["x-api-key"] = self._config.api_key
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._config.timeout_seconds,
                headers=headers,
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_quote(
        self,
        *,
        input_mint: str,
        output_mint: str,
        amount: str,
        slippage_bps: int | None = None,
        platform_fee_bps: int | None = None,
    ) -> SwapQuote:
        """``GET /swap/v1/quote`` — best-price quote with optional platform fee.

        The raw quote response is stashed in ``raw`` so the adapter can hand it
        back verbatim to ``build_swap`` (Jupiter requires the exact quote echo).
        """
        params: dict[str, Any] = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
        }
        if slippage_bps is not None:
            params["slippageBps"] = slippage_bps
        effective_fee = (
            platform_fee_bps if platform_fee_bps is not None else self._config.platform_fee_bps
        )
        if effective_fee is not None:
            params["platformFeeBps"] = effective_fee

        client = await self._client_()
        resp = await client.get("/swap/v1/quote", params=params)
        resp.raise_for_status()
        data = resp.json()
        return SwapQuote(
            quote_id=f"{input_mint}:{output_mint}:{amount}",
            sell_amount=str(data.get("inAmount", amount)),
            buy_amount=str(data.get("outAmount", "")),
            buy_amount_min=(
                str(data.get("otherAmountThreshold"))
                if data.get("otherAmountThreshold") is not None
                else None
            ),
            # Solana has no EVM calldata; build_swap turns the quote into a
            # serialized transaction.  Keep the slot/context for audit.
            transaction={"contextSlot": data.get("contextSlot")},
            raw=data,
        )

    async def build_swap(
        self,
        *,
        quote_response: dict[str, Any],
        user_public_key: str,
        fee_account: str | None = None,
    ) -> dict[str, Any]:
        """``POST /swap/v1/swap`` — turn the quote into a base64 transaction.

        ``fee_account`` (SPL token account receiving the platform fee) falls
        back to the configured default.
        """
        body: dict[str, Any] = {
            "quoteResponse": quote_response,
            "userPublicKey": user_public_key,
        }
        account = fee_account or self._config.fee_account
        if account:
            body["feeAccount"] = account

        client = await self._client_()
        resp = await client.post("/swap/v1/swap", json=body)
        resp.raise_for_status()
        return resp.json()
