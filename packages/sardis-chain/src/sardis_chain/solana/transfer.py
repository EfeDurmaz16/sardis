"""SPL token transfer builder for Solana using solders."""
from __future__ import annotations

import base64
import logging
import struct
from dataclasses import dataclass

from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.message import MessageV0
from solders.pubkey import Pubkey

from .client import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    SYSTEM_PROGRAM_ID,
    SYSVAR_RENT_PUBKEY,
    TOKEN_DECIMALS,
    TOKEN_PROGRAM_ID,
    SolanaClient,
    derive_ata,
)

logger = logging.getLogger(__name__)


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


@dataclass
class PreparedSolanaTransaction:
    """A prepared Solana transaction ready for MPC signing."""
    message_base64: str
    blockhash: str
    sender: str
    recipient: str
    mint: str
    amount: int
    create_recipient_ata: bool
    instructions_count: int


def _build_create_ata_instruction(
    payer: Pubkey, owner: Pubkey, mint: Pubkey
) -> Instruction:
    """Build a CreateAssociatedTokenAccount instruction."""
    ata = derive_ata(owner, mint)
    return Instruction(
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
        accounts=[
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
        ],
        data=b"",  # CreateAssociatedTokenAccount has no data
    )


def _build_spl_transfer_checked_instruction(
    source_ata: Pubkey,
    mint: Pubkey,
    dest_ata: Pubkey,
    owner: Pubkey,
    amount: int,
    decimals: int,
) -> Instruction:
    """Build an SPL Token TransferChecked instruction.

    TransferChecked (instruction index 12) verifies decimals on-chain,
    preventing accidental wrong-decimal transfers.
    """
    # TransferChecked: u8(12) + u64(amount) + u8(decimals)
    data = struct.pack("<BQB", 12, amount, decimals)

    return Instruction(
        program_id=TOKEN_PROGRAM_ID,
        accounts=[
            AccountMeta(pubkey=source_ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=dest_ata, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=True, is_writable=False),
        ],
        data=data,
    )


async def get_or_create_ata(
    client: SolanaClient, owner: str, mint: str
) -> tuple[str, bool]:
    """Get the ATA for owner+mint.

    Returns (ata_address, needs_creation).
    """
    # First try RPC lookup (handles non-canonical ATAs)
    accounts = await client.get_token_accounts_by_owner(owner, mint)
    if accounts:
        return accounts[0]["pubkey"], False

    # Derive the canonical ATA
    ata = derive_ata(Pubkey.from_string(owner), Pubkey.from_string(mint))
    return str(ata), True


async def build_spl_transfer(
    client: SolanaClient,
    params: SolanaTransferParams,
) -> PreparedSolanaTransaction:
    """Build an SPL token transfer transaction ready for signing.

    Returns a PreparedSolanaTransaction with a serialized message
    that can be sent to Turnkey MPC for ed25519 signing.
    """
    logger.info(
        "Building SPL transfer: %s -> %s, mint=%s, amount=%d",
        params.sender, params.recipient, params.mint, params.amount,
    )

    sender_pk = Pubkey.from_string(params.sender)
    recipient_pk = Pubkey.from_string(params.recipient)
    mint_pk = Pubkey.from_string(params.mint)
    decimals = params.decimals or TOKEN_DECIMALS.get(params.mint, 6)

    # Resolve ATAs
    sender_ata_str, sender_needs_create = await get_or_create_ata(
        client, params.sender, params.mint
    )
    if sender_needs_create:
        raise ValueError(
            f"Sender {params.sender} has no token account for mint {params.mint}. "
            f"Cannot transfer without a funded token account."
        )
    sender_ata = Pubkey.from_string(sender_ata_str)

    recipient_ata_str, recipient_needs_create = await get_or_create_ata(
        client, params.recipient, params.mint
    )
    recipient_ata = Pubkey.from_string(recipient_ata_str)

    # Build instructions
    instructions: list[Instruction] = []

    if recipient_needs_create:
        instructions.append(
            _build_create_ata_instruction(sender_pk, recipient_pk, mint_pk)
        )

    instructions.append(
        _build_spl_transfer_checked_instruction(
            source_ata=sender_ata,
            mint=mint_pk,
            dest_ata=recipient_ata,
            owner=sender_pk,
            amount=params.amount,
            decimals=decimals,
        )
    )

    # Get recent blockhash
    blockhash = await client.get_latest_blockhash()

    # Build VersionedMessage (v0 for address lookup table support)
    message = MessageV0.try_compile(
        payer=sender_pk,
        instructions=instructions,
        address_lookup_table_accounts=[],
        recent_blockhash=Hash.from_string(blockhash),
    )

    # Serialize message for signing
    message_bytes = bytes(message)
    message_base64 = base64.b64encode(message_bytes).decode("ascii")

    return PreparedSolanaTransaction(
        message_base64=message_base64,
        blockhash=blockhash,
        sender=params.sender,
        recipient=params.recipient,
        mint=params.mint,
        amount=params.amount,
        create_recipient_ata=recipient_needs_create,
        instructions_count=len(instructions),
    )


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
