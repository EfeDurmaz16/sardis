"""FraudSignalPort adapters over the Stripe Radar + SEON clients.

Each adapter normalizes a vendor's read into a :class:`RiskSignalResult`
(provider, 0-100 score, reasons, recommended_action).  It contributes a
*signal* the in-house RiskEngine combines — it never decides allow/deny.  On a
transport/auth/shape failure it raises :class:`ProviderError`; the RiskEngine
treats a raising feed on a high-value path as "cannot clear" and escalates
(fail-closed), never silently allowing.
"""

from __future__ import annotations

from typing import Any

from ..ports.types import (
    CustodyModel,
    ProviderCapability,
    ProviderError,
    RecommendedAction,
    RiskSignalResult,
)
from .client import SeonClient, StripeRadarClient


class StripeRadarFraudSignalAdapter:
    """:class:`FraudSignalPort` over Stripe Radar's charge-outcome risk read.

    Stripe scores card legs it processes; an on-chain Sardis-native payment has
    no Stripe charge, so when the context carries no ``stripe_charge_id`` the
    adapter returns a NOT_ASSESSED zero-score signal (it abstains rather than
    inventing risk).  When a charge id is present it surfaces the network
    risk_score / risk_level.
    """

    capability = ProviderCapability.FRAUD_SIGNAL

    def __init__(self, client: StripeRadarClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "stripe_radar"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.SIMULATED  # no funds flow through a signal feed

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    @staticmethod
    def _level_to_action(level: str) -> RecommendedAction:
        return {
            "normal": RecommendedAction.ALLOW,
            "elevated": RecommendedAction.REVIEW,
            "highest": RecommendedAction.DECLINE,
        }.get(level, RecommendedAction.NOT_ASSESSED)

    @staticmethod
    def _level_to_score(level: str) -> float:
        # When Radar (non-Fraud-Teams) returns only a level, map to a
        # representative 0-100 score within that band's documented range.
        return {
            "normal": 20.0,
            "elevated": 70.0,
            "highest": 90.0,
        }.get(level, 0.0)

    async def score(self, context: dict[str, Any]) -> RiskSignalResult:
        charge_id = context.get("stripe_charge_id") or context.get("charge_id")
        if not charge_id:
            return RiskSignalResult(
                provider=self.provider,
                score=0.0,
                reasons=("no stripe charge in context; not a Stripe-scored leg",),
                recommended_action=RecommendedAction.NOT_ASSESSED,
                sandbox=self.sandbox,
            )
        try:
            outcome = await self._client.get_charge_outcome(str(charge_id))
        except Exception as exc:  # noqa: BLE001 - normalized to ProviderError
            raise ProviderError(
                f"stripe_radar_score_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc

        level = outcome.risk_level
        # Prefer the numeric Fraud-Teams score; otherwise map the level to a band.
        score = (
            float(outcome.risk_score)
            if outcome.risk_score is not None
            else self._level_to_score(level)
        )
        reasons = [f"stripe risk_level={level}"]
        if outcome.risk_score is not None:
            reasons.append(f"risk_score={outcome.risk_score}")
        if outcome.reason:
            reasons.append(str(outcome.reason))
        return RiskSignalResult(
            provider=self.provider,
            score=max(0.0, min(100.0, score)),
            reasons=tuple(reasons),
            recommended_action=self._level_to_action(level),
            sandbox=self.sandbox,
            reference=outcome.charge_id,
            raw={
                "risk_level": level,
                "risk_score": outcome.risk_score,
                "outcome_type": outcome.outcome_type,
                "reason": outcome.reason,
            },
        )


class SeonFraudSignalAdapter:
    """:class:`FraudSignalPort` over SEON's fraud-api score + state."""

    capability = ProviderCapability.FRAUD_SIGNAL

    def __init__(self, client: SeonClient) -> None:
        self._client = client

    @property
    def provider(self) -> str:
        return "seon"

    @property
    def custody_model(self) -> CustodyModel:
        return CustodyModel.SIMULATED

    @property
    def sandbox(self) -> bool:
        return self._client.is_sandbox

    @staticmethod
    def _state_to_action(state: str) -> RecommendedAction:
        return {
            "APPROVE": RecommendedAction.ALLOW,
            "REVIEW": RecommendedAction.REVIEW,
            "DECLINE": RecommendedAction.DECLINE,
        }.get(state.upper(), RecommendedAction.NOT_ASSESSED)

    def _build_body(self, context: dict[str, Any]) -> dict[str, Any]:
        """Map the engine's context onto SEON's fraud-api request body.

        Only fields Sardis actually has for an agent payment are sent; SEON
        scores on whatever subset is present.
        """
        body: dict[str, Any] = {
            # Turn on the enrichment modules only when we have the input for them.
            "config": {
                "email_api": bool(context.get("email")),
                "ip_api": bool(context.get("ip")),
                "device_fingerprinting": bool(context.get("session")),
            },
        }
        amount = context.get("amount")
        if amount is not None:
            # Money is a decimal string on the wire — never a float literal.
            body["transaction_amount"] = str(amount)
        for src, dst in (
            ("currency", "transaction_currency"),
            ("email", "email"),
            ("ip", "ip"),
            ("agent_id", "user_id"),
            ("counterparty", "transaction_id"),
            ("session", "session"),
        ):
            val = context.get(src)
            if val:
                body[dst] = str(val)
        return body

    async def score(self, context: dict[str, Any]) -> RiskSignalResult:
        try:
            result = await self._client.score(self._build_body(context))
        except Exception as exc:  # noqa: BLE001 - normalized to ProviderError
            raise ProviderError(
                f"seon_score_failed: {exc}",
                provider=self.provider,
                capability=self.capability,
                retryable=True,
            ) from exc

        reasons = [f"seon state={result.state}", f"fraud_score={result.fraud_score:g}"]
        for rule in result.applied_rules[:5]:
            name = rule.get("name") or rule.get("id")
            if name:
                reasons.append(f"rule:{name}")
        return RiskSignalResult(
            provider=self.provider,
            score=max(0.0, min(100.0, float(result.fraud_score))),
            reasons=tuple(reasons),
            recommended_action=self._state_to_action(result.state),
            sandbox=self.sandbox,
            reference=result.seon_id or None,
            raw={"state": result.state, "applied_rules": result.applied_rules},
        )
