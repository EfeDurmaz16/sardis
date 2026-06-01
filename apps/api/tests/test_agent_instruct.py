"""Tests for the de-demoed agent /instruct endpoint and wallet provisioning.

The /instruct endpoint used to be canned keyword matching ("Simple instruction
parsing for demo"). It now runs payment-style instructions through the real
SpendingPolicy engine (read-only — no money moves) and returns an honest
allow / requires_approval / deny decision. These tests pin that behaviour and
the helper parsers.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from server.routes.agents.lifecycle import (
    _classify_instruction,
    _extract_amount,
    _extract_merchant,
)

# ---------------------------------------------------------------------------
# Parser helper unit tests (no app needed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("pay $20 to openai", Decimal("20")),
        ("send 1,250.50 usd to vendor", Decimal("1250.50")),
        ("buy usdc 5 of credits", Decimal("5")),
        ("transfer €99 to bob", Decimal("99")),
        ("pay 49.99 dollars", Decimal("49.99")),
        ("what is my balance", None),
        ("pay the invoice", None),
    ],
)
def test_extract_amount(text, expected):
    assert _extract_amount(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("pay $20 to openai", "openai"),
        ("buy credits at anthropic for my project", "anthropic"),
        ("send $5 to acme-corp.", "acme-corp"),
        ("pay $5", None),
    ],
)
def test_extract_merchant(text, expected):
    assert _extract_merchant(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("pay $20 to openai", "payment"),
        ("buy some compute", "payment"),
        ("what is my balance", "balance"),
        ("show my spending policy", "policy"),
        ("hello there", "other"),
    ],
)
def test_classify_instruction(text, expected):
    assert _classify_instruction(text) == expected


# ---------------------------------------------------------------------------
# /instruct endpoint integration tests
# ---------------------------------------------------------------------------

async def _create_agent(client, **policy_kwargs):
    body = {
        "name": "Instruct Test Agent",
        "create_wallet": True,
    }
    body.update(policy_kwargs)
    resp = await client.post("/api/v2/agents", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["agent_id"]


@pytest.mark.asyncio
async def test_instruct_payment_within_policy_allows(client):
    agent_id = await _create_agent(
        client,
        spending_limits={"per_transaction": "100.00", "daily": "1000.00",
                         "monthly": "10000.00", "total": "100000.00"},
        policy={"auto_approve_below": "100.00"},
    )
    resp = await client.post(f"/api/v2/agents/{agent_id}/instruct",
                             json={"instruction": "pay $20 to openai"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["intent"] == "payment"
    assert data["decision"] == "allow"
    assert data["parsed"]["amount"] == "20"
    assert data["parsed"]["merchant"] == "openai"
    # Read-only — never executes
    assert data["tx_id"] is None


@pytest.mark.asyncio
async def test_instruct_payment_over_per_tx_limit_denies(client):
    agent_id = await _create_agent(
        client,
        spending_limits={"per_transaction": "50.00", "daily": "1000.00",
                         "monthly": "10000.00", "total": "100000.00"},
    )
    resp = await client.post(f"/api/v2/agents/{agent_id}/instruct",
                             json={"instruction": "pay $500 to randomvendor"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["intent"] == "payment"
    assert data["decision"] == "deny"
    assert data["tx_id"] is None


@pytest.mark.asyncio
async def test_instruct_payment_above_approval_threshold_requires_approval(client):
    agent_id = await _create_agent(
        client,
        spending_limits={"per_transaction": "1000.00", "daily": "10000.00",
                         "monthly": "100000.00", "total": "1000000.00"},
        policy={"require_approval_above": "100.00"},
    )
    resp = await client.post(f"/api/v2/agents/{agent_id}/instruct",
                             json={"instruction": "pay $250 to bigvendor"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["intent"] == "payment"
    assert data["decision"] == "requires_approval"
    assert data["tx_id"] is None


@pytest.mark.asyncio
async def test_instruct_payment_to_blocked_merchant_denies(client):
    agent_id = await _create_agent(
        client,
        policy={"blocked_merchants": ["casino"]},
    )
    resp = await client.post(f"/api/v2/agents/{agent_id}/instruct",
                             json={"instruction": "pay $10 to casino"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["decision"] == "deny"


@pytest.mark.asyncio
async def test_instruct_payment_without_amount_denies(client):
    agent_id = await _create_agent(client)
    resp = await client.post(f"/api/v2/agents/{agent_id}/instruct",
                             json={"instruction": "buy me something nice"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["intent"] == "payment"
    assert data["decision"] == "deny"
    assert data["reason_code"] == "amount_not_specified"


@pytest.mark.asyncio
async def test_instruct_balance_returns_real_wallet(client):
    agent_id = await _create_agent(client)
    resp = await client.post(f"/api/v2/agents/{agent_id}/instruct",
                             json={"instruction": "what is my wallet balance"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["intent"] == "balance"
    assert data["tool_call"]["name"] == "get_wallet_balance"


@pytest.mark.asyncio
async def test_instruct_policy_query(client):
    agent_id = await _create_agent(client)
    resp = await client.post(f"/api/v2/agents/{agent_id}/instruct",
                             json={"instruction": "what is my spending policy"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["intent"] == "policy"
    assert "policy" in data["response"].lower()
