"""Execution mode routing for multi-modal payments.

Routes payment intents to the correct executor based on credentials,
merchant capabilities, cost, and policy-governed fallback rules.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from .credential_store import CredentialStore
from .delegated_credential import CredentialNetwork, DelegatedCredential
from .execution_intent import ExecutionIntent
from .merchant_capability import MerchantCapabilityStore, MerchantExecutionCapability

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    NATIVE_CRYPTO = "native_crypto"
    OFFRAMP_SETTLEMENT = "offramp_settlement"
    DELEGATED_CARD = "delegated_card"


class FallbackPolicy(str, Enum):
    FAIL_CLOSED = "fail_closed"
    POLICY_GOVERNED = "policy_governed"


@dataclass
class ExecutionModeSelection:
    """Result of mode routing — includes reasoning trace for explainability."""

    mode: ExecutionMode
    credential_id: Optional[str] = None
    reason: str = ""
    estimated_fee: Decimal = Decimal("0")
    settlement_time_seconds: int = 0

    # Fallback tracking
    fallback_applied: bool = False
    original_mode: Optional[ExecutionMode] = None

    # Explainability
    evaluated_modes: list[str] = field(default_factory=list)
    rejected_modes: dict[str, str] = field(default_factory=dict)
    capability_confidence_used: float = 0.0
    consent_freshness_valid: bool = True
    policy_fallback_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "credential_id": self.credential_id,
            "reason": self.reason,
            "estimated_fee": str(self.estimated_fee),
            "settlement_time_seconds": self.settlement_time_seconds,
            "fallback_applied": self.fallback_applied,
            "original_mode": self.original_mode.value if self.original_mode else None,
            "evaluated_modes": self.evaluated_modes,
            "rejected_modes": self.rejected_modes,
        }


@dataclass
class RoutingThresholds:
    """Operationalised confidence thresholds."""

    min_confidence_for_auto_route: float = 0.7
    min_confidence_for_user_approved_route: float = 0.4
    capability_staleness_window_hours: int = 72


# Cost/settlement estimates per mode
_MODE_COST_RANK: dict[ExecutionMode, tuple[Decimal, int]] = {
    ExecutionMode.NATIVE_CRYPTO: (Decimal("0.005"), 30),       # 0.5%, ~30s
    ExecutionMode.OFFRAMP_SETTLEMENT: (Decimal("0.015"), 3600),  # 1.5%, ~1h
    ExecutionMode.DELEGATED_CARD: (Decimal("0.025"), 7200),     # 2.5%, ~2h
}


class ExecutionModeRouter:
    """Selects optimal execution mode for a payment intent."""

    def __init__(
        self,
        credential_store: CredentialStore,
        merchant_capability_store: MerchantCapabilityStore,
        thresholds: Optional[RoutingThresholds] = None,
    ) -> None:
        self._cred_store = credential_store
        self._merchant_store = merchant_capability_store
        self._thresholds = thresholds or RoutingThresholds()

    async def resolve(self, intent: ExecutionIntent) -> ExecutionModeSelection:
        """Pick the best execution mode for this intent."""
        evaluated: list[str] = []
        rejected: dict[str, str] = {}

        explicit_mode_str = intent.metadata.get("execution_mode", "")
        explicit_cred_id = intent.metadata.get("credential_id", "") or getattr(intent, "credential_id", "")
        merchant_id = intent.metadata.get("merchant_id", "")
        fallback_policy_str = intent.metadata.get("fallback_policy", "fail_closed")
        fallback_policy = (
            FallbackPolicy.POLICY_GOVERNED
            if fallback_policy_str == "policy_governed"
            else FallbackPolicy.FAIL_CLOSED
        )

        # Fetch merchant capabilities (may be None for unknown merchants)
        merchant_cap: Optional[MerchantExecutionCapability] = None
        if merchant_id:
            merchant_cap = await self._merchant_store.get(merchant_id)

        # ── Explicit mode requested ──────────────────────────────
        if explicit_mode_str:
            try:
                explicit_mode = ExecutionMode(explicit_mode_str)
            except ValueError:
                raise ValueError(f"Unknown execution mode: {explicit_mode_str}")

            evaluated.append(explicit_mode.value)
            ok, reason = await self._check_mode_viable(
                explicit_mode, intent, merchant_cap, explicit_cred_id,
            )
            if ok:
                fee, settle = _MODE_COST_RANK[explicit_mode]
                return ExecutionModeSelection(
                    mode=explicit_mode,
                    credential_id=explicit_cred_id or None,
                    reason=f"Explicit mode: {explicit_mode.value}",
                    estimated_fee=intent.amount * fee,
                    settlement_time_seconds=settle,
                    evaluated_modes=evaluated,
                    rejected_modes=rejected,
                    capability_confidence_used=(
                        merchant_cap.confidence if merchant_cap else 0.0
                    ),
                )

            # Explicit mode not viable — fail closed (no silent fallback)
            rejected[explicit_mode.value] = reason
            if fallback_policy == FallbackPolicy.FAIL_CLOSED:
                raise ValueError(
                    f"Explicit mode {explicit_mode.value} not available: {reason}. "
                    "Fallback is FAIL_CLOSED."
                )

            # Policy-governed fallback: fall through to auto-routing
            logger.warning(
                "Explicit mode %s failed (%s), policy allows fallback",
                explicit_mode.value, reason,
            )

        # ── Auto mode: evaluate candidates ───────────────────────
        candidates: list[tuple[ExecutionMode, Decimal, int, Optional[str]]] = []

        for mode in ExecutionMode:
            evaluated.append(mode.value)
            ok, reason = await self._check_mode_viable(
                mode, intent, merchant_cap, "",
            )
            if not ok:
                rejected[mode.value] = reason
                continue

            # Confidence check for auto-routing
            if merchant_cap and merchant_cap.confidence < self._thresholds.min_confidence_for_auto_route:
                if mode in (ExecutionMode.DELEGATED_CARD, ExecutionMode.OFFRAMP_SETTLEMENT):
                    rejected[mode.value] = (
                        f"merchant confidence {merchant_cap.confidence} "
                        f"below auto-route threshold {self._thresholds.min_confidence_for_auto_route}"
                    )
                    continue

            fee_rate, settle = _MODE_COST_RANK[mode]
            cred_id: Optional[str] = None
            if mode == ExecutionMode.DELEGATED_CARD:
                creds = await self._cred_store.get_active_for_agent(intent.agent_id)
                if creds:
                    cred_id = creds[0].credential_id
            candidates.append((mode, intent.amount * fee_rate, settle, cred_id))

        if not candidates:
            raise ValueError(
                f"No execution mode available. Evaluated: {evaluated}, "
                f"Rejected: {rejected}"
            )

        # Cost-rank: crypto < offramp < card
        candidates.sort(key=lambda c: (c[1], c[2]))
        best_mode, best_fee, best_settle, best_cred = candidates[0]

        fallback_applied = bool(explicit_mode_str)
        return ExecutionModeSelection(
            mode=best_mode,
            credential_id=best_cred,
            reason=f"Auto-selected: lowest cost ({best_mode.value})",
            estimated_fee=best_fee,
            settlement_time_seconds=best_settle,
            fallback_applied=fallback_applied,
            original_mode=(
                ExecutionMode(explicit_mode_str) if explicit_mode_str else None
            ),
            evaluated_modes=evaluated,
            rejected_modes=rejected,
            capability_confidence_used=(
                merchant_cap.confidence if merchant_cap else 0.0
            ),
            policy_fallback_allowed=fallback_applied,
        )

    async def get_available_modes(
        self,
        agent_id: str,
        amount: Decimal,
        currency: str,
        merchant_id: Optional[str] = None,
    ) -> list[ExecutionModeSelection]:
        """List all viable modes for a given context."""
        merchant_cap = None
        if merchant_id:
            merchant_cap = await self._merchant_store.get(merchant_id)

        intent = ExecutionIntent(
            agent_id=agent_id,
            amount=amount,
            currency=currency,
            metadata={"merchant_id": merchant_id or ""},
        )

        results: list[ExecutionModeSelection] = []
        for mode in ExecutionMode:
            ok, reason = await self._check_mode_viable(mode, intent, merchant_cap, "")
            fee_rate, settle = _MODE_COST_RANK[mode]
            cred_id = None
            if mode == ExecutionMode.DELEGATED_CARD and ok:
                creds = await self._cred_store.get_active_for_agent(agent_id)
                if creds:
                    cred_id = creds[0].credential_id
            results.append(ExecutionModeSelection(
                mode=mode,
                credential_id=cred_id,
                reason=reason if not ok else f"Available ({mode.value})",
                estimated_fee=amount * fee_rate,
                settlement_time_seconds=settle,
                capability_confidence_used=(
                    merchant_cap.confidence if merchant_cap else 0.0
                ),
            ))
        return results

    # ── Private helpers ──────────────────────────────────────────

    async def _check_mode_viable(
        self,
        mode: ExecutionMode,
        intent: ExecutionIntent,
        merchant_cap: Optional[MerchantExecutionCapability],
        credential_id: str,
    ) -> tuple[bool, str]:
        """Check whether a mode is viable for the given intent."""

        if mode == ExecutionMode.NATIVE_CRYPTO:
            if not intent.recipient_address:
                return False, "no recipient on-chain address"
            if merchant_cap and not merchant_cap.accepts_native_crypto:
                return False, "merchant does not accept crypto"
            return True, "OK"

        if mode == ExecutionMode.OFFRAMP_SETTLEMENT:
            # Offramp is available if merchant accepts card/fiat
            if merchant_cap and not merchant_cap.accepts_card:
                return False, "merchant does not accept fiat settlement"
            return True, "OK"

        if mode == ExecutionMode.DELEGATED_CARD:
            # Need active credential
            if credential_id:
                cred = await self._cred_store.get(credential_id)
                if cred is None:
                    return False, f"credential {credential_id} not found"
                ok, reason = cred.can_execute(
                    intent.amount,
                    merchant_id=intent.metadata.get("merchant_id"),
                    mcc_code=intent.metadata.get("mcc_code"),
                )
                if not ok:
                    return False, reason
                return True, "OK"

            # No specific credential — check if agent has any active ones
            creds = await self._cred_store.get_active_for_agent(intent.agent_id)
            if not creds:
                return False, "no active delegated credentials for agent"

            # Check merchant supports delegated card
            if merchant_cap and not merchant_cap.supports_delegated_card:
                return False, "merchant does not support delegated card"

            # Check at least one credential can execute
            for c in creds:
                ok, _ = c.can_execute(
                    intent.amount,
                    merchant_id=intent.metadata.get("merchant_id"),
                    mcc_code=intent.metadata.get("mcc_code"),
                )
                if ok:
                    return True, "OK"
            return False, "no credential with valid scope for this transaction"

        return False, f"unknown mode: {mode}"
