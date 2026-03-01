"""Tests for safe_account.py — Safe Smart Account helpers."""

import importlib.util
import os
import sys

import pytest

# Import safe_account directly to avoid sardis_chain.__init__ pulling in
# heavy cross-package deps (sardis_ledger, etc.)
_spec = importlib.util.spec_from_file_location(
    "safe_account",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "sardis_chain",
        "safe_account.py",
    ),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

SAFE_ADDRESSES = _mod.SAFE_ADDRESSES
predict_safe_address = _mod.predict_safe_address
build_safe_init_code = _mod.build_safe_init_code
encode_safe_exec = _mod.encode_safe_exec
_encode_safe_setup = _mod._encode_safe_setup


# ============ Fixtures ============

OWNER = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"  # Foundry default
OWNER_2 = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
POLICY_MODULE = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
POLICY_MODULE_2 = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
SALT = 0
SALT_2 = 42


# ============ SAFE_ADDRESSES ============


class TestSafeAddresses:
    def test_all_keys_present(self):
        expected = {
            "proxy_factory",
            "safe_singleton",
            "safe_4337_module",
            "multi_send",
            "fallback_handler",
        }
        assert set(SAFE_ADDRESSES.keys()) == expected

    def test_addresses_are_checksummed(self):
        from web3 import Web3

        for key, addr in SAFE_ADDRESSES.items():
            assert addr == Web3.to_checksum_address(addr), (
                f"{key} address is not checksummed"
            )

    def test_addresses_are_42_chars(self):
        for key, addr in SAFE_ADDRESSES.items():
            assert len(addr) == 42, f"{key} address wrong length"
            assert addr.startswith("0x"), f"{key} address missing 0x prefix"


# ============ predict_safe_address ============


class TestPredictSafeAddress:
    def test_returns_checksummed_address(self):
        from web3 import Web3

        addr = predict_safe_address(OWNER, SALT, POLICY_MODULE)
        assert addr == Web3.to_checksum_address(addr)
        assert len(addr) == 42

    def test_deterministic(self):
        """Same inputs always produce the same address."""
        a1 = predict_safe_address(OWNER, SALT, POLICY_MODULE)
        a2 = predict_safe_address(OWNER, SALT, POLICY_MODULE)
        assert a1 == a2

    def test_different_owner_different_address(self):
        a1 = predict_safe_address(OWNER, SALT, POLICY_MODULE)
        a2 = predict_safe_address(OWNER_2, SALT, POLICY_MODULE)
        assert a1 != a2

    def test_different_salt_different_address(self):
        a1 = predict_safe_address(OWNER, SALT, POLICY_MODULE)
        a2 = predict_safe_address(OWNER, SALT_2, POLICY_MODULE)
        assert a1 != a2

    def test_different_policy_module_different_address(self):
        a1 = predict_safe_address(OWNER, SALT, POLICY_MODULE)
        a2 = predict_safe_address(OWNER, SALT, POLICY_MODULE_2)
        assert a1 != a2

    def test_custom_fallback_handler_changes_address(self):
        custom_handler = "0x1234567890abcdef1234567890abcdef12345678"
        a1 = predict_safe_address(OWNER, SALT, POLICY_MODULE)
        a2 = predict_safe_address(
            OWNER, SALT, POLICY_MODULE, fallback_handler=custom_handler
        )
        assert a1 != a2


# ============ build_safe_init_code ============


class TestBuildSafeInitCode:
    def test_starts_with_factory_address(self):
        init_code = build_safe_init_code(OWNER, POLICY_MODULE, SALT)
        factory = SAFE_ADDRESSES["proxy_factory"].lower()
        assert init_code.lower().startswith(factory)

    def test_contains_create_proxy_selector(self):
        from web3 import Web3

        init_code = build_safe_init_code(OWNER, POLICY_MODULE, SALT)
        selector = Web3.keccak(
            text="createProxyWithNonce(address,bytes,uint256)"
        )[:4].hex()
        # The selector should appear right after the factory address
        after_factory = init_code[42:]  # skip factory address
        assert after_factory.startswith("0x")
        calldata_hex = after_factory[2:]  # skip 0x
        assert calldata_hex.startswith(selector)

    def test_deterministic(self):
        a = build_safe_init_code(OWNER, POLICY_MODULE, SALT)
        b = build_safe_init_code(OWNER, POLICY_MODULE, SALT)
        assert a == b

    def test_different_inputs_different_output(self):
        a = build_safe_init_code(OWNER, POLICY_MODULE, SALT)
        b = build_safe_init_code(OWNER_2, POLICY_MODULE, SALT)
        assert a != b

    def test_contains_singleton_address(self):
        init_code = build_safe_init_code(OWNER, POLICY_MODULE, SALT)
        singleton = SAFE_ADDRESSES["safe_singleton"][2:].lower()
        # The singleton address should be ABI-encoded (left-padded to 32 bytes)
        padded = singleton.zfill(64)
        assert padded in init_code.lower()


# ============ encode_safe_exec ============


class TestEncodeSafeExec:
    def test_returns_hex_string(self):
        result = encode_safe_exec(
            to="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            value=0,
            data=b"",
        )
        assert result.startswith("0x")
        # Should be valid hex
        bytes.fromhex(result[2:])

    def test_selector_is_execute_user_op(self):
        from web3 import Web3

        result = encode_safe_exec(
            to="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            value=0,
            data=b"",
        )
        expected_selector = Web3.keccak(
            text="executeUserOp(address,uint256,bytes,uint8)"
        )[:4].hex()
        assert result[2:10] == expected_selector

    def test_encodes_value(self):
        result_zero = encode_safe_exec(
            to="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            value=0,
            data=b"",
        )
        result_one_eth = encode_safe_exec(
            to="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            value=10**18,
            data=b"",
        )
        assert result_zero != result_one_eth

    def test_encodes_data(self):
        result_empty = encode_safe_exec(
            to="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            value=0,
            data=b"",
        )
        result_with_data = encode_safe_exec(
            to="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            value=0,
            data=b"\x01\x02\x03",
        )
        assert result_empty != result_with_data

    def test_operation_is_call(self):
        """The last ABI-encoded uint8 should be 0 (Call, not DelegateCall)."""
        result = encode_safe_exec(
            to="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            value=0,
            data=b"",
        )
        # Last 32 bytes (64 hex chars) should be uint8=0
        last_word = result[-64:]
        assert int(last_word, 16) == 0


# ============ _encode_safe_setup ============


class TestEncodeSafeSetup:
    def test_returns_bytes(self):
        result = _encode_safe_setup(OWNER, POLICY_MODULE)
        assert isinstance(result, bytes)

    def test_starts_with_setup_selector(self):
        from web3 import Web3

        result = _encode_safe_setup(OWNER, POLICY_MODULE)
        expected_selector = Web3.keccak(
            text="setup(address[],uint256,address,bytes,address,address,uint256,address)"
        )[:4]
        assert result[:4] == expected_selector

    def test_deterministic(self):
        a = _encode_safe_setup(OWNER, POLICY_MODULE)
        b = _encode_safe_setup(OWNER, POLICY_MODULE)
        assert a == b

    def test_different_owner_different_output(self):
        a = _encode_safe_setup(OWNER, POLICY_MODULE)
        b = _encode_safe_setup(OWNER_2, POLICY_MODULE)
        assert a != b

    def test_uses_default_fallback_handler(self):
        """Without explicit handler, uses SAFE_ADDRESSES fallback."""
        result_default = _encode_safe_setup(OWNER, POLICY_MODULE)
        result_explicit = _encode_safe_setup(
            OWNER,
            POLICY_MODULE,
            fallback_handler=SAFE_ADDRESSES["fallback_handler"],
        )
        assert result_default == result_explicit

    def test_custom_fallback_handler(self):
        custom = "0x1234567890abcdef1234567890abcdef12345678"
        result_default = _encode_safe_setup(OWNER, POLICY_MODULE)
        result_custom = _encode_safe_setup(
            OWNER, POLICY_MODULE, fallback_handler=custom
        )
        assert result_default != result_custom
