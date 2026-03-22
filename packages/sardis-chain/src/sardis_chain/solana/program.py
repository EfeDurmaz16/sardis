"""Sardis Solana Anchor program client.

Builds Anchor instructions (8-byte discriminator + borsh-serialized args),
derives wallet/merchant/token PDAs, and maps Anchor error codes to Python
reason strings matching the spending_policy.py engine.

Two layers of instruction helpers:
  - ``build_*_data()`` — return raw ``bytes`` (discriminator + borsh args).
    The caller is responsible for building the full ``Instruction``.
  - ``build_*_ix()`` — return a complete ``solders.instruction.Instruction``
    with the correct account metas.  These are the primary entry points used
    by the SolanaExecutor.
"""
from __future__ import annotations

import hashlib
import logging
import struct
from dataclasses import dataclass

from solders.instruction import AccountMeta, Instruction
from solders.pubkey import Pubkey

from .client import TOKEN_PROGRAM_ID, SYSTEM_PROGRAM_ID, SYSVAR_RENT_PUBKEY

logger = logging.getLogger(__name__)

# ── Program ID ─────────────────────────────────────────────────────────────
# Placeholder — updated after devnet deployment.
SARDIS_WALLET_PROGRAM_ID = "5shhNxoGDhGe7XotwG5usrZ21K5mZdj3q2oGZC7cYpvN"

# ── PDA Seeds ──────────────────────────────────────────────────────────────
WALLET_SEED = b"sardis_wallet"
MERCHANT_SEED = b"merchants"
TOKEN_SEED = b"tokens"

# ── Trust Levels (mirrors Rust) ────────────────────────────────────────────
TRUST_LOW = 0
TRUST_MEDIUM = 1
TRUST_HIGH = 2
TRUST_UNLIMITED = 3

# ── Merchant Rule Types ────────────────────────────────────────────────────
RULE_ALLOW = 0
RULE_DENY = 1

# ── Anchor Error Code → Python reason_code mapping ────────────────────────
ERROR_CODE_MAP: dict[int, str] = {
    6000: "amount_must_be_positive",
    6001: "per_transaction_limit",
    6002: "total_limit_exceeded",
    6003: "daily_limit_exceeded",
    6004: "weekly_limit_exceeded",
    6005: "monthly_limit_exceeded",
    6006: "merchant_denied",
    6007: "merchant_not_allowlisted",
    6008: "merchant_cap_exceeded",
    6009: "token_not_allowlisted",
    6010: "wallet_paused",
    6011: "cosigner_required",
    6012: "cosign_daily_limit_exceeded",
    6013: "merchant_registry_full",
    6014: "merchant_not_found",
    6015: "token_list_full",
    6016: "token_not_found",
    6017: "invalid_trust_level",
    6018: "wallet_not_paused",
    6019: "token_already_listed",
    6020: "merchant_already_listed",
}


def anchor_error_to_reason(error_code: int) -> str:
    """Map an Anchor custom error code to Python spending_policy reason_code."""
    return ERROR_CODE_MAP.get(error_code, f"unknown_program_error_{error_code}")


# ── Instruction Discriminator ──────────────────────────────────────────────
def _discriminator(namespace: str, name: str) -> bytes:
    """Compute Anchor 8-byte instruction discriminator.

    SHA256("global:<snake_case_name>")[:8]
    """
    preimage = f"{namespace}:{name}"
    return hashlib.sha256(preimage.encode()).digest()[:8]


# Pre-computed discriminators for all instructions.
DISC_INITIALIZE_WALLET = _discriminator("global", "initialize_wallet")
DISC_EXECUTE_TRANSFER = _discriminator("global", "execute_transfer")
DISC_EXECUTE_COSIGNED = _discriminator("global", "execute_cosigned_transfer")
DISC_UPDATE_POLICY = _discriminator("global", "update_policy")
DISC_FREEZE_WALLET = _discriminator("global", "freeze_wallet")
DISC_UNFREEZE_WALLET = _discriminator("global", "unfreeze_wallet")
DISC_ADD_MERCHANT_RULE = _discriminator("global", "add_merchant_rule")
DISC_REMOVE_MERCHANT_RULE = _discriminator("global", "remove_merchant_rule")
DISC_SET_ALLOWLIST_MODE = _discriminator("global", "set_allowlist_mode")
DISC_ADD_TOKEN = _discriminator("global", "add_token")
DISC_REMOVE_TOKEN = _discriminator("global", "remove_token")
DISC_SET_TOKEN_ENFORCED = _discriminator("global", "set_token_allowlist_enforced")
DISC_UPDATE_AUTHORITY = _discriminator("global", "update_authority")
DISC_CLOSE_WALLET = _discriminator("global", "close_wallet")


# ── PDA Derivation ─────────────────────────────────────────────────────────
@dataclass
class WalletPDAs:
    """Derived PDA addresses for an agent wallet."""
    wallet: str
    wallet_bump: int
    merchant_registry: str
    merchant_registry_bump: int
    token_allowlist: str
    token_allowlist_bump: int


def _find_program_address(seeds: list[bytes], program_id: str) -> tuple[str, int]:
    """Derive a Solana PDA.

    Uses the same algorithm as Pubkey.findProgramAddress:
    for bump in 255..0:
        candidate = SHA256(seeds + [bump] + program_id + "ProgramDerivedAddress")
        if candidate is NOT on ed25519 curve -> return (candidate, bump)
    """
    pid = Pubkey.from_string(program_id)
    pda, bump = Pubkey.find_program_address(seeds, pid)
    return str(pda), bump


def derive_wallet_pdas(
    owner: str,
    program_id: str = SARDIS_WALLET_PROGRAM_ID,
) -> WalletPDAs:
    """Derive all three PDA addresses for an agent wallet.

    Seeds:
      wallet:            [b"sardis_wallet", owner_pubkey]
      merchant_registry: [b"merchants", wallet_pda]
      token_allowlist:   [b"tokens", wallet_pda]
    """
    owner_bytes = bytes(Pubkey.from_string(owner))

    wallet_addr, wallet_bump = _find_program_address(
        [WALLET_SEED, owner_bytes], program_id
    )

    wallet_bytes = bytes(Pubkey.from_string(wallet_addr))

    merchant_addr, merchant_bump = _find_program_address(
        [MERCHANT_SEED, wallet_bytes], program_id
    )
    token_addr, token_bump = _find_program_address(
        [TOKEN_SEED, wallet_bytes], program_id
    )

    return WalletPDAs(
        wallet=wallet_addr,
        wallet_bump=wallet_bump,
        merchant_registry=merchant_addr,
        merchant_registry_bump=merchant_bump,
        token_allowlist=token_addr,
        token_allowlist_bump=token_bump,
    )


# ── Instruction Data Builders ──────────────────────────────────────────────
# These return raw bytes (discriminator + borsh args) for building Solana
# TransactionInstructions. The caller is responsible for passing the correct
# account metas.

def _encode_option_u64(value: int | None) -> bytes:
    """Borsh-encode Option<u64>: 0x00 for None, 0x01 + le_u64 for Some."""
    if value is None:
        return b"\x00"
    return b"\x01" + struct.pack("<Q", value)


def _encode_option_u8(value: int | None) -> bytes:
    """Borsh-encode Option<u8>."""
    if value is None:
        return b"\x00"
    return b"\x01" + struct.pack("<B", value)


def _encode_option_pubkey(value: str | None) -> bytes:
    """Borsh-encode Option<Pubkey>."""
    if value is None:
        return b"\x00"
    return b"\x01" + bytes(Pubkey.from_string(value))


def _encode_pubkey(value: str) -> bytes:
    """Borsh-encode a Pubkey (32 bytes)."""
    return bytes(Pubkey.from_string(value))


def build_execute_transfer_data(amount: int) -> bytes:
    """Build instruction data for execute_transfer.

    Args:
        amount: Transfer amount in token minor units.

    Returns:
        8-byte discriminator + borsh(u64 amount).
    """
    return DISC_EXECUTE_TRANSFER + struct.pack("<Q", amount)


def build_execute_cosigned_data(amount: int) -> bytes:
    """Build instruction data for execute_cosigned_transfer."""
    return DISC_EXECUTE_COSIGNED + struct.pack("<Q", amount)


@dataclass
class InitializeWalletArgs:
    """Arguments for initialize_wallet instruction."""
    trust_level: int
    limit_per_tx: int
    limit_total: int
    daily_limit: int
    weekly_limit: int
    monthly_limit: int
    cosign_limit_per_tx: int
    cosign_daily_limit: int
    co_signer: str  # Pubkey string


def build_initialize_wallet_data(args: InitializeWalletArgs) -> bytes:
    """Build instruction data for initialize_wallet."""
    data = DISC_INITIALIZE_WALLET
    data += struct.pack("<B", args.trust_level)
    data += struct.pack("<Q", args.limit_per_tx)
    data += struct.pack("<Q", args.limit_total)
    data += struct.pack("<Q", args.daily_limit)
    data += struct.pack("<Q", args.weekly_limit)
    data += struct.pack("<Q", args.monthly_limit)
    data += struct.pack("<Q", args.cosign_limit_per_tx)
    data += struct.pack("<Q", args.cosign_daily_limit)
    data += _encode_pubkey(args.co_signer)
    return data


@dataclass
class UpdatePolicyArgs:
    """Arguments for update_policy instruction."""
    trust_level: int | None = None
    limit_per_tx: int | None = None
    limit_total: int | None = None
    daily_limit: int | None = None
    weekly_limit: int | None = None
    monthly_limit: int | None = None
    cosign_limit_per_tx: int | None = None
    cosign_daily_limit: int | None = None
    co_signer: str | None = None


def build_update_policy_data(args: UpdatePolicyArgs) -> bytes:
    """Build instruction data for update_policy."""
    data = DISC_UPDATE_POLICY
    data += _encode_option_u8(args.trust_level)
    data += _encode_option_u64(args.limit_per_tx)
    data += _encode_option_u64(args.limit_total)
    data += _encode_option_u64(args.daily_limit)
    data += _encode_option_u64(args.weekly_limit)
    data += _encode_option_u64(args.monthly_limit)
    data += _encode_option_u64(args.cosign_limit_per_tx)
    data += _encode_option_u64(args.cosign_daily_limit)
    data += _encode_option_pubkey(args.co_signer)
    return data


def build_freeze_wallet_data() -> bytes:
    """Build instruction data for freeze_wallet."""
    return DISC_FREEZE_WALLET


def build_unfreeze_wallet_data() -> bytes:
    """Build instruction data for unfreeze_wallet."""
    return DISC_UNFREEZE_WALLET


def build_add_merchant_rule_data(
    address: str, rule_type: int, max_per_tx: int
) -> bytes:
    """Build instruction data for add_merchant_rule."""
    data = DISC_ADD_MERCHANT_RULE
    data += _encode_pubkey(address)
    data += struct.pack("<B", rule_type)
    data += struct.pack("<Q", max_per_tx)
    return data


def build_remove_merchant_rule_data(address: str) -> bytes:
    """Build instruction data for remove_merchant_rule."""
    return DISC_REMOVE_MERCHANT_RULE + _encode_pubkey(address)


def build_set_allowlist_mode_data(enabled: bool) -> bytes:
    """Build instruction data for set_allowlist_mode."""
    return DISC_SET_ALLOWLIST_MODE + struct.pack("<B", int(enabled))


def build_add_token_data(mint: str) -> bytes:
    """Build instruction data for add_token."""
    return DISC_ADD_TOKEN + _encode_pubkey(mint)


def build_remove_token_data(mint: str) -> bytes:
    """Build instruction data for remove_token."""
    return DISC_REMOVE_TOKEN + _encode_pubkey(mint)


def build_set_token_enforced_data(enforced: bool) -> bytes:
    """Build instruction data for set_token_allowlist_enforced."""
    return DISC_SET_TOKEN_ENFORCED + struct.pack("<B", int(enforced))


def build_update_authority_data(new_authority: str) -> bytes:
    """Build instruction data for update_authority."""
    return DISC_UPDATE_AUTHORITY + _encode_pubkey(new_authority)


def build_close_wallet_data() -> bytes:
    """Build instruction data for close_wallet."""
    return DISC_CLOSE_WALLET


# ── Full Instruction Builders (data + account metas) ──────────────────────
# These return ``solders.instruction.Instruction`` objects ready to include in
# a Solana transaction.  They mirror the Anchor account structs defined in the
# Rust program (see ``programs/sardis_agent_wallet/src/instructions/*.rs``).

def _pubkey(value: str | Pubkey) -> Pubkey:
    """Coerce a string or Pubkey to Pubkey."""
    if isinstance(value, Pubkey):
        return value
    return Pubkey.from_string(value)


def build_initialize_wallet_ix(
    *,
    owner: str | Pubkey,
    system_program: str | Pubkey = SYSTEM_PROGRAM_ID,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
    args: InitializeWalletArgs,
) -> Instruction:
    """Build a complete ``initialize_wallet`` instruction.

    Accounts (from Anchor ``InitializeWallet`` context):
      0. owner         — signer, writable (payer for PDA rent)
      1. wallet        — writable (PDA: ``[b"sardis_wallet", owner]``)
      2. system_program
    """
    pid = _pubkey(program_id)
    owner_pk = _pubkey(owner)

    wallet_pk, _bump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=owner_pk, is_signer=True, is_writable=True),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=True),
            AccountMeta(pubkey=_pubkey(system_program), is_signer=False, is_writable=False),
        ],
        data=build_initialize_wallet_data(args),
    )


def build_execute_transfer_ix(
    *,
    owner: str | Pubkey,
    source_token_account: str | Pubkey,
    destination_token_account: str | Pubkey,
    mint: str | Pubkey,
    amount: int,
    token_program: str | Pubkey = TOKEN_PROGRAM_ID,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``execute_transfer`` instruction.

    This is the critical payment instruction.  The Anchor program performs
    all policy checks (pause, token allowlist, merchant rules, per-tx /
    daily / weekly / monthly / total limits) and then CPI-calls SPL
    TransferChecked.

    Accounts (from Anchor ``ExecuteTransfer`` context):
      0. owner              — signer (agent MPC key)
      1. wallet             — writable PDA (``[b"sardis_wallet", owner]``)
      2. merchant_registry  — PDA (``[b"merchants", wallet]``)
      3. token_allowlist    — PDA (``[b"tokens", wallet]``)
      4. source             — writable (source token account, owned by wallet PDA)
      5. destination        — writable (recipient token account)
      6. mint               — token mint (for TransferChecked decimals check)
      7. token_program      — SPL Token program
    """
    pid = _pubkey(program_id)
    owner_pk = _pubkey(owner)

    # Derive PDAs
    wallet_pk, _wbump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )
    merchant_pk, _mbump = Pubkey.find_program_address(
        [MERCHANT_SEED, bytes(wallet_pk)], pid
    )
    token_pk, _tbump = Pubkey.find_program_address(
        [TOKEN_SEED, bytes(wallet_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=owner_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=True),
            AccountMeta(pubkey=merchant_pk, is_signer=False, is_writable=False),
            AccountMeta(pubkey=token_pk, is_signer=False, is_writable=False),
            AccountMeta(pubkey=_pubkey(source_token_account), is_signer=False, is_writable=True),
            AccountMeta(pubkey=_pubkey(destination_token_account), is_signer=False, is_writable=True),
            AccountMeta(pubkey=_pubkey(mint), is_signer=False, is_writable=False),
            AccountMeta(pubkey=_pubkey(token_program), is_signer=False, is_writable=False),
        ],
        data=build_execute_transfer_data(amount),
    )


def build_update_policy_ix(
    *,
    authority: str | Pubkey,
    owner: str | Pubkey,
    args: UpdatePolicyArgs,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``update_policy`` instruction.

    Accounts (from Anchor ``UpdatePolicy`` context):
      0. authority — signer (wallet authority, initially = owner)
      1. wallet   — writable PDA (``[b"sardis_wallet", owner]``)
    """
    pid = _pubkey(program_id)
    authority_pk = _pubkey(authority)
    owner_pk = _pubkey(owner)

    wallet_pk, _bump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=authority_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=True),
        ],
        data=build_update_policy_data(args),
    )


def build_freeze_wallet_ix(
    *,
    authority: str | Pubkey,
    owner: str | Pubkey,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``freeze_wallet`` instruction.

    Accounts (from Anchor ``FreezeWallet`` context):
      0. authority — signer
      1. wallet   — writable PDA (``[b"sardis_wallet", owner]``)
    """
    pid = _pubkey(program_id)
    authority_pk = _pubkey(authority)
    owner_pk = _pubkey(owner)

    wallet_pk, _bump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=authority_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=True),
        ],
        data=build_freeze_wallet_data(),
    )


def build_unfreeze_wallet_ix(
    *,
    authority: str | Pubkey,
    owner: str | Pubkey,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``unfreeze_wallet`` instruction.

    Accounts (from Anchor ``FreezeWallet`` context):
      0. authority — signer
      1. wallet   — writable PDA (``[b"sardis_wallet", owner]``)
    """
    pid = _pubkey(program_id)
    authority_pk = _pubkey(authority)
    owner_pk = _pubkey(owner)

    wallet_pk, _bump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=authority_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=True),
        ],
        data=build_unfreeze_wallet_data(),
    )


def build_add_merchant_rule_ix(
    *,
    authority: str | Pubkey,
    owner: str | Pubkey,
    address: str,
    rule_type: int,
    max_per_tx: int,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``add_merchant_rule`` instruction.

    Accounts (from Anchor ``ManageMerchant`` context):
      0. authority          — signer
      1. wallet             — PDA (``[b"sardis_wallet", owner]``)
      2. merchant_registry  — writable PDA (``[b"merchants", wallet]``)
    """
    pid = _pubkey(program_id)
    authority_pk = _pubkey(authority)
    owner_pk = _pubkey(owner)

    wallet_pk, _wbump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )
    merchant_pk, _mbump = Pubkey.find_program_address(
        [MERCHANT_SEED, bytes(wallet_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=authority_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=False),
            AccountMeta(pubkey=merchant_pk, is_signer=False, is_writable=True),
        ],
        data=build_add_merchant_rule_data(address, rule_type, max_per_tx),
    )


def build_remove_merchant_rule_ix(
    *,
    authority: str | Pubkey,
    owner: str | Pubkey,
    address: str,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``remove_merchant_rule`` instruction.

    Accounts (from Anchor ``ManageMerchant`` context):
      0. authority          — signer
      1. wallet             — PDA (``[b"sardis_wallet", owner]``)
      2. merchant_registry  — writable PDA (``[b"merchants", wallet]``)
    """
    pid = _pubkey(program_id)
    authority_pk = _pubkey(authority)
    owner_pk = _pubkey(owner)

    wallet_pk, _wbump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )
    merchant_pk, _mbump = Pubkey.find_program_address(
        [MERCHANT_SEED, bytes(wallet_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=authority_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=False),
            AccountMeta(pubkey=merchant_pk, is_signer=False, is_writable=True),
        ],
        data=build_remove_merchant_rule_data(address),
    )


def build_add_token_ix(
    *,
    authority: str | Pubkey,
    owner: str | Pubkey,
    mint: str,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``add_token`` instruction.

    Accounts (from Anchor ``ManageToken`` context):
      0. authority        — signer
      1. wallet           — PDA (``[b"sardis_wallet", owner]``)
      2. token_allowlist  — writable PDA (``[b"tokens", wallet]``)
    """
    pid = _pubkey(program_id)
    authority_pk = _pubkey(authority)
    owner_pk = _pubkey(owner)

    wallet_pk, _wbump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )
    token_pk, _tbump = Pubkey.find_program_address(
        [TOKEN_SEED, bytes(wallet_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=authority_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=False),
            AccountMeta(pubkey=token_pk, is_signer=False, is_writable=True),
        ],
        data=build_add_token_data(mint),
    )


def build_remove_token_ix(
    *,
    authority: str | Pubkey,
    owner: str | Pubkey,
    mint: str,
    program_id: str | Pubkey = SARDIS_WALLET_PROGRAM_ID,
) -> Instruction:
    """Build a complete ``remove_token`` instruction.

    Accounts (from Anchor ``ManageToken`` context):
      0. authority        — signer
      1. wallet           — PDA (``[b"sardis_wallet", owner]``)
      2. token_allowlist  — writable PDA (``[b"tokens", wallet]``)
    """
    pid = _pubkey(program_id)
    authority_pk = _pubkey(authority)
    owner_pk = _pubkey(owner)

    wallet_pk, _wbump = Pubkey.find_program_address(
        [WALLET_SEED, bytes(owner_pk)], pid
    )
    token_pk, _tbump = Pubkey.find_program_address(
        [TOKEN_SEED, bytes(wallet_pk)], pid
    )

    return Instruction(
        program_id=pid,
        accounts=[
            AccountMeta(pubkey=authority_pk, is_signer=True, is_writable=False),
            AccountMeta(pubkey=wallet_pk, is_signer=False, is_writable=False),
            AccountMeta(pubkey=token_pk, is_signer=False, is_writable=True),
        ],
        data=build_remove_token_data(mint),
    )


# ── Error Parsing ──────────────────────────────────────────────────────────
def parse_program_error(error_data: dict | str | int) -> str | None:
    """Extract Python reason_code from a Solana transaction error.

    Anchor custom errors come as InstructionError with custom code.
    The code = 6000 + offset → we map to reason strings.

    Returns None if the error is not a Sardis program error.
    """
    if isinstance(error_data, int):
        return anchor_error_to_reason(error_data)

    if isinstance(error_data, str):
        return None

    # Transaction-level error: {"InstructionError": [idx, {"Custom": code}]}
    if isinstance(error_data, dict):
        ix_err = error_data.get("InstructionError")
        if isinstance(ix_err, list) and len(ix_err) == 2:
            detail = ix_err[1]
            if isinstance(detail, dict):
                code = detail.get("Custom")
                if isinstance(code, int):
                    return anchor_error_to_reason(code)

    return None
