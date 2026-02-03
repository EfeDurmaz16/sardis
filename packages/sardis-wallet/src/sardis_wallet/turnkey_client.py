"""Turnkey MPC HTTP client for non-custodial wallet operations.

Handles P-256 stamp authentication and communicates with the Turnkey v1 API
to create wallets, sign transactions, and manage wallet accounts.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

TURNKEY_BASE_URL = "https://api.turnkey.com"


class TurnkeyClient:
    """Async HTTP client for the Turnkey API with P-256 stamp authentication."""

    def __init__(
        self,
        api_key: str,
        api_private_key: str,
        organization_id: str,
        base_url: str = TURNKEY_BASE_URL,
    ):
        self._api_key = api_key
        self._api_private_key = api_private_key
        self._organization_id = organization_id
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    def _stamp_request(self, body: str) -> Dict[str, str]:
        """Create a P-256 stamp for request authentication.

        The stamp authenticates the request body by signing its SHA-256 hash
        with the API private key using ECDSA P-256.
        """
        try:
            from cryptography.hazmat.primitives.asymmetric import ec, utils
            from cryptography.hazmat.primitives import hashes, serialization
            import base64

            body_hash = hashlib.sha256(body.encode()).digest()

            # Load the private key (PEM or raw hex)
            if self._api_private_key.startswith("-----"):
                private_key = serialization.load_pem_private_key(
                    self._api_private_key.encode(), password=None
                )
            else:
                # Assume hex-encoded raw key
                key_bytes = bytes.fromhex(self._api_private_key)
                private_key = ec.derive_private_key(
                    int.from_bytes(key_bytes, "big"), ec.SECP256R1()
                )

            signature = private_key.sign(body_hash, ec.ECDSA(utils.Prehashed(hashes.SHA256())))

            stamp = base64.urlsafe_b64encode(signature).decode().rstrip("=")

            return {
                "X-Stamp": stamp,
                "X-Stamp-Key": self._api_key,
            }
        except ImportError:
            raise RuntimeError(
                "cryptography package is required for Turnkey P-256 stamps. "
                "Install with: pip install cryptography"
            )

    async def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send an authenticated POST request to the Turnkey API."""
        body_json = json.dumps(body, separators=(",", ":"), sort_keys=True)
        stamp_headers = self._stamp_request(body_json)

        response = await self._client.post(
            path,
            content=body_json,
            headers=stamp_headers,
        )
        response.raise_for_status()
        return response.json()

    async def create_wallet(self, wallet_name: str) -> Dict[str, Any]:
        """Create a new HD wallet.

        Returns:
            Dict with walletId and other wallet metadata.
        """
        body = {
            "type": "ACTIVITY_TYPE_CREATE_WALLET",
            "timestampMs": str(int(time.time() * 1000)),
            "organizationId": self._organization_id,
            "parameters": {
                "walletName": wallet_name,
            },
        }

        result = await self._post("/public/v1/submit/create_wallet", body)
        activity = result.get("activity", {})
        wallet_result = activity.get("result", {}).get("createWalletResult", {})

        logger.info(f"Turnkey wallet created: {wallet_result.get('walletId', 'unknown')}")
        return wallet_result

    async def create_wallet_accounts(
        self,
        wallet_id: str,
        chain_type: str = "CHAIN_TYPE_ETHEREUM",
        count: int = 1,
    ) -> Dict[str, Any]:
        """Create accounts (addresses) for an existing wallet.

        Args:
            wallet_id: The wallet to add accounts to.
            chain_type: Chain type (CHAIN_TYPE_ETHEREUM, CHAIN_TYPE_SOLANA, etc.)
            count: Number of accounts to create.

        Returns:
            Dict with addresses list.
        """
        body = {
            "type": "ACTIVITY_TYPE_CREATE_WALLET_ACCOUNTS",
            "timestampMs": str(int(time.time() * 1000)),
            "organizationId": self._organization_id,
            "parameters": {
                "walletId": wallet_id,
                "accounts": [
                    {
                        "curve": "CURVE_SECP256K1",
                        "pathFormat": "PATH_FORMAT_BIP32",
                        "path": f"m/44'/60'/0'/0/{i}",
                        "addressFormat": "ADDRESS_FORMAT_ETHEREUM",
                    }
                    for i in range(count)
                ],
            },
        }

        result = await self._post("/public/v1/submit/create_wallet_accounts", body)
        activity = result.get("activity", {})
        return activity.get("result", {}).get("createWalletAccountsResult", {})

    async def sign_transaction(
        self,
        wallet_id: str,
        unsigned_transaction: str,
        sign_with: str,
    ) -> Dict[str, Any]:
        """Sign a transaction with a wallet address.

        Args:
            wallet_id: Wallet containing the signing key.
            unsigned_transaction: Hex-encoded unsigned transaction.
            sign_with: Address to sign with.

        Returns:
            Dict with signedTransaction.
        """
        body = {
            "type": "ACTIVITY_TYPE_SIGN_TRANSACTION",
            "timestampMs": str(int(time.time() * 1000)),
            "organizationId": self._organization_id,
            "parameters": {
                "signWith": sign_with,
                "type": "TRANSACTION_TYPE_ETHEREUM",
                "unsignedTransaction": unsigned_transaction,
            },
        }

        result = await self._post("/public/v1/submit/sign_transaction", body)
        activity = result.get("activity", {})
        return activity.get("result", {}).get("signTransactionResult", {})

    async def get_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet details.

        Returns:
            Dict with wallet metadata and accounts.
        """
        body = {
            "organizationId": self._organization_id,
            "walletId": wallet_id,
        }

        return await self._post("/public/v1/query/get_wallet", body)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
