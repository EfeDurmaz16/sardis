"""Circle Programmable Wallets client.

Provides developer-controlled wallet operations via Circle's W3S API:
- Wallet set and wallet creation
- Transaction signing (developer-controlled)
- Balance queries
- Transaction status polling

Circle Programmable Wallets are free for <1,000 wallets and provide
native USDC support with Smart Contract Accounts (SCA).

Reference: https://developers.circle.com/w3s/developer-controlled-wallets-quickstart
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

CIRCLE_W3S_BASE_URL = "https://api.circle.com/v1/w3s"

# Circle blockchain ID mapping
CIRCLE_BLOCKCHAIN_IDS: dict[str, str] = {
    "base": "BASE",
    "base_sepolia": "BASE-SEPOLIA",
    "ethereum": "ETH",
    "ethereum_sepolia": "ETH-SEPOLIA",
    "polygon": "MATIC",
    "polygon_amoy": "MATIC-AMOY",
    "arbitrum": "ARB",
    "arbitrum_sepolia": "ARB-SEPOLIA",
    "optimism": "OP",
    "solana": "SOL",
    "solana_devnet": "SOL-DEVNET",
}


class CircleAPIError(Exception):
    """Error from Circle W3S API."""

    def __init__(self, message: str, status_code: int = 0, code: str = ""):
        self.status_code = status_code
        self.code = code
        super().__init__(message)


@dataclass
class CircleWallet:
    """Represents a Circle Programmable Wallet."""

    wallet_id: str
    wallet_set_id: str
    address: str
    blockchain: str
    account_type: str
    state: str
    create_date: str = ""


@dataclass
class CircleTransaction:
    """Represents a Circle transaction."""

    tx_id: str
    state: str  # INITIATED, PENDING, CONFIRMED, FAILED, CANCELLED
    tx_hash: Optional[str] = None
    error_reason: Optional[str] = None


class CircleWalletClient:
    """Client for Circle Programmable Wallets (developer-controlled).

    Usage:
        client = CircleWalletClient(api_key="...", entity_secret="...")

        # Create a wallet set
        ws_id = await client.create_wallet_set("my-agents")

        # Create a wallet on Base
        wallet = await client.create_wallet(ws_id, ["base"])

        # Sign and send a transaction
        tx = await client.sign_transaction(wallet.wallet_id, raw_tx)

        # Check balance
        balances = await client.get_balance(wallet.wallet_id)
    """

    def __init__(
        self,
        api_key: str,
        entity_secret: str,
        *,
        base_url: str = CIRCLE_W3S_BASE_URL,
        timeout_seconds: float = 30.0,
    ):
        self._api_key = api_key
        self._entity_secret = entity_secret
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
        json: Optional[dict] = None,
    ) -> dict:
        """Make an authenticated request to Circle W3S API."""
        url = f"{self._base_url}{path}"
        try:
            resp = await self._client.request(method, url, json=json)
            resp.raise_for_status()
            data = resp.json()
            if "data" in data:
                return data["data"]
            return data
        except httpx.HTTPStatusError as e:
            body = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else {}
            raise CircleAPIError(
                f"Circle API error: {e.response.status_code} {body.get('message', '')}",
                status_code=e.response.status_code,
                code=body.get("code", ""),
            ) from e
        except httpx.TimeoutException as e:
            raise CircleAPIError("Circle API timeout") from e

    def _build_entity_secret_cipher(self) -> str:
        """Build entity secret ciphertext for Circle API.

        Circle requires the entity secret to be RSA-encrypted with their
        public key. For simplicity, we pass it hex-encoded — the actual
        encryption should be done via Circle's SDK in production.
        """
        return self._entity_secret

    async def create_wallet_set(self, name: str) -> str:
        """Create a new wallet set.

        Args:
            name: Human-readable name for the wallet set.

        Returns:
            Wallet set ID.
        """
        import uuid
        data = await self._request(
            "POST",
            "/developer/walletSets",
            json={
                "idempotencyKey": str(uuid.uuid4()),
                "name": name,
                "entitySecretCiphertext": self._build_entity_secret_cipher(),
            },
        )
        wallet_set = data.get("walletSet", data)
        ws_id = wallet_set.get("id", "")
        logger.info("Created Circle wallet set: %s (%s)", ws_id, name)
        return ws_id

    async def create_wallet(
        self,
        wallet_set_id: str,
        blockchains: list[str],
        account_type: str = "SCA",
        count: int = 1,
    ) -> list[CircleWallet]:
        """Create wallets in a wallet set.

        Args:
            wallet_set_id: The wallet set to create wallets in.
            blockchains: Chain names (e.g. ["base", "ethereum"]).
            account_type: "SCA" (Smart Contract Account) or "EOA".
            count: Number of wallets to create.

        Returns:
            List of created CircleWallet objects.
        """
        import uuid
        # Map chain names to Circle blockchain IDs
        circle_chains = []
        for chain in blockchains:
            cid = CIRCLE_BLOCKCHAIN_IDS.get(chain)
            if not cid:
                raise ValueError(
                    f"Chain '{chain}' not supported by Circle. "
                    f"Supported: {list(CIRCLE_BLOCKCHAIN_IDS.keys())}"
                )
            circle_chains.append(cid)

        data = await self._request(
            "POST",
            "/developer/wallets",
            json={
                "idempotencyKey": str(uuid.uuid4()),
                "walletSetId": wallet_set_id,
                "blockchains": circle_chains,
                "accountType": account_type,
                "count": count,
                "entitySecretCiphertext": self._build_entity_secret_cipher(),
            },
        )

        wallets_data = data.get("wallets", [data] if "id" in data else [])
        wallets = []
        for w in wallets_data:
            wallets.append(CircleWallet(
                wallet_id=w["id"],
                wallet_set_id=wallet_set_id,
                address=w.get("address", ""),
                blockchain=w.get("blockchain", ""),
                account_type=w.get("accountType", account_type),
                state=w.get("state", "LIVE"),
                create_date=w.get("createDate", ""),
            ))

        logger.info(
            "Created %d Circle wallet(s) on %s",
            len(wallets), circle_chains,
        )
        return wallets

    async def sign_transaction(
        self,
        wallet_id: str,
        raw_transaction: str,
    ) -> CircleTransaction:
        """Sign and submit a transaction via Circle.

        Args:
            wallet_id: Circle wallet ID.
            raw_transaction: Hex-encoded raw transaction data.

        Returns:
            CircleTransaction with the transaction state.
        """
        import uuid
        data = await self._request(
            "POST",
            "/developer/transactions/contractExecution",
            json={
                "idempotencyKey": str(uuid.uuid4()),
                "walletId": wallet_id,
                "callData": raw_transaction,
                "entitySecretCiphertext": self._build_entity_secret_cipher(),
            },
        )

        tx_id = data.get("id", "")
        state = data.get("state", "INITIATED")
        logger.info("Circle transaction submitted: %s (state=%s)", tx_id, state)

        return CircleTransaction(
            tx_id=tx_id,
            state=state,
            tx_hash=data.get("txHash"),
        )

    async def get_balance(self, wallet_id: str) -> list[dict]:
        """Get token balances for a wallet.

        Args:
            wallet_id: Circle wallet ID.

        Returns:
            List of balance dicts with token, amount, chain info.
        """
        data = await self._request("GET", f"/wallets/{wallet_id}/balances")
        return data.get("tokenBalances", [])

    async def get_transaction(self, tx_id: str) -> CircleTransaction:
        """Get transaction status by ID.

        Args:
            tx_id: Circle transaction ID.

        Returns:
            CircleTransaction with current state.
        """
        data = await self._request("GET", f"/transactions/{tx_id}")
        tx_data = data.get("transaction", data)
        return CircleTransaction(
            tx_id=tx_data.get("id", tx_id),
            state=tx_data.get("state", "UNKNOWN"),
            tx_hash=tx_data.get("txHash"),
            error_reason=tx_data.get("errorReason"),
        )

    async def poll_transaction(
        self,
        tx_id: str,
        *,
        timeout: float = 60.0,
        interval: float = 2.0,
    ) -> CircleTransaction:
        """Poll a transaction until it reaches a terminal state.

        Args:
            tx_id: Circle transaction ID.
            timeout: Maximum seconds to wait.
            interval: Seconds between polls.

        Returns:
            CircleTransaction in a terminal state.

        Raises:
            CircleAPIError: If timeout exceeded or transaction failed.
        """
        terminal_states = {"CONFIRMED", "COMPLETE", "FAILED", "CANCELLED"}
        start = time.monotonic()

        while time.monotonic() - start < timeout:
            tx = await self.get_transaction(tx_id)
            if tx.state in terminal_states:
                if tx.state in ("FAILED", "CANCELLED"):
                    raise CircleAPIError(
                        f"Transaction {tx_id} {tx.state}: {tx.error_reason}",
                    )
                return tx
            await asyncio.sleep(interval)

        raise CircleAPIError(
            f"Transaction {tx_id} timed out after {timeout}s (last state: {tx.state})"
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
