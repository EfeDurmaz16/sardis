from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sardis_api.routers import secure_checkout


class _CardRepo:
    async def get_by_card_id(self, card_id: str):
        return {
            "card_id": card_id,
            "wallet_id": "wallet_1",
            "provider": "lithic",
            "provider_card_id": "provider_card_1",
            "card_type": "multi_use",
            "limit_per_tx": 100,
            "limit_daily": 500,
            "limit_monthly": 5000,
            "status": "active",
        }

    async def update_status(self, card_id: str, status: str):
        return {"card_id": card_id, "status": status}


class _CardProvider:
    def __init__(self) -> None:
        self.freeze_calls: list[str] = []

    async def freeze_card(self, provider_card_id: str):
        self.freeze_calls.append(provider_card_id)
        return {"provider_card_id": provider_card_id, "status": "frozen"}


class _AuditSink:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def record_event(self, event: dict):
        self.events.append(event)


def test_security_incident_severity_taxonomy():
    assert secure_checkout._security_incident_severity("policy_denied") == secure_checkout.SecurityIncidentSeverity.MEDIUM
    assert secure_checkout._security_incident_severity("merchant_anomaly") == secure_checkout.SecurityIncidentSeverity.HIGH
    assert secure_checkout._security_incident_severity("executor_auth_failed") == secure_checkout.SecurityIncidentSeverity.CRITICAL
    assert secure_checkout._security_incident_severity("unknown_code") == secure_checkout.SecurityIncidentSeverity.HIGH


def test_security_incident_cooldown_uses_env_override(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_INCIDENT_COOLDOWN_HIGH_SECONDS", "42")
    assert secure_checkout._security_incident_cooldown_seconds(secure_checkout.SecurityIncidentSeverity.HIGH) == 42


def test_auto_unfreeze_allowed_for_severity_defaults(monkeypatch):
    monkeypatch.delenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_ALLOWED_SEVERITIES", raising=False)
    assert secure_checkout._auto_unfreeze_allowed_for_severity(secure_checkout.SecurityIncidentSeverity.LOW) is True
    assert secure_checkout._auto_unfreeze_allowed_for_severity(secure_checkout.SecurityIncidentSeverity.MEDIUM) is True
    assert secure_checkout._auto_unfreeze_allowed_for_severity(secure_checkout.SecurityIncidentSeverity.CRITICAL) is False


@pytest.mark.asyncio
async def test_security_incident_emits_severity_and_ops_approval_pending(monkeypatch):
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_FREEZE_ON_SECURITY_INCIDENT", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_ON_SECURITY_INCIDENT", "1")
    monkeypatch.setenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_OPS_APPROVED", "0")
    monkeypatch.setenv("SARDIS_CHECKOUT_DISPATCH_SECURITY_ALERTS", "0")

    audit_sink = _AuditSink()
    card_provider = _CardProvider()
    deps = secure_checkout.SecureCheckoutDependencies(
        wallet_repo=None,
        agent_repo=None,
        card_repo=_CardRepo(),
        card_provider=card_provider,
        audit_sink=audit_sink,
    )
    job = {
        "job_id": "scj_1",
        "intent_id": "intent_1",
        "wallet_id": "wallet_1",
        "card_id": "card_1",
        "merchant_origin": "https://merchant.example",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    await secure_checkout._handle_security_incident(
        deps=deps,
        job=job,
        code="policy_denied",
        detail="policy denied on spend",
    )

    assert card_provider.freeze_calls == ["provider_card_1"]
    event_types = [event["event_type"] for event in audit_sink.events]
    assert "secure_checkout.security_incident" in event_types
    assert "secure_checkout.card_auto_frozen" in event_types
    assert "secure_checkout.card_unfreeze_pending_ops_approval" in event_types

    security_event = next(event for event in audit_sink.events if event["event_type"] == "secure_checkout.security_incident")
    payload = security_event["payload"]
    assert payload["severity"] == "medium"
    assert "freeze_card" in payload["planned_actions"]
    assert "auto_unfreeze_blocked_missing_ops_approval" in payload["planned_actions"]
