"""Turnkey MPC HTTP client for non-custodial wallet operations.

Handles P-256 stamp authentication and communicates with the Turnkey v1 API
to create wallets, sign transactions, and manage wallet accounts.

The stamp format follows the official Turnkey Python SDK:
  base64url(json({"publicKey": ..., "scheme": "SIGNATURE_SCHEME_TK_API_P256", "signature": ...}))
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

TURNKEY_BASE_URL = "https://api.turnkey.com"


class TurnkeyClient:
    """Async HTTP client for the Turnkey API with P-256 stamp authentication.

    This is the single authoritative Turnkey client for all packages.
    Use `post()` for raw API calls or the higher-level helpers for common operations.
    """

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
        self._signing_key = None
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

        # Eagerly init signing key so errors surface early
        self._init_signing_key()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _init_signing_key(self):
        """Initialize the P-256 ECDSA signing key from API credentials."""
        if not self._api_private_key:
            return
        try:
            from cryptography.hazmat.primitives.asymmetric import ec

            private_key_int = int(self._api_private_key, 16)
            self._signing_key = ec.derive_private_key(private_key_int, ec.SECP256R1())
        except ImportError:
            raise RuntimeError(
                "cryptography package is required for Turnkey P-256 stamps. "
                "Install with: pip install cryptography"
            )

    def _create_stamp(self, body: str) -> str:
        """Create an official Turnkey API stamp (base64url JSON envelope).

        Matches the format from https://github.com/tkhq/python-sdk
        """
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        if not self._signing_key:
            raise ValueError("Turnkey signing key not initialized")

        signature = self._signing_key.sign(body.encode(), ec.ECDSA(hashes.SHA256()))

        stamp_payload = {
            "publicKey": self._api_key,
            "scheme": "SIGNATURE_SCHEME_TK_API_P256",
            "signature": signature.hex(),
        }

        stamp_json = json.dumps(stamp_payload)
        return base64.urlsafe_b64encode(stamp_json.encode()).decode().rstrip("=")

    def _stamp_headers(self, body_json: str) -> Dict[str, str]:
        """Return HTTP headers with the X-Stamp for a serialised request body."""
        return {"X-Stamp": self._create_stamp(body_json)}

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    async def post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send an authenticated POST request to the Turnkey API.

        This is the public entry point used both internally and by
        external callers (e.g. ``TurnkeyMPCSigner`` in sardis-chain).
        """
        body_json = json.dumps(body, separators=(",", ":"), sort_keys=True)
        headers = self._stamp_headers(body_json)

        response = await self._client.post(path, content=body_json, headers=headers)
        response.raise_for_status()
        return response.json()

    @property
    def organization_id(self) -> str:
        return self._organization_id

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    async def create_wallet(self, wallet_name: str) -> Dict[str, Any]:
        """Create a new HD wallet."""
        body = {
            "type": "ACTIVITY_TYPE_CREATE_WALLET",
            "timestampMs": str(int(time.time() * 1000)),
            "organizationId": self._organization_id,
            "parameters": {
                "walletName": wallet_name,
            },
        }

        result = await self.post("/public/v1/submit/create_wallet", body)
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
        """Create accounts (addresses) for an existing wallet."""
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

        result = await self.post("/public/v1/submit/create_wallet_accounts", body)
        activity = result.get("activity", {})
        return activity.get("result", {}).get("createWalletAccountsResult", {})

    async def sign_transaction(
        self,
        wallet_id: str,
        unsigned_transaction: str,
        sign_with: str,
        transaction_type: str = "TRANSACTION_TYPE_ETHEREUM",
    ) -> Dict[str, Any]:
        """Sign a transaction with a wallet address.

        Args:
            wallet_id: Turnkey wallet ID.
            unsigned_transaction: Hex-encoded (EVM) or base64-encoded (Solana) unsigned tx.
            sign_with: Address or public key to sign with.
            transaction_type: Turnkey transaction type. Use TRANSACTION_TYPE_ETHEREUM
                for EVM chains or TRANSACTION_TYPE_SOLANA for Solana.
        """
        body = {
            "type": "ACTIVITY_TYPE_SIGN_TRANSACTION",
            "timestampMs": str(int(time.time() * 1000)),
            "organizationId": self._organization_id,
            "parameters": {
                "signWith": sign_with,
                "type": transaction_type,
                "unsignedTransaction": unsigned_transaction,
            },
        }

        result = await self.post("/public/v1/submit/sign_transaction", body)
        activity = result.get("activity", {})
        return activity.get("result", {}).get("signTransactionResult", {})

    async def sign_solana_transaction(
        self,
        wallet_id: str,
        unsigned_transaction: str,
        sign_with: str,
    ) -> Dict[str, Any]:
        """Sign a Solana transaction (ed25519) with a wallet address.

        Args:
            wallet_id: Turnkey wallet ID.
            unsigned_transaction: Base64-encoded unsigned Solana transaction.
            sign_with: Solana public key to sign with.
        """
        return await self.sign_transaction(
            wallet_id=wallet_id,
            unsigned_transaction=unsigned_transaction,
            sign_with=sign_with,
            transaction_type="TRANSACTION_TYPE_SOLANA",
        )

    async def get_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet details."""
        body = {
            "organizationId": self._organization_id,
            "walletId": wallet_id,
        }
        return await self.post("/public/v1/query/get_wallet", body)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
