"""Tests for the NotificationPort: taxonomy, sandbox, registry env-gating, adapters.

Delivery only — these prove the port relays an approval and a decision, never
decides an outcome, and that dev/tests run with NO keys (sandbox fallback).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from server.providers.ports import (
    DeliveryResult,
    NotificationPort,
    ProviderCapability,
    RelayedDecision,
)
from server.providers.ports.types import ProviderError
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxNotificationPort


def _dev_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=False, database_url="", circle_cpn=SimpleNamespace())


def test_notification_capability_in_taxonomy():
    assert ProviderCapability.NOTIFICATION.value == "notification"


def test_sandbox_satisfies_notification_protocol():
    port = SandboxNotificationPort(provider="sandbox")
    assert isinstance(port, NotificationPort)
    assert port.sandbox is True
    assert port.capability is ProviderCapability.NOTIFICATION


@pytest.mark.asyncio
async def test_sandbox_send_records_and_returns_handle():
    port = SandboxNotificationPort(provider="sandbox")
    dr = await port.send_approval_request(
        approval_id="apreq_1", agent_id="a1", amount="250", currency="USDC",
        counterparty="0xabc", reason="over threshold",
        channels=("sms", "imessage"), require_step_up=True,
    )
    assert isinstance(dr, DeliveryResult)
    assert dr.ok and dr.handle and dr.step_up_issued
    assert set(dr.channels) == {"sms", "imessage"}
    assert len(port.sent) == 1 and port.sent[0]["approval_id"] == "apreq_1"


@pytest.mark.asyncio
async def test_sandbox_record_decision_normalizes_verb():
    port = SandboxNotificationPort(provider="sandbox")
    rd = await port.record_decision(
        approval_id="apreq_1", decision="APPROVE", approver="efe", channel="sms",
    )
    assert isinstance(rd, RelayedDecision)
    assert rd.decision == "approved"
    with pytest.raises(ProviderError):
        await port.record_decision(approval_id="x", decision="maybe", approver="efe")


def test_registry_falls_back_to_sandbox_with_no_keys():
    reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
    port = reg.notification()
    assert isinstance(port, SandboxNotificationPort)
    assert reg.has_real(ProviderCapability.NOTIFICATION) is False


def test_registry_wires_twilio_when_keys_present():
    env = {
        "TWILIO_ACCOUNT_SID": "ACxxxx",
        "TWILIO_AUTH_TOKEN": "tok",
        "TWILIO_FROM_NUMBER": "+15555555555",
    }
    reg = ProviderRegistry.from_settings(_dev_settings(), environ=env)
    assert reg.has_real(ProviderCapability.NOTIFICATION) is True
    assert reg.notification().provider == "twilio"


def test_registry_wires_photon_relay_when_keys_present():
    env = {
        "PHOTON_RELAY_URL": "https://relay.sardis.sh",
        "PHOTON_RELAY_SECRET": "shh",
    }
    reg = ProviderRegistry.from_settings(_dev_settings(), environ=env)
    assert reg.has_real(ProviderCapability.NOTIFICATION) is True
    assert reg.notification().provider == "photon"


def test_photon_relay_decision_fail_closed_without_verified_signature():
    from server.providers.adapters import PhotonRelayNotificationAdapter

    adapter = PhotonRelayNotificationAdapter(
        relay_url="https://relay.sardis.sh", relay_secret="shh", sandbox=True,
    )
    import asyncio

    with pytest.raises(ProviderError):
        asyncio.run(
            adapter.record_decision(
                approval_id="apreq_1", decision="approve", approver="efe",
                proof={},  # no relay_verified -> fail closed
            )
        )


def test_photon_relay_hmac_roundtrips():
    from server.providers.adapters import PhotonRelayNotificationAdapter

    adapter = PhotonRelayNotificationAdapter(
        relay_url="https://relay.sardis.sh", relay_secret="shh", sandbox=True,
    )
    body = b'{"x":1}'
    sig = adapter._sign(body)
    assert adapter.verify_relay_signature(body=body, signature=sig) is True
    assert adapter.verify_relay_signature(body=body, signature="bad") is False
