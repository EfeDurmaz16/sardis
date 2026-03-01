"""Solana RPC client wrapper."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# Solana mainnet token mint addresses
SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOLANA_USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
SOLANA_PYUSD_MINT = "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo"

TOKEN_DECIMALS = {
    SOLANA_USDC_MINT: 6,
    SOLANA_USDT_MINT: 6,
    SOLANA_PYUSD_MINT: 6,
}


@dataclass
class SolanaConfig:
    """Solana connection configuration."""
    rpc_url: str
    commitment: str = "confirmed"
    timeout: float = 30.0


def get_solana_config() -> SolanaConfig:
    """Build Solana config from environment variables."""
    return SolanaConfig(
        rpc_url=os.getenv("SARDIS_SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
    )


class SolanaClient:
    """Async Solana JSON-RPC client.

    Uses raw httpx instead of solana-py to minimize dependencies.
    All Solana RPC methods are called via JSON-RPC 2.0.
    """

    def __init__(self, config: SolanaConfig | None = None) -> None:
        self.config = config or get_solana_config()
        self._client = httpx.AsyncClient(timeout=self.config.timeout)
        self._request_id = 0

    async def _rpc(self, method: str, params: list[Any] | None = None) -> Any:
        """Make a JSON-RPC call to Solana."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }
        resp = await self._client.post(self.config.rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise SolanaRPCError(data["error"].get("message", "Unknown RPC error"), data["error"])
        return data.get("result")

    async def get_balance(self, pubkey: str) -> int:
        """Get SOL balance in lamports."""
        result = await self._rpc("getBalance", [pubkey, {"commitment": self.config.commitment}])
        return result["value"]

    async def get_token_balance(self, token_account: str) -> int:
        """Get SPL token balance for a token account."""
        result = await self._rpc("getTokenAccountBalance", [token_account])
        return int(result["value"]["amount"])

    async def get_token_accounts_by_owner(
        self, owner: str, mint: str
    ) -> list[dict[str, Any]]:
        """Get all token accounts for an owner and mint."""
        result = await self._rpc(
            "getTokenAccountsByOwner",
            [
                owner,
                {"mint": mint},
                {"encoding": "jsonParsed", "commitment": self.config.commitment},
            ],
        )
        return result.get("value", [])

    async def get_latest_blockhash(self) -> str:
        """Get latest blockhash for transaction building."""
        result = await self._rpc(
            "getLatestBlockhash", [{"commitment": self.config.commitment}]
        )
        return result["value"]["blockhash"]

    async def send_raw_transaction(self, signed_tx_base64: str) -> str:
        """Send a signed transaction. Returns transaction signature."""
        result = await self._rpc(
            "sendTransaction",
            [
                signed_tx_base64,
                {"encoding": "base64", "skipPreflight": False},
            ],
        )
        logger.info("Solana tx sent: %s", result)
        return result

    async def confirm_transaction(
        self, signature: str, commitment: str | None = None
    ) -> bool:
        """Confirm a transaction has reached the desired commitment level."""
        result = await self._rpc(
            "getSignatureStatuses", [[signature]]
        )
        statuses = result.get("value", [])
        if not statuses or statuses[0] is None:
            return False
        status = statuses[0]
        if status.get("err"):
            raise SolanaTransactionError(f"Transaction failed: {status['err']}", signature)
        target = commitment or self.config.commitment
        # confirmed and finalized both satisfy "confirmed"
        confirmation = status.get("confirmationStatus", "")
        if target == "finalized":
            return confirmation == "finalized"
        return confirmation in ("confirmed", "finalized")

    async def get_minimum_balance_for_rent_exemption(self, data_size: int) -> int:
        """Get minimum balance for rent exemption."""
        return await self._rpc("getMinimumBalanceForRentExemption", [data_size])

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


class SolanaRPCError(Exception):
    """Solana RPC error."""
    def __init__(self, message: str, error_data: dict[str, Any] | None = None):
        super().__init__(message)
        self.error_data = error_data or {}


class SolanaTransactionError(Exception):
    """Solana transaction execution error."""
    def __init__(self, message: str, signature: str | None = None):
        super().__init__(message)
        self.signature = signature
