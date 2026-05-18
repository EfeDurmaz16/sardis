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
    assert identity["agent_payment_identity"]["agent_id"] == agent_id
    assert identity["agent_payment_identity"]["did"] == f"did:sardis:{agent_id}"
    assert identity["agent_payment_identity"]["spend_authority_tier"] == "basic"
    assert identity["evidence"]["policy_ref"] == identity["policy_ref"]

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
    assert resolved["agent_payment_identity"]["payment_identity_id"] == identity["payment_identity_id"]
    assert resolved["evidence"]["policy_ref"] == resolved["policy_ref"]


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


@pytest.mark.asyncio
async def test_create_agent_auto_registers_kya_manifest(client):
    create_agent = await client.post(
        "/api/v2/agents",
        json={
            "name": "KYA Sync Agent",
            "description": "agent should auto-register in KYA service",
            "create_wallet": False,
        },
    )
    assert create_agent.status_code == 201
    agent_id = create_agent.json()["agent_id"]

    kya_status = await client.get(f"/api/v2/compliance/kya/{agent_id}")
    assert kya_status.status_code == 200
    payload = kya_status.json()
    assert payload["agent_id"] == agent_id
    assert payload["level"] == "basic"
    assert payload["status"] == "active"


@pytest.mark.asyncio
async def test_get_agent_payment_identity_profile(client):
    create_agent = await client.post(
        "/api/v2/agents",
        json={
            "name": "Canonical Identity Agent",
            "description": "agent profile endpoint smoke test",
            "create_wallet": True,
        },
    )
    assert create_agent.status_code == 201
    agent = create_agent.json()

    profile = await client.get(f"/api/v2/agents/{agent['agent_id']}/agent-payment-identity")
    assert profile.status_code == 200
    body = profile.json()

    assert body["agent_id"] == agent["agent_id"]
    assert body["organization_id"] == agent["owner_id"]
    assert body["wallet_id"] == agent["wallet_id"]
    assert body["did"] == f"did:sardis:{agent['agent_id']}"
    assert body["policy_ref"].startswith("policy_sha256:")
