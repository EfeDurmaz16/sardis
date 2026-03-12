"""Integration tests for the Sardis Solana Anchor program Python client.

Tests the program.py module: PDA derivation, instruction data encoding,
error code mapping, and discriminator computation.

These tests do NOT require a running Solana validator — they validate
the client-side logic that builds instructions and parses errors.
"""
from __future__ import annotations

import hashlib
import struct

import pytest

from sardis_chain.solana.program import (
    DISC_EXECUTE_TRANSFER,
    DISC_FREEZE_WALLET,
    DISC_INITIALIZE_WALLET,
    ERROR_CODE_MAP,
    RULE_ALLOW,
    RULE_DENY,
    SARDIS_WALLET_PROGRAM_ID,
    TRUST_HIGH,
    TRUST_LOW,
    TRUST_MEDIUM,
    TRUST_UNLIMITED,
    InitializeWalletArgs,
    UpdatePolicyArgs,
    anchor_error_to_reason,
    build_add_merchant_rule_data,
    build_add_token_data,
    build_close_wallet_data,
    build_execute_cosigned_data,
    build_execute_transfer_data,
    build_freeze_wallet_data,
    build_initialize_wallet_data,
    build_remove_merchant_rule_data,
    build_remove_token_data,
    build_set_allowlist_mode_data,
    build_set_token_enforced_data,
    build_unfreeze_wallet_data,
    build_update_authority_data,
    build_update_policy_data,
    parse_program_error,
)


# ── Discriminator Tests ────────────────────────────────────────────────────

class TestDiscriminators:
    """Verify Anchor discriminator computation matches the standard algorithm."""

    def test_discriminator_algorithm(self):
        """SHA256("global:<name>")[:8] should match pre-computed discriminators."""
        expected = hashlib.sha256(b"global:execute_transfer").digest()[:8]
        assert DISC_EXECUTE_TRANSFER == expected

    def test_discriminator_uniqueness(self):
        """All instruction discriminators must be unique."""
        from sardis_chain.solana.program import (
            DISC_ADD_MERCHANT_RULE,
            DISC_ADD_TOKEN,
            DISC_CLOSE_WALLET,
            DISC_EXECUTE_COSIGNED,
            DISC_REMOVE_MERCHANT_RULE,
            DISC_REMOVE_TOKEN,
            DISC_SET_ALLOWLIST_MODE,
            DISC_SET_TOKEN_ENFORCED,
            DISC_UNFREEZE_WALLET,
            DISC_UPDATE_AUTHORITY,
            DISC_UPDATE_POLICY,
        )

        all_discs = [
            DISC_INITIALIZE_WALLET,
            DISC_EXECUTE_TRANSFER,
            DISC_EXECUTE_COSIGNED,
            DISC_UPDATE_POLICY,
            DISC_FREEZE_WALLET,
            DISC_UNFREEZE_WALLET,
            DISC_ADD_MERCHANT_RULE,
            DISC_REMOVE_MERCHANT_RULE,
            DISC_SET_ALLOWLIST_MODE,
            DISC_ADD_TOKEN,
            DISC_REMOVE_TOKEN,
            DISC_SET_TOKEN_ENFORCED,
            DISC_UPDATE_AUTHORITY,
            DISC_CLOSE_WALLET,
        ]
        assert len(all_discs) == len(set(all_discs)), "Discriminator collision detected"

    def test_discriminator_length(self):
        """All discriminators must be exactly 8 bytes."""
        assert len(DISC_EXECUTE_TRANSFER) == 8
        assert len(DISC_INITIALIZE_WALLET) == 8
        assert len(DISC_FREEZE_WALLET) == 8


# ── Error Code Mapping Tests ──────────────────────────────────────────────

class TestErrorCodeMapping:
    """Verify Anchor error codes map correctly to Python reason strings."""

    def test_all_codes_mapped(self):
        """All 21 error codes (6000-6020) should have mappings."""
        for code in range(6000, 6021):
            reason = anchor_error_to_reason(code)
            assert not reason.startswith("unknown_"), f"Code {code} not mapped"

    def test_specific_mappings(self):
        """Spot-check key error codes match spending_policy.py reasons."""
        assert anchor_error_to_reason(6000) == "amount_must_be_positive"
        assert anchor_error_to_reason(6001) == "per_transaction_limit"
        assert anchor_error_to_reason(6003) == "daily_limit_exceeded"
        assert anchor_error_to_reason(6006) == "merchant_denied"
        assert anchor_error_to_reason(6009) == "token_not_allowlisted"
        assert anchor_error_to_reason(6010) == "wallet_paused"

    def test_unknown_code(self):
        """Unknown error codes should return descriptive fallback."""
        reason = anchor_error_to_reason(9999)
        assert reason == "unknown_program_error_9999"

    def test_parse_instruction_error(self):
        """Parse Solana InstructionError format."""
        error_data = {"InstructionError": [0, {"Custom": 6010}]}
        assert parse_program_error(error_data) == "wallet_paused"

    def test_parse_raw_code(self):
        """Parse raw integer error code."""
        assert parse_program_error(6001) == "per_transaction_limit"

    def test_parse_non_program_error(self):
        """Non-program errors should return None."""
        assert parse_program_error("some string error") is None
        assert parse_program_error({"OtherError": "foo"}) is None


# ── Instruction Data Encoding Tests ────────────────────────────────────────

class TestInstructionEncoding:
    """Verify borsh-encoded instruction data is correctly structured."""

    def test_execute_transfer_data(self):
        """execute_transfer: 8-byte disc + u64 amount."""
        amount = 1_000_000  # 1 USDC
        data = build_execute_transfer_data(amount)
        assert len(data) == 16  # 8 disc + 8 u64
        assert data[:8] == DISC_EXECUTE_TRANSFER
        decoded_amount = struct.unpack("<Q", data[8:])[0]
        assert decoded_amount == amount

    def test_execute_cosigned_data(self):
        """execute_cosigned_transfer: 8-byte disc + u64 amount."""
        amount = 5_000_000
        data = build_execute_cosigned_data(amount)
        assert len(data) == 16
        decoded_amount = struct.unpack("<Q", data[8:])[0]
        assert decoded_amount == amount

    def test_freeze_wallet_data(self):
        """freeze_wallet: discriminator only (no args)."""
        data = build_freeze_wallet_data()
        assert len(data) == 8
        assert data == DISC_FREEZE_WALLET

    def test_unfreeze_wallet_data(self):
        """unfreeze_wallet: discriminator only."""
        data = build_unfreeze_wallet_data()
        assert len(data) == 8

    def test_close_wallet_data(self):
        """close_wallet: discriminator only."""
        data = build_close_wallet_data()
        assert len(data) == 8

    def test_set_allowlist_mode_data(self):
        """set_allowlist_mode: disc + bool as u8."""
        data_on = build_set_allowlist_mode_data(True)
        assert len(data_on) == 9
        assert data_on[8] == 1

        data_off = build_set_allowlist_mode_data(False)
        assert data_off[8] == 0

    def test_set_token_enforced_data(self):
        """set_token_allowlist_enforced: disc + bool as u8."""
        data = build_set_token_enforced_data(True)
        assert len(data) == 9
        assert data[8] == 1

    def test_update_policy_all_none(self):
        """update_policy with all None args: disc + 9 x 0x00 option tags."""
        args = UpdatePolicyArgs()
        data = build_update_policy_data(args)
        # 8 disc + 9 option tags (each 1 byte for None)
        assert len(data) == 8 + 9

    def test_update_policy_some_values(self):
        """update_policy with some values set."""
        args = UpdatePolicyArgs(
            trust_level=2,
            limit_per_tx=500_000_000,
            daily_limit=5_000_000_000,
        )
        data = build_update_policy_data(args)
        # disc(8) + Some(u8)(2) + Some(u64)(9) + None(1) + Some(u64)(9) + None*5(5)
        expected_len = 8 + 2 + 9 + 1 + 9 + 1 + 1 + 1 + 1 + 1
        assert len(data) == expected_len


# ── Trust Level Constants ──────────────────────────────────────────────────

class TestTrustLevels:
    """Verify trust level constants match Rust enum values."""

    def test_trust_levels(self):
        assert TRUST_LOW == 0
        assert TRUST_MEDIUM == 1
        assert TRUST_HIGH == 2
        assert TRUST_UNLIMITED == 3

    def test_rule_types(self):
        assert RULE_ALLOW == 0
        assert RULE_DENY == 1


# ── Program ID ─────────────────────────────────────────────────────────────

class TestProgramId:
    """Verify program ID is set correctly."""

    def test_program_id_is_base58(self):
        """Program ID should be a valid base58 string."""
        assert len(SARDIS_WALLET_PROGRAM_ID) > 0
        # Base58 alphabet check
        base58_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
        assert all(c in base58_chars for c in SARDIS_WALLET_PROGRAM_ID)
