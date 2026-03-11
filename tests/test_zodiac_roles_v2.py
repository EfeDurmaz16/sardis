"""Tests for Zodiac Roles Modifier v2 integration.

Covers issue #134. Tests calldata encoding, policy mapping, and setup generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from eth_abi import decode, encode
from web3 import Web3

from sardis_chain.zodiac_roles import (
    APPROVE_SELECTOR,
    EURC_ADDRESSES,
    TRANSFER_SELECTOR,
    USDC_ADDRESSES,
    ZODIAC_ADDRESSES,
    AllowanceConfig,
    Clearance,
    ConditionFlat,
    ExecutionOptions,
    Operator,
    ParameterType,
    RoleConfig,
    RolePermission,
    ZodiacRolesSetup,
    build_agent_wallet_setup,
    build_allow_function,
    build_allow_target,
    build_assign_roles,
    build_exec_transaction_with_role,
    build_multisend_payload,
    build_revoke_target,
    build_role_setup_transactions,
    build_scope_function,
    build_scope_target,
    build_set_allowance,
    build_set_default_role,
    condition_equal_to,
    condition_less_than,
    condition_or,
    condition_pass,
    condition_within_allowance,
    decode_role_key,
    encode_role_key,
    make_allowance_key,
    policy_to_role_config,
)


# ============ Stub SpendingPolicy for testing ============

@dataclass
class StubTimeWindowLimit:
    window_type: str
    limit_amount: Decimal
    currency: str = "USDC"


@dataclass
class StubSpendingPolicy:
    """Minimal SpendingPolicy stub for testing policy mapping."""
    limit_per_tx: Decimal = Decimal("500")
    limit_total: Decimal = Decimal("10000")
    daily_limit: StubTimeWindowLimit | None = None
    weekly_limit: StubTimeWindowLimit | None = None
    monthly_limit: StubTimeWindowLimit | None = None
    allowed_destination_addresses: list[str] = field(default_factory=list)
    allowed_tokens: list[str] = field(default_factory=list)
    blocked_destination_addresses: list[str] = field(default_factory=list)


TEST_AGENT = "0x1234567890AbcdEF1234567890aBcdef12345678"
TEST_SAFE = "0xABCDabcdABCDabcdABCDabcdABCDabcdABCDabcd"


# ============ Key Encoding Tests ============

class TestEncodeRoleKey:
    def test_basic_encoding(self):
        key = encode_role_key("agent_spending")
        assert len(key) == 32
        assert key[:14] == b"agent_spending"
        assert key[14:] == b"\x00" * 18

    def test_max_length(self):
        name = "a" * 32
        key = encode_role_key(name)
        assert len(key) == 32
        assert key == name.encode("ascii")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="1-32 characters"):
            encode_role_key("")

    def test_too_long_raises(self):
        with pytest.raises(ValueError, match="1-32 characters"):
            encode_role_key("a" * 33)


class TestDecodeRoleKey:
    def test_roundtrip(self):
        name = "agent_spending"
        assert decode_role_key(encode_role_key(name)) == name

    def test_decode_padded(self):
        key = b"test" + b"\x00" * 28
        assert decode_role_key(key) == "test"


# ============ Allowance Key Tests ============

class TestMakeAllowanceKey:
    def test_deterministic(self):
        key1 = make_allowance_key("agent", "USDC", "daily")
        key2 = make_allowance_key("agent", "USDC", "daily")
        assert key1 == key2
        assert len(key1) == 32

    def test_different_inputs_different_keys(self):
        key1 = make_allowance_key("agent", "USDC", "daily")
        key2 = make_allowance_key("agent", "USDC", "weekly")
        key3 = make_allowance_key("agent", "EURC", "daily")
        assert key1 != key2
        assert key1 != key3


# ============ Calldata Builder Tests ============

class TestBuildAssignRoles:
    def test_encodes_correctly(self):
        role_key = encode_role_key("agent_spending")
        calldata = build_assign_roles(TEST_AGENT, [role_key], [True])

        # First 4 bytes = selector
        selector = calldata[:4]
        expected_selector = Web3.keccak(text="assignRoles(address,bytes32[],bool[])")[:4]
        assert selector == expected_selector

        # Decode params
        decoded = decode(
            ["address", "bytes32[]", "bool[]"],
            calldata[4:],
        )
        assert decoded[0].lower() == TEST_AGENT.lower()
        assert list(decoded[1]) == [role_key]
        assert list(decoded[2]) == [True]


class TestBuildSetDefaultRole:
    def test_encodes_correctly(self):
        role_key = encode_role_key("agent")
        calldata = build_set_default_role(TEST_AGENT, role_key)
        selector = calldata[:4]
        expected = Web3.keccak(text="setDefaultRole(address,bytes32)")[:4]
        assert selector == expected


class TestBuildScopeTarget:
    def test_encodes_correctly(self):
        role_key = encode_role_key("agent")
        usdc = USDC_ADDRESSES[8453]
        calldata = build_scope_target(role_key, usdc)

        selector = calldata[:4]
        expected = Web3.keccak(text="scopeTarget(bytes32,address)")[:4]
        assert selector == expected

        decoded = decode(["bytes32", "address"], calldata[4:])
        assert decoded[0] == role_key
        assert decoded[1].lower() == usdc.lower()


class TestBuildAllowTarget:
    def test_encodes_with_options(self):
        role_key = encode_role_key("admin")
        calldata = build_allow_target(role_key, TEST_SAFE, ExecutionOptions.SEND)
        selector = calldata[:4]
        expected = Web3.keccak(text="allowTarget(bytes32,address,uint8)")[:4]
        assert selector == expected


class TestBuildRevokeTarget:
    def test_encodes_correctly(self):
        role_key = encode_role_key("agent")
        calldata = build_revoke_target(role_key, TEST_SAFE)
        selector = calldata[:4]
        expected = Web3.keccak(text="revokeTarget(bytes32,address)")[:4]
        assert selector == expected


class TestBuildAllowFunction:
    def test_encodes_transfer(self):
        role_key = encode_role_key("agent")
        usdc = USDC_ADDRESSES[8453]
        calldata = build_allow_function(
            role_key, usdc, TRANSFER_SELECTOR, ExecutionOptions.NONE
        )
        selector = calldata[:4]
        expected = Web3.keccak(text="allowFunction(bytes32,address,bytes4,uint8)")[:4]
        assert selector == expected


class TestBuildScopeFunction:
    def test_encodes_with_conditions(self):
        role_key = encode_role_key("agent")
        usdc = USDC_ADDRESSES[8453]
        conditions = [
            condition_pass(),  # recipient: any
            condition_less_than(1000000),  # amount < 1 USDC
        ]
        calldata = build_scope_function(
            role_key, usdc, TRANSFER_SELECTOR, conditions
        )
        selector = calldata[:4]
        expected = Web3.keccak(
            text="scopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8)"
        )[:4]
        assert selector == expected
        # Should be valid calldata (no decode errors)
        assert len(calldata) > 4


class TestBuildSetAllowance:
    def test_encodes_daily_limit(self):
        config = AllowanceConfig(
            key=make_allowance_key("agent", "USDC", "daily"),
            balance=500_000_000,  # 500 USDC
            max_refill=500_000_000,
            refill=500_000_000,
            period=86400,  # 1 day
            timestamp=0,
        )
        calldata = build_set_allowance(config)
        selector = calldata[:4]
        expected = Web3.keccak(
            text="setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)"
        )[:4]
        assert selector == expected

    def test_one_time_allowance(self):
        config = AllowanceConfig(
            key=make_allowance_key("agent", "USDC", "lifetime"),
            balance=10_000_000_000,  # 10,000 USDC
            max_refill=0,
            refill=0,
            period=0,  # One-time
            timestamp=0,
        )
        calldata = build_set_allowance(config)
        assert len(calldata) > 4


class TestBuildExecTransactionWithRole:
    def test_encodes_transfer_call(self):
        role_key = encode_role_key("agent_spending")
        usdc = USDC_ADDRESSES[8453]
        # ERC-20 transfer calldata
        transfer_data = (
            TRANSFER_SELECTOR
            + encode(["address", "uint256"], [TEST_SAFE, 100_000_000])
        )

        calldata = build_exec_transaction_with_role(
            to=usdc,
            value=0,
            data=transfer_data,
            operation=0,  # Call
            role_key=role_key,
            should_revert=True,
        )
        selector = calldata[:4]
        expected = Web3.keccak(
            text="execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)"
        )[:4]
        assert selector == expected


# ============ Condition Builder Tests ============

class TestConditionBuilders:
    def test_pass_condition(self):
        c = condition_pass()
        assert c.operator == Operator.PASS
        assert c.comp_value == b""

    def test_within_allowance(self):
        key = make_allowance_key("agent", "USDC", "daily")
        c = condition_within_allowance(key)
        assert c.operator == Operator.WITHIN_ALLOWANCE
        assert c.comp_value == key

    def test_equal_to_address(self):
        c = condition_equal_to(TEST_AGENT)
        assert c.operator == Operator.EQUAL_TO
        # Should contain ABI-encoded address
        decoded = decode(["address"], c.comp_value)
        assert decoded[0].lower() == TEST_AGENT.lower()

    def test_equal_to_int(self):
        c = condition_equal_to(42)
        assert c.operator == Operator.EQUAL_TO
        decoded = decode(["uint256"], c.comp_value)
        assert decoded[0] == 42

    def test_less_than(self):
        c = condition_less_than(1000)
        assert c.operator == Operator.LESS_THAN
        decoded = decode(["uint256"], c.comp_value)
        assert decoded[0] == 1000

    def test_or_combinator(self):
        c = condition_or()
        assert c.operator == Operator.OR
        assert c.comp_value == b""


# ============ Policy Mapping Tests ============

class TestPolicyToRoleConfig:
    def test_basic_policy(self):
        policy = StubSpendingPolicy(limit_per_tx=Decimal("500"))
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
        )

        assert isinstance(config, RoleConfig)
        assert decode_role_key(config.key) == "agent_spending"
        assert TEST_AGENT in config.members
        # Should have transfer + approve permissions for USDC
        assert len(config.permissions) == 2
        # At least per-tx allowance
        assert len(config.allowances) >= 1

    def test_with_daily_limit(self):
        policy = StubSpendingPolicy(
            limit_per_tx=Decimal("100"),
            daily_limit=StubTimeWindowLimit("daily", Decimal("500")),
        )
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
        )

        # Should have per-tx + daily allowance
        assert len(config.allowances) == 2
        daily_allowance = [a for a in config.allowances if a.period == 86400]
        assert len(daily_allowance) == 1
        assert daily_allowance[0].balance == 500_000_000  # 500 USDC

    def test_with_all_time_windows(self):
        policy = StubSpendingPolicy(
            limit_per_tx=Decimal("100"),
            daily_limit=StubTimeWindowLimit("daily", Decimal("500")),
            weekly_limit=StubTimeWindowLimit("weekly", Decimal("2000")),
            monthly_limit=StubTimeWindowLimit("monthly", Decimal("5000")),
        )
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
        )

        # per_tx + daily + weekly + monthly = 4
        assert len(config.allowances) == 4

    def test_with_destination_allowlist(self):
        recipient = "0xDEADbeefDeAdbEEFdeadbeEFDeAdbEEFDeaDBeeF"
        policy = StubSpendingPolicy(
            limit_per_tx=Decimal("100"),
            allowed_destination_addresses=[recipient],
        )
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
        )

        # Transfer permission should have OR + EqualTo conditions for recipient
        transfer_perms = [
            p for p in config.permissions if p.selector == TRANSFER_SELECTOR
        ]
        assert len(transfer_perms) == 1
        # Should have OR condition + address condition + amount condition
        assert len(transfer_perms[0].conditions) >= 3

    def test_multi_token(self):
        policy = StubSpendingPolicy(limit_per_tx=Decimal("100"))
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
            tokens=["USDC", "EURC"],
        )

        # 2 tokens × (transfer + approve) = 4 permissions
        assert len(config.permissions) == 4
        targets = {p.target for p in config.permissions}
        assert USDC_ADDRESSES[8453] in targets
        assert EURC_ADDRESSES[8453] in targets

    def test_unsupported_chain_token_skipped(self):
        policy = StubSpendingPolicy(limit_per_tx=Decimal("100"))
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=99999,  # Non-existent chain
            tokens=["USDC"],
        )

        # No permissions should be generated
        assert len(config.permissions) == 0

    def test_custom_role_name(self):
        policy = StubSpendingPolicy()
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
            role_name="custom_role",
        )
        assert decode_role_key(config.key) == "custom_role"


# ============ Setup Transaction Builder Tests ============

class TestBuildRoleSetupTransactions:
    def test_generates_transactions(self):
        policy = StubSpendingPolicy(
            limit_per_tx=Decimal("500"),
            daily_limit=StubTimeWindowLimit("daily", Decimal("1000")),
        )
        config = policy_to_role_config(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
        )
        txs = build_role_setup_transactions(
            config=config,
            roles_modifier_address=ZODIAC_ADDRESSES["roles_singleton"],
        )

        # Should have: 2 allowances + 1 scope target + 2 scope functions + 1 assign + 1 default role
        assert len(txs) >= 5
        # All should be non-empty bytes
        assert all(len(tx) > 4 for tx in txs)

    def test_empty_config_minimal_transactions(self):
        config = RoleConfig(
            key=encode_role_key("empty"),
            members=[TEST_AGENT],
            permissions=[],
            allowances=[],
        )
        txs = build_role_setup_transactions(
            config=config,
            roles_modifier_address=ZODIAC_ADDRESSES["roles_singleton"],
        )
        # Only assign + default role
        assert len(txs) == 2


# ============ MultiSend Tests ============

class TestBuildMultisendPayload:
    def test_encodes_batch(self):
        tx1 = build_scope_target(
            encode_role_key("agent"), USDC_ADDRESSES[8453]
        )
        tx2 = build_allow_function(
            encode_role_key("agent"),
            USDC_ADDRESSES[8453],
            TRANSFER_SELECTOR,
        )

        payload = build_multisend_payload(
            [tx1, tx2],
            ZODIAC_ADDRESSES["roles_singleton"],
        )

        # Should start with multiSend selector
        selector = payload[:4]
        expected = Web3.keccak(text="multiSend(bytes)")[:4]
        assert selector == expected

    def test_empty_batch(self):
        payload = build_multisend_payload([], ZODIAC_ADDRESSES["roles_singleton"])
        selector = payload[:4]
        expected = Web3.keccak(text="multiSend(bytes)")[:4]
        assert selector == expected


# ============ High-Level Integration Tests ============

class TestBuildAgentWalletSetup:
    def test_complete_setup(self):
        policy = StubSpendingPolicy(
            limit_per_tx=Decimal("500"),
            daily_limit=StubTimeWindowLimit("daily", Decimal("1000")),
        )

        setup = build_agent_wallet_setup(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
        )

        assert isinstance(setup, ZodiacRolesSetup)
        assert setup.roles_modifier_address == ZODIAC_ADDRESSES["roles_singleton"]
        assert setup.role_name == "agent_spending"
        assert setup.agent_address == TEST_AGENT
        assert setup.transaction_count > 0
        assert setup.allowance_count >= 1
        assert setup.permission_count >= 1
        assert len(setup.multisend_payload) > 4
        assert setup.role_key_hex.startswith("0x")

    def test_custom_roles_modifier(self):
        policy = StubSpendingPolicy()
        custom_address = "0x1111111111111111111111111111111111111111"

        setup = build_agent_wallet_setup(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=8453,
            roles_modifier_address=custom_address,
        )

        assert setup.roles_modifier_address == custom_address

    def test_default_roles_modifier(self):
        policy = StubSpendingPolicy()
        setup = build_agent_wallet_setup(
            policy=policy,
            agent_address=TEST_AGENT,
        )
        assert setup.roles_modifier_address == ZODIAC_ADDRESSES["roles_singleton"]

    def test_ethereum_chain(self):
        policy = StubSpendingPolicy(limit_per_tx=Decimal("100"))
        setup = build_agent_wallet_setup(
            policy=policy,
            agent_address=TEST_AGENT,
            chain_id=1,
            tokens=["USDC"],
        )
        # Should have permissions for Ethereum USDC
        assert setup.permission_count == 2  # transfer + approve


# ============ Constants Tests ============

class TestConstants:
    def test_zodiac_addresses(self):
        assert "roles_singleton" in ZODIAC_ADDRESSES
        assert ZODIAC_ADDRESSES["roles_singleton"].startswith("0x")

    def test_usdc_addresses(self):
        assert 8453 in USDC_ADDRESSES  # Base
        assert 1 in USDC_ADDRESSES  # Ethereum
        assert 137 in USDC_ADDRESSES  # Polygon

    def test_eurc_addresses(self):
        assert 8453 in EURC_ADDRESSES  # Base
        assert 1 in EURC_ADDRESSES  # Ethereum

    def test_function_selectors(self):
        # transfer(address,uint256) = 0xa9059cbb
        assert TRANSFER_SELECTOR == bytes.fromhex("a9059cbb")
        # approve(address,uint256) = 0x095ea7b3
        assert APPROVE_SELECTOR == bytes.fromhex("095ea7b3")


class TestEnums:
    def test_execution_options(self):
        assert ExecutionOptions.NONE == 0
        assert ExecutionOptions.SEND == 1
        assert ExecutionOptions.DELEGATE == 2
        assert ExecutionOptions.BOTH == 3

    def test_clearance(self):
        assert Clearance.NONE == 0
        assert Clearance.TARGET == 1
        assert Clearance.FUNCTION == 2

    def test_operator_values(self):
        assert Operator.PASS == 0
        assert Operator.WITHIN_ALLOWANCE == 16
        assert Operator.CALL_WITHIN_ALLOWANCE == 18


# ============ Module Export Tests ============

class TestModuleExports:
    def test_zodiac_roles_importable(self):
        from sardis_chain import zodiac_roles
        assert zodiac_roles is not None

    def test_key_functions_exported(self):
        from sardis_chain.zodiac_roles import (
            build_agent_wallet_setup,
            build_role_setup_transactions,
            encode_role_key,
            policy_to_role_config,
        )
        assert all([
            build_agent_wallet_setup,
            build_role_setup_transactions,
            encode_role_key,
            policy_to_role_config,
        ])
