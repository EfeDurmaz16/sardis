"""Sardis Solana Anchor program client.

Builds Anchor instructions (8-byte discriminator + borsh-serialized args),
derives wallet/merchant/token PDAs, and maps Anchor error codes to Python
reason strings matching the spending_policy.py engine.
"""
from __future__ import annotations

import hashlib
import logging
import struct
from dataclasses import dataclass

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
        if candidate is NOT on ed25519 curve → return (candidate, bump)
    """
    # This requires solders or solana-py for actual PDA derivation.
    # We import lazily to avoid hard dependency at module level.
    try:
        from solders.pubkey import Pubkey  # type: ignore[import-untyped]
    except ImportError:
        # Fallback: use solana-py
        from solana.publickey import PublicKey  # type: ignore[import-untyped]

        pda, bump = PublicKey.find_program_address(seeds, PublicKey(program_id))
        return str(pda), bump

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
    try:
        from solders.pubkey import Pubkey  # type: ignore[import-untyped]
        owner_bytes = bytes(Pubkey.from_string(owner))
    except ImportError:
        from solana.publickey import PublicKey  # type: ignore[import-untyped]
        owner_bytes = bytes(PublicKey(owner))

    wallet_addr, wallet_bump = _find_program_address(
        [WALLET_SEED, owner_bytes], program_id
    )

    try:
        from solders.pubkey import Pubkey  # type: ignore[import-untyped]
        wallet_bytes = bytes(Pubkey.from_string(wallet_addr))
    except ImportError:
        from solana.publickey import PublicKey  # type: ignore[import-untyped]
        wallet_bytes = bytes(PublicKey(wallet_addr))

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
    try:
        from solders.pubkey import Pubkey  # type: ignore[import-untyped]
        return b"\x01" + bytes(Pubkey.from_string(value))
    except ImportError:
        from solana.publickey import PublicKey  # type: ignore[import-untyped]
        return b"\x01" + bytes(PublicKey(value))


def _encode_pubkey(value: str) -> bytes:
    """Borsh-encode a Pubkey (32 bytes)."""
    try:
        from solders.pubkey import Pubkey  # type: ignore[import-untyped]
        return bytes(Pubkey.from_string(value))
    except ImportError:
        from solana.publickey import PublicKey  # type: ignore[import-untyped]
        return bytes(PublicKey(value))


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
