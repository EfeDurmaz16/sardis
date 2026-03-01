"""Gasless Solana transactions via Kora Network fee payer."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .client import SolanaClient, SolanaConfig
from .transfer import SolanaTransferParams, build_spl_transfer

logger = logging.getLogger(__name__)

KORA_API_BASE = "https://api.kora.network/v1"


@dataclass
class GaslessTransferResult:
    """Result of a gasless transfer."""
    signature: str
    fee_payer: str
    sender: str
    recipient: str
    mint: str
    amount: int
    gasless: bool = True


class KoraGaslessClient:
    """Client for Kora Network gasless transaction service.

    Kora provides fee-payer services for Solana, allowing users
    to transact SPL tokens without holding SOL for gas.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("SARDIS_KORA_API_KEY", "")
        self._client = httpx.AsyncClient(
            base_url=KORA_API_BASE,
            timeout=30.0,
        )

    @property
    def available(self) -> bool:
        """Check if Kora API key is configured."""
        return bool(self.api_key)

    async def request_fee_payer(
        self, transaction_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Request Kora to co-sign as fee payer.

        Args:
            transaction_data: The unsigned transaction details from build_spl_transfer.

        Returns:
            Dict with fee_payer pubkey and partially-signed transaction.
        """
        if not self.available:
            raise KoraUnavailableError("Kora API key not configured")

        resp = await self._client.post(
            "/transactions/sponsor",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "transaction": transaction_data,
                "network": "mainnet-beta",
            },
        )
        if resp.status_code != 200:
            raise KoraUnavailableError(f"Kora API error: {resp.status_code} - {resp.text}")

        return resp.json()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


class KoraUnavailableError(Exception):
    """Raised when Kora fee payer service is unavailable."""


async def build_gasless_transfer(
    client: SolanaClient,
    params: SolanaTransferParams,
    kora_client: KoraGaslessClient | None = None,
) -> dict[str, Any]:
    """Build a gasless SPL token transfer using Kora fee payer.

    If Kora is unavailable, falls back to a standard transfer
    where the sender pays SOL for gas.
    """
    # Build the base transfer
    tx_data = await build_spl_transfer(client, params)

    # Try gasless via Kora
    kora = kora_client or KoraGaslessClient()
    if kora.available:
        try:
            sponsored = await kora.request_fee_payer(tx_data)
            tx_data["fee_payer"] = sponsored.get("fee_payer")
            tx_data["sponsored_tx"] = sponsored.get("transaction")
            tx_data["gasless"] = True
            logger.info("Gasless transfer via Kora: fee_payer=%s", tx_data["fee_payer"])
            return tx_data
        except KoraUnavailableError:
            logger.warning("Kora unavailable, falling back to sender-pays-gas")

    # Fallback: sender pays gas
    tx_data["fee_payer"] = params.sender
    tx_data["gasless"] = False
    logger.info("Standard transfer (sender pays gas): %s", params.sender)
    return tx_data
