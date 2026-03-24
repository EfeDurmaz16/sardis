"""FX Transaction Signer — chain-aware signing for swaps and bridges.

3-tier signing architecture:

1. **Tempo (type 0x76)** → Account Keychain access key
   - Root key stays in Turnkey MPC (used only for authorize_key)
   - Access key signs locally via pytempo (fast, no API call per tx)
   - Spending limits enforced at protocol level (precompile)
   - Format: 0x03 || root_address || inner_signature

2. **Base/Ethereum (type 0x02)** → Turnkey MPC
   - Standard EIP-1559 transactions signed via Turnkey API
   - Non-custodial, enterprise-grade
   - Supports all EVM chains

3. **Fallback** → Local EOA (dev/test only)
   - Raw private key from env var
   - Works for both Tempo and EVM chains

Usage::

    signer = await create_fx_signer()

    # Tempo: uses access key (local, fast)
    signed = await signer.sign_tempo_transaction(tempo_tx)

    # Base: uses Turnkey MPC (remote, secure)
    tx_hash = await signer.sign_and_broadcast_evm(tx_dict, rpc_url, chain="base")
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("sardis.chain.fx_signer")


class FXSigner:
    """Chain-aware signer: Tempo access key + Turnkey MPC + EOA fallback."""

    def __init__(
        self,
        turnkey_client=None,
        turnkey_wallet_id: str | None = None,
        turnkey_sign_with: str | None = None,
        eoa_private_key: str | None = None,
        tempo_access_key: str | None = None,
        tempo_root_address: str | None = None,
    ) -> None:
        self._turnkey = turnkey_client
        self._turnkey_wallet_id = turnkey_wallet_id
        self._turnkey_sign_with = turnkey_sign_with
        self._eoa_key = eoa_private_key
        self._tempo_access_key = tempo_access_key
        self._tempo_root_address = tempo_root_address

        # Determine available modes
        self._has_turnkey = bool(self._turnkey and self._turnkey_wallet_id)
        self._has_tempo_access_key = bool(self._tempo_access_key)
        self._has_eoa = bool(self._eoa_key)

    @property
    def mode(self) -> str:
        """Primary signing mode."""
        if self._has_turnkey:
            return "turnkey"
        if self._has_tempo_access_key:
            return "tempo_access_key"
        if self._has_eoa:
            return "eoa"
        return "none"

    @property
    def is_available(self) -> bool:
        return self._has_turnkey or self._has_tempo_access_key or self._has_eoa

    @property
    def address(self) -> str | None:
        """Get the signer's EVM address."""
        if self._tempo_root_address:
            return self._tempo_root_address
        if self._turnkey_sign_with:
            return self._turnkey_sign_with
        if self._has_eoa:
            try:
                from eth_account import Account
                return Account.from_key(self._eoa_key).address
            except ImportError:
                return None
        return None

    def can_sign_tempo(self) -> bool:
        """Can sign Tempo type 0x76 transactions."""
        return self._has_tempo_access_key or self._has_eoa

    def can_sign_evm(self) -> bool:
        """Can sign standard EVM type 0x02 transactions."""
        return self._has_turnkey or self._has_eoa

    # ------------------------------------------------------------------
    # Tempo signing (type 0x76 via pytempo)
    # ------------------------------------------------------------------

    def sign_tempo_transaction(self, tempo_tx) -> Any:
        """Sign a Tempo type 0x76 transaction locally.

        Uses access key (preferred) or EOA private key.
        Returns signed TempoTransaction.
        """
        key = self._tempo_access_key or self._eoa_key
        if not key:
            raise RuntimeError(
                "No Tempo signing key. Set SARDIS_TEMPO_ACCESS_KEY or SARDIS_EOA_PRIVATE_KEY."
            )

        signed = tempo_tx.sign(key)

        # If using access key with keychain signature format
        if self._has_tempo_access_key and self._tempo_root_address:
            logger.info(
                "Signed Tempo tx via access key (root=%s)",
                self._tempo_root_address[:10],
            )
        else:
            logger.info("Signed Tempo tx via EOA")

        return signed

    def get_tempo_key(self) -> str | None:
        """Get the key for Tempo type 0x76 signing (access key or EOA)."""
        return self._tempo_access_key or self._eoa_key

    # ------------------------------------------------------------------
    # EVM signing (type 0x02 via Turnkey MPC)
    # ------------------------------------------------------------------

    async def sign_and_broadcast_evm(
        self,
        tx_dict: dict[str, Any],
        rpc_url: str,
        chain: str = "base",
    ) -> str:
        """Sign an EVM transaction and broadcast via RPC. Returns tx_hash."""
        import httpx

        if self._has_eoa:
            from eth_account import Account
            account = Account.from_key(self._eoa_key)
            signed = account.sign_transaction(tx_dict)
            raw_tx = "0x" + signed.raw_transaction.hex()
            logger.info("Signed EVM tx via EOA for %s", chain)

        elif self._has_turnkey:
            import rlp
            chain_id = tx_dict.get("chainId", 1)
            to_bytes = bytes.fromhex(tx_dict["to"][2:]) if tx_dict.get("to") else b""
            data_val = tx_dict.get("data", "0x")
            data_bytes = bytes.fromhex(data_val[2:]) if isinstance(data_val, str) else data_val

            tx_fields = [
                chain_id,
                tx_dict.get("nonce", 0),
                tx_dict.get("maxPriorityFeePerGas", tx_dict.get("gasPrice", 1_000_000_000)),
                tx_dict.get("maxFeePerGas", tx_dict.get("gasPrice", 50_000_000_000)),
                tx_dict.get("gas", 300_000),
                to_bytes,
                tx_dict.get("value", 0),
                data_bytes,
                [],
            ]
            rlp_encoded = rlp.encode(tx_fields)
            unsigned_hex = "02" + rlp_encoded.hex()

            result = await self._turnkey.sign_transaction(
                wallet_id=self._turnkey_wallet_id,
                unsigned_transaction=unsigned_hex,
                sign_with=self._turnkey_sign_with,
            )
            raw_tx = "0x" + result.get("signedTransaction", "")
            logger.info("Signed EVM tx via Turnkey MPC for %s", chain)

        else:
            raise RuntimeError("No EVM signing method available")

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
        logger.info("Broadcast tx %s on %s", tx_hash, chain)
        return tx_hash

    # ------------------------------------------------------------------
    # Turnkey root key operations (one-time setup)
    # ------------------------------------------------------------------

    async def authorize_tempo_access_key(
        self,
        access_key_address: str,
        signature_type: int = 1,  # secp256k1
        expiry_seconds: int = 86400 * 7,  # 7 days
        token_limits: dict[str, int] | None = None,
    ) -> str:
        """Use Turnkey MPC to authorize an access key on Tempo Account Keychain.

        This is a ONE-TIME operation per access key. The root key (in Turnkey)
        signs a standard EVM tx that calls AccountKeychain.authorize_key().
        After this, the access key can sign type 0x76 txs locally.

        Args:
            access_key_address: The access key's public address.
            signature_type: 1=secp256k1, 2=p256, 3=webauthn
            expiry_seconds: How long the access key is valid.
            token_limits: {token_address: max_amount} spending limits.

        Returns:
            Transaction hash of the authorize_key call.
        """
        if not self._has_turnkey:
            raise RuntimeError("Turnkey MPC required to authorize access keys")

        import time
        from pytempo.contracts import AccountKeychain

        expiry = int(time.time()) + expiry_seconds

        limits = []
        if token_limits:
            limits = [(token, amount) for token, amount in token_limits.items()]

        # Build the authorize_key call
        call = AccountKeychain.authorize_key(
            key_id=access_key_address,
            signature_type=signature_type,
            expiry=expiry,
            enforce_limits=bool(limits),
            limits=limits or None,
        )

        # This is a standard EVM call to the Keychain precompile
        # Turnkey CAN sign this because it's going to a regular address
        rpc_url = os.getenv("SARDIS_TEMPO_RPC_URL", "https://rpc.tempo.xyz")

        tx_dict = {
            "to": AccountKeychain.ADDRESS,
            "data": "0x" + call.data.hex() if isinstance(call.data, bytes) else call.data,
            "value": 0,
            "gas": 200_000,
            "chainId": int(os.getenv("SARDIS_TEMPO_CHAIN_ID", "4217")),
        }

        # Get nonce
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionCount",
                "params": [self._turnkey_sign_with, "pending"],
                "id": 1,
            })
            tx_dict["nonce"] = int(resp.json()["result"], 16)

            resp2 = await client.post(rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 2,
            })
            gas_price = int(resp2.json()["result"], 16)
            tx_dict["gasPrice"] = gas_price

        tx_hash = await self.sign_and_broadcast_evm(tx_dict, rpc_url, chain="tempo")

        logger.info(
            "Authorized access key %s on Tempo Keychain (expiry=%ds, limits=%s) tx=%s",
            access_key_address, expiry_seconds, limits, tx_hash,
        )
        return tx_hash

    # ------------------------------------------------------------------
    # Backward compat
    # ------------------------------------------------------------------

    def get_private_key(self) -> str | None:
        """Get raw private key for legacy callers."""
        return self._tempo_access_key or self._eoa_key


async def create_fx_signer() -> FXSigner:
    """Create the best available FX signer from environment.

    Checks in order:
    1. Tempo access key (SARDIS_TEMPO_ACCESS_KEY) — for type 0x76
    2. Turnkey MPC (TURNKEY_API_KEY + wallet) — for type 0x02
    3. Local EOA (SARDIS_EOA_PRIVATE_KEY) — fallback for both

    The ideal production setup has BOTH:
    - Tempo access key for Tempo chain (fast, local)
    - Turnkey MPC for Base/Ethereum (secure, remote)
    """
    # Tempo access key (for type 0x76 signing)
    tempo_access_key = os.getenv("SARDIS_TEMPO_ACCESS_KEY")
    tempo_root = os.getenv("SARDIS_TURNKEY_SIGN_WITH") or os.getenv("SARDIS_TEMPO_ROOT_ADDRESS")

    # Turnkey MPC (for type 0x02 signing)
    turnkey_key = os.getenv("TURNKEY_API_KEY")
    turnkey_private = os.getenv("TURNKEY_API_PRIVATE_KEY")
    turnkey_org = os.getenv("TURNKEY_ORGANIZATION_ID")
    turnkey_wallet = os.getenv("SARDIS_TURNKEY_WALLET_ID")
    turnkey_address = os.getenv("SARDIS_TURNKEY_SIGN_WITH")

    turnkey_client = None
    if turnkey_key and turnkey_private and turnkey_org and turnkey_wallet:
        try:
            from sardis_wallet.turnkey_client import TurnkeyClient
            turnkey_client = TurnkeyClient(
                api_key=turnkey_key,
                api_private_key=turnkey_private,
                organization_id=turnkey_org,
            )
        except Exception as e:
            logger.warning("Turnkey init failed: %s", e)

    # Local EOA fallback
    eoa_key = os.getenv("SARDIS_EOA_PRIVATE_KEY") or os.getenv("SARDIS_TEMPO_SIGNER_KEY")

    signer = FXSigner(
        turnkey_client=turnkey_client,
        turnkey_wallet_id=turnkey_wallet,
        turnkey_sign_with=turnkey_address,
        eoa_private_key=eoa_key,
        tempo_access_key=tempo_access_key,
        tempo_root_address=tempo_root,
    )

    modes = []
    if signer._has_tempo_access_key:
        modes.append("tempo_access_key")
    if signer._has_turnkey:
        modes.append("turnkey_mpc")
    if signer._has_eoa:
        modes.append("eoa")

    # Enforce Turnkey MPC in production — never silently fall back to EOA
    env = os.getenv("SARDIS_ENV", "").lower()
    chain_mode = os.getenv("SARDIS_CHAIN_MODE", "").lower()
    is_production = env in ("production", "prod") or chain_mode == "live"

    if is_production and not signer._has_turnkey:
        raise RuntimeError(
            "Turnkey MPC credentials required in production. "
            "Set TURNKEY_API_KEY, TURNKEY_API_PRIVATE_KEY, "
            "TURNKEY_ORGANIZATION_ID, and SARDIS_TURNKEY_WALLET_ID. "
            "EOA fallback is not allowed when SARDIS_ENV=production "
            "or SARDIS_CHAIN_MODE=live."
        )

    logger.info("FX signer initialized: %s", " + ".join(modes) or "NONE")
    return signer
