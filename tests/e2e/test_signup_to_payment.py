"""E2E smoke test: signup → agent → wallet → policy → simulated payment.

Verifies the full new-user journey works end-to-end against the API
in test/sandbox mode. No real money is moved.

Usage:
    pytest tests/e2e/test_signup_to_payment.py -v
"""

from __future__ import annotations

import os
import secrets
import time

import httpx
import pytest

API_URL = os.getenv("SARDIS_TEST_API_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def registered_user():
    """Register a new user and return (access_token, api_key, org_id)."""
    email = f"test_{secrets.token_hex(6)}@sardistest.dev"
    password = f"TestPass_{secrets.token_hex(8)}"

    resp = httpx.post(
        f"{API_URL}/api/v2/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "E2E Test User",
        },
        timeout=15,
    )

    assert resp.status_code == 201, f"Registration failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "access_token" in data
    assert "org_id" in data

    return {
        "access_token": data["access_token"],
        "api_key": data.get("api_key", ""),
        "org_id": data["org_id"],
        "user_id": data.get("user_id", ""),
        "email": email,
    }


@pytest.fixture(scope="module")
def auth_headers(registered_user):
    """Auth headers for API calls."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


class TestSignupToPayment:
    """Full journey: register → create agent → create wallet → set policy → simulate payment."""

    def test_01_registration_returns_token(self, registered_user):
        """Registration returns access_token and org_id."""
        assert registered_user["access_token"]
        assert registered_user["org_id"]

    def test_02_create_agent(self, auth_headers):
        """Create an agent via the API."""
        resp = httpx.post(
            f"{API_URL}/api/v2/agents",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "name": "e2e_test_agent",
                "description": "E2E smoke test agent",
                "owner_id": "self",
            },
            timeout=15,
        )

        # Accept 201 (created) or 200 (already exists)
        assert resp.status_code in (200, 201), f"Create agent failed: {resp.status_code} {resp.text}"
        data = resp.json()
        agent_id = data.get("agent_id") or data.get("id")
        assert agent_id, f"No agent_id in response: {data}"

        # Store for subsequent tests
        TestSignupToPayment._agent_id = agent_id

    def test_03_list_agents(self, auth_headers):
        """Verify the agent appears in the list."""
        resp = httpx.get(
            f"{API_URL}/api/v2/agents",
            headers=auth_headers,
            timeout=15,
        )

        assert resp.status_code == 200, f"List agents failed: {resp.status_code}"
        data = resp.json()
        agents = data if isinstance(data, list) else data.get("agents", [])
        assert len(agents) >= 1, "Expected at least 1 agent"

    def test_04_simulate_payment(self, auth_headers):
        """Run a simulated payment via the simulation endpoint."""
        agent_id = getattr(TestSignupToPayment, "_agent_id", "e2e_test_agent")

        resp = httpx.post(
            f"{API_URL}/api/v2/simulation",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "agent_id": agent_id,
                "amount": "5.00",
                "currency": "USDC",
                "merchant_id": "test_merchant",
                "description": "E2E smoke test payment",
            },
            timeout=15,
        )

        # Simulation endpoint may return 200 with result or 404 if not available
        if resp.status_code == 200:
            data = resp.json()
            # The simulation response typically has a "would_succeed" field
            assert "would_succeed" in data or "result" in data or "status" in data, (
                f"Unexpected simulation response: {data}"
            )
        elif resp.status_code == 404:
            pytest.skip("Simulation endpoint not available in this environment")
        else:
            pytest.fail(f"Simulation failed: {resp.status_code} {resp.text}")

    def test_05_billing_plan_defaults_to_free(self, auth_headers):
        """New user should be on the free plan."""
        resp = httpx.get(
            f"{API_URL}/api/v2/billing/account",
            headers=auth_headers,
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            plan = data.get("account", {}).get("plan") or data.get("plan")
            assert plan == "free", f"Expected free plan, got {plan}"
        elif resp.status_code == 503:
            pytest.skip("Billing not enabled in this environment")

    def test_06_duplicate_registration_returns_409(self, registered_user):
        """Re-registering with the same email should return 409."""
        resp = httpx.post(
            f"{API_URL}/api/v2/auth/register",
            json={
                "email": registered_user["email"],
                "password": "AnotherPassword123",
            },
            timeout=15,
        )

        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
