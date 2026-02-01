"""Fireblocks MPC signer integration.

Implements the MPCSignerPort interface using the Fireblocks REST API
for vault account management and transaction signing.

Requires:
- FIREBLOCKS_API_KEY environment variable
- FIREBLOCKS_API_SECRET environment variable (RSA private key path or contents)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class FireblocksSigner:
    """Fireblocks MPC signer using the Fireblocks REST API.

    This signer creates vault accounts and signs transactions via the
    Fireblocks infrastructure, providing institutional-grade MPC custody.
    """

    BASE_URL = "https://api.fireblocks.io/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self._api_key = api_key or os.getenv("FIREBLOCKS_API_KEY", "")
        self._api_secret = api_secret or os.getenv("FIREBLOCKS_API_SECRET", "")
        self._base_url = base_url or self.BASE_URL
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30,
            )
        return self._client

    def _sign_jwt(self, path: str, body: str = "") -> str:
        """Create a signed JWT for Fireblocks API authentication.

        Uses the Fireblocks API key and RSA private key to produce
        a short-lived JWT token for request authentication.
        """
        import jwt  # PyJWT

        now = int(time.time())
        payload = {
            "uri": path,
            "nonce": hashlib.sha256(f"{now}".encode()).hexdigest(),
            "iat": now,
            "exp": now + 30,
            "sub": self._api_key,
            "bodyHash": hashlib.sha256(body.encode()).hexdigest(),
        }
        return jwt.encode(payload, self._api_secret, algorithm="RS256")

    async def _request(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Fireblocks API."""
        client = await self._get_client()
        body_str = json.dumps(body) if body else ""
        token = self._sign_jwt(path, body_str)

        headers = {
            "X-API-Key": self._api_key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await client.request(
            method, path, headers=headers, content=body_str if body else None
        )
        response.raise_for_status()
        return response.json()

    # --- MPCSignerPort interface ---

    async def create_wallet(self, name: str) -> Dict[str, Any]:
        """Create a Fireblocks vault account."""
        result = await self._request(
            "POST",
            "/vault/accounts",
            {"name": name, "autoFuel": True},
        )
        logger.info(f"Created Fireblocks vault account: {result.get('id')}")
        return result

    async def get_address(self, vault_id: str, asset_id: str = "ETH") -> str:
        """Get a deposit address for a vault account asset."""
        result = await self._request(
            "GET",
            f"/vault/accounts/{vault_id}/{asset_id}/addresses",
        )
        addresses = result if isinstance(result, list) else []
        if not addresses:
            # Generate a new address
            result = await self._request(
                "POST",
                f"/vault/accounts/{vault_id}/{asset_id}/addresses",
            )
            return result.get("address", "")
        return addresses[0].get("address", "")

    async def sign_transaction(
        self,
        vault_id: str,
        destination_address: str,
        asset_id: str,
        amount: str,
        note: str = "",
    ) -> Dict[str, Any]:
        """Sign and submit a transaction via Fireblocks."""
        tx_payload = {
            "assetId": asset_id,
            "source": {
                "type": "VAULT_ACCOUNT",
                "id": vault_id,
            },
            "destination": {
                "type": "ONE_TIME_ADDRESS",
                "oneTimeAddress": {"address": destination_address},
            },
            "amount": amount,
            "note": note or "Sardis payment",
        }
        result = await self._request("POST", "/transactions", tx_payload)
        logger.info(f"Fireblocks tx submitted: {result.get('id')}")
        return result

    async def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """Get transaction status from Fireblocks."""
        return await self._request("GET", f"/transactions/{tx_id}")

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
