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


# --- Twilio adapter, with a mocked httpx client (no real keys, no network) ----


class _FakeResponse:
    def __init__(self, json_body: dict, status_code: int = 201) -> None:
        self._json = json_body
        self.status_code = status_code
        self.content = b"{}"

    def json(self) -> dict:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(
                "error", request=None, response=None  # type: ignore[arg-type]
            )


class _FakeTwilioHttp:
    """Records every POST and returns canned Twilio-shaped responses by URL."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def post(self, url, *, auth=None, data=None, **kwargs):
        self.calls.append({"url": url, "auth": auth, "data": dict(data or {})})
        if url.endswith("/Messages.json"):
            return _FakeResponse({"sid": "SM_fake_123", "status": "queued"})
        if url.endswith("/Verifications"):
            return _FakeResponse({"sid": "VE_fake", "status": "pending"})
        if url.endswith("/VerificationCheck"):
            # Approved only when the submitted code matches the canned secret.
            code = (data or {}).get("Code")
            status = "approved" if code == "424242" else "pending"
            return _FakeResponse({"status": status})
        return _FakeResponse({}, status_code=404)

    async def aclose(self) -> None:  # pragma: no cover - cleanup
        pass


def _twilio(http: _FakeTwilioHttp, **overrides):
    from server.providers.adapters import TwilioNotificationAdapter

    kwargs = {
        "account_sid": "ACtest",
        "auth_token": "tok",
        "from_number": "+15555550100",
        "verify_service_sid": "VAtest",
        "sandbox": True,
        "http_client": http,
    }
    kwargs.update(overrides)
    return TwilioNotificationAdapter(**kwargs)


@pytest.mark.asyncio
async def test_twilio_sms_composes_correctly():
    """SMS delivery hits Messages.json with the right To/From/Body and no OTP
    when step-up is not required."""
    http = _FakeTwilioHttp()
    adapter = _twilio(http)
    dr = await adapter.send_approval_request(
        approval_id="apreq_99",
        agent_id="agent_x",
        amount="250.00",
        currency="USDC",
        counterparty="0xCAFE",
        reason="vendor invoice",
        channels=("sms",),
        require_step_up=False,
        metadata={"to": "+15555550199"},
    )
    assert dr.provider == "twilio" and dr.ok
    assert dr.handle == "SM_fake_123"
    assert dr.step_up_issued is False
    assert "sms" in dr.channels

    # Exactly one call (Messages.json), no Verify start when step-up not asked.
    assert len(http.calls) == 1
    msg = http.calls[0]
    assert msg["url"].endswith("/Accounts/ACtest/Messages.json")
    assert msg["data"]["To"] == "+15555550199"
    assert msg["data"]["From"] == "+15555550100"
    body = msg["data"]["Body"]
    assert "apreq_99" in body and "250.00 USDC" in body and "0xCAFE" in body
    assert "APPROVE" in body and "DENY" in body


@pytest.mark.asyncio
async def test_twilio_over_threshold_triggers_otp_step_up():
    """When the gate marks a high-value approval require_step_up=True, the adapter
    issues a Verify OTP challenge alongside the SMS."""
    http = _FakeTwilioHttp()
    adapter = _twilio(http)
    dr = await adapter.send_approval_request(
        approval_id="apreq_big",
        agent_id="agent_x",
        amount="50000.00",
        currency="USDC",
        counterparty="0xBEEF",
        reason="large transfer",
        channels=("sms",),
        require_step_up=True,
        metadata={"to": "+15555550199"},
    )
    assert dr.step_up_issued is True
    urls = [c["url"] for c in http.calls]
    assert any(u.endswith("/Messages.json") for u in urls)
    assert any(u.endswith("/Services/VAtest/Verifications") for u in urls)
    verify_call = next(c for c in http.calls if c["url"].endswith("/Verifications"))
    assert verify_call["data"]["To"] == "+15555550199"
    assert verify_call["data"]["Channel"] == "sms"


@pytest.mark.asyncio
async def test_twilio_record_decision_fails_closed_on_bad_otp():
    """A wrong OTP code must NOT yield a decision — fail closed (ProviderError)."""
    http = _FakeTwilioHttp()
    adapter = _twilio(http)
    with pytest.raises(ProviderError):
        await adapter.record_decision(
            approval_id="apreq_big",
            decision="approve",
            approver="efe",
            proof={"otp_code": "000000", "to": "+15555550199"},
        )


@pytest.mark.asyncio
async def test_twilio_record_decision_accepts_verified_otp():
    """A correct OTP yields a verified, normalized decision (engine still re-checks)."""
    http = _FakeTwilioHttp()
    adapter = _twilio(http)
    rd = await adapter.record_decision(
        approval_id="apreq_big",
        decision="APPROVE",
        approver="efe",
        proof={"otp_code": "424242", "to": "+15555550199"},
    )
    assert rd.decision == "approved"
    assert rd.proof.get("step_up_verified") is True
    # The VerificationCheck endpoint (singular) was hit.
    assert http.calls[-1]["url"].endswith("/Services/VAtest/VerificationCheck")


def test_twilio_requires_account_sid_and_token():
    """Adapter never silently no-ops without credentials — it raises."""
    from server.providers.adapters import TwilioNotificationAdapter

    with pytest.raises(ProviderError):
        TwilioNotificationAdapter(account_sid="", auth_token="", sandbox=True)
