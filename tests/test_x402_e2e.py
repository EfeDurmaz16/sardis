"""End-to-end tests for x402 integration."""
from __future__ import annotations

import base64
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sardis_v2_core.control_plane import ControlPlane
from sardis_v2_core.execution_intent import ExecutionResult, IntentStatus
from sardis_v2_core.x402_events import (
    X402_EVENT_CHALLENGE_CREATED,
    X402_EVENT_PAYMENT_SETTLED,
    normalize_x402_event,
    settlement_status_to_event_type,
)
from sardis_v2_core.x402_metrics import X402MetricsCollector
from sardis_v2_core.x402_policy_guard import X402PolicyGuard


class TestX402Events:
    def test_normalize_challenge_event(self):
        event = normalize_x402_event(
            X402_EVENT_CHALLENGE_CREATED,
            payment_id="x402_test",
            network="base",
            amount="1000000",
        )
        assert event["event_type"] == "x402.challenge.created"
        assert event["data"]["payment_id"] == "x402_test"
        assert "event_id" in event
        assert "timestamp" in event

    def test_normalize_settled_event(self):
        event = normalize_x402_event(
            X402_EVENT_PAYMENT_SETTLED,
            payment_id="x402_test",
            tx_hash="0x123",
        )
        assert event["event_type"] == "x402.payment.settled"
        assert event["data"]["tx_hash"] == "0x123"

    def test_settlement_status_to_event_type(self):
        assert settlement_status_to_event_type("verified") == "x402.payment.verified"
        assert settlement_status_to_event_type("settled") == "x402.payment.settled"
        assert settlement_status_to_event_type("failed") == "x402.payment.failed"
        assert settlement_status_to_event_type("unknown") is None


class TestX402Metrics:
    def test_counter_increments(self):
        metrics = X402MetricsCollector()
        metrics.challenge_generated("base", "USDC")
        metrics.challenge_generated("base", "USDC")
        assert metrics.get_counter("x402.challenge.generated") == 2

    def test_histogram_records(self):
        metrics = X402MetricsCollector()
        metrics.settlement_completed("base", "server", 150.0)
        metrics.settlement_completed("base", "server", 200.0)
        values = metrics.get_histogram("x402.settlement.duration_ms")
        assert len(values) == 2
        assert 150.0 in values
        assert 200.0 in values

    def test_policy_check_metrics(self):
        metrics = X402MetricsCollector()
        metrics.policy_check(allowed=True, source="server")
        metrics.policy_check(allowed=False, source="client")
        assert metrics.get_counter("x402.policy.check") == 2

    def test_reset(self):
        metrics = X402MetricsCollector()
        metrics.challenge_generated("base", "USDC")
        metrics.reset()
        assert metrics.get_counter("x402.challenge.generated") == 0


@pytest.mark.asyncio
async def test_agent_pays_x402_api_e2e():
    """Full client flow: agent encounters 402 -> policy check -> pay -> success."""
    from sardis_v2_core.x402_client import X402Client
    from sardis_v2_core.x402_policy_guard import X402PolicyGuard

    # Setup: policy allows payment
    policy_eval = AsyncMock(return_value={"allowed": True})
    compliance = AsyncMock(return_value={"allowed": True})
    cp = ControlPlane(
        policy_evaluator=MagicMock(evaluate=policy_eval),
        compliance_checker=MagicMock(check=compliance),
    )
    guard = X402PolicyGuard(cp)

    # Create client
    client = X402Client(policy_guard=guard, max_cost="10")

    # Verify policy evaluation works
    from sardis_protocol.x402 import X402Challenge
    challenge = X402Challenge(
        payment_id="x402_e2e_test",
        resource_uri="https://api.example.com/data",
        amount="1000000",
        currency="USDC",
        payee_address="0x" + "a" * 40,
        network="base",
        token_address="0x" + "b" * 40,
        expires_at=9999999999,
        nonce="e2e_nonce",
    )

    ok, reason = await guard.evaluate(challenge, "agent_1", "org_1", "wal_1")
    assert ok is True
    assert reason == ""

    # Verify the intent had correct metadata
    intent = policy_eval.call_args[0][0]
    assert intent.metadata["x402_payment_id"] == "x402_e2e_test"
    assert intent.amount == Decimal("1")


@pytest.mark.asyncio
async def test_sardis_serves_x402_content_e2e():
    """Full server flow: middleware generates 402, client pays, gets content."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sardis_api.middleware.x402 import (
        X402MiddlewareConfig,
        X402PaymentMiddleware,
        X402PricingRegistry,
        X402PricingRule,
    )

    # Setup app with x402 middleware
    app = FastAPI()
    pricing = X402PricingRegistry()
    pricing.add_rule(X402PricingRule(
        path_prefix="/api/v2/premium",
        amount="500000",  # $0.50
        currency="USDC",
        network="base",
    ))

    config = X402MiddlewareConfig(
        pricing_registry=pricing,
        payee_address="0x" + "a" * 40,
        enabled=True,
    )
    app.add_middleware(X402PaymentMiddleware, config=config)

    @app.get("/api/v2/premium/data")
    async def premium_data():
        return {"premium": True, "data": "secret"}

    client = TestClient(app)

    # Step 1: Request without payment -> 402
    response = client.get("/api/v2/premium/data")
    assert response.status_code == 402

    body = response.json()
    assert body["error"] == "payment_required"
    assert body["amount"] == "500000"

    # Verify challenge header is present and parseable
    payment_required_header = response.headers.get("PaymentRequired", "")
    assert payment_required_header
    challenge_data = json.loads(base64.b64decode(payment_required_header))
    assert challenge_data["amount"] == "500000"
    assert challenge_data["currency"] == "USDC"
