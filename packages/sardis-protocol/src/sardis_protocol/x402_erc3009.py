"""ERC-3009 TransferWithAuthorization support for x402 payments.

ERC-3009 enables gas-free USDC transfers via meta-transactions with EIP-712 signatures.
This module provides authorization building, validation, and encoding for contract calls.

Reference: https://eips.ethereum.org/EIPS/eip-3009
USDC Implementation: https://github.com/circlefin/stablecoin-evm
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


USDC_TRANSFER_WITH_AUTHORIZATION_SELECTOR = "0xe3ee160e"

# EIP-712 domain fields for USDC
EIP712_DOMAIN_TYPE = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
    {"name": "verifyingContract", "type": "address"},
]

TRANSFER_WITH_AUTHORIZATION_TYPE = [
    {"name": "from", "type": "address"},
    {"name": "to", "type": "address"},
    {"name": "value", "type": "uint256"},
    {"name": "validAfter", "type": "uint256"},
    {"name": "validBefore", "type": "uint256"},
    {"name": "nonce", "type": "bytes32"},
]


@dataclass(slots=True)
class ERC3009Authorization:
    """ERC-3009 TransferWithAuthorization parameters.

    Attributes:
        from_address: Payer address (0x...)
        to_address: Payee address (0x...)
        value: Amount in smallest unit (e.g., USDC has 6 decimals)
        valid_after: Unix timestamp - authorization not valid before this time
        valid_before: Unix timestamp - authorization not valid after this time
        nonce: Unique nonce (hex string, 32 bytes when decoded)
        v: Signature v component (recovery id)
        r: Signature r component (hex string)
        s: Signature s component (hex string)
    """
    from_address: str
    to_address: str
    value: int
    valid_after: int
    valid_before: int
    nonce: str
    v: int = 0
    r: str = ""
    s: str = ""


def build_transfer_authorization(
    from_addr: str,
    to_addr: str,
    value: int,
    valid_after: int,
    valid_before: int,
    nonce: str,
) -> dict[str, Any]:
    """Build EIP-712 typed data for TransferWithAuthorization.

    Returns a dictionary containing the EIP-712 typed data structure that must
    be signed by the payer. The signature components (v, r, s) should then be
    added to create a complete ERC3009Authorization.

    Args:
        from_addr: Payer address (0x-prefixed hex)
        to_addr: Payee address (0x-prefixed hex)
        value: Transfer amount in token's smallest unit
        valid_after: Unix timestamp when authorization becomes valid
        valid_before: Unix timestamp when authorization expires
        nonce: Unique hex string (should be 32 bytes when decoded)

    Returns:
        EIP-712 typed data dict with keys: types, primaryType, domain, message
    """
    return {
        "types": {
            "EIP712Domain": EIP712_DOMAIN_TYPE,
            "TransferWithAuthorization": TRANSFER_WITH_AUTHORIZATION_TYPE,
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": "USD Coin",
            "version": "2",
            "chainId": 1,  # Must be set to actual chain ID before signing
            "verifyingContract": "0x...",  # Must be set to USDC contract address
        },
        "message": {
            "from": from_addr,
            "to": to_addr,
            "value": str(value),
            "validAfter": str(valid_after),
            "validBefore": str(valid_before),
            "nonce": nonce,
        },
    }


def validate_authorization_timing(
    auth: ERC3009Authorization,
    now: int | None = None,
) -> tuple[bool, str | None]:
    """Check that authorization timing is valid.

    Validates that:
    - valid_after is not in the future
    - valid_before is not in the past
    - valid_after < valid_before

    Args:
        auth: Authorization to validate
        now: Current unix timestamp (defaults to time.time())

    Returns:
        Tuple of (is_valid, error_reason).
        If valid, returns (True, None).
        If invalid, returns (False, "reason_string").
    """
    current_time = now if now is not None else int(time.time())

    if auth.valid_after >= auth.valid_before:
        return False, "valid_after_must_be_before_valid_before"

    if current_time < auth.valid_after:
        return False, "authorization_not_yet_valid"

    if current_time >= auth.valid_before:
        return False, "authorization_expired"

    return True, None


def encode_authorization_params(auth: ERC3009Authorization) -> bytes:
    """ABI-encode authorization parameters for USDC contract call.

    Encodes parameters for:
    transferWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    )

    Args:
        auth: Complete authorization with signature components

    Returns:
        ABI-encoded bytes ready to append to function selector
    """
    # Address encoding: left-pad to 32 bytes
    from_bytes = _address_to_bytes32(auth.from_address)
    to_bytes = _address_to_bytes32(auth.to_address)

    # uint256 encoding: big-endian 32 bytes
    value_bytes = _int_to_uint256(auth.value)
    valid_after_bytes = _int_to_uint256(auth.valid_after)
    valid_before_bytes = _int_to_uint256(auth.valid_before)

    # bytes32 nonce: ensure it's 32 bytes
    nonce_bytes = _hex_to_bytes32(auth.nonce)

    # uint8 v: pad to 32 bytes
    v_bytes = _int_to_uint256(auth.v)

    # bytes32 signature components
    r_bytes = _hex_to_bytes32(auth.r)
    s_bytes = _hex_to_bytes32(auth.s)

    return (
        from_bytes
        + to_bytes
        + value_bytes
        + valid_after_bytes
        + valid_before_bytes
        + nonce_bytes
        + v_bytes
        + r_bytes
        + s_bytes
    )


def _address_to_bytes32(address: str) -> bytes:
    """Convert 0x-prefixed address to 32-byte padded representation.

    Args:
        address: Ethereum address (0x-prefixed, 20 bytes)

    Returns:
        32 bytes with address left-padded with zeros
    """
    addr = address.lower()
    if addr.startswith("0x"):
        addr = addr[2:]

    addr_bytes = bytes.fromhex(addr)
    if len(addr_bytes) != 20:
        raise ValueError(f"invalid_address_length: expected 20 bytes, got {len(addr_bytes)}")

    # Left-pad to 32 bytes (addresses are padded on the left in ABI encoding)
    return bytes(12) + addr_bytes


def _int_to_uint256(value: int) -> bytes:
    """Convert integer to uint256 (32 bytes, big-endian).

    Args:
        value: Non-negative integer

    Returns:
        32 bytes representing the value
    """
    if value < 0:
        raise ValueError("uint256_must_be_non_negative")

    return value.to_bytes(32, byteorder="big")


def _hex_to_bytes32(hex_string: str) -> bytes:
    """Convert hex string to exactly 32 bytes.

    Args:
        hex_string: Hex string (with or without 0x prefix)

    Returns:
        Exactly 32 bytes
    """
    hex_str = hex_string.lower()
    if hex_str.startswith("0x"):
        hex_str = hex_str[2:]

    result = bytes.fromhex(hex_str)

    if len(result) > 32:
        raise ValueError(f"hex_too_long: expected max 32 bytes, got {len(result)}")

    # Left-pad to 32 bytes if shorter
    if len(result) < 32:
        result = bytes(32 - len(result)) + result

    return result


__all__ = [
    "USDC_TRANSFER_WITH_AUTHORIZATION_SELECTOR",
    "EIP712_DOMAIN_TYPE",
    "TRANSFER_WITH_AUTHORIZATION_TYPE",
    "ERC3009Authorization",
    "build_transfer_authorization",
    "validate_authorization_timing",
    "encode_authorization_params",
]
