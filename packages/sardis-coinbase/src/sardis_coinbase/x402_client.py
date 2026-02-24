"""x402 HTTP payment client."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from .cdp_client import CoinbaseCDPProvider


class PaymentPolicyDenied(Exception):
    """Raised when Sardis policy blocks an x402 payment."""


class X402Client:
    """HTTP 402 client that auto-pays with CDP USDC and retries."""

    def __init__(self, cdp_provider: CoinbaseCDPProvider, cdp_wallet_id: str, policy_checker: Any):
        self.cdp = cdp_provider
        self.wallet_id = cdp_wallet_id
        self.policy_checker = policy_checker
        self._http = httpx.AsyncClient()

    async def close(self) -> None:
        await self._http.aclose()

    async def get(self, url: str, **kwargs) -> httpx.Response:
        response = await self._http.get(url, **kwargs)
        if response.status_code == 402:
            return await self._handle_payment_required(url, "GET", response, **kwargs)
        return response

    async def _handle_payment_required(
        self,
        url: str,
        method: str,
        payment_response: httpx.Response,
        **kwargs,
    ) -> httpx.Response:
        payment_info = payment_response.json()
        amount = Decimal(str(payment_info["amount"]))
        recipient = payment_info["recipient"]
        network = payment_info.get("network", "base-mainnet")

        allowed, reason = await self.policy_checker(
            amount=amount,
            merchant=url,
            payment_type="x402",
        )
        if not allowed:
            raise PaymentPolicyDenied(f"x402 payment blocked: {reason}")

        tx_hash = await self.cdp.send_usdc(
            cdp_wallet_id=self.wallet_id,
            to_address=recipient,
            amount_usdc=amount,
        )

        headers = kwargs.get("headers", {})
        headers["X-Payment"] = f"txHash={tx_hash},network={network}"
        kwargs["headers"] = headers
        return await self._http.request(method, url, **kwargs)
