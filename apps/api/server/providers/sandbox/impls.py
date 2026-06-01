"""Sandbox / mock implementations of every capability port.

Returned by :class:`server.providers.registry.ProviderRegistry` when a real
provider's credentials are absent **and** the runtime is non-production, so the
test suite and local dev run green without live keys.  Every result is marked
``sandbox=True`` and ``custody_model=SIMULATED`` — a simulated response can
never be mistaken for a settled production movement of funds.

These impls are deterministic (uuid-suffixed references) and perform no I/O.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ..ports.capabilities import (
    BridgePort,
    CardPort,
    CustodyPort,
    FiatAccountPort,
    FraudSignalPort,
    KycPort,
    KytPort,
    NotificationPort,
    OfframpPort,
    OnrampPort,
    SwapPort,
)
from ..ports.types import (
    CustodyModel,
    DeliveryResult,
    MinorUnits,
    NormalizedTxn,
    ProviderCapability,
    ProviderResult,
    RecommendedAction,
    RelayedDecision,
    RiskSignalResult,
)

logger = logging.getLogger(__name__)


def _ref(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class _SandboxBase:
    """Common metadata for every sandbox port."""

    capability: ProviderCapability

    def __init__(self, *, provider: str) -> None:
        self._provider = provider

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.SIMULATED

    @property
    def sandbox(self) -> bool:
        return True

    def _result(self, *, reference: str | None, status: str, **raw: Any) -> ProviderResult:
        return ProviderResult(
            provider=self._provider,
            capability=self.capability,
            custody_model=CustodyModel.SIMULATED,
            sandbox=True,
            reference=reference,
            status=status,
            raw=dict(raw),
        )


class SandboxCustodyPort(_SandboxBase, CustodyPort):
    capability = ProviderCapability.CUSTODY

    async def get_address(self, wallet_ref: str, *, chain: str) -> str:
        # Deterministic, well-formed-looking EVM address per wallet_ref.
        suffix = uuid.uuid5(uuid.NAMESPACE_OID, f"{wallet_ref}:{chain}").hex[:40]
        return "0x" + suffix

    async def sign_payload(self, wallet_ref: str, *, payload: dict[str, Any]) -> ProviderResult:
        return self._result(reference=_ref("sig"), status="signed", wallet_ref=wallet_ref)


class SandboxFiatAccountPort(_SandboxBase, FiatAccountPort):
    capability = ProviderCapability.FIAT_ACCOUNT

    async def create_account(
        self, *, owner_ref: str, currency: str = "USD", metadata: dict[str, Any] | None = None
    ) -> ProviderResult:
        return self._result(reference=_ref("facct"), status="active", currency=currency)

    async def get_balance(self, account_ref: str) -> tuple[MinorUnits, str]:
        return (0, "USD")

    async def create_payout(
        self,
        *,
        account_ref: str,
        destination_ref: str,
        amount_minor: MinorUnits,
        currency: str = "USD",
        method: str = "ACH_NEXT_DAY",
        idempotency_key: str | None = None,
        memo: str | None = None,
    ) -> NormalizedTxn:
        return NormalizedTxn(
            provider=self._provider,
            capability=self.capability,
            custody_model=CustodyModel.SIMULATED,
            reference=_ref("pay"),
            status="pending",
            amount_minor=amount_minor,
            currency=currency,
            sandbox=True,
            source=account_ref,
            destination=destination_ref,
            raw={"method": method, "simulated": True},
        )

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        # Sandbox accepts unsigned webhooks for local testing only.
        return True


class SandboxOnrampPort(_SandboxBase, OnrampPort):
    capability = ProviderCapability.ONRAMP

    async def create_session(
        self,
        *,
        wallet_address: str,
        chain: str,
        crypto_currency: str = "usdc",
        fiat_currency: str = "USD",
        amount_minor: MinorUnits | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        ref = _ref("onramp")
        return self._result(
            reference=ref,
            status="created",
            url=f"https://sandbox.onramp.local/{ref}",
            chain=chain,
            crypto_currency=crypto_currency,
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        return self._result(reference=session_ref, status="completed")


class SandboxOfframpPort(_SandboxBase, OfframpPort):
    capability = ProviderCapability.OFFRAMP

    async def create_payout(
        self,
        *,
        source_chain: str,
        source_token: str,
        amount_minor: MinorUnits,
        destination_bank_ref: str,
        fiat_currency: str = "USD",
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> NormalizedTxn:
        return NormalizedTxn(
            provider=self._provider,
            capability=self.capability,
            custody_model=CustodyModel.SIMULATED,
            reference=_ref("offramp"),
            status="pending",
            amount_minor=amount_minor,
            currency=fiat_currency,
            sandbox=True,
            chain=source_chain,
            source=source_token,
            destination=destination_bank_ref,
            raw={"simulated": True},
        )

    async def get_status(self, payout_ref: str) -> ProviderResult:
        return self._result(reference=payout_ref, status="completed")


class SandboxSwapPort(_SandboxBase, SwapPort):
    capability = ProviderCapability.SWAP

    async def quote(
        self, *, chain: str, sell_token: str, buy_token: str, sell_amount_minor: MinorUnits
    ) -> ProviderResult:
        return self._result(
            reference=_ref("quote"),
            status="quoted",
            chain=chain,
            sell_token=sell_token,
            buy_token=buy_token,
            # 1:1 deterministic sandbox rate.
            buy_amount_minor=sell_amount_minor,
        )

    async def build_execution(self, *, quote_ref: str, taker_address: str) -> ProviderResult:
        return self._result(reference=quote_ref, status="ready", calldata="0x", to="0x")


class SandboxBridgePort(_SandboxBase, BridgePort):
    capability = ProviderCapability.BRIDGE

    async def quote(
        self, *, from_chain: str, to_chain: str, token: str, amount_minor: MinorUnits
    ) -> ProviderResult:
        return self._result(
            reference=_ref("bquote"),
            status="quoted",
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            receive_amount_minor=amount_minor,
        )

    async def build_execution(
        self, *, quote_ref: str, sender_address: str, recipient_address: str
    ) -> ProviderResult:
        return self._result(reference=quote_ref, status="ready", messages=[])


class SandboxCardPort(_SandboxBase, CardPort):
    capability = ProviderCapability.CARD

    async def issue_card(
        self,
        *,
        owner_ref: str,
        spend_limit_minor: MinorUnits | None = None,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        return self._result(
            reference=_ref("card"),
            status="active",
            last_four="4242",
            spend_limit_minor=spend_limit_minor,
            currency=currency,
        )

    async def set_state(self, card_ref: str, *, state: str) -> ProviderResult:
        return self._result(reference=card_ref, status=state)

    async def set_limit(
        self, card_ref: str, *, spend_limit_minor: MinorUnits, currency: str = "USD"
    ) -> ProviderResult:
        return self._result(
            reference=card_ref, status="active", spend_limit_minor=spend_limit_minor
        )


class SandboxKycPort(_SandboxBase, KycPort):
    capability = ProviderCapability.KYC

    async def create_session(
        self, *, subject_ref: str, kind: str = "kyc", metadata: dict[str, Any] | None = None
    ) -> ProviderResult:
        ref = _ref("kyc")
        return self._result(
            reference=ref, status="pending", url=f"https://sandbox.kyc.local/{ref}", kind=kind
        )

    async def get_status(self, session_ref: str) -> ProviderResult:
        return self._result(reference=session_ref, status="approved")

    def verify_webhook(self, *, body: bytes, headers: dict[str, str]) -> bool:
        return True


class SandboxKytPort(_SandboxBase, KytPort):
    capability = ProviderCapability.KYT

    async def screen_address(self, *, address: str, chain: str | None = None) -> ProviderResult:
        # Sandbox always returns a clean verdict; the moat still decides.
        return self._result(reference=_ref("kyt"), status="clear", risk="low", hits=[])

    async def screen_counterparty(
        self, *, name: str, metadata: dict[str, Any] | None = None
    ) -> ProviderResult:
        return self._result(reference=_ref("kyt"), status="clear", risk="low", hits=[])


class SandboxFraudSignalPort(_SandboxBase, FraudSignalPort):
    """Deterministic mock fraud-signal feed for dev + tests (no keys, no I/O).

    Returns a clean, low-risk signal so the in-house RiskEngine's behavioral
    score drives the decision with no external influence — exactly what we want
    when no real feed is configured.  Marked ``sandbox=True`` so it can never be
    mistaken for a live cross-customer signal.
    """

    capability = ProviderCapability.FRAUD_SIGNAL

    async def score(self, context: dict[str, Any]) -> RiskSignalResult:
        return RiskSignalResult(
            provider=self._provider,
            score=0.0,
            reasons=("sandbox: no external fraud signal feed configured",),
            recommended_action=RecommendedAction.NOT_ASSESSED,
            sandbox=True,
            reference=_ref("fraud"),
            raw={"simulated": True},
        )


class SandboxNotificationPort(_SandboxBase, NotificationPort):
    """In-memory approval delivery for dev + tests — logs, no I/O, no keys.

    Records every dispatched approval in :attr:`sent` so tests can assert a
    notification was emitted, and accepts any inbound decision (channel proof is
    trusted in sandbox only).  The engine still re-checks policy/mandate, so a
    sandbox "approve" can never bypass the moat.
    """

    capability = ProviderCapability.NOTIFICATION

    def __init__(self, *, provider: str) -> None:
        super().__init__(provider=provider)
        # Public test surface: list of dispatched approval payloads.
        self.sent: list[dict[str, Any]] = []
        self.decisions: list[RelayedDecision] = []

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
        payload = {
            "approval_id": approval_id,
            "agent_id": agent_id,
            "amount": amount,
            "currency": currency,
            "counterparty": counterparty,
            "reason": reason,
            "channels": tuple(channels),
            "require_step_up": require_step_up,
            "metadata": metadata or {},
        }
        self.sent.append(payload)
        logger.info(
            "[sandbox-notify] approval %s dispatched: %s %s -> %s (channels=%s, step_up=%s)",
            approval_id, amount, currency, counterparty, channels, require_step_up,
        )
        return DeliveryResult(
            provider=self._provider,
            sandbox=True,
            ok=True,
            handle=_ref("dlv"),
            channels=tuple(channels),
            step_up_issued=require_step_up,
            raw={"simulated": True},
        )

    async def record_decision(
        self,
        *,
        approval_id: str,
        decision: str,
        approver: str,
        proof: dict[str, Any] | None = None,
        channel: str = "dashboard",
    ) -> RelayedDecision:
        norm = decision.strip().lower()
        if norm not in ("approved", "approve", "denied", "deny"):
            from ..ports.types import ProviderError

            raise ProviderError(
                f"unknown decision verb: {decision!r}",
                provider=self._provider,
                capability=self.capability,
            )
        norm = "approved" if norm.startswith("approv") else "denied"
        rd = RelayedDecision(
            approval_id=approval_id,
            decision=norm,
            approver=approver,
            channel=channel,
            proof=dict(proof or {}),
            raw={"simulated": True},
        )
        self.decisions.append(rd)
        return rd
