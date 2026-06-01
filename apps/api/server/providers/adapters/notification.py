"""Notification (human-in-the-loop delivery) port adapters.

Two real, env-gated adapters behind the :class:`NotificationPort` protocol:

* :class:`TwilioNotificationAdapter` — Twilio **Verify** (OTP step-up) +
  **Messaging** (SMS/WhatsApp), called over the public REST API with a thin
  ``httpx`` client (no SDK dependency for the two endpoints we use).  Research:
  Verify v2 ``/Services/{sid}/Verifications`` + ``/VerificationChecks``;
  Messaging ``/Accounts/{sid}/Messages.json`` (twilio.com/docs/verify/api,
  twilio.com/docs/sms/api/message-resource).

* :class:`PhotonRelayNotificationAdapter` — Photon / Spectrum agent-native
  omni-channel delivery (iMessage / WhatsApp / Telegram / Slack / Discord).

  **Research (May 2026, cited inline below).** Spectrum's *message send* surface
  — including the ``poll()`` interactive builder that renders the Approve / Deny
  choice — lives **only in the TypeScript SDK** ``spectrum-ts``
  (npm, ``Spectrum({ projectId, projectSecret })`` then ``space.send(...)``;
  github.com/photon-hq/spectrum-ts, photon.codes/docs/spectrum-ts/content).
  Spectrum **Cloud** publishes a REST control-plane API at
  ``https://spectrum.photon.codes/openapi/json`` (Basic
  ``base64(projectId:projectSecret)``) covering projects / lines / platforms /
  users / **webhooks** — but it exposes **no message-send / interactive-message
  endpoint**.  Inbound human decisions arrive as **webhooks**: Spectrum POSTs
  each event to a registered URL, signed **HMAC-SHA256**, and a button/poll press
  arrives as a ``poll_option`` content event
  (photon.codes/docs/spectrum-ts/content, photon.codes/docs/webhooks/events).

  **Chosen Python-integration path → thin Node sidecar (lowest-friction correct
  path).**  Because the outbound interactive ``poll()`` send is TS-only, Python
  cannot call it directly.  Sardis (the moat) builds the *agent-native
  interactive payload* here in Python, HMAC-signs it, and POSTs it to a thin
  Node sidecar (or the existing sardis-cloud TS surface) that owns ``spectrum-ts``
  and runs ``space.send(poll("…", "Approve", "Deny"))``.  The human's button
  press flows back as a Spectrum ``poll_option`` webhook → the sidecar forwards
  it (HMAC-signed) to Sardis's inbound route → :meth:`record_decision`.  We do
  NOT fake the TS send in Python; the sidecar contract is documented in
  ``docs/providers.md`` and scaffolded as a follow-up rather than half-built.

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


# The two interactive choices Spectrum renders as a poll (poll() builder).
# Inbound, a press arrives as a ``poll_option`` content event carrying the
# chosen option title; we map it back to a normalized decision.
_PHOTON_APPROVE_LABEL = "Approve"
_PHOTON_DENY_LABEL = "Deny"


class PhotonRelayNotificationAdapter:
    """:class:`NotificationPort` — Photon/Spectrum agent-native omni-channel.

    The interactive ``poll()`` send is TS-only (``spectrum-ts``), so Python
    builds the *agent-native interactive payload* (an Approve / Deny poll plus a
    human-readable line), HMAC-signs it, and POSTs it to a thin Node sidecar that
    owns the SDK and runs ``space.send(poll("…", "Approve", "Deny"))`` against
    iMessage / WhatsApp / Telegram / Slack / Discord.  The human's button press
    returns as a Spectrum ``poll_option`` webhook (HMAC-SHA256-signed); the
    inbound route verifies the signature and calls :meth:`record_decision`.

    Optional ``project_id`` / ``project_secret`` are the Spectrum Cloud
    control-plane credentials (Basic auth); the sidecar uses them to resolve
    lines/spaces.  We pass them through to the sidecar rather than calling the
    control-plane REST API directly (it has no message-send endpoint).
    """

    capability = ProviderCapability.NOTIFICATION

    def __init__(
        self,
        *,
        relay_url: str,
        relay_secret: str,
        project_id: str | None = None,
        project_secret: str | None = None,
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
        self._project_id = project_id
        self._project_secret = project_secret
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
        # HMAC-SHA256, matching Spectrum's own webhook signature scheme so the
        # same verifier covers both legs of the relay.
        return hmac.new(self._relay_secret, body, hashlib.sha256).hexdigest()

    @staticmethod
    def build_interactive_payload(
        *,
        approval_id: str,
        agent_id: str | None,
        amount: str,
        currency: str,
        counterparty: str | None,
        reason: str,
    ) -> dict[str, Any]:
        """Build the Spectrum-native interactive approval message.

        Pure (no I/O) so the orchestrator and tests can assert the rendered
        payload.  ``interactive`` is a Spectrum ``poll`` component the sidecar
        passes straight to ``space.send(poll(question, *options))``; ``text`` is
        the agent-native human-readable line shown alongside it.  ``callback_id``
        is echoed back on the ``poll_option`` webhook so the inbound route can
        correlate the press to this ApprovalRequest.
        """
        agent = agent_id or "your agent"
        who = counterparty or "an unknown counterparty"
        text = (
            f"{agent} wants to pay {amount} {currency} to {who}.\n"
            f"Reason: {reason}\n"
            "Approve or Deny?"
        )
        return {
            "text": text,
            "interactive": {
                "kind": "poll",
                "question": (
                    f"Approve {amount} {currency} to {who}?"
                ),
                "options": [_PHOTON_APPROVE_LABEL, _PHOTON_DENY_LABEL],
                "callback_id": approval_id,
            },
        }

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
        interactive = self.build_interactive_payload(
            approval_id=approval_id,
            agent_id=agent_id,
            amount=amount,
            currency=currency,
            counterparty=counterparty,
            reason=reason,
        )
        payload = {
            "approval_id": approval_id,
            "agent_id": agent_id,
            "amount": amount,
            "currency": currency,
            "counterparty": counterparty,
            "reason": reason,
            "channels": list(channels),
            "require_step_up": require_step_up,
            # Spectrum control-plane credentials for the sidecar to resolve the
            # line/space (no secret is logged or returned).
            "project_id": self._project_id,
            "message": interactive,
            "metadata": metadata or {},
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        headers = {
            "content-type": "application/json",
            "x-sardis-signature": self._sign(body),
        }
        if self._project_secret:
            # Basic base64(projectId:projectSecret) — the documented Spectrum
            # Cloud control-plane auth the sidecar forwards upstream.
            import base64

            token = base64.b64encode(
                f"{self._project_id or ''}:{self._project_secret}".encode()
            ).decode()
            headers["x-spectrum-authorization"] = f"Basic {token}"
        try:
            resp = await self._http.post(
                f"{self._relay_url}/approvals/send",
                content=body,
                headers=headers,
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
            raw={"interactive": interactive, **data},
        )

    def verify_relay_signature(self, *, body: bytes, signature: str) -> bool:
        """Verify an inbound webhook HMAC-SHA256.  Fail-closed (False).

        Covers both the sidecar's relay signature and (same scheme) Spectrum's
        own webhook signature, so one verifier guards the inbound decision route.
        """
        try:
            return hmac.compare_digest(self._sign(body), signature)
        except Exception:  # pragma: no cover - defensive
            return False

    @staticmethod
    def decision_from_poll_option(option_title: str) -> str:
        """Map an inbound Spectrum ``poll_option`` title to a decision verb.

        A button press arrives as a ``poll_option`` content event carrying the
        chosen option's title (``"Approve"`` / ``"Deny"``).
        """
        return _normalize_decision(option_title, provider="photon")

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
        # The sidecar / Spectrum signs its callback; the inbound route verifies
        # the HMAC over the raw body and passes it through as
        # proof['relay_verified'].  If the caller did not verify, fail closed —
        # a forged poll_option must never move money.
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
