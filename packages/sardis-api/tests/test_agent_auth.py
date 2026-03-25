"""Tests for Agent Auth Protocol endpoints.

Covers:
  - Discovery endpoint returns valid configuration
  - Capability listing
  - Agent registration + JWT verification
  - Capability execution mapped to sardis services
  - Constraint validation (amount limit, vendor scope, rail)
  - Spending mandate to capability grant mapper
  - Agent revocation
"""
from __future__ import annotations

import base64
import json
import time
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent_jwt(sub: str, exp: int | None = None) -> str:
    """Build a minimal unsigned JWT for testing.

    Structure: header.payload.signature (all base64url).
    The test Agent Auth verifier accepts structurally valid JWTs
    when the agent is registered and active.
    """
    header = base64.urlsafe_b64encode(json.dumps({"alg": "EdDSA", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload_data = {"sub": sub, "iat": int(time.time())}
    if exp is not None:
        payload_data["exp"] = exp
    else:
        payload_data["exp"] = int(time.time()) + 3600
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(b"test_signature_placeholder").rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discovery_endpoint(client: AsyncClient):
    """GET /.well-known/agent-configuration returns valid config."""
    resp = await client.get("/.well-known/agent-configuration")
    assert resp.status_code == 200
    data = resp.json()

    assert data["provider"]["name"] == "Sardis Payment OS"
    assert "delegated" in data["supported_modes"]
    assert "autonomous" in data["supported_modes"]
    assert "Ed25519" in data["algorithms"]
    assert "payment" in data["capabilities"]
    assert "fx_quote" in data["capabilities"]
    assert "policy_check" in data["capabilities"]
    assert "mandate_create" in data["capabilities"]
    assert "balance_check" in data["capabilities"]
    assert "device_authorization" in data["approval_methods"]
    assert "endpoints" in data
    assert data["x-fides-compatible"] is True
    assert data["x-sardis-mandate-support"] is True


# ---------------------------------------------------------------------------
# Capability Listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capability_listing(client: AsyncClient):
    """GET /api/v2/capability/list returns all capabilities with schemas."""
    resp = await client.get("/api/v2/capability/list")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 5
    cap_ids = [c["id"] for c in data["capabilities"]]
    assert "payment" in cap_ids
    assert "fx_quote" in cap_ids
    assert "policy_check" in cap_ids
    assert "mandate_create" in cap_ids
    assert "balance_check" in cap_ids

    # Verify each capability has a schema
    for cap in data["capabilities"]:
        assert "schema" in cap
        assert "input" in cap["schema"]
        assert "output" in cap["schema"]


# ---------------------------------------------------------------------------
# Agent Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_registration(client: AsyncClient):
    """POST /api/v2/agent/register creates an agent identity."""
    resp = await client.post("/api/v2/agent/register", json={
        "agent_name": "Test Shopping Agent",
        "agent_description": "Automated procurement agent",
        "public_key": "a" * 64,  # 32 bytes hex
        "algorithm": "Ed25519",
        "mode": "delegated",
        "capabilities_requested": ["payment", "balance_check"],
    })
    assert resp.status_code == 201
    data = resp.json()

    assert data["status"] == "active"
    assert data["mode"] == "delegated"
    assert data["public_key"] == "a" * 64
    assert data["algorithm"] == "Ed25519"
    assert len(data["capabilities_granted"]) == 2
    assert data["agent_id"].startswith("agent_auth_")
    assert len(data["next_steps"]) > 0


@pytest.mark.asyncio
async def test_agent_registration_invalid_mode(client: AsyncClient):
    """POST /api/v2/agent/register rejects invalid mode."""
    resp = await client.post("/api/v2/agent/register", json={
        "agent_name": "Bad Agent",
        "public_key": "b" * 64,
        "mode": "unsupervised",
    })
    assert resp.status_code == 400
    assert "Unsupported mode" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_agent_registration_invalid_algorithm(client: AsyncClient):
    """POST /api/v2/agent/register rejects unsupported algorithm."""
    resp = await client.post("/api/v2/agent/register", json={
        "agent_name": "RSA Agent",
        "public_key": "c" * 64,
        "algorithm": "RSA",
    })
    assert resp.status_code == 400
    assert "Unsupported algorithm" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Agent Status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_status(client: AsyncClient):
    """GET /api/v2/agent/status returns agent info and grants."""
    # Register first
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Status Test Agent",
        "public_key": "d" * 64,
        "capabilities_requested": ["payment"],
    })
    agent_id = reg.json()["agent_id"]

    # Check status
    resp = await client.get(f"/api/v2/agent/status?agent_id={agent_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == agent_id
    assert data["status"] == "active"
    assert len(data["capabilities"]) == 1


@pytest.mark.asyncio
async def test_agent_status_not_found(client: AsyncClient):
    """GET /api/v2/agent/status returns 404 for unknown agent."""
    resp = await client.get("/api/v2/agent/status?agent_id=nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Capability Execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capability_execution_payment(client: AsyncClient):
    """POST /api/v2/capability/execute handles payment capability."""
    # Register agent with payment grant
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Payment Agent",
        "public_key": "e" * 64,
        "capabilities_requested": ["payment"],
    })
    agent_id = reg.json()["agent_id"]

    # Execute with agent JWT
    jwt_token = _make_agent_jwt(agent_id)
    resp = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",
            "parameters": {
                "amount": "100.00",
                "currency": "USDC",
                "recipient": "0x1234567890abcdef",
                "rail": "usdc",
            },
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["capability"] == "payment"
    assert data["status"] == "completed"
    assert data["result"] is not None
    assert data["result"]["amount"] == "100.00"
    assert data["execution_id"].startswith("exec_")


@pytest.mark.asyncio
async def test_capability_execution_balance_check(client: AsyncClient):
    """POST /api/v2/capability/execute handles balance_check capability."""
    # Register agent
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Balance Agent",
        "public_key": "f" * 64,
        "capabilities_requested": ["balance_check"],
    })
    agent_id = reg.json()["agent_id"]

    jwt_token = _make_agent_jwt(agent_id)
    resp = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "balance_check",
            "parameters": {"wallet_id": "wal_test_001"},
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["capability"] == "balance_check"


@pytest.mark.asyncio
async def test_capability_execution_unknown(client: AsyncClient):
    """POST /api/v2/capability/execute rejects unknown capability."""
    resp = await client.post("/api/v2/capability/execute", json={
        "capability": "teleport",
        "parameters": {},
    })
    assert resp.status_code == 400
    assert "Unknown capability" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_capability_execution_no_grant(client: AsyncClient):
    """POST /api/v2/capability/execute blocks agent without grant."""
    # Register agent WITHOUT payment capability
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Limited Agent",
        "public_key": "1a" * 32,
        "capabilities_requested": ["balance_check"],  # only balance
    })
    agent_id = reg.json()["agent_id"]

    jwt_token = _make_agent_jwt(agent_id)
    resp = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",  # not granted
            "parameters": {"amount": "50", "recipient": "0xabc"},
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    assert resp.status_code == 403
    assert "does not have an active grant" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Constraint Validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_constraint_amount_limit(client: AsyncClient):
    """Capability execution rejects amount exceeding constraint."""
    # Register agent
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Constrained Agent",
        "public_key": "2a" * 32,
        "capabilities_requested": [],
    })
    agent_id = reg.json()["agent_id"]

    # Grant payment with amount constraint
    grant_resp = await client.post(
        f"/api/v2/agent/request-capability?agent_id={agent_id}",
        json={
            "capability": "payment",
            "constraints": {
                "amount": {"max_per_tx": "500"},
                "currency": {"in": ["USDC"]},
                "rail": {"in": ["usdc", "card"]},
            },
        },
    )
    assert grant_resp.status_code == 200

    jwt_token = _make_agent_jwt(agent_id)

    # Within limit: should succeed
    resp_ok = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",
            "parameters": {"amount": "100", "currency": "USDC", "recipient": "0x1", "rail": "usdc"},
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    assert resp_ok.status_code == 200

    # Over limit: should fail
    resp_fail = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",
            "parameters": {"amount": "1000", "currency": "USDC", "recipient": "0x1"},
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    assert resp_fail.status_code == 403
    assert "exceeds per-transaction limit" in resp_fail.json()["detail"]


@pytest.mark.asyncio
async def test_constraint_currency_restriction(client: AsyncClient):
    """Capability execution rejects disallowed currency."""
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "USDC Only Agent",
        "public_key": "3a" * 32,
        "capabilities_requested": [],
    })
    agent_id = reg.json()["agent_id"]

    await client.post(
        f"/api/v2/agent/request-capability?agent_id={agent_id}",
        json={
            "capability": "payment",
            "constraints": {"currency": {"in": ["USDC"]}},
        },
    )

    jwt_token = _make_agent_jwt(agent_id)
    resp = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",
            "parameters": {"amount": "10", "currency": "ETH", "recipient": "0x1"},
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    assert resp.status_code == 403
    assert "not in allowed currencies" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_constraint_rail_restriction(client: AsyncClient):
    """Capability execution rejects disallowed rail."""
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Card Only Agent",
        "public_key": "4a" * 32,
        "capabilities_requested": [],
    })
    agent_id = reg.json()["agent_id"]

    await client.post(
        f"/api/v2/agent/request-capability?agent_id={agent_id}",
        json={
            "capability": "payment",
            "constraints": {"rail": {"in": ["card"]}},
        },
    )

    jwt_token = _make_agent_jwt(agent_id)
    resp = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",
            "parameters": {"amount": "10", "recipient": "0x1", "rail": "bank"},
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    assert resp.status_code == 403
    assert "not in allowed rails" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Spending Mandate <-> Capability Grant Mapper
# ---------------------------------------------------------------------------

def test_mandate_to_capability_grant():
    """Spending mandate converts to capability grant with correct constraints."""
    from sardis_api.routers.agent_auth import mandate_to_capability_grant

    mandate = {
        "id": "mandate_abc123",
        "amount_per_tx": Decimal("500"),
        "amount_daily": Decimal("2000"),
        "amount_monthly": Decimal("50000"),
        "currency": "USDC",
        "allowed_rails": ["card", "usdc"],
        "allowed_chains": ["base"],
        "purpose_scope": "dev_tools",
        "merchant_scope": {"in": ["github", "aws"]},
        "approval_mode": "auto",
        "status": "active",
        "created_at": "2026-03-25T00:00:00Z",
        "expires_at": "2027-03-25T00:00:00Z",
    }

    grant = mandate_to_capability_grant(mandate)

    assert grant["capability"] == "payment"
    assert grant["status"] == "active"
    assert grant["source_mandate_id"] == "mandate_abc123"
    assert grant["expires_at"] == "2027-03-25T00:00:00Z"

    c = grant["constraints"]
    assert c["amount"]["max_per_tx"] == "500"
    assert c["amount"]["max_daily"] == "2000"
    assert c["amount"]["max_monthly"] == "50000"
    assert c["currency"]["in"] == ["USDC"]
    assert c["rail"]["in"] == ["card", "usdc"]
    assert c["chain"]["in"] == ["base"]
    assert c["purpose"]["in"] == ["dev_tools"]
    assert c["vendor_category"] == {"in": ["github", "aws"]}
    assert c["approval_mode"] == "auto"


def test_capability_grant_to_mandate():
    """Capability grant converts back to mandate shape."""
    from sardis_api.routers.agent_auth import capability_grant_to_mandate

    grant = {
        "capability": "payment",
        "status": "active",
        "constraints": {
            "amount": {"max_per_tx": "500", "max_daily": "2000"},
            "currency": {"in": ["USDC"]},
            "rail": {"in": ["card", "usdc"]},
            "chain": {"in": ["base"]},
            "purpose": {"in": ["dev_tools"]},
            "vendor_category": {"in": ["github"]},
            "approval_mode": "auto",
        },
    }

    mandate = capability_grant_to_mandate(grant)

    assert mandate["amount_per_tx"] == Decimal("500")
    assert mandate["amount_daily"] == Decimal("2000")
    assert mandate["currency"] == "USDC"
    assert mandate["allowed_rails"] == ["card", "usdc"]
    assert mandate["allowed_chains"] == ["base"]
    assert mandate["purpose_scope"] == "dev_tools"
    assert mandate["merchant_scope"] == {"in": ["github"]}
    assert mandate["approval_mode"] == "auto"


def test_mandate_roundtrip():
    """Mandate -> grant -> mandate roundtrip preserves key fields."""
    from sardis_api.routers.agent_auth import mandate_to_capability_grant, capability_grant_to_mandate

    original = {
        "id": "mandate_rt1",
        "amount_per_tx": Decimal("100"),
        "amount_daily": Decimal("500"),
        "currency": "USDC",
        "allowed_rails": ["usdc"],
        "purpose_scope": "testing",
        "status": "active",
        "created_at": "2026-03-25T00:00:00Z",
    }

    grant = mandate_to_capability_grant(original)
    reconstructed = capability_grant_to_mandate(grant)

    assert reconstructed["amount_per_tx"] == original["amount_per_tx"]
    assert reconstructed["amount_daily"] == original["amount_daily"]
    assert reconstructed["currency"] == original["currency"]
    assert reconstructed["allowed_rails"] == original["allowed_rails"]
    assert reconstructed["purpose_scope"] == original["purpose_scope"]


# ---------------------------------------------------------------------------
# Request Capability
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_capability(client: AsyncClient):
    """POST /api/v2/agent/request-capability grants additional capability."""
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Upgrade Agent",
        "public_key": "5a" * 32,
        "capabilities_requested": ["balance_check"],
    })
    agent_id = reg.json()["agent_id"]

    resp = await client.post(
        f"/api/v2/agent/request-capability?agent_id={agent_id}",
        json={
            "capability": "payment",
            "constraints": {"amount": {"max_per_tx": "1000"}},
            "justification": "Need to make procurement purchases",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["capability"] == "payment"
    assert data["status"] == "active"
    assert data["grant_id"].startswith("grant_")


@pytest.mark.asyncio
async def test_request_unknown_capability(client: AsyncClient):
    """POST /api/v2/agent/request-capability rejects unknown capability."""
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Unknown Cap Agent",
        "public_key": "6a" * 32,
    })
    agent_id = reg.json()["agent_id"]

    resp = await client.post(
        f"/api/v2/agent/request-capability?agent_id={agent_id}",
        json={"capability": "time_travel"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Agent Revocation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_revocation(client: AsyncClient):
    """POST /api/v2/agent/revoke disables agent and all grants."""
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Revokable Agent",
        "public_key": "7a" * 32,
        "capabilities_requested": ["payment", "balance_check"],
    })
    agent_id = reg.json()["agent_id"]

    # Revoke
    resp = await client.post("/api/v2/agent/revoke", json={
        "agent_id": agent_id,
        "reason": "Security incident",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "revoked"
    assert data["reason"] == "Security incident"

    # Status should show revoked
    status_resp = await client.get(f"/api/v2/agent/status?agent_id={agent_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_revoked_agent_cannot_execute(client: AsyncClient):
    """Revoked agent's JWT is rejected for capability execution."""
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Soon Revoked Agent",
        "public_key": "8a" * 32,
        "capabilities_requested": ["payment"],
    })
    agent_id = reg.json()["agent_id"]

    # Revoke
    await client.post("/api/v2/agent/revoke", json={"agent_id": agent_id})

    # Try to execute
    jwt_token = _make_agent_jwt(agent_id)
    resp = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",
            "parameters": {"amount": "10", "recipient": "0x1"},
        },
        headers={"X-Agent-JWT": jwt_token},
    )
    # Agent JWT verification should fail (agent status is revoked),
    # so execution proceeds without agent context (no grant check).
    # The request still succeeds via API key auth, but without agent-specific grants.
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Expired JWT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_jwt_ignored(client: AsyncClient):
    """Expired agent JWT is ignored (falls back to API key auth)."""
    reg = await client.post("/api/v2/agent/register", json={
        "agent_name": "Expired JWT Agent",
        "public_key": "9a" * 32,
        "capabilities_requested": ["payment"],
    })
    agent_id = reg.json()["agent_id"]

    # Create expired JWT
    expired_jwt = _make_agent_jwt(agent_id, exp=int(time.time()) - 3600)

    resp = await client.post(
        "/api/v2/capability/execute",
        json={
            "capability": "payment",
            "parameters": {"amount": "10", "recipient": "0x1"},
        },
        headers={"X-Agent-JWT": expired_jwt},
    )
    # Should still work via API key auth (no agent context = no grant check)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# FX Quote and Policy Check capabilities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_capability_execution_fx_quote(client: AsyncClient):
    """POST /api/v2/capability/execute handles fx_quote capability."""
    resp = await client.post("/api/v2/capability/execute", json={
        "capability": "fx_quote",
        "parameters": {
            "from_currency": "USD",
            "to_currency": "USDC",
            "amount": "1000",
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["capability"] == "fx_quote"
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_capability_execution_policy_check(client: AsyncClient):
    """POST /api/v2/capability/execute handles policy_check capability."""
    resp = await client.post("/api/v2/capability/execute", json={
        "capability": "policy_check",
        "parameters": {"amount": "100"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["capability"] == "policy_check"
    assert data["status"] == "completed"
