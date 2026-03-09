"""Coinbase Developer Platform (CDP) Swap and Bridge API client.

Provides token swap and cross-chain bridge functionality via the
Coinbase Developer Platform API.

Features:
- Token swap quotes and execution on Base and other chains
- Cross-chain bridge quotes via CCTP and native bridges
- Slippage protection with configurable limits

Reference: https://docs.cdp.coinbase.com/onchain-data/docs/swap
"""
from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)


CDP_API_BASE = "https://api.developer.coinbase.com"

# Chain ID mapping for CDP
CDP_CHAIN_IDS: dict[str, str] = {
    "base": "base",
    "base_sepolia": "base-sepolia",
    "ethereum": "ethereum",
    "polygon": "polygon",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
}


class CDPSwapError(Exception):
    """Error from CDP Swap API."""

    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)


@dataclass
class SwapQuote:
    """A swap quote from CDP."""

    quote_id: str
    from_token: str
    to_token: str
    from_amount: Decimal
    to_amount: Decimal
    exchange_rate: Decimal
    fee_amount: Decimal
    fee_token: str
    expires_at: str
    chain: str
    calldata: str = ""
    to_address: str = ""


@dataclass
class SwapResult:
    """Result of an executed swap."""

    tx_hash: str
    from_amount: Decimal
    to_amount: Decimal
    status: str  # "confirmed", "pending", "failed"


@dataclass
class BridgeQuote:
    """A cross-chain bridge quote from CDP."""

    quote_id: str
    from_chain: str
    to_chain: str
    token: str
    from_amount: Decimal
    to_amount: Decimal
    fee_amount: Decimal
    estimated_time_seconds: int
    calldata: str = ""
    to_address: str = ""


class CDPSwapClient:
    """Coinbase Developer Platform swap/bridge API client."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = CDP_API_BASE,
        timeout_seconds: float = 30.0,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make an authenticated request to CDP API."""
        url = f"{self._base_url}{path}"
        try:
            resp = await self._client.request(
                method, url, json=json, params=params
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            body = {}
            with contextlib.suppress(Exception):
                body = e.response.json()
            raise CDPSwapError(
                f"CDP API error: {e.response.status_code} {body.get('message', '')}",
                status_code=e.response.status_code,
            ) from e
        except httpx.TimeoutException as e:
            raise CDPSwapError("CDP API timeout") from e

    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain: str,
        *,
        slippage_bps: int = 100,  # 1% default slippage
    ) -> SwapQuote:
        """Get a swap quote.

        Args:
            from_token: Source token address or symbol.
            to_token: Destination token address or symbol.
            amount: Amount to swap (in token units).
            chain: Chain name (e.g. "base").
            slippage_bps: Max slippage in basis points.

        Returns:
            SwapQuote with pricing and calldata.
        """
        cdp_chain = CDP_CHAIN_IDS.get(chain)
        if not cdp_chain:
            raise CDPSwapError(f"Chain '{chain}' not supported by CDP Swap")

        data = await self._request(
            "POST",
            "/onchain/v1/swap/quote",
            json={
                "fromAsset": from_token,
                "toAsset": to_token,
                "amount": str(amount),
                "network": cdp_chain,
                "slippageBps": slippage_bps,
            },
        )

        quote = data.get("quote", data)
        return SwapQuote(
            quote_id=quote.get("quoteId", ""),
            from_token=from_token,
            to_token=to_token,
            from_amount=Decimal(str(quote.get("fromAmount", amount))),
            to_amount=Decimal(str(quote.get("toAmount", "0"))),
            exchange_rate=Decimal(str(quote.get("exchangeRate", "0"))),
            fee_amount=Decimal(str(quote.get("fee", {}).get("amount", "0"))),
            fee_token=quote.get("fee", {}).get("token", from_token),
            expires_at=quote.get("expiresAt", ""),
            chain=chain,
            calldata=quote.get("calldata", ""),
            to_address=quote.get("toAddress", ""),
        )

    async def execute_swap(
        self,
        quote_id: str,
        wallet_signer: Any,
    ) -> SwapResult:
        """Execute a swap from a previously obtained quote.

        Args:
            quote_id: Quote ID from get_quote().
            wallet_signer: MPC signer to sign the swap transaction.

        Returns:
            SwapResult with transaction details.
        """
        data = await self._request(
            "POST",
            "/onchain/v1/swap/execute",
            json={"quoteId": quote_id},
        )

        swap = data.get("swap", data)
        tx_hash = swap.get("txHash", "")

        return SwapResult(
            tx_hash=tx_hash,
            from_amount=Decimal(str(swap.get("fromAmount", "0"))),
            to_amount=Decimal(str(swap.get("toAmount", "0"))),
            status=swap.get("status", "pending"),
        )

    async def get_bridge_quote(
        self,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: Decimal,
    ) -> BridgeQuote:
        """Get a cross-chain bridge quote.

        Args:
            from_chain: Source chain name.
            to_chain: Destination chain name.
            token: Token to bridge (address or symbol).
            amount: Amount to bridge.

        Returns:
            BridgeQuote with pricing and estimated time.
        """
        cdp_from = CDP_CHAIN_IDS.get(from_chain)
        cdp_to = CDP_CHAIN_IDS.get(to_chain)
        if not cdp_from or not cdp_to:
            raise CDPSwapError(
                f"Bridge not supported: {from_chain} -> {to_chain}"
            )

        data = await self._request(
            "POST",
            "/onchain/v1/bridge/quote",
            json={
                "fromNetwork": cdp_from,
                "toNetwork": cdp_to,
                "token": token,
                "amount": str(amount),
            },
        )

        quote = data.get("quote", data)
        return BridgeQuote(
            quote_id=quote.get("quoteId", ""),
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            from_amount=Decimal(str(quote.get("fromAmount", amount))),
            to_amount=Decimal(str(quote.get("toAmount", "0"))),
            fee_amount=Decimal(str(quote.get("fee", {}).get("amount", "0"))),
            estimated_time_seconds=int(quote.get("estimatedTimeSeconds", 300)),
            calldata=quote.get("calldata", ""),
            to_address=quote.get("toAddress", ""),
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
