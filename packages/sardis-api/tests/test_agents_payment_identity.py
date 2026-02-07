"""Tests for agent payment identity bootstrap endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_and_resolve_payment_identity(client):
    # Create agent without wallet to validate ensure_wallet path
    create_agent = await client.post(
        "/api/v2/agents",
        json={
            "name": "Identity Demo Agent",
            "description": "agent for payment identity bootstrap tests",
            "create_wallet": False,
        },
    )
    assert create_agent.status_code == 201
    agent_id = create_agent.json()["agent_id"]
    assert create_agent.json()["wallet_id"] is None

    # Create one-click payment identity
    create_identity = await client.post(
        f"/api/v2/agents/{agent_id}/payment-identity",
        json={
            "mode": "live",
            "chain": "base_sepolia",
            "ensure_wallet": True,
            "ttl_seconds": 3600,
        },
    )
    assert create_identity.status_code == 200
    identity = create_identity.json()

    assert identity["payment_identity_id"].startswith("spi_")
    assert identity["agent_id"] == agent_id
    assert identity["wallet_id"]
    assert identity["mode"] == "live"
    assert identity["chain"] == "base_sepolia"
    assert "--payment-identity" in identity["mcp_init_snippet"]

    # Resolve identity and verify payload
    resolve_identity = await client.get(
        f"/api/v2/agents/payment-identities/{identity['payment_identity_id']}",
    )
    assert resolve_identity.status_code == 200
    resolved = resolve_identity.json()

    assert resolved["payment_identity_id"] == identity["payment_identity_id"]
    assert resolved["agent_id"] == agent_id
    assert resolved["wallet_id"] == identity["wallet_id"]
    assert resolved["policy_ref"].startswith("policy_sha256:")


@pytest.mark.asyncio
async def test_payment_identity_rejects_tampered_signature(client):
    create_agent = await client.post(
        "/api/v2/agents",
        json={"name": "Tamper Identity Agent", "create_wallet": True},
    )
    assert create_agent.status_code == 201
    agent_id = create_agent.json()["agent_id"]

    create_identity = await client.post(
        f"/api/v2/agents/{agent_id}/payment-identity",
        json={"ttl_seconds": 3600},
    )
    assert create_identity.status_code == 200
    identity = create_identity.json()["payment_identity_id"]

    # Flip trailing char to break signature
    tampered = identity[:-1] + ("A" if identity[-1] != "A" else "B")
    resolve = await client.get(f"/api/v2/agents/payment-identities/{tampered}")
    assert resolve.status_code == 401
    assert "signature" in resolve.json()["detail"].lower()
