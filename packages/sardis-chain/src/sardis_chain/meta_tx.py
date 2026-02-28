"""
EIP-2771 Meta-Transaction Support for Gas-Free Transactions.

This module implements EIP-2771 (https://eips.ethereum.org/EIPS/eip-2771) which allows
users to submit transactions without paying gas. A relayer pays the gas fee and submits
the transaction on behalf of the user.

Key Components:
- ForwardRequest: The meta-transaction structure
- MetaTransactionRelayer: Service to relay meta-transactions
- Signature verification for user intent
- Nonce management for replay protection

Flow:
1. User signs a ForwardRequest (off-chain)
2. Signed request is sent to relayer
3. Relayer validates signature and submits to Forwarder contract
4. Forwarder verifies signature and forwards call to target contract
5. Target contract trusts msg.sender from Forwarder

Trusted Forwarder Contracts:
- Ethereum: 0x... (to be deployed)
- Base: 0x... (to be deployed)
- Polygon: 0x... (to be deployed)
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

from eth_account import Account
from eth_account.messages import encode_defunct, encode_structured_data
from eth_utils import to_checksum_address, keccak

logger = logging.getLogger(__name__)


# EIP-712 Domain for ForwardRequest
EIP712_DOMAIN = {
    "name": "MinimalForwarder",
    "version": "0.0.1",
    "chainId": None,  # Set dynamically per chain
    "verifyingContract": None,  # Set to forwarder address
}

# EIP-712 ForwardRequest type
FORWARD_REQUEST_TYPE = {
    "ForwardRequest": [
        {"name": "from", "type": "address"},
        {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"},
        {"name": "gas", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "data", "type": "bytes"},
    ]
}


@dataclass
class ForwardRequest:
    """
    EIP-2771 ForwardRequest structure.

    This represents a meta-transaction that a relayer will submit on behalf of the user.
    The user signs this request off-chain, and the relayer pays for gas.
    """
    from_address: str  # User's address (signer)
    to_address: str    # Target contract address
    value: int = 0     # Native token value in wei
    gas: int = 300000  # Gas limit for the forwarded call
    nonce: int = 0     # User's nonce in the forwarder (for replay protection)
    data: bytes = b""  # Calldata for the target contract

    # Signature fields (populated after signing)
    signature: Optional[str] = None
    deadline: Optional[int] = None  # Unix timestamp when signature expires

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for EIP-712 encoding."""
        return {
            "from": to_checksum_address(self.from_address),
            "to": to_checksum_address(self.to_address),
            "value": self.value,
            "gas": self.gas,
            "nonce": self.nonce,
            "data": self.data.hex() if isinstance(self.data, bytes) else self.data,
        }

    def compute_typed_data_hash(self, chain_id: int, forwarder_address: str) -> bytes:
        """
        Compute EIP-712 typed data hash for signing.

        Args:
            chain_id: Chain ID (e.g., 8453 for Base)
            forwarder_address: Address of the trusted forwarder contract

        Returns:
            32-byte hash to be signed
        """
        # Set domain parameters
        domain = EIP712_DOMAIN.copy()
        domain["chainId"] = chain_id
        domain["verifyingContract"] = to_checksum_address(forwarder_address)

        # Build EIP-712 structured data
        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                **FORWARD_REQUEST_TYPE,
            },
            "primaryType": "ForwardRequest",
            "domain": domain,
            "message": self.to_dict(),
        }

        # Encode and hash
        encoded_data = encode_structured_data(structured_data)
        return encoded_data.body

    def sign(self, private_key: str, chain_id: int, forwarder_address: str) -> None:
        """
        Sign the forward request using EIP-712.

        Args:
            private_key: Private key to sign with (must match from_address)
            chain_id: Chain ID
            forwarder_address: Forwarder contract address
        """
        # Compute typed data hash
        message_hash = self.compute_typed_data_hash(chain_id, forwarder_address)

        # Sign with private key
        account = Account.from_key(private_key)
        signature = account.signHash(message_hash)

        # Store signature as hex string (r + s + v format)
        self.signature = signature.signature.hex()

        logger.debug(
            f"Signed ForwardRequest: from={self.from_address} to={self.to_address} "
            f"nonce={self.nonce} signature={self.signature[:20]}..."
        )

    def verify_signature(self, chain_id: int, forwarder_address: str) -> bool:
        """
        Verify the signature matches the from_address.

        Args:
            chain_id: Chain ID
            forwarder_address: Forwarder contract address

        Returns:
            True if signature is valid
        """
        if not self.signature:
            return False

        # Compute typed data hash
        message_hash = self.compute_typed_data_hash(chain_id, forwarder_address)

        # Recover signer address from signature
        try:
            recovered_address = Account.recover_message(
                encode_defunct(message_hash),
                signature=self.signature
            )
            return recovered_address.lower() == self.from_address.lower()
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False


@dataclass
class MetaTransactionResult:
    """Result of a relayed meta-transaction."""
    tx_hash: str
    relayer_address: str
    user_address: str
    target_address: str
    gas_used: Optional[int] = None
    gas_cost_wei: Optional[int] = None
    relayed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error: Optional[str] = None


class MetaTransactionRelayer:
    """
    Service to relay meta-transactions on behalf of users.

    This service:
    1. Accepts signed ForwardRequests from users
    2. Validates signatures
    3. Submits to the trusted Forwarder contract
    4. Pays gas fees
    5. Returns transaction receipt
    """

    # Trusted forwarder contract addresses per chain.
    # Override via environment: SARDIS_FORWARDER_<CHAIN>=0x...
    # e.g. SARDIS_FORWARDER_BASE=0xabc...
    # Defaults to OpenZeppelin MinimalForwarder deployments where available.
    _DEFAULT_FORWARDER_ADDRESSES = {
        "base": "",
        "base_sepolia": "",
        "polygon": "",
        "polygon_amoy": "",
        "ethereum": "",
        "arbitrum": "",
        "optimism": "",
    }

    # execute((address,address,uint256,uint256,uint256,bytes),bytes)
    EXECUTE_SELECTOR = "47153f82"

    @classmethod
    def get_forwarder_addresses(cls) -> Dict[str, str]:
        """Load forwarder addresses from env vars, falling back to defaults."""
        import os
        addresses = {}
        for chain, default in cls._DEFAULT_FORWARDER_ADDRESSES.items():
            env_key = f"SARDIS_FORWARDER_{chain.upper()}"
            addresses[chain] = os.getenv(env_key, default)
        return addresses

    def __init__(
        self,
        relayer_private_key: str,
        rpc_client: Any,  # ProductionRPCClient
        chain_id: int,
        chain_name: str,
    ):
        """
        Initialize the meta-transaction relayer.

        Args:
            relayer_private_key: Private key of the relayer account (pays gas)
            rpc_client: RPC client for submitting transactions
            chain_id: Chain ID (e.g., 8453 for Base)
            chain_name: Chain name (e.g., "base")
        """
        self.relayer_account = Account.from_key(relayer_private_key)
        self.relayer_address = self.relayer_account.address
        self.rpc_client = rpc_client
        self.chain_id = chain_id
        self.chain_name = chain_name

        # Get forwarder address for this chain
        addresses = self.get_forwarder_addresses()
        self.forwarder_address = addresses.get(chain_name.lower(), "")
        if not self.forwarder_address or self.forwarder_address == "0x" + "0" * 40:
            logger.warning(
                f"No forwarder contract deployed for {chain_name}. "
                "Meta-transactions will not work until forwarder is deployed."
            )

        logger.info(
            f"MetaTransactionRelayer initialized: chain={chain_name} "
            f"relayer={self.relayer_address} forwarder={self.forwarder_address}"
        )

    async def get_user_nonce(self, user_address: str) -> int:
        """
        Get the current nonce for a user in the forwarder contract.

        Args:
            user_address: User's address

        Returns:
            Current nonce value
        """
        # Call forwarder.getNonce(user_address)
        # Function selector: getNonce(address) = 0x2d0335ab
        selector = bytes.fromhex("2d0335ab")
        address_bytes = bytes.fromhex(user_address[2:].lower().zfill(64))
        call_data = selector + address_bytes

        result = await self.rpc_client._call(
            "eth_call",
            [
                {
                    "to": self.forwarder_address,
                    "data": "0x" + call_data.hex(),
                },
                "latest",
            ],
        )

        # Parse uint256 result
        nonce = int(result, 16)
        return nonce

    def validate_request(self, request: ForwardRequest) -> tuple[bool, Optional[str]]:
        """
        Validate a ForwardRequest before relaying.

        Args:
            request: The forward request to validate

        Returns:
            (is_valid, error_message)
        """
        # Check signature exists
        if not request.signature:
            return False, "Missing signature"

        # Verify signature
        if not request.verify_signature(self.chain_id, self.forwarder_address):
            return False, "Invalid signature"

        # Check deadline if present
        if request.deadline:
            now = int(datetime.now(timezone.utc).timestamp())
            if now > request.deadline:
                return False, "Request expired"

        # Check addresses are valid
        try:
            to_checksum_address(request.from_address)
            to_checksum_address(request.to_address)
        except Exception:
            return False, "Invalid address format"

        return True, None

    async def relay(self, request: ForwardRequest) -> MetaTransactionResult:
        """
        Relay a meta-transaction to the forwarder contract.

        Args:
            request: Signed ForwardRequest

        Returns:
            MetaTransactionResult with transaction details

        Raises:
            ValueError: If request validation fails
            Exception: If transaction submission fails
        """
        # Validate request
        is_valid, error = self.validate_request(request)
        if not is_valid:
            raise ValueError(f"Invalid ForwardRequest: {error}")

        logger.info(
            f"Relaying meta-transaction: from={request.from_address} "
            f"to={request.to_address} nonce={request.nonce}"
        )

        # Encode call to forwarder.execute(ForwardRequest, signature)
        # Function selector: execute((address,address,uint256,uint256,uint256,bytes),bytes)
        # This would normally use web3.py's contract encoding
        # For now, we'll use a simplified version

        # TODO: Replace with actual contract call encoding
        # This requires the forwarder contract ABI
        call_data = self._encode_execute_call(request)

        # Build transaction
        tx_params = {
            "from": self.relayer_address,
            "to": self.forwarder_address,
            "data": call_data,
            "gas": request.gas + 50000,  # Add overhead for forwarder
        }

        # Estimate gas
        try:
            gas_estimate = await self.rpc_client._call("eth_estimateGas", [tx_params])
            tx_params["gas"] = int(gas_estimate, 16)
        except Exception as e:
            logger.warning(f"Gas estimation failed, using default: {e}")

        # Get gas price
        gas_price = await self.rpc_client._call("eth_gasPrice", [])
        tx_params["gasPrice"] = gas_price

        # Get nonce for relayer
        nonce = await self.rpc_client._call(
            "eth_getTransactionCount", [self.relayer_address, "pending"]
        )
        tx_params["nonce"] = nonce
        tx_params["chainId"] = self.chain_id

        # Sign transaction with relayer key
        signed_tx = self.relayer_account.sign_transaction(tx_params)

        # Submit transaction
        tx_hash = await self.rpc_client._call(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )

        logger.info(f"Meta-transaction submitted: tx_hash={tx_hash}")

        # Return result
        return MetaTransactionResult(
            tx_hash=tx_hash,
            relayer_address=self.relayer_address,
            user_address=request.from_address,
            target_address=request.to_address,
            gas_used=tx_params.get("gas"),
            gas_cost_wei=tx_params.get("gas", 0) * int(gas_price, 16),
        )

    def _encode_execute_call(self, request: ForwardRequest) -> str:
        """
        ABI-encode the execute((ForwardRequest), bytes signature) call.

        Follows Solidity ABI encoding for:
          execute((address,address,uint256,uint256,uint256,bytes), bytes)

        Args:
            request: ForwardRequest to encode

        Returns:
            Encoded calldata as hex string (0x-prefixed)
        """
        sig = request.signature or ""
        sig_bytes = bytes.fromhex(sig.removeprefix("0x")) if sig else b""

        # ABI-encode the ForwardRequest struct fields
        from_addr = bytes.fromhex(request.from_address[2:].lower().zfill(64))
        to_addr = bytes.fromhex(request.to_address[2:].lower().zfill(64))
        value_bytes = request.value.to_bytes(32, byteorder="big")
        gas_bytes = request.gas.to_bytes(32, byteorder="big")
        nonce_bytes = request.nonce.to_bytes(32, byteorder="big")

        data_raw = request.data if isinstance(request.data, bytes) else bytes.fromhex(request.data)

        # Head: selector + 2 offset pointers (struct at 0x40, sig at dynamic)
        # Struct is: 5 static fields (5*32=160 bytes) + dynamic `data`
        # Offsets are relative to the start of the params area

        # offset to struct (tuple) = 0x40 (64) because we have 2 words of offsets
        struct_offset = 64
        # struct static = 5*32 = 160, then dynamic offset word (32) + data length word (32) + padded data
        data_padded_len = ((len(data_raw) + 31) // 32) * 32
        struct_total = 160 + 32 + 32 + data_padded_len  # 5 fields + data_offset + data_len + data_padded
        sig_offset = struct_offset + struct_total

        # Build encoding
        parts = []
        # Selector
        parts.append(bytes.fromhex(self.EXECUTE_SELECTOR))
        # Offset to struct (word 0)
        parts.append(struct_offset.to_bytes(32, "big"))
        # Offset to signature bytes (word 1)
        parts.append(sig_offset.to_bytes(32, "big"))

        # -- Struct encoding --
        # 5 static fields
        parts.append(from_addr)
        parts.append(to_addr)
        parts.append(value_bytes)
        parts.append(gas_bytes)
        parts.append(nonce_bytes)
        # Offset to `data` within struct (relative to struct start) = 6*32 = 192
        parts.append((192).to_bytes(32, "big"))
        # Length of data
        parts.append(len(data_raw).to_bytes(32, "big"))
        # data (padded to 32 bytes)
        parts.append(data_raw + b"\x00" * (data_padded_len - len(data_raw)))

        # -- Signature bytes encoding --
        sig_padded_len = ((len(sig_bytes) + 31) // 32) * 32
        parts.append(len(sig_bytes).to_bytes(32, "big"))
        parts.append(sig_bytes + b"\x00" * (sig_padded_len - len(sig_bytes)))

        return "0x" + b"".join(parts).hex()

    async def relay_batch(
        self, requests: list[ForwardRequest]
    ) -> list[MetaTransactionResult]:
        """
        Relay multiple meta-transactions in parallel.

        Args:
            requests: List of signed ForwardRequests

        Returns:
            List of MetaTransactionResults
        """
        results = []
        for request in requests:
            try:
                result = await self.relay(request)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to relay meta-transaction: {e}")
                results.append(
                    MetaTransactionResult(
                        tx_hash="",
                        relayer_address=self.relayer_address,
                        user_address=request.from_address,
                        target_address=request.to_address,
                        success=False,
                        error=str(e),
                    )
                )
        return results


# Utility functions

def create_transfer_meta_tx(
    from_address: str,
    to_address: str,
    token_address: str,
    amount_wei: int,
    nonce: int,
) -> ForwardRequest:
    """
    Create a ForwardRequest for an ERC20 transfer.

    Args:
        from_address: Sender's address
        to_address: Recipient's address
        token_address: ERC20 token contract address
        amount_wei: Amount in smallest token unit
        nonce: User's nonce in the forwarder

    Returns:
        ForwardRequest ready to be signed
    """
    # Encode ERC20 transfer(address,uint256)
    # Function selector: 0xa9059cbb
    selector = bytes.fromhex("a9059cbb")
    to_bytes = bytes.fromhex(to_address[2:].lower().zfill(64))
    amount_bytes = amount_wei.to_bytes(32, byteorder="big")
    transfer_data = selector + to_bytes + amount_bytes

    return ForwardRequest(
        from_address=from_address,
        to_address=token_address,
        value=0,
        gas=100000,  # Standard ERC20 transfer gas
        nonce=nonce,
        data=transfer_data,
    )


def is_meta_tx_supported(chain: str) -> bool:
    """
    Check if meta-transactions are supported on a chain.

    Args:
        chain: Chain name (e.g., "base", "polygon")

    Returns:
        True if forwarder contract is deployed
    """
    addresses = MetaTransactionRelayer.get_forwarder_addresses()
    forwarder = addresses.get(chain.lower(), "")
    return bool(forwarder) and forwarder != "0x" + "0" * 40
