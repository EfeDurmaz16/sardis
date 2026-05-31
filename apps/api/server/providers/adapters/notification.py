"""Notification (human-in-the-loop delivery) port adapters.

Two real, env-gated adapters behind the :class:`NotificationPort` protocol:

* :class:`TwilioNotificationAdapter` — Twilio **Verify** (OTP step-up) +
  **Messaging** (SMS/WhatsApp), called over the public REST API with a thin
  ``httpx`` client (no SDK dependency for the two endpoints we use).  Research:
  Verify v2 ``/Services/{sid}/Verifications`` + ``/VerificationChecks``;
  Messaging ``/Accounts/{sid}/Messages.json`` (twilio.com/docs/verify/api,
  twilio.com/docs/sms/api/message-resource).

* :class:`PhotonRelayNotificationAdapter` — Photon / Spectrum is a
  **TypeScript-only** SDK (``spectrum-ts``, npm, PROJECT_ID/PROJECT_SECRET
  against Spectrum Cloud's edge/gRPC gateway); it does **not** publish a
  documented HTTP API callable from Python (github.com/photon-hq/spectrum-ts,
  photon.codes/docs/spectrum-ts).  So Python relays through a thin Node sidecar
  / the sardis-cloud TS surface that owns the SDK: we POST the approval to a
  configured relay URL with an HMAC-signed body; the sidecar drives
  ``spectrum-ts`` to deliver to iMessage/WhatsApp/Telegram and posts the human's
  decision back to Sardis.

Both adapters are **delivery only** — they never decide an outcome.  Neither is
a money custodian (``custody_model`` reflects no funds flow through here).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from ..ports.types import (
    CustodyModel,
    DeliveryResult,
    ProviderCapability,
    ProviderError,
    RelayedDecision,
)

logger = logging.getLogger(__name__)

_TWILIO_API_ROOT = "https://api.twilio.com/2010-04-01"
_TWILIO_VERIFY_ROOT = "https://verify.twilio.com/v2"


def _normalize_decision(decision: str, *, provider: str) -> str:
    norm = decision.strip().lower()
    if norm.startswith("approv"):
        return "approved"
    if norm.startswith("den") or norm.startswith("reject"):
        return "denied"
    raise ProviderError(
        f"unknown decision verb: {decision!r}",
        provider=provider,
        capability=ProviderCapability.NOTIFICATION,
    )


class TwilioNotificationAdapter:
    """:class:`NotificationPort` over Twilio Verify + Messaging REST."""

    capability = ProviderCapability.NOTIFICATION

    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_number: str | None = None,
        verify_service_sid: str | None = None,
        messaging_service_sid: str | None = None,
        sandbox: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not account_sid or not auth_token:
            raise ProviderError(
                "Twilio requires account_sid and auth_token",
                provider="twilio",
                capability=ProviderCapability.NOTIFICATION,
            )
        self._account_sid = account_sid
        self._auth = (account_sid, auth_token)
        self._from = from_number
        self._verify_service_sid = verify_service_sid
        self._messaging_service_sid = messaging_service_sid
        self._sandbox = sandbox
        self._http = http_client or httpx.AsyncClient(timeout=15.0)

    @property
    def provider(self) -> str:
        return "twilio"

    @property
    def custody_model(self) -> CustodyModel:
        # No funds flow through a notification provider.
        return CustodyModel.NON_CUSTODIAL

    @property
    def sandbox(self) -> bool:
        return self._sandbox

    async def aclose(self) -> None:
        await self._http.aclose()

    async def send_approval_request(
        self,
        *,
        approval_id: str,
        agent_id: str | None,
        amount: str,
        currency: str,
        counterparty: str | None,
        reason: str,
        channels: tuple[str, ...] = ("dashboard",),
        require_step_up: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryResult:
        to = (metadata or {}).get("to") or (metadata or {}).get("phone")
        if not to:
            raise ProviderError(
                "Twilio delivery requires metadata['to'] (E.164 phone number)",
                provider="twilio",
                capability=ProviderCapability.NOTIFICATION,
            )

        body = (
            f"Sardis approval {approval_id}: agent {agent_id or 'unknown'} requests "
            f"{amount} {currency} to {counterparty or 'unknown'}. Reason: {reason}. "
            "Reply APPROVE or DENY."
        )

        sent_channels: list[str] = []
        step_up_issued = False
        raw: dict[str, Any] = {}

        # 1) Notify via Messaging (SMS / WhatsApp).
        try:
            form: dict[str, str] = {"To": to, "Body": body}
            if self._messaging_service_sid:
                form["MessagingServiceSid"] = self._messaging_service_sid
            elif self._from:
                form["From"] = self._from
            else:
                raise ProviderError(
                    "Twilio messaging requires from_number or messaging_service_sid",
                    provider="twilio",
                    capability=ProviderCapability.NOTIFICATION,
                )
            resp = await self._http.post(
                f"{_TWILIO_API_ROOT}/Accounts/{self._account_sid}/Messages.json",
                auth=self._auth,
                data=form,
            )
            resp.raise_for_status()
            payload = resp.json()
            raw["message"] = {"sid": payload.get("sid"), "status": payload.get("status")}
            sent_channels.append("sms")
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"twilio messaging delivery failed: {exc}",
                provider="twilio",
                capability=ProviderCapability.NOTIFICATION,
                retryable=True,
            ) from exc

        # 2) Step-up: issue an OTP via Verify so the inbound decision can be
        #    OTP-verified (high-value approvals).
        if require_step_up and self._verify_service_sid:
            try:
                resp = await self._http.post(
                    f"{_TWILIO_VERIFY_ROOT}/Services/{self._verify_service_sid}/Verifications",
                    auth=self._auth,
                    data={"To": to, "Channel": "sms"},
                )
                resp.raise_for_status()
                raw["verify"] = {"status": resp.json().get("status")}
                step_up_issued = True
            except httpx.HTTPError as exc:
                # Fail-closed for step-up: an approval requiring step-up must NOT
                # proceed if the OTP could not be issued.
                raise ProviderError(
                    f"twilio verify (step-up) failed to issue: {exc}",
                    provider="twilio",
                    capability=ProviderCapability.NOTIFICATION,
                    retryable=True,
                ) from exc

        return DeliveryResult(
            provider="twilio",
            sandbox=self._sandbox,
            ok=True,
            handle=raw.get("message", {}).get("sid"),
            channels=tuple(sent_channels),
            step_up_issued=step_up_issued,
            raw=raw,
        )

    async def record_decision(
        self,
        *,
        approval_id: str,
        decision: str,
        approver: str,
        proof: dict[str, Any] | None = None,
        channel: str = "sms",
    ) -> RelayedDecision:
        norm = _normalize_decision(decision, provider="twilio")
        proof = dict(proof or {})

        # If a Verify OTP was issued, validate it before accepting the decision.
        otp = proof.get("otp_code")
        to = proof.get("to") or proof.get("phone")
        if otp and to and self._verify_service_sid:
            try:
                resp = await self._http.post(
                    f"{_TWILIO_VERIFY_ROOT}/Services/{self._verify_service_sid}/VerificationCheck",
                    auth=self._auth,
                    data={"To": to, "Code": str(otp)},
                )
                resp.raise_for_status()
                status = resp.json().get("status")
            except httpx.HTTPError as exc:
                raise ProviderError(
                    f"twilio verify check failed: {exc}",
                    provider="twilio",
                    capability=ProviderCapability.NOTIFICATION,
                ) from exc
            if status != "approved":
                raise ProviderError(
                    "twilio OTP step-up not verified — refusing decision (fail-closed)",
                    provider="twilio",
                    capability=ProviderCapability.NOTIFICATION,
                )
            proof["step_up_verified"] = True

        return RelayedDecision(
            approval_id=approval_id,
            decision=norm,
            approver=approver,
            channel=channel,
            proof=proof,
            raw={},
        )


class PhotonRelayNotificationAdapter:
    """:class:`NotificationPort` that relays to Photon/Spectrum via a sidecar.

    Photon's ``spectrum-ts`` is TypeScript-only, so Python POSTs an HMAC-signed
    approval to a relay endpoint (a Node sidecar / the sardis-cloud TS surface)
    that owns the SDK and delivers to iMessage/WhatsApp/Telegram.  Inbound
    decisions arrive HMAC-signed and are verified here before being accepted.
    """

    capability = ProviderCapability.NOTIFICATION

    def __init__(
        self,
        *,
        relay_url: str,
        relay_secret: str,
        sandbox: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not relay_url or not relay_secret:
            raise ProviderError(
                "Photon relay requires relay_url and relay_secret",
                provider="photon",
                capability=ProviderCapability.NOTIFICATION,
            )
        self._relay_url = relay_url.rstrip("/")
        self._relay_secret = relay_secret.encode()
        self._sandbox = sandbox
        self._http = http_client or httpx.AsyncClient(timeout=15.0)

    @property
    def provider(self) -> str:
        return "photon"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.NON_CUSTODIAL

    @property
    def sandbox(self) -> bool:
        return self._sandbox

    async def aclose(self) -> None:
        await self._http.aclose()

    def _sign(self, body: bytes) -> str:
        return hmac.new(self._relay_secret, body, hashlib.sha256).hexdigest()

    async def send_approval_request(
        self,
        *,
        approval_id: str,
        agent_id: str | None,
        amount: str,
        currency: str,
        counterparty: str | None,
        reason: str,
        channels: tuple[str, ...] = ("imessage",),
        require_step_up: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> DeliveryResult:
        payload = {
            "approval_id": approval_id,
            "agent_id": agent_id,
            "amount": amount,
            "currency": currency,
            "counterparty": counterparty,
            "reason": reason,
            "channels": list(channels),
            "require_step_up": require_step_up,
            "metadata": metadata or {},
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        try:
            resp = await self._http.post(
                f"{self._relay_url}/approvals/send",
                content=body,
                headers={
                    "content-type": "application/json",
                    "x-sardis-signature": self._sign(body),
                },
            )
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"photon relay delivery failed: {exc}",
                provider="photon",
                capability=ProviderCapability.NOTIFICATION,
                retryable=True,
            ) from exc
        return DeliveryResult(
            provider="photon",
            sandbox=self._sandbox,
            ok=True,
            handle=data.get("job_id") or data.get("handle"),
            channels=tuple(channels),
            step_up_issued=bool(data.get("step_up_issued")),
            raw=data,
        )

    def verify_relay_signature(self, *, body: bytes, signature: str) -> bool:
        """Verify an inbound relay callback HMAC.  Fail-closed (False)."""
        try:
            return hmac.compare_digest(self._sign(body), signature)
        except Exception:  # pragma: no cover - defensive
            return False

    async def record_decision(
        self,
        *,
        approval_id: str,
        decision: str,
        approver: str,
        proof: dict[str, Any] | None = None,
        channel: str = "imessage",
    ) -> RelayedDecision:
        norm = _normalize_decision(decision, provider="photon")
        proof = dict(proof or {})
        # The relay signs its callback; the inbound route verifies the HMAC over
        # the raw body and passes it through as proof['relay_verified'].  If the
        # caller did not verify, fail closed.
        if not proof.get("relay_verified"):
            raise ProviderError(
                "photon relay decision missing verified signature — refusing (fail-closed)",
                provider="photon",
                capability=ProviderCapability.NOTIFICATION,
            )
        return RelayedDecision(
            approval_id=approval_id,
            decision=norm,
            approver=approver,
            channel=channel,
            proof=proof,
            raw={},
        )
