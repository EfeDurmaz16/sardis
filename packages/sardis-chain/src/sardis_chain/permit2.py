"""Permit2 (Uniswap) helper for time-bound token approvals.

Permit2 provides signature-based token approvals with expiration,
eliminating the risk of hanging unlimited approvals on agent wallets.

Permit2 is:
- Immutable, non-upgradable, no admin
- Audited, $3M bug bounty
- Deployed at the same address on all EVM chains
- Used by Uniswap, 1inch, Paraswap, and many others

References:
- https://github.com/Uniswap/permit2
- https://docs.uniswap.org/contracts/permit2/overview
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from web3 import Web3
from eth_abi import encode


# Canonical Permit2 address — same on ALL EVM chains (CREATE2)
PERMIT2_ADDRESS = "0x000000000022D473030F116dDEE9F6B43aC78BA3"

# EIP-712 domain
PERMIT2_DOMAIN_NAME = "Permit2"

# Type hashes
_PERMIT_SINGLE_TYPEHASH = Web3.keccak(
    text="PermitSingle(PermitDetails details,address spender,uint256 sigDeadline)PermitDetails(address token,uint160 amount,uint48 expiration,uint48 nonce)"
)

_PERMIT_DETAILS_TYPEHASH = Web3.keccak(
    text="PermitDetails(address token,uint160 amount,uint48 expiration,uint48 nonce)"
)

_PERMIT_BATCH_TYPEHASH = Web3.keccak(
    text="PermitBatch(PermitDetails[] details,address spender,uint256 sigDeadline)PermitDetails(address token,uint160 amount,uint48 expiration,uint48 nonce)"
)

# Function selectors
_APPROVE_SELECTOR = Web3.keccak(text="approve(address,address,uint160,uint48)")[:4]
_PERMIT_SELECTOR = Web3.keccak(
    text="permit(address,((address,uint160,uint48,uint48),address,uint256),bytes)"
)[:4]
_TRANSFER_FROM_SELECTOR = Web3.keccak(
    text="transferFrom(address,address,uint160,address)"
)[:4]
_ALLOWANCE_SELECTOR = Web3.keccak(text="allowance(address,address,address)")[:4]


@dataclass
class PermitDetails:
    """Token approval details for Permit2."""
    token: str
    amount: int  # uint160
    expiration: int  # uint48 timestamp
    nonce: int  # uint48


@dataclass
class PermitSingle:
    """Single token permit for Permit2 signature."""
    details: PermitDetails
    spender: str
    sig_deadline: int  # uint256 timestamp


def encode_approve(token: str, spender: str, amount: int, expiration: int) -> str:
    """Encode Permit2.approve() calldata.

    Sets an on-chain allowance for a spender on a specific token,
    with an expiration timestamp.

    Args:
        token: ERC-20 token address
        spender: Address allowed to spend
        amount: Maximum amount (uint160)
        expiration: Unix timestamp when approval expires (uint48)

    Returns:
        Hex-encoded calldata
    """
    params = encode(
        ["address", "address", "uint160", "uint48"],
        [
            Web3.to_checksum_address(token),
            Web3.to_checksum_address(spender),
            amount,
            expiration,
        ],
    )
    return "0x" + (_APPROVE_SELECTOR + params).hex()


def encode_transfer_from(
    from_addr: str, to_addr: str, amount: int, token: str
) -> str:
    """Encode Permit2.transferFrom() calldata.

    Transfers tokens from one address to another using Permit2 allowance.

    Args:
        from_addr: Source address (must have approved Permit2)
        to_addr: Destination address
        amount: Amount to transfer (uint160)
        token: ERC-20 token address

    Returns:
        Hex-encoded calldata
    """
    params = encode(
        ["address", "address", "uint160", "address"],
        [
            Web3.to_checksum_address(from_addr),
            Web3.to_checksum_address(to_addr),
            amount,
            Web3.to_checksum_address(token),
        ],
    )
    return "0x" + (_TRANSFER_FROM_SELECTOR + params).hex()


def encode_check_allowance(owner: str, token: str, spender: str) -> str:
    """Encode Permit2.allowance() view call.

    Returns (uint160 amount, uint48 expiration, uint48 nonce).

    Args:
        owner: Token owner address
        token: ERC-20 token address
        spender: Spender address

    Returns:
        Hex-encoded calldata for eth_call
    """
    params = encode(
        ["address", "address", "address"],
        [
            Web3.to_checksum_address(owner),
            Web3.to_checksum_address(token),
            Web3.to_checksum_address(spender),
        ],
    )
    return "0x" + (_ALLOWANCE_SELECTOR + params).hex()


def build_permit_single_hash(
    permit: PermitSingle,
    chain_id: int,
) -> bytes:
    """Build EIP-712 typed data hash for PermitSingle.

    This hash needs to be signed by the token owner via MPC.

    Args:
        permit: PermitSingle struct
        chain_id: Chain ID for domain separator

    Returns:
        32-byte hash to sign
    """
    # Domain separator
    domain_separator = Web3.keccak(
        encode(
            ["bytes32", "bytes32", "uint256", "address"],
            [
                Web3.keccak(text="EIP712Domain(string name,uint256 chainId,address verifyingContract)"),
                Web3.keccak(text=PERMIT2_DOMAIN_NAME),
                chain_id,
                Web3.to_checksum_address(PERMIT2_ADDRESS),
            ],
        )
    )

    # PermitDetails hash
    details_hash = Web3.keccak(
        encode(
            ["bytes32", "address", "uint160", "uint48", "uint48"],
            [
                _PERMIT_DETAILS_TYPEHASH,
                Web3.to_checksum_address(permit.details.token),
                permit.details.amount,
                permit.details.expiration,
                permit.details.nonce,
            ],
        )
    )

    # PermitSingle hash
    struct_hash = Web3.keccak(
        encode(
            ["bytes32", "bytes32", "address", "uint256"],
            [
                _PERMIT_SINGLE_TYPEHASH,
                details_hash,
                Web3.to_checksum_address(permit.spender),
                permit.sig_deadline,
            ],
        )
    )

    # EIP-712 final hash
    return Web3.keccak(
        b"\x19\x01" + domain_separator + struct_hash
    )


def default_expiration(hours: int = 24) -> int:
    """Generate an expiration timestamp N hours from now."""
    return int(time.time()) + (hours * 3600)
