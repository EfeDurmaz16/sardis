"""Tests for exception retry policy execution."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from sardis_api.routers import exceptions as exceptions_router
from sardis_v2_core.exception_workflows import ExceptionType


@dataclass
class _FakeTreasuryRepo:
    payment: dict
    retry_increments: list[tuple[str, str]]
    upserts: list[tuple[str, dict, str | None]]
    event_appends: list[tuple[str, str, list[dict]]]

    def __init__(self, payment: dict):
        self.payment = payment
        self.retry_increments = []
        self.upserts = []
        self.event_appends = []

    async def get_ach_payment(self, organization_id: str, payment_token: str) -> dict | None:
        if (
            organization_id == self.payment.get("organization_id")
            and payment_token == self.payment.get("payment_token")
        ):
            return dict(self.payment)
        return None

    async def increment_retry_count(self, organization_id: str, payment_token: str) -> None:
        self.retry_increments.append((organization_id, payment_token))

    async def upsert_ach_payment(
        self,
        organization_id: str,
        payment: dict,
        *,
        idempotency_key: str | None = None,
    ) -> dict:
        self.upserts.append((organization_id, payment, idempotency_key))
        return payment

    async def append_ach_events(
        self,
        organization_id: str,
        payment_token: str,
        events: list[dict],
    ) -> None:
        self.event_appends.append((organization_id, payment_token, events))


class _FakeLithicClient:
    def __init__(self, *, result: object | None = None, error: Exception | None = None):
        self._result = result
        self._error = error
        self.requests: list[object] = []

    async def create_payment(self, request: object) -> object:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return self._result


@pytest.fixture(autouse=True)
def _reset_exception_state():
    exceptions_router._engine._exceptions.clear()
    exceptions_router._retry_policies.clear()
    exceptions_router._seed_default_policies()
    yield
    exceptions_router._engine._exceptions.clear()
    exceptions_router._retry_policies.clear()
    exceptions_router._seed_default_policies()


@pytest.mark.asyncio
async def test_retry_executes_supported_treasury_retry(client, app):
    repo = _FakeTreasuryRepo(
        payment={
            "organization_id": "org_test",
            "payment_token": "pay_original_123",
            "financial_account_token": "fa_123",
            "external_bank_account_token": "eba_123",
            "direction": "PAYMENT",
            "method": "ACH_NEXT_DAY",
            "sec_code": "CCD",
            "amount_minor": 4200,
            "retry_count": 0,
            "user_defined_id": "invoice_123",
        }
    )
    lithic = _FakeLithicClient(
        result=SimpleNamespace(
            token="pay_retry_456",
            status="PENDING",
            result="APPROVED",
            direction="PAYMENT",
            method="ACH_NEXT_DAY",
            currency="USD",
            pending_amount=4200,
            settled_amount=0,
            financial_account_token="fa_123",
            external_bank_account_token="eba_123",
            user_defined_id="invoice_123",
            events=[{"token": "evt_retry_1", "type": "ACH_ORIGINATION_INITIATED"}],
            raw={
                "token": "pay_retry_456",
                "status": "PENDING",
                "result": "APPROVED",
                "direction": "PAYMENT",
                "method": "ACH_NEXT_DAY",
                "currency": "USD",
                "pending_amount": 4200,
                "external_bank_account_token": "eba_123",
                "financial_account_token": "fa_123",
                "user_defined_id": "invoice_123",
                "method_attributes": {"sec_code": "CCD"},
            },
        )
    )
    app.state.treasury_repo = repo
    app.state.lithic_treasury_client = lithic

    seeded = exceptions_router._engine.create_exception(
        transaction_id="pay_original_123",
        agent_id="agent_demo",
        exception_type=ExceptionType.CHAIN_FAILURE,
        description="Initial ACH send failed",
        original_amount=Decimal("42.00"),
        currency="USD",
        max_retries=3,
        metadata={
            "retry_target": {
                "kind": "treasury_payment",
                "organization_id": "org_test",
                "payment_token": "pay_original_123",
            }
        },
    )

    response = await client.post(f"/api/v2/exceptions/{seeded.exception_id}/retry", json={})
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "resolved"
    assert "Automated treasury retry succeeded" in body["resolution_notes"]
    assert body["retry_count"] == 1
    assert body["metadata"]["last_retry_result"]["retried_payment_token"] == "pay_retry_456"

    audit = body["metadata"]["recovery_automation"][-1]
    assert audit["executed"] is True
    assert audit["executor"] == "lithic_treasury_retry"
    assert audit["payment_token"] == "pay_original_123"
    assert audit["retried_payment_token"] == "pay_retry_456"

    assert len(lithic.requests) == 1
    assert repo.retry_increments == [("org_test", "pay_original_123")]
    assert len(repo.upserts) == 1
    assert len(repo.event_appends) == 1


@pytest.mark.asyncio
async def test_retry_applies_fallback_when_treasury_retry_fails(client, app):
    repo = _FakeTreasuryRepo(
        payment={
            "organization_id": "org_test",
            "payment_token": "pay_original_999",
            "financial_account_token": "fa_999",
            "external_bank_account_token": "eba_999",
            "direction": "PAYMENT",
            "method": "ACH_NEXT_DAY",
            "sec_code": "CCD",
            "amount_minor": 1500,
            "retry_count": 0,
            "user_defined_id": "invoice_999",
        }
    )
    lithic = _FakeLithicClient(error=RuntimeError("provider timeout"))
    app.state.treasury_repo = repo
    app.state.lithic_treasury_client = lithic

    seeded = exceptions_router._engine.create_exception(
        transaction_id="pay_original_999",
        agent_id="agent_demo",
        exception_type=ExceptionType.CHAIN_FAILURE,
        description="Retryable provider timeout",
        original_amount=Decimal("15.00"),
        currency="USD",
        max_retries=3,
        metadata={
            "retry_target": {
                "kind": "treasury_payment",
                "organization_id": "org_test",
                "payment_token": "pay_original_999",
            }
        },
    )

    response = await client.post(f"/api/v2/exceptions/{seeded.exception_id}/retry", json={})
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "escalated"
    assert "Automated retry failed" in body["resolution_notes"]
    audit = body["metadata"]["recovery_automation"][-1]
    assert audit["executed"] is True
    assert audit["reason"] == "live_retry_failed"
    assert audit["fallback_action_executed"] == "escalate"
    assert repo.retry_increments == []
