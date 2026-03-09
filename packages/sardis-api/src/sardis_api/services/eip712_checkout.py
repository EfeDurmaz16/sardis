"""EIP-712 typed data definitions for Sardis Checkout wallet connection.

Provides session-bound, chain-bound typed data signing to replace
freeform EIP-191 message signing for the connect-external flow.

The typed data binds to:
- sessionId: prevents cross-session replay
- walletAddress: prevents address spoofing
- chainId: prevents cross-chain replay
- nonce: prevents same-session replay

Frontend calls `eth_signTypedData_v4` with the structure returned by
`build_connect_typed_data()`, and the backend verifies via
`verify_eip712_connect_signature()`.
"""
from __future__ import annotations

import logging
import os
import secrets
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data

logger = logging.getLogger(__name__)

# Chain name → chain ID mapping for checkout
CHECKOUT_CHAIN_IDS: dict[str, int] = {
    "base": 8453,
    "base_sepolia": 84532,
    "ethereum": 1,
    "polygon": 137,
    "arbitrum": 42161,
    "optimism": 10,
}

# EIP-712 domain constants
EIP712_DOMAIN_NAME = "Sardis Checkout"
EIP712_DOMAIN_VERSION = "1"

# Type definitions for the connect message
CONNECT_TYPES = {
    "SardisCheckoutConnect": [
        {"name": "sessionId", "type": "string"},
        {"name": "walletAddress", "type": "address"},
        {"name": "chainId", "type": "uint256"},
        {"name": "nonce", "type": "string"},
    ],
}

# Type definitions for the payment approval message (stronger than connect)
PAYMENT_APPROVAL_TYPES = {
    "SardisPaymentApproval": [
        {"name": "sessionId", "type": "string"},
        {"name": "walletAddress", "type": "address"},
        {"name": "chainId", "type": "uint256"},
        {"name": "nonce", "type": "string"},
        {"name": "merchantDomain", "type": "string"},
        {"name": "amount", "type": "string"},
        {"name": "token", "type": "string"},
        {"name": "destination", "type": "address"},
        {"name": "cartHash", "type": "bytes32"},
        {"name": "originHash", "type": "bytes32"},
    ],
}


def build_payment_approval_typed_data(
    session_id: str,
    wallet_address: str,
    merchant_domain: str,
    amount: str,
    token: str,
    destination: str,
    cart_hash: str,
    origin_hash: str,
    chain_id: int | None = None,
    nonce: str | None = None,
) -> dict[str, Any]:
    """Build EIP-712 typed data for payment approval.

    This is stronger than the connect message — it binds the wallet's
    approval to the exact payment parameters, cart contents, and page origin.
    A prompt injection that changes any of these fields will produce a
    different hash and the signature won't verify.
    """
    if chain_id is None:
        chain_id = get_checkout_chain_id()
    if nonce is None:
        nonce = generate_nonce()

    # Pad hashes to bytes32 if needed
    cart_hash_bytes = _to_bytes32(cart_hash)
    origin_hash_bytes = _to_bytes32(origin_hash)

    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            **PAYMENT_APPROVAL_TYPES,
        },
        "primaryType": "SardisPaymentApproval",
        "domain": {
            "name": EIP712_DOMAIN_NAME,
            "version": EIP712_DOMAIN_VERSION,
            "chainId": chain_id,
        },
        "message": {
            "sessionId": session_id,
            "walletAddress": wallet_address,
            "chainId": chain_id,
            "nonce": nonce,
            "merchantDomain": merchant_domain,
            "amount": amount,
            "token": token,
            "destination": destination,
            "cartHash": cart_hash_bytes,
            "originHash": origin_hash_bytes,
        },
    }


def _to_bytes32(hex_str: str) -> str:
    """Convert a hex hash string to 0x-prefixed bytes32 format."""
    clean = hex_str.replace("0x", "")[:64]
    return "0x" + clean.ljust(64, "0")


def verify_eip712_payment_approval(
    signature: str,
    session_id: str,
    wallet_address: str,
    merchant_domain: str,
    amount: str,
    token: str,
    destination: str,
    cart_hash: str,
    origin_hash: str,
    chain_id: int,
    nonce: str,
) -> tuple[bool, str | None]:
    """Verify an EIP-712 payment approval signature.

    This verifies that the wallet owner approved this exact payment
    with this exact cart, origin, and merchant binding.
    """
    try:
        typed_data = build_payment_approval_typed_data(
            session_id=session_id,
            wallet_address=wallet_address,
            merchant_domain=merchant_domain,
            amount=amount,
            token=token,
            destination=destination,
            cart_hash=cart_hash,
            origin_hash=origin_hash,
            chain_id=chain_id,
            nonce=nonce,
        )
        signable = encode_typed_data(full_message=typed_data)
        recovered = Account.recover_message(signable, signature=signature)
    except Exception as e:
        logger.warning("EIP-712 payment approval verification failed: %s", e)
        return False, f"Invalid EIP-712 signature: {e}"

    if recovered.lower() != wallet_address.lower():
        return False, (
            f"Recovered address {recovered} does not match "
            f"claimed address {wallet_address}"
        )

    return True, None


def get_checkout_chain_id() -> int:
    """Resolve the chain ID for the current checkout chain configuration."""
    chain_name = os.getenv("SARDIS_CHECKOUT_CHAIN", "base")
    chain_id = CHECKOUT_CHAIN_IDS.get(chain_name)
    if chain_id is None:
        raise ValueError(f"Unknown checkout chain: {chain_name}")
    return chain_id


def generate_nonce() -> str:
    """Generate a cryptographically random nonce for replay protection."""
    return secrets.token_hex(16)


def build_connect_typed_data(
    session_id: str,
    wallet_address: str,
    chain_id: int | None = None,
    nonce: str | None = None,
) -> dict[str, Any]:
    """Build the EIP-712 typed data structure for wallet connection.

    Returns the full typed data dict that the frontend passes to
    ``eth_signTypedData_v4``.

    Args:
        session_id: The checkout session ID to bind to.
        wallet_address: The wallet address connecting.
        chain_id: Override chain ID. If None, uses checkout chain config.
        nonce: Override nonce. If None, generates a random one.

    Returns:
        Dict with keys: types, primaryType, domain, message.
    """
    if chain_id is None:
        chain_id = get_checkout_chain_id()
    if nonce is None:
        nonce = generate_nonce()

    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            **CONNECT_TYPES,
        },
        "primaryType": "SardisCheckoutConnect",
        "domain": {
            "name": EIP712_DOMAIN_NAME,
            "version": EIP712_DOMAIN_VERSION,
            "chainId": chain_id,
        },
        "message": {
            "sessionId": session_id,
            "walletAddress": wallet_address,
            "chainId": chain_id,
            "nonce": nonce,
        },
    }


def verify_eip712_connect_signature(
    signature: str,
    session_id: str,
    wallet_address: str,
    chain_id: int,
    nonce: str,
) -> tuple[bool, str | None]:
    """Verify an EIP-712 typed data signature for wallet connection.

    Args:
        signature: The hex signature from eth_signTypedData_v4.
        session_id: Expected session ID.
        wallet_address: Expected wallet address (the claimed signer).
        chain_id: Expected chain ID.
        nonce: The nonce that was signed.

    Returns:
        (is_valid, error_message). error_message is None on success.
    """
    try:
        typed_data = build_connect_typed_data(
            session_id=session_id,
            wallet_address=wallet_address,
            chain_id=chain_id,
            nonce=nonce,
        )
        signable = encode_typed_data(full_message=typed_data)
        recovered = Account.recover_message(signable, signature=signature)
    except Exception as e:
        logger.warning("EIP-712 signature verification failed: %s", e)
        return False, f"Invalid EIP-712 signature: {e}"

    if recovered.lower() != wallet_address.lower():
        return False, (
            f"Recovered address {recovered} does not match "
            f"claimed address {wallet_address}"
        )

    return True, None
