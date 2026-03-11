"""Zodiac Roles Modifier v2 — on-chain policy enforcement for agent wallets.

Integrates Gnosis Guild's Zodiac Roles Modifier with Sardis Safe smart accounts
to enforce spending policies on-chain. Maps SpendingPolicy rules to Roles v2
permissions: scoped targets, function-level conditions, and auto-refill allowances.

Architecture:
    [AI Agent (Turnkey MPC EOA)]
            |
            v  execTransactionWithRole(...)
    [Roles Modifier Proxy]   ← checks role + target + function + conditions + allowances
            |
            v
        [Safe Smart Account]  ← executes the authorized transaction

Spec: https://docs.roles.gnosisguild.org/
Audits: G0 Group, Omniscia
Pre-deployed singleton: 0x9646fDAD06d3e24444381f44362a3B0eB343D337 (all EVM chains)

Issue: #134
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import IntEnum
from typing import Any

from eth_abi import encode
from web3 import Web3

logger = logging.getLogger(__name__)

# ============ Zodiac Roles v2 Addresses ============
# Deterministic CREATE2 — same on all 18+ chains

ZODIAC_ADDRESSES = {
    "roles_singleton": "0x9646fDAD06d3e24444381f44362a3B0eB343D337",
    "integrity": "0x6a6Af4b16458Bc39817e4019fB02BD3b26d41049",
    "packer": "0x61C5B1bE435391fDd7BC6703F3740C0d11728a8C",
    "multisend_unwrapper": "0xB4Cd4bb764C089f20DA18700CE8bc5e49F369efD",
}

# Common ERC-20 function selectors
TRANSFER_SELECTOR = Web3.keccak(text="transfer(address,uint256)")[:4]
APPROVE_SELECTOR = Web3.keccak(text="approve(address,uint256)")[:4]
TRANSFER_FROM_SELECTOR = Web3.keccak(text="transferFrom(address,address,uint256)")[:4]

# USDC addresses per chain (checksummed)
USDC_ADDRESSES: dict[int, str] = {
    1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",       # Ethereum
    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",     # Base
    137: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",      # Polygon
    42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",    # Arbitrum
    10: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",       # Optimism
}

EURC_ADDRESSES: dict[int, str] = {
    1: "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c",       # Ethereum
    8453: "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",    # Base
}

# Max role key length (32 bytes when encoded)
MAX_ROLE_KEY_LENGTH = 32


# ============ Enums ============

class ExecutionOptions(IntEnum):
    """What a role can do when calling a target."""
    NONE = 0        # Call only, no ETH value, no delegatecall
    SEND = 1        # Can send ETH value
    DELEGATE = 2    # Can delegatecall
    BOTH = 3        # Can send ETH and delegatecall


class Clearance(IntEnum):
    """Target access level."""
    NONE = 0        # Not allowed (default)
    TARGET = 1      # All functions allowed (wildcard)
    FUNCTION = 2    # Only specific whitelisted functions


class Operator(IntEnum):
    """Condition operators for parameter scoping."""
    PASS = 0
    AND = 1
    OR = 2
    NOR = 3
    MATCHES = 4
    EQUAL_TO = 5
    GREATER_THAN = 6
    LESS_THAN = 7
    SIGNED_INT_GREATER_THAN = 8
    SIGNED_INT_LESS_THAN = 9
    BITMASK = 10
    CUSTOM = 11
    ARRAY_SOME = 12
    ARRAY_EVERY = 13
    ARRAY_SUBSET = 14
    EQUAL_TO_AVATAR = 15
    WITHIN_ALLOWANCE = 16
    ETHER_WITHIN_ALLOWANCE = 17
    CALL_WITHIN_ALLOWANCE = 18


class ParameterType(IntEnum):
    """ABI parameter types for conditions."""
    STATIC = 0      # Fixed-size (uint256, address, bool, etc.)
    DYNAMIC = 1     # Variable-size (bytes, string)
    TUPLE = 2       # Struct/tuple


# ============ Data Types ============

@dataclass
class ConditionFlat:
    """A single condition in the flat format expected by scopeFunction().

    The conditions array is evaluated as a tree. Parent/children relationships
    are determined by the `parent` index (0 = root level).
    """
    parent: int = 0
    param_type: ParameterType = ParameterType.STATIC
    operator: Operator = Operator.PASS
    comp_value: bytes = b""

    def encode(self) -> tuple[int, int, int, bytes]:
        """Encode to tuple for ABI encoding."""
        return (self.parent, self.param_type, self.operator, self.comp_value)


@dataclass
class AllowanceConfig:
    """Configuration for a spending/rate allowance.

    Allowances are consumed atomically during transaction execution and
    auto-refill on a configurable period.
    """
    key: bytes  # bytes32 allowance identifier
    balance: int  # Initial balance (token units, 6 decimals for USDC)
    max_refill: int  # Maximum accumulated balance
    refill: int  # Amount added each period
    period: int  # Seconds between refills (0 = one-time)
    timestamp: int = 0  # Last refill timestamp (0 = now)


@dataclass
class RolePermission:
    """A single permission entry for a role."""
    target: str  # Contract address
    selector: bytes  # 4-byte function selector
    conditions: list[ConditionFlat] = field(default_factory=list)
    execution_options: ExecutionOptions = ExecutionOptions.NONE


@dataclass
class RoleConfig:
    """Complete configuration for a Zodiac Role."""
    key: bytes  # bytes32 role key
    members: list[str] = field(default_factory=list)  # Addresses
    permissions: list[RolePermission] = field(default_factory=list)
    allowances: list[AllowanceConfig] = field(default_factory=list)


# ============ Key Encoding ============

def encode_role_key(name: str) -> bytes:
    """Encode a human-readable role name to bytes32.

    Valid: a-z, 0-9, underscore, max 32 chars.

    Args:
        name: Role name (e.g. "agent_spending").

    Returns:
        bytes32 role key, right-padded with zeros.

    Raises:
        ValueError: If name is invalid.
    """
    if not name or len(name) > MAX_ROLE_KEY_LENGTH:
        raise ValueError(f"Role key must be 1-{MAX_ROLE_KEY_LENGTH} characters")
    encoded = name.encode("ascii")
    if len(encoded) > 32:
        raise ValueError(f"Role key exceeds 32 bytes when encoded")
    return encoded.ljust(32, b"\x00")


def decode_role_key(key: bytes) -> str:
    """Decode a bytes32 role key to human-readable string."""
    return key.rstrip(b"\x00").decode("ascii")


# ============ Allowance Key Helpers ============

def make_allowance_key(role_name: str, token: str, window: str) -> bytes:
    """Create a deterministic allowance key.

    Args:
        role_name: Role name (e.g. "agent_spending").
        token: Token symbol (e.g. "USDC").
        window: Time window (e.g. "daily", "weekly", "monthly", "per_tx").

    Returns:
        bytes32 allowance key.
    """
    raw = f"{role_name}:{token}:{window}"
    return Web3.keccak(text=raw)


# ============ Calldata Builders ============

def build_assign_roles(
    module_address: str,
    role_keys: list[bytes],
    member_of: list[bool],
) -> bytes:
    """Build assignRoles(address,bytes32[],bool[]) calldata.

    Args:
        module_address: Address to assign/revoke roles for.
        role_keys: List of role keys.
        member_of: List of bools (True = assign, False = revoke).

    Returns:
        Encoded calldata.
    """
    selector = Web3.keccak(text="assignRoles(address,bytes32[],bool[])")[:4]
    params = encode(
        ["address", "bytes32[]", "bool[]"],
        [Web3.to_checksum_address(module_address), role_keys, member_of],
    )
    return selector + params


def build_set_default_role(
    module_address: str,
    role_key: bytes,
) -> bytes:
    """Build setDefaultRole(address,bytes32) calldata."""
    selector = Web3.keccak(text="setDefaultRole(address,bytes32)")[:4]
    params = encode(
        ["address", "bytes32"],
        [Web3.to_checksum_address(module_address), role_key],
    )
    return selector + params


def build_scope_target(role_key: bytes, target_address: str) -> bytes:
    """Build scopeTarget(bytes32,address) calldata.

    Sets target clearance to Function (only whitelisted functions allowed).
    """
    selector = Web3.keccak(text="scopeTarget(bytes32,address)")[:4]
    params = encode(
        ["bytes32", "address"],
        [role_key, Web3.to_checksum_address(target_address)],
    )
    return selector + params


def build_allow_target(
    role_key: bytes,
    target_address: str,
    options: ExecutionOptions = ExecutionOptions.NONE,
) -> bytes:
    """Build allowTarget(bytes32,address,uint8) calldata.

    Sets target clearance to Target (all functions allowed).
    """
    selector = Web3.keccak(text="allowTarget(bytes32,address,uint8)")[:4]
    params = encode(
        ["bytes32", "address", "uint8"],
        [role_key, Web3.to_checksum_address(target_address), options],
    )
    return selector + params


def build_revoke_target(role_key: bytes, target_address: str) -> bytes:
    """Build revokeTarget(bytes32,address) calldata."""
    selector = Web3.keccak(text="revokeTarget(bytes32,address)")[:4]
    params = encode(
        ["bytes32", "address"],
        [role_key, Web3.to_checksum_address(target_address)],
    )
    return selector + params


def build_allow_function(
    role_key: bytes,
    target_address: str,
    fn_selector: bytes,
    options: ExecutionOptions = ExecutionOptions.NONE,
) -> bytes:
    """Build allowFunction(bytes32,address,bytes4,uint8) calldata.

    Allows calling a function with any parameters (wildcard).
    """
    selector = Web3.keccak(
        text="allowFunction(bytes32,address,bytes4,uint8)"
    )[:4]
    # Pad fn_selector to bytes4
    fn_sel = fn_selector[:4].ljust(4, b"\x00")
    params = encode(
        ["bytes32", "address", "bytes4", "uint8"],
        [role_key, Web3.to_checksum_address(target_address), fn_sel, options],
    )
    return selector + params


def build_scope_function(
    role_key: bytes,
    target_address: str,
    fn_selector: bytes,
    conditions: list[ConditionFlat],
    options: ExecutionOptions = ExecutionOptions.NONE,
) -> bytes:
    """Build scopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8) calldata.

    Allows calling a function with parameter conditions enforced.
    """
    selector = Web3.keccak(
        text="scopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8)"
    )[:4]
    fn_sel = fn_selector[:4].ljust(4, b"\x00")
    conditions_tuples = [c.encode() for c in conditions]
    params = encode(
        ["bytes32", "address", "bytes4", "(uint8,uint8,uint8,bytes)[]", "uint8"],
        [
            role_key,
            Web3.to_checksum_address(target_address),
            fn_sel,
            conditions_tuples,
            options,
        ],
    )
    return selector + params


def build_set_allowance(config: AllowanceConfig) -> bytes:
    """Build setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64) calldata."""
    selector = Web3.keccak(
        text="setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)"
    )[:4]
    params = encode(
        ["bytes32", "uint128", "uint128", "uint128", "uint64", "uint64"],
        [
            config.key,
            config.balance,
            config.max_refill,
            config.refill,
            config.period,
            config.timestamp,
        ],
    )
    return selector + params


def build_exec_transaction_with_role(
    to: str,
    value: int,
    data: bytes,
    operation: int,
    role_key: bytes,
    should_revert: bool = True,
) -> bytes:
    """Build execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool) calldata.

    This is what the agent calls to execute a transaction through the Roles Modifier.
    """
    selector = Web3.keccak(
        text="execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)"
    )[:4]
    params = encode(
        ["address", "uint256", "bytes", "uint8", "bytes32", "bool"],
        [Web3.to_checksum_address(to), value, data, operation, role_key, should_revert],
    )
    return selector + params


# ============ Condition Builders ============

def condition_within_allowance(allowance_key: bytes) -> ConditionFlat:
    """Create a WithinAllowance condition for a parameter.

    The parameter's value is deducted from the referenced allowance.
    Used to enforce spending limits on transfer amounts.
    """
    return ConditionFlat(
        parent=0,
        param_type=ParameterType.STATIC,
        operator=Operator.WITHIN_ALLOWANCE,
        comp_value=allowance_key,
    )


def condition_equal_to(value: str | int | bytes) -> ConditionFlat:
    """Create an EqualTo condition for a parameter.

    For addresses: pass hex string.
    For uint256: pass int.
    For bytes: pass raw bytes.
    """
    if isinstance(value, str) and value.startswith("0x"):
        comp = encode(["address"], [Web3.to_checksum_address(value)])
    elif isinstance(value, int):
        comp = encode(["uint256"], [value])
    else:
        comp = value if isinstance(value, bytes) else encode(["bytes32"], [value])

    return ConditionFlat(
        parent=0,
        param_type=ParameterType.STATIC,
        operator=Operator.EQUAL_TO,
        comp_value=comp,
    )


def condition_less_than(value: int) -> ConditionFlat:
    """Create a LessThan condition for a numeric parameter."""
    return ConditionFlat(
        parent=0,
        param_type=ParameterType.STATIC,
        operator=Operator.LESS_THAN,
        comp_value=encode(["uint256"], [value]),
    )


def condition_or() -> ConditionFlat:
    """Create an OR logical combinator condition."""
    return ConditionFlat(
        parent=0,
        param_type=ParameterType.STATIC,
        operator=Operator.OR,
        comp_value=b"",
    )


def condition_pass() -> ConditionFlat:
    """Create a Pass condition (no constraint)."""
    return ConditionFlat(
        parent=0,
        param_type=ParameterType.STATIC,
        operator=Operator.PASS,
        comp_value=b"",
    )


# ============ Policy Mapping ============

def _usdc_decimals() -> int:
    """USDC uses 6 decimals."""
    return 6


def _to_token_units(amount: Decimal, decimals: int = 6) -> int:
    """Convert human-readable amount to token units (integer)."""
    return int(amount * (10 ** decimals))


def _window_to_seconds(window_type: str) -> int:
    """Convert window type string to seconds."""
    mapping = {
        "daily": 86400,
        "weekly": 604800,
        "monthly": 2592000,  # 30 days
    }
    return mapping.get(window_type, 86400)


def policy_to_role_config(
    policy: Any,  # SpendingPolicy from sardis_v2_core
    agent_address: str,
    chain_id: int = 8453,
    role_name: str = "agent_spending",
    tokens: list[str] | None = None,
) -> RoleConfig:
    """Map a SpendingPolicy to a Zodiac Roles v2 RoleConfig.

    Translates Sardis spending policy rules into on-chain Roles permissions:
    - Per-transaction limit → WithinAllowance condition on transfer amount
    - Daily/weekly/monthly limits → Separate allowances with auto-refill
    - Allowed tokens → Scoped targets per token contract
    - Destination allowlists → EqualTo conditions on transfer recipient

    Args:
        policy: SpendingPolicy instance.
        agent_address: Agent's Ethereum address (Turnkey MPC signer).
        chain_id: Target chain ID.
        role_name: Name for the role (default: "agent_spending").
        tokens: Token symbols to scope (default: ["USDC"]).

    Returns:
        RoleConfig ready for on-chain deployment.
    """
    if tokens is None:
        tokens = ["USDC"]

    role_key = encode_role_key(role_name)
    permissions: list[RolePermission] = []
    allowances: list[AllowanceConfig] = []

    for token_symbol in tokens:
        token_address = _get_token_address(token_symbol, chain_id)
        if not token_address:
            logger.warning(
                "No %s address for chain %d, skipping", token_symbol, chain_id
            )
            continue

        # Per-transaction allowance
        per_tx_key = make_allowance_key(role_name, token_symbol, "per_tx")
        per_tx_units = _to_token_units(policy.limit_per_tx)
        allowances.append(AllowanceConfig(
            key=per_tx_key,
            balance=per_tx_units,
            max_refill=per_tx_units,
            refill=per_tx_units,
            period=1,  # Refills every second (effectively per-tx)
            timestamp=0,
        ))

        # Time-window allowances
        for window_limit in [policy.daily_limit, policy.weekly_limit, policy.monthly_limit]:
            if window_limit is None:
                continue
            window_key = make_allowance_key(
                role_name, token_symbol, window_limit.window_type
            )
            window_units = _to_token_units(window_limit.limit_amount)
            allowances.append(AllowanceConfig(
                key=window_key,
                balance=window_units,
                max_refill=window_units,
                refill=window_units,
                period=_window_to_seconds(window_limit.window_type),
                timestamp=0,
            ))

        # Build transfer() permission with conditions
        transfer_conditions = _build_transfer_conditions(
            policy=policy,
            role_name=role_name,
            token_symbol=token_symbol,
        )

        permissions.append(RolePermission(
            target=token_address,
            selector=TRANSFER_SELECTOR,
            conditions=transfer_conditions,
            execution_options=ExecutionOptions.NONE,
        ))

        # Build approve() permission (capped to per-tx limit)
        approve_conditions = [
            condition_pass(),  # spender (any)
            condition_within_allowance(per_tx_key),  # amount
        ]
        permissions.append(RolePermission(
            target=token_address,
            selector=APPROVE_SELECTOR,
            conditions=approve_conditions,
            execution_options=ExecutionOptions.NONE,
        ))

    return RoleConfig(
        key=role_key,
        members=[agent_address],
        permissions=permissions,
        allowances=allowances,
    )


def _build_transfer_conditions(
    policy: Any,
    role_name: str,
    token_symbol: str,
) -> list[ConditionFlat]:
    """Build conditions for ERC-20 transfer(address,uint256).

    Parameter 0: recipient (address)
    Parameter 1: amount (uint256)
    """
    conditions: list[ConditionFlat] = []

    # Condition for parameter 0: recipient
    allowed_addrs = getattr(policy, "allowed_destination_addresses", [])
    if allowed_addrs and len(allowed_addrs) > 0:
        # Create OR group for allowed recipients
        or_cond = condition_or()
        or_cond.parent = 0
        conditions.append(or_cond)
        or_index = len(conditions)  # 1-based parent ref in the tree

        for addr in allowed_addrs:
            eq_cond = condition_equal_to(addr)
            eq_cond.parent = or_index
            conditions.append(eq_cond)
    else:
        # No recipient restriction
        conditions.append(condition_pass())

    # Condition for parameter 1: amount within allowance
    per_tx_key = make_allowance_key(role_name, token_symbol, "per_tx")
    amount_condition = condition_within_allowance(per_tx_key)
    conditions.append(amount_condition)

    return conditions


def _get_token_address(token_symbol: str, chain_id: int) -> str | None:
    """Look up token contract address by symbol and chain."""
    registry: dict[str, dict[int, str]] = {
        "USDC": USDC_ADDRESSES,
        "EURC": EURC_ADDRESSES,
    }
    addresses = registry.get(token_symbol.upper(), {})
    return addresses.get(chain_id)


# ============ Setup Transaction Builder ============

def build_role_setup_transactions(
    config: RoleConfig,
    roles_modifier_address: str,
) -> list[bytes]:
    """Build a list of calldata payloads to configure a role on-chain.

    These transactions must be executed by the Safe (as owner of the
    Roles Modifier), typically via a MultiSend batch.

    The order is:
    1. Set allowances (must exist before conditions reference them)
    2. Scope targets (set clearance to Function)
    3. Scope functions (with conditions)
    4. Assign role to members

    Args:
        config: Complete role configuration.
        roles_modifier_address: Address of the Roles Modifier proxy.

    Returns:
        List of encoded calldata payloads, each targeting the roles_modifier_address.
    """
    transactions: list[bytes] = []

    # 1. Set allowances
    for allowance in config.allowances:
        transactions.append(build_set_allowance(allowance))

    # 2. Scope targets and functions
    scoped_targets: set[str] = set()
    for perm in config.permissions:
        target = Web3.to_checksum_address(perm.target)

        # Scope the target (only once per target)
        if target not in scoped_targets:
            transactions.append(build_scope_target(config.key, target))
            scoped_targets.add(target)

        # Scope the function with conditions
        if perm.conditions:
            transactions.append(build_scope_function(
                role_key=config.key,
                target_address=target,
                fn_selector=perm.selector,
                conditions=perm.conditions,
                options=perm.execution_options,
            ))
        else:
            transactions.append(build_allow_function(
                role_key=config.key,
                target_address=target,
                fn_selector=perm.selector,
                options=perm.execution_options,
            ))

    # 3. Assign role to members
    for member in config.members:
        transactions.append(build_assign_roles(
            module_address=member,
            role_keys=[config.key],
            member_of=[True],
        ))

    # 4. Set default role for members
    for member in config.members:
        transactions.append(build_set_default_role(
            module_address=member,
            role_key=config.key,
        ))

    return transactions


def build_multisend_payload(
    transactions: list[bytes],
    target_address: str,
) -> bytes:
    """Encode a batch of transactions into a MultiSend payload.

    Each transaction in the batch calls the same target (Roles Modifier).

    MultiSend format per entry:
        operation (uint8, 0=Call) | to (address, 20B) | value (uint256, 32B) |
        dataLength (uint256, 32B) | data (bytes)

    Args:
        transactions: List of calldata payloads.
        target_address: Target for all calls (Roles Modifier proxy).

    Returns:
        Packed MultiSend payload.
    """
    target_bytes = bytes.fromhex(target_address[2:].lower().zfill(40))
    packed = b""

    for tx_data in transactions:
        packed += (
            b"\x00"  # operation = Call
            + target_bytes  # to (20 bytes)
            + int.to_bytes(0, 32, "big")  # value = 0
            + int.to_bytes(len(tx_data), 32, "big")  # dataLength
            + tx_data  # data
        )

    # Wrap in multiSend(bytes) call
    selector = Web3.keccak(text="multiSend(bytes)")[:4]
    params = encode(["bytes"], [packed])
    return selector + params


# ============ High-Level Integration ============

@dataclass
class ZodiacRolesSetup:
    """Result of building a Zodiac Roles setup for an agent wallet.

    Contains all the information needed to deploy and configure the
    Roles Modifier for a Safe wallet.
    """
    roles_modifier_address: str
    role_key: bytes
    role_name: str
    agent_address: str
    setup_transactions: list[bytes]
    multisend_payload: bytes
    allowance_count: int
    permission_count: int

    @property
    def role_key_hex(self) -> str:
        return "0x" + self.role_key.hex()

    @property
    def transaction_count(self) -> int:
        return len(self.setup_transactions)


def build_agent_wallet_setup(
    policy: Any,  # SpendingPolicy
    agent_address: str,
    chain_id: int = 8453,
    roles_modifier_address: str | None = None,
    role_name: str = "agent_spending",
    tokens: list[str] | None = None,
) -> ZodiacRolesSetup:
    """Build a complete Zodiac Roles setup for an agent wallet.

    This is the main entry point. Given a SpendingPolicy, it produces
    all the on-chain transactions needed to configure the Roles Modifier
    so the agent can only execute transactions within policy bounds.

    Args:
        policy: SpendingPolicy defining the agent's spending rules.
        agent_address: Agent's Ethereum address (Turnkey MPC signer).
        chain_id: Target chain ID (default: 8453 = Base).
        roles_modifier_address: Address of the Roles Modifier proxy.
            Defaults to the pre-deployed singleton.
        role_name: Human-readable role name.
        tokens: Token symbols to configure (default: ["USDC"]).

    Returns:
        ZodiacRolesSetup with all transactions and metadata.
    """
    if roles_modifier_address is None:
        roles_modifier_address = ZODIAC_ADDRESSES["roles_singleton"]

    # Map policy to role config
    role_config = policy_to_role_config(
        policy=policy,
        agent_address=agent_address,
        chain_id=chain_id,
        role_name=role_name,
        tokens=tokens,
    )

    # Build setup transactions
    setup_txs = build_role_setup_transactions(
        config=role_config,
        roles_modifier_address=roles_modifier_address,
    )

    # Build multisend payload
    multisend = build_multisend_payload(
        transactions=setup_txs,
        target_address=roles_modifier_address,
    )

    return ZodiacRolesSetup(
        roles_modifier_address=roles_modifier_address,
        role_key=role_config.key,
        role_name=role_name,
        agent_address=agent_address,
        setup_transactions=setup_txs,
        multisend_payload=multisend,
        allowance_count=len(role_config.allowances),
        permission_count=len(role_config.permissions),
    )
