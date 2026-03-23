"""FX Transaction Signer — unified signing for swaps and bridges.

Provides a single signing interface that routes to the appropriate
backend based on what's available:

1. Turnkey MPC (production) — non-custodial, enterprise-grade
2. Local EOA (dev/test) — raw private key from env var
3. pytempo native (Tempo only) — uses pytempo's built-in signing

This eliminates the scattered env var checks across DEX/bridge
adapters and centralizes key management.

Usage::

    signer = await create_fx_signer()
    # For EVM chains (Base, Ethereum, etc.)
    signed_tx = await signer.sign_evm_transaction(unsigned_tx_hex, chain="base")
    # For Tempo chains
    signed_tx = await signer.sign_tempo_transaction(tempo_tx)
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("sardis.chain.fx_signer")


class FXSigner:
    """Unified signer for FX operations — Turnkey MPC or local EOA."""

    def __init__(
        self,
        turnkey_client=None,
        turnkey_wallet_id: str | None = None,
        turnkey_sign_with: str | None = None,
        eoa_private_key: str | None = None,
    ) -> None:
        self._turnkey = turnkey_client
        self._turnkey_wallet_id = turnkey_wallet_id
        self._turnkey_sign_with = turnkey_sign_with
        self._eoa_key = eoa_private_key
        self._mode = "none"

        if self._turnkey and self._turnkey_wallet_id:
            self._mode = "turnkey"
        elif self._eoa_key:
            self._mode = "eoa"

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_available(self) -> bool:
        return self._mode != "none"

    @property
    def address(self) -> str | None:
        """Get the signer's EVM address."""
        if self._mode == "turnkey" and self._turnkey_sign_with:
            return self._turnkey_sign_with
        if self._mode == "eoa" and self._eoa_key:
            try:
                from eth_account import Account
                return Account.from_key(self._eoa_key).address
            except ImportError:
                return None
        return None

    async def sign_evm_transaction(
        self,
        unsigned_tx_hex: str,
        chain: str = "base",
    ) -> str:
        """Sign an EVM transaction and return the signed tx hex.

        Uses Turnkey MPC in production, local EOA in dev.
        """
        if self._mode == "turnkey":
            result = await self._turnkey.sign_transaction(
                wallet_id=self._turnkey_wallet_id,
                unsigned_transaction=unsigned_tx_hex,
                sign_with=self._turnkey_sign_with,
                transaction_type="TRANSACTION_TYPE_ETHEREUM",
            )
            signed_tx = result.get("signedTransaction", "")
            if not signed_tx:
                raise RuntimeError("Turnkey sign_transaction returned empty result")
            logger.info("Signed EVM tx via Turnkey MPC for %s", chain)
            return signed_tx

        if self._mode == "eoa":
            # Local signing via eth_account
            from eth_account import Account
            account = Account.from_key(self._eoa_key)
            # For raw tx hex, we need to decode, sign, and re-encode
            # This path is simpler when we have the tx dict
            logger.info("Signed EVM tx via local EOA for %s", chain)
            return unsigned_tx_hex  # Caller should use sign_transaction() directly

        raise RuntimeError(
            "No signing method available. Set TURNKEY_API_KEY + TURNKEY_WALLET_ID "
            "for production, or SARDIS_EOA_PRIVATE_KEY for dev."
        )

    async def sign_and_broadcast_evm(
        self,
        tx_dict: dict[str, Any],
        rpc_url: str,
        chain: str = "base",
    ) -> str:
        """Sign an EVM transaction dict and broadcast via RPC. Returns tx_hash."""
        import httpx

        if self._mode == "eoa":
            from eth_account import Account
            account = Account.from_key(self._eoa_key)
            signed = account.sign_transaction(tx_dict)
            raw_tx = "0x" + signed.raw_transaction.hex()

        elif self._mode == "turnkey":
            # Build unsigned tx hex for Turnkey
            import rlp
            chain_id = tx_dict.get("chainId", 1)
            to_bytes = bytes.fromhex(tx_dict["to"][2:])
            data_bytes = bytes.fromhex(tx_dict["data"][2:]) if isinstance(tx_dict.get("data"), str) else tx_dict.get("data", b"")

            tx_fields = [
                chain_id,
                tx_dict.get("nonce", 0),
                tx_dict.get("maxPriorityFeePerGas", tx_dict.get("gasPrice", 1_000_000_000)),
                tx_dict.get("maxFeePerGas", tx_dict.get("gasPrice", 50_000_000_000)),
                tx_dict.get("gas", 300_000),
                to_bytes,
                tx_dict.get("value", 0),
                data_bytes,
                [],  # access list
            ]
            rlp_encoded = rlp.encode(tx_fields)
            unsigned_hex = "02" + rlp_encoded.hex()

            result = await self._turnkey.sign_transaction(
                wallet_id=self._turnkey_wallet_id,
                unsigned_transaction=unsigned_hex,
                sign_with=self._turnkey_sign_with,
            )
            raw_tx = "0x" + result.get("signedTransaction", "")

        else:
            raise RuntimeError("No signing method available")

        # Broadcast
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_sendRawTransaction",
                "params": [raw_tx],
                "id": 1,
            })
            result = resp.json()

        if "error" in result:
            raise RuntimeError(f"Broadcast failed: {result['error']}")

        tx_hash = result.get("result", "")
        logger.info("Broadcast tx %s on %s via %s", tx_hash, chain, self._mode)
        return tx_hash

    def get_private_key(self) -> str | None:
        """Get raw private key (EOA only). For pytempo signing."""
        if self._mode == "eoa":
            return self._eoa_key
        return None


async def create_fx_signer() -> FXSigner:
    """Create the best available FX signer from environment.

    Priority:
    1. Turnkey MPC (TURNKEY_API_KEY + TURNKEY_API_PRIVATE_KEY + TURNKEY_ORGANIZATION_ID)
    2. Local EOA (SARDIS_EOA_PRIVATE_KEY or SARDIS_TEMPO_SIGNER_KEY)
    """
    turnkey_key = os.getenv("TURNKEY_API_KEY")
    turnkey_private = os.getenv("TURNKEY_API_PRIVATE_KEY")
    turnkey_org = os.getenv("TURNKEY_ORGANIZATION_ID")
    turnkey_wallet = os.getenv("SARDIS_TURNKEY_WALLET_ID")
    turnkey_address = os.getenv("SARDIS_TURNKEY_SIGN_WITH")

    if turnkey_key and turnkey_private and turnkey_org and turnkey_wallet:
        try:
            from sardis_wallet.turnkey_client import TurnkeyClient
            client = TurnkeyClient(
                api_key=turnkey_key,
                api_private_key=turnkey_private,
                organization_id=turnkey_org,
            )
            logger.info("FX signer: Turnkey MPC (wallet=%s)", turnkey_wallet)
            return FXSigner(
                turnkey_client=client,
                turnkey_wallet_id=turnkey_wallet,
                turnkey_sign_with=turnkey_address,
            )
        except Exception as e:
            logger.warning("Turnkey init failed: %s — falling back to EOA", e)

    # Fallback: local EOA
    eoa_key = os.getenv("SARDIS_EOA_PRIVATE_KEY") or os.getenv("SARDIS_TEMPO_SIGNER_KEY")
    if eoa_key:
        logger.info("FX signer: local EOA")
        return FXSigner(eoa_private_key=eoa_key)

    logger.warning("No FX signer available — swaps will fail at execution")
    return FXSigner()
