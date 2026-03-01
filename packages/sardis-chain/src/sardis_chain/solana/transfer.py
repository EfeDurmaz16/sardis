"""SPL token transfer builder for Solana."""
from __future__ import annotations

import base64
import logging
import struct
from dataclasses import dataclass
from typing import Any

from .client import SolanaClient, TOKEN_DECIMALS

logger = logging.getLogger(__name__)

# Solana program IDs
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"


@dataclass
class SolanaTransferParams:
    """Parameters for an SPL token transfer."""
    sender: str
    recipient: str
    mint: str
    amount: int  # In token minor units (e.g., 1 USDC = 1_000_000)
    decimals: int = 6


@dataclass
class SolanaTransferResult:
    """Result of a Solana transfer."""
    signature: str
    sender: str
    recipient: str
    mint: str
    amount: int
    confirmed: bool = False


def derive_ata(owner: str, mint: str) -> str:
    """Derive the Associated Token Account address.

    This is a simplified derivation -- in production this uses
    the findProgramAddress algorithm. For now, we rely on the
    RPC to resolve ATAs via getTokenAccountsByOwner.
    """
    # NOTE: Actual PDA derivation requires ed25519 point operations.
    # We use the RPC-based approach in get_or_create_ata() instead.
    raise NotImplementedError(
        "Use get_or_create_ata() with an RPC client for ATA resolution"
    )


async def get_or_create_ata(
    client: SolanaClient, owner: str, mint: str
) -> str:
    """Get the Associated Token Account for owner+mint, or indicate it needs creation.

    Returns the ATA address if it exists.
    Raises ValueError if ATA doesn't exist (caller should create it).
    """
    accounts = await client.get_token_accounts_by_owner(owner, mint)
    if accounts:
        return accounts[0]["pubkey"]
    raise ValueError(
        f"No token account found for owner={owner}, mint={mint}. "
        f"ATA must be created before transfer."
    )


async def build_spl_transfer(
    client: SolanaClient,
    params: SolanaTransferParams,
) -> dict[str, Any]:
    """Build an SPL token transfer transaction.

    Returns a dict with transaction details ready for signing.
    The actual signing happens via Turnkey MPC (ed25519).
    """
    logger.info(
        "Building SPL transfer: %s -> %s, mint=%s, amount=%d",
        params.sender, params.recipient, params.mint, params.amount,
    )

    # Resolve sender's token account
    sender_ata = await get_or_create_ata(client, params.sender, params.mint)

    # Resolve recipient's token account (may need creation)
    try:
        recipient_ata = await get_or_create_ata(client, params.recipient, params.mint)
        create_ata = False
    except ValueError:
        # Recipient ATA doesn't exist -- include creation instruction
        recipient_ata = None
        create_ata = True

    # Get recent blockhash
    blockhash = await client.get_latest_blockhash()

    decimals = params.decimals or TOKEN_DECIMALS.get(params.mint, 6)

    return {
        "type": "spl_transfer",
        "sender": params.sender,
        "sender_ata": sender_ata,
        "recipient": params.recipient,
        "recipient_ata": recipient_ata,
        "create_recipient_ata": create_ata,
        "mint": params.mint,
        "amount": params.amount,
        "decimals": decimals,
        "blockhash": blockhash,
        "programs": {
            "token": TOKEN_PROGRAM_ID,
            "ata": ASSOCIATED_TOKEN_PROGRAM_ID,
            "system": SYSTEM_PROGRAM_ID,
        },
    }


async def execute_spl_transfer(
    client: SolanaClient,
    signed_tx_base64: str,
    params: SolanaTransferParams,
) -> SolanaTransferResult:
    """Execute a signed SPL transfer and confirm it."""
    signature = await client.send_raw_transaction(signed_tx_base64)

    confirmed = await client.confirm_transaction(signature)

    return SolanaTransferResult(
        signature=signature,
        sender=params.sender,
        recipient=params.recipient,
        mint=params.mint,
        amount=params.amount,
        confirmed=confirmed,
    )
