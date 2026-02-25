from __future__ import annotations

from decimal import Decimal

from sardis_v2_core.spending_policy import SpendingPolicy
from sardis_v2_core.spending_policy_json import spending_policy_from_json, spending_policy_to_json


def test_execution_context_denies_non_allowlisted_destination():
    policy = SpendingPolicy(
        agent_id="agent_1",
        limit_total=Decimal("1000"),
        allowed_destination_addresses=["0xabc"],
    )

    ok, reason = policy.validate_execution_context(
        destination="0xdef",
        chain="base",
        token="USDC",
    )

    assert ok is False
    assert reason == "destination_not_allowlisted"


def test_execution_context_denies_blocked_destination_even_if_allowlisted():
    policy = SpendingPolicy(
        agent_id="agent_1",
        limit_total=Decimal("1000"),
        allowed_destination_addresses=["0xabc"],
        blocked_destination_addresses=["0xabc"],
    )

    ok, reason = policy.validate_execution_context(
        destination="0xabc",
        chain="base",
        token="USDC",
    )

    assert ok is False
    assert reason == "destination_blocked"


def test_execution_context_denies_non_allowlisted_chain_and_token():
    policy = SpendingPolicy(
        agent_id="agent_1",
        limit_total=Decimal("1000"),
        allowed_chains=["base"],
        allowed_tokens=["USDC"],
    )

    ok_chain, reason_chain = policy.validate_execution_context(
        destination="0xabc",
        chain="ethereum",
        token="USDC",
    )
    ok_token, reason_token = policy.validate_execution_context(
        destination="0xabc",
        chain="base",
        token="DAI",
    )

    assert ok_chain is False
    assert reason_chain == "chain_not_allowlisted"
    assert ok_token is False
    assert reason_token == "token_not_allowlisted"


def test_execution_context_allows_when_within_guardrails():
    policy = SpendingPolicy(
        agent_id="agent_1",
        limit_total=Decimal("1000"),
        allowed_chains=["base"],
        allowed_tokens=["USDC"],
        allowed_destination_addresses=["0xabc"],
    )

    ok, reason = policy.validate_execution_context(
        destination="0xAbC",
        chain="BASE",
        token="usdc",
    )

    assert ok is True
    assert reason == "OK"


def test_guardrails_roundtrip_in_policy_json():
    policy = SpendingPolicy(
        agent_id="agent_1",
        limit_total=Decimal("1000"),
        allowed_chains=["base", "base-sepolia"],
        allowed_tokens=["USDC"],
        allowed_destination_addresses=["0xabc"],
        blocked_destination_addresses=["0xdef"],
    )

    payload = spending_policy_to_json(policy)
    restored = spending_policy_from_json(payload)

    assert restored.allowed_chains == ["base", "base-sepolia"]
    assert restored.allowed_tokens == ["USDC"]
    assert restored.allowed_destination_addresses == ["0xabc"]
    assert restored.blocked_destination_addresses == ["0xdef"]
