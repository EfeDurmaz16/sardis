"""Lit Protocol MPC signer implementing MPCSignerPort.

Uses Lit Protocol's Programmable Key Pairs (PKPs) as a backup MPC signing
provider. PKPs are threshold-cryptography keys distributed across the Lit
network -- no single node holds the full private key.

Environment variables:
    LIT_PROTOCOL_API_KEY:        Relay server API key (required)
    LIT_PROTOCOL_NETWORK:        "datil-dev" | "datil-test" | "datil" (default: datil-test)
    LIT_PROTOCOL_RELAY_URL:      Custom relay URL (optional)

Each wallet_id is mapped to a PKP via the relay server. PKP addresses are
deterministic from their public keys, so the same wallet_id always resolves
to the same on-chain address regardless of which Lit node handles the request.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

from .executor import MPCSignerPort, TransactionRequest

logger = logging.getLogger(__name__)

# Lit Protocol network configurations
LIT_NETWORKS: Dict[str, Dict[str, str]] = {
    "datil-dev": {
        "relay_url": "https://relayer-server-staging-cayenne.getlit.dev",
        "rpc_url": "https://chain-rpc.litprotocol.com/http",
        "chain": "chronicleTestnet",
    },
    "datil-test": {
        "relay_url": "https://datil-test-relayer.getlit.dev",
        "rpc_url": "https://chain-rpc.litprotocol.com/http",
        "chain": "chronicleTestnet",
    },
    "datil": {
        "relay_url": "https://datil-relayer.getlit.dev",
        "rpc_url": "https://chain-rpc.litprotocol.com/http",
        "chain": "chronicle",
    },
}

# Default Lit Action code for signing EVM transactions
SIGN_TX_LIT_ACTION = """
const go = async () => {
    const sigShare = await LitActions.signEcdsa({
        toSign: dataToSign,
        publicKey,
        sigName: "sig1",
    });
};
go();
"""

SIGN_HASH_LIT_ACTION = """
const go = async () => {
    const sigShare = await LitActions.signEcdsa({
        toSign: dataToSign,
        publicKey,
        sigName: "sig1",
    });
};
go();
"""


class LitProtocolSigner(MPCSignerPort):
    """Lit Protocol PKP-based MPC signer.

    Maps each Sardis wallet_id to a Lit PKP. On first use for a wallet_id,
    mints a new PKP via the relay server. Subsequent calls use the cached
    PKP token ID.

    The signer communicates with the Lit relay for PKP management and with
    the Lit nodes for actual signing operations.
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    REQUEST_TIMEOUT = 30.0

    def __init__(
        self,
        api_key: str | None = None,
        network: str | None = None,
        relay_url: str | None = None,
    ):
        self._api_key = api_key or os.getenv("LIT_PROTOCOL_API_KEY", "")
        self._network = network or os.getenv("LIT_PROTOCOL_NETWORK", "datil-test")

        if self._network not in LIT_NETWORKS:
            raise ValueError(
                f"Unknown Lit network: {self._network}. "
                f"Valid options: {', '.join(LIT_NETWORKS)}"
            )

        net_config = LIT_NETWORKS[self._network]
        self._relay_url = (
            relay_url
            or os.getenv("LIT_PROTOCOL_RELAY_URL")
            or net_config["relay_url"]
        )

        self._client = httpx.AsyncClient(
            timeout=self.REQUEST_TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "api-key": self._api_key,
            },
        )

        # Cache: wallet_id -> {pkp_public_key, pkp_token_id, eth_address}
        self._pkp_cache: Dict[str, Dict[str, str]] = {}

        logger.info(
            "LitProtocolSigner initialized (network=%s, relay=%s)",
            self._network,
            self._relay_url,
        )

    async def _request(
        self,
        method: str,
        url: str,
        body: Dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic."""
        try:
            if method == "POST":
                resp = await self._client.post(url, json=body)
            else:
                resp = await self._client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(
                    "Lit request failed (attempt %d): %s", retry_count + 1, e
                )
                await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                return await self._request(method, url, body, retry_count + 1)
            raise

    async def _get_or_mint_pkp(self, wallet_id: str) -> Dict[str, str]:
        """Get cached PKP or mint a new one for the wallet_id.

        Uses a deterministic auth method ID derived from the wallet_id so the
        same wallet always resolves to the same PKP.
        """
        if wallet_id in self._pkp_cache:
            return self._pkp_cache[wallet_id]

        # Derive a deterministic identifier from wallet_id
        auth_method_id = hashlib.sha256(
            f"sardis:lit:pkp:{wallet_id}".encode()
        ).hexdigest()

        # First, try to look up existing PKP by auth method
        try:
            lookup_result = await self._request(
                "POST",
                f"{self._relay_url}/auth/pkp/lookup",
                {"authMethodType": 1, "authMethodId": f"0x{auth_method_id}"},
            )
            pkp_token_ids = lookup_result.get("pkpTokenIds", [])
            if pkp_token_ids:
                # Fetch PKP info for the first token ID
                pkp_info = await self._request(
                    "GET",
                    f"{self._relay_url}/auth/pkp/{pkp_token_ids[0]}",
                )
                entry = {
                    "pkp_public_key": pkp_info.get("publicKey", ""),
                    "pkp_token_id": pkp_token_ids[0],
                    "eth_address": pkp_info.get("ethAddress", ""),
                }
                self._pkp_cache[wallet_id] = entry
                logger.info(
                    "Resolved existing PKP for wallet %s: %s",
                    wallet_id,
                    entry["eth_address"],
                )
                return entry
        except Exception:
            # Lookup failed, proceed to mint
            pass

        # Mint a new PKP via the relay
        logger.info("Minting new PKP for wallet %s", wallet_id)
        mint_result = await self._request(
            "POST",
            f"{self._relay_url}/auth/pkp/mint",
            {
                "authMethodType": 1,
                "authMethodId": f"0x{auth_method_id}",
                "authMethodPubkey": f"0x{auth_method_id}",
            },
        )

        request_id = mint_result.get("requestId", "")
        if not request_id:
            raise RuntimeError(f"Lit PKP mint returned no requestId: {mint_result}")

        # Poll for mint completion
        pkp_info = await self._poll_mint(request_id)

        entry = {
            "pkp_public_key": pkp_info.get("pkpPublicKey", ""),
            "pkp_token_id": pkp_info.get("pkpTokenId", ""),
            "eth_address": pkp_info.get("pkpEthAddress", ""),
        }
        self._pkp_cache[wallet_id] = entry
        logger.info(
            "Minted PKP for wallet %s: address=%s, tokenId=%s",
            wallet_id,
            entry["eth_address"],
            entry["pkp_token_id"][:16] + "...",
        )
        return entry

    async def _poll_mint(
        self, request_id: str, timeout: float = 60.0
    ) -> Dict[str, Any]:
        """Poll relay for PKP mint completion."""
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                status = await self._request(
                    "GET",
                    f"{self._relay_url}/auth/pkp/status/{request_id}",
                )
                if status.get("status") == "Succeeded":
                    return status
                if status.get("status") == "Failed":
                    raise RuntimeError(
                        f"PKP mint failed: {status.get('error', 'unknown')}"
                    )
            except httpx.HTTPStatusError:
                pass  # Not ready yet
            await asyncio.sleep(2.0)

        raise TimeoutError(f"PKP mint timed out after {timeout}s")

    async def _execute_lit_action(
        self,
        pkp_public_key: str,
        data_to_sign: bytes,
    ) -> str:
        """Execute a Lit Action to sign data with a PKP.

        Returns the hex-encoded signature.
        """
        # Convert data to uint8 array representation for Lit Action
        data_hex = data_to_sign.hex()

        result = await self._request(
            "POST",
            f"{self._relay_url}/execute/sign",
            {
                "publicKey": pkp_public_key,
                "dataToSign": f"0x{data_hex}",
                "authMethods": [],
                "code": SIGN_HASH_LIT_ACTION,
                "jsParams": {
                    "publicKey": pkp_public_key,
                    "dataToSign": list(data_to_sign),
                },
            },
        )

        sig = result.get("sig1") or result.get("signature") or {}
        if isinstance(sig, dict):
            r = sig.get("r", "").removeprefix("0x").zfill(64)
            s = sig.get("s", "").removeprefix("0x").zfill(64)
            v = sig.get("recid", 0)
            if isinstance(v, str):
                v = int(v, 16) if v.startswith("0x") else int(v)
            v = v + 27 if v < 27 else v
            return f"0x{r}{s}{v:02x}"
        elif isinstance(sig, str):
            return sig if sig.startswith("0x") else f"0x{sig}"

        raise RuntimeError(f"Unexpected Lit signing response: {result}")

    # ------------------------------------------------------------------
    # MPCSignerPort implementation
    # ------------------------------------------------------------------

    async def sign_transaction(
        self,
        wallet_id: str,
        tx: TransactionRequest,
    ) -> str:
        """Sign an EVM transaction via Lit Protocol PKP."""
        import rlp

        from .executor import CHAIN_CONFIGS

        pkp = await self._get_or_mint_pkp(wallet_id)

        chain_config = CHAIN_CONFIGS.get(tx.chain, {})
        chain_id = chain_config.get("chain_id", 1)

        nonce = tx.nonce if tx.nonce is not None else 0
        max_priority_fee = tx.max_priority_fee_per_gas or 1_000_000_000
        max_fee = tx.max_fee_per_gas or 50_000_000_000
        gas_limit = tx.gas_limit or 100000
        to_address = bytes.fromhex(
            tx.to_address[2:] if tx.to_address.startswith("0x") else tx.to_address
        )
        value = tx.value
        data = tx.data or b""

        # EIP-1559 (Type 2) unsigned transaction
        tx_fields = [
            chain_id,
            nonce,
            max_priority_fee,
            max_fee,
            gas_limit,
            to_address,
            value,
            data,
            [],  # access list
        ]

        rlp_encoded = rlp.encode(tx_fields)
        # The hash to sign is keccak256(0x02 || rlp(fields))
        unsigned_payload = b"\x02" + rlp_encoded

        from hashlib import sha3_256
        try:
            from eth_hash.auto import keccak
            tx_hash = keccak(unsigned_payload)
        except ImportError:
            # Fallback: use pysha3 or hashlib
            import hashlib as _hl
            tx_hash = _hl.new("keccak_256", unsigned_payload).digest()

        signature_hex = await self._execute_lit_action(
            pkp["pkp_public_key"],
            tx_hash,
        )

        # Parse signature components
        sig = signature_hex.removeprefix("0x")
        r = int(sig[:64], 16)
        s = int(sig[64:128], 16)
        v = int(sig[128:130], 16)

        # Build signed EIP-1559 transaction
        signed_fields = [
            chain_id,
            nonce,
            max_priority_fee,
            max_fee,
            gas_limit,
            to_address,
            value,
            data,
            [],  # access list
            v - 27,  # EIP-1559 uses yParity (0 or 1)
            r,
            s,
        ]

        signed_rlp = rlp.encode(signed_fields)
        signed_tx_hex = "0x02" + signed_rlp.hex()

        logger.info("Transaction signed via Lit Protocol PKP for wallet %s", wallet_id)
        return signed_tx_hex

    async def get_address(self, wallet_id: str, chain: str) -> str:
        """Get the PKP's Ethereum address for a wallet.

        All EVM chains share the same address since PKPs use secp256k1.
        """
        pkp = await self._get_or_mint_pkp(wallet_id)
        return pkp["eth_address"]

    async def sign_user_operation_hash(
        self, wallet_id: str, user_op_hash: str
    ) -> str:
        """Sign an ERC-4337 UserOperation hash via Lit Protocol PKP."""
        pkp = await self._get_or_mint_pkp(wallet_id)

        hash_hex = user_op_hash.removeprefix("0x")
        hash_bytes = bytes.fromhex(hash_hex)

        signature = await self._execute_lit_action(
            pkp["pkp_public_key"],
            hash_bytes,
        )

        logger.info(
            "UserOp hash signed via Lit Protocol PKP for wallet %s", wallet_id
        )
        return signature

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
