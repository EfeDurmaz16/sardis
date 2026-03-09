"""Central control plane for payment execution.

Orchestrates the full pipeline: policy → anomaly → compliance → chain → ledger.
All payment flows (A2A, AP2, checkout) submit ExecutionIntents here.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from sardis_guardrails.anomaly_engine import AnomalyEngine
    from sardis_guardrails.kill_switch import KillSwitch
    from sardis_guardrails.transaction_caps import TransactionCapEngine

from .config import SardisSettings, load_settings
from .execution_intent import (
    ExecutionIntent,
    ExecutionResult,
    IntentStatus,
    SimulationResult,
)
from .execution_receipt import build_receipt

logger = logging.getLogger(__name__)


class PolicyEvaluator(Protocol):
    """Interface for policy evaluation."""
    async def evaluate(self, intent: ExecutionIntent) -> dict[str, Any]: ...


class ComplianceChecker(Protocol):
    """Interface for compliance checks."""
    async def check(self, intent: ExecutionIntent) -> dict[str, Any]: ...


class ChainExecutor(Protocol):
    """Interface for chain execution."""
    async def execute(self, intent: ExecutionIntent) -> dict[str, Any]: ...


class LedgerRecorder(Protocol):
    """Interface for ledger recording."""
    async def record(self, intent: ExecutionIntent, tx_result: dict[str, Any]) -> str: ...


class ControlPlane:
    """Single execution path from intent to completion.

    Orchestrates:
    1. Policy evaluation (spending rules, allowlists)
    2. Compliance checks (KYC, AML, sanctions)
    3. Chain execution (on-chain transfer)
    4. Ledger recording (audit trail)
    5. Receipt generation (signed proof)
    """

    def __init__(
        self,
        policy_evaluator: PolicyEvaluator | None = None,
        compliance_checker: ComplianceChecker | None = None,
        chain_executor: ChainExecutor | None = None,
        ledger_recorder: LedgerRecorder | None = None,
        anomaly_engine: AnomalyEngine | None = None,
        kill_switch: KillSwitch | None = None,
        cap_engine: TransactionCapEngine | None = None,
        receipt_store: Any | None = None,
        outcome_tracker: Any | None = None,
        trust_scorer: Any | None = None,
        fides_config: Any | None = None,
        agit_policy_engine: Any | None = None,
        settings: SardisSettings | None = None,
    ) -> None:
        self._policy = policy_evaluator
        self._compliance = compliance_checker
        self._chain = chain_executor
        self._ledger = ledger_recorder
        self._anomaly_engine = anomaly_engine
        self._kill_switch = kill_switch
        self._cap_engine = cap_engine
        self._receipt_store = receipt_store
        self._outcome_tracker = outcome_tracker
        self._trust_scorer = trust_scorer
        self._fides_config = fides_config
        self._agit_policy_engine = agit_policy_engine
        self._settings = settings or load_settings()

    async def submit(self, intent: ExecutionIntent) -> ExecutionResult:
        """Execute an intent through the full pipeline."""
        logger.info(
            "ControlPlane: submitting intent=%s source=%s amount=%s chain=%s",
            intent.intent_id, intent.source.value, intent.amount, intent.chain,
        )

        try:
            # Step 0a: Kill switch check (defense-in-depth)
            if self._kill_switch is not None:
                from sardis_guardrails.kill_switch import KillSwitchError

                try:
                    # Check global, org, and agent scopes
                    await self._kill_switch.check(
                        agent_id=intent.agent_id, org_id=intent.org_id,
                    )
                    # Check chain-level kill switch
                    if intent.chain:
                        await self._kill_switch.check_chain(intent.chain)
                except KillSwitchError as e:
                    intent.status = IntentStatus.REJECTED
                    intent.error = f"kill_switch_active: {e}"
                    logger.warning(
                        "ControlPlane: intent=%s blocked by kill switch: %s",
                        intent.intent_id, e,
                    )
                    return ExecutionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        status=IntentStatus.REJECTED,
                        error=f"kill_switch_active: {e}",
                    )

            # Step 0b: Transaction cap check (defense-in-depth)
            if self._cap_engine is not None and intent.amount > 0:
                cap_result = await self._cap_engine.check_and_record(
                    amount=intent.amount,
                    org_id=intent.org_id,
                    agent_id=intent.agent_id or None,
                )
                if not cap_result.allowed:
                    intent.status = IntentStatus.REJECTED
                    intent.error = f"transaction_cap_exceeded: {cap_result.message}"
                    logger.warning(
                        "ControlPlane: intent=%s blocked by transaction cap: %s",
                        intent.intent_id, cap_result.message,
                    )
                    return ExecutionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        status=IntentStatus.REJECTED,
                        error=f"transaction_cap_exceeded: {cap_result.message}",
                        data={
                            "cap_type": cap_result.cap_type,
                            "remaining": str(cap_result.remaining),
                            "daily_total": str(cap_result.daily_total),
                        },
                    )

            # Step 1: Policy evaluation (skip if already done upstream)
            if self._policy and intent.policy_result is None:
                intent.status = IntentStatus.POLICY_CHECKED
                policy_result = await self._policy.evaluate(intent)
                intent.policy_result = policy_result
                if not policy_result.get("allowed", True):
                    intent.status = IntentStatus.REJECTED
                    intent.error = policy_result.get("reason", "Policy denied")
                    return ExecutionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        status=IntentStatus.REJECTED,
                        error=intent.error,
                    )

            # Step 1.25: AGIT policy chain integrity (if enabled)
            if self._agit_policy_engine and intent.agent_id:
                try:
                    import asyncio
                    verification = await asyncio.to_thread(
                        self._agit_policy_engine.verify_policy_chain, intent.agent_id,
                    )
                    if not verification.valid:
                        intent.status = IntentStatus.REJECTED
                        intent.error = "policy_chain_tampered"
                        logger.warning(
                            "ControlPlane: intent=%s blocked — policy chain tampered at commit %s",
                            intent.intent_id, verification.broken_at,
                        )
                        return ExecutionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            status=IntentStatus.REJECTED,
                            error="policy_chain_tampered",
                            data={
                                "broken_at": verification.broken_at,
                                "chain_length": verification.chain_length,
                                "error": verification.error,
                            },
                        )
                except Exception as e:
                    if self._settings.agit_fail_open:
                        logger.warning(
                            "ControlPlane: AGIT chain check failed for intent=%s: %s (fail-open enabled)",
                            intent.intent_id, e,
                        )
                    else:
                        logger.error(
                            "ControlPlane: AGIT chain check failed for intent=%s: %s (fail-closed, rejecting)",
                            intent.intent_id, e,
                        )
                        return ExecutionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            status=IntentStatus.REJECTED,
                            error=f"AGIT policy verification unavailable: {e}",
                        )

            # Step 1.5a: FIDES trust gate (if enabled)
            if self._trust_scorer and self._fides_config and intent.metadata.get("fides_did"):
                try:
                    trust_score = await self._trust_scorer.calculate_trust(
                        agent_id=intent.agent_id,
                        agent_did=intent.metadata["fides_did"],
                    )
                    min_trust = getattr(self._fides_config, "min_trust_for_payment", 0.3)
                    if trust_score.overall < min_trust:
                        intent.status = IntentStatus.REJECTED
                        intent.error = f"trust_score_insufficient: {trust_score.overall:.2f} < {min_trust}"
                        return ExecutionResult(
                            intent_id=intent.intent_id,
                            success=False,
                            status=IntentStatus.REJECTED,
                            error=intent.error,
                            data={
                                "trust_score": trust_score.overall,
                                "trust_tier": trust_score.tier.value,
                                "min_required": min_trust,
                            },
                        )
                except Exception as e:
                    logger.warning(
                        "ControlPlane: FIDES trust check failed for intent=%s: %s (non-blocking)",
                        intent.intent_id, e,
                    )

            # Step 1.5: Anomaly risk assessment (optional)
            anomaly_flag: dict[str, Any] | None = None
            if self._anomaly_engine is not None:
                from sardis_guardrails.anomaly_engine import RiskAction

                assessment = self._anomaly_engine.assess_risk(
                    agent_id=intent.agent_id,
                    amount=intent.amount,
                    merchant_id=intent.metadata.get("merchant_id"),
                    merchant_category=intent.metadata.get("merchant_category"),
                    behavioral_alerts=intent.metadata.get("behavioral_alerts"),
                    baseline_mean=intent.metadata.get("baseline_mean"),
                    baseline_std=intent.metadata.get("baseline_std"),
                    recent_tx_count_1h=intent.metadata.get("recent_tx_count_1h", 0),
                    is_new_merchant=intent.metadata.get("is_new_merchant", False),
                    hour_of_day=intent.metadata.get("hour_of_day"),
                    typical_hours=intent.metadata.get("typical_hours"),
                )
                logger.info(
                    "ControlPlane: anomaly assessment intent=%s score=%.3f action=%s",
                    intent.intent_id, assessment.overall_score, assessment.action.value,
                )

                if assessment.action == RiskAction.KILL_SWITCH:
                    intent.status = IntentStatus.REJECTED
                    intent.error = "kill_switch_activated_by_anomaly"
                    return ExecutionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        status=IntentStatus.REJECTED,
                        error="kill_switch_activated_by_anomaly",
                        data={"anomaly_score": assessment.overall_score,
                              "anomaly_action": assessment.action.value},
                    )

                if assessment.action == RiskAction.FREEZE_AGENT:
                    intent.status = IntentStatus.REJECTED
                    intent.error = "agent_frozen_by_anomaly"
                    return ExecutionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        status=IntentStatus.REJECTED,
                        error="agent_frozen_by_anomaly",
                        data={"anomaly_score": assessment.overall_score,
                              "anomaly_action": assessment.action.value},
                    )

                if assessment.action == RiskAction.REQUIRE_APPROVAL:
                    intent.status = IntentStatus.REJECTED
                    intent.error = "anomaly_requires_approval"
                    return ExecutionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        status=IntentStatus.REJECTED,
                        error="anomaly_requires_approval",
                        data={"anomaly_score": assessment.overall_score,
                              "anomaly_action": assessment.action.value},
                    )

                if assessment.action == RiskAction.FLAG:
                    anomaly_flag = {
                        "anomaly_flagged": True,
                        "anomaly_score": assessment.overall_score,
                        "anomaly_action": assessment.action.value,
                        "anomaly_signals": [
                            {"type": s.signal_type, "score": s.score, "description": s.description}
                            for s in assessment.signals if s.score > 0
                        ],
                    }
                    logger.warning(
                        "ControlPlane: intent=%s flagged by anomaly engine (score=%.3f)",
                        intent.intent_id, assessment.overall_score,
                    )

                # RiskAction.ALLOW → continue normally (anomaly_flag stays None)

            # Step 2: Compliance (skip if already done upstream)
            if self._compliance and intent.compliance_result is None:
                intent.status = IntentStatus.COMPLIANCE_CHECKED
                compliance_result = await self._compliance.check(intent)
                intent.compliance_result = compliance_result
                if not compliance_result.get("allowed", True):
                    intent.status = IntentStatus.REJECTED
                    intent.error = compliance_result.get("reason", "Compliance check failed")
                    return ExecutionResult(
                        intent_id=intent.intent_id,
                        success=False,
                        status=IntentStatus.REJECTED,
                        error=intent.error,
                    )

            # Step 3: Chain execution
            intent.status = IntentStatus.EXECUTING
            if self._chain:
                tx_result = await self._chain.execute(intent)
                intent.tx_hash = tx_result.get("tx_hash", "")
            else:
                tx_result = {}

            # Step 4: Ledger recording
            if self._ledger:
                entry_id = await self._ledger.record(intent, tx_result)
                intent.ledger_entry_id = entry_id

            # Step 5: Receipt generation
            receipt = build_receipt(
                intent=intent.to_dict(),
                policy_snapshot=intent.policy_result,
                compliance_result=intent.compliance_result,
                tx_hash=intent.tx_hash,
                chain=intent.chain,
                ledger_entry_id=intent.ledger_entry_id,
                org_id=intent.org_id,
                agent_id=intent.agent_id,
                amount=str(intent.amount),
                currency=intent.currency,
            )
            intent.receipt_id = receipt.receipt_id
            intent.status = IntentStatus.COMPLETED

            # Persist receipt if store available
            if self._receipt_store is not None:
                try:
                    await self._receipt_store.save(receipt)
                except Exception as e:
                    logger.warning("Failed to persist receipt %s: %s", receipt.receipt_id, e)

            # Record decision outcome for learning loops
            if self._outcome_tracker is not None:
                try:
                    await self._outcome_tracker.record_decision(
                        receipt_id=receipt.receipt_id,
                        intent_id=intent.intent_id,
                        decision="approved",
                        reason="pipeline_passed",
                        agent_id=intent.agent_id,
                        org_id=intent.org_id,
                        merchant_id=intent.metadata.get("merchant_id", ""),
                        amount=intent.amount,
                        currency=intent.currency,
                        anomaly_score=anomaly_flag.get("anomaly_score", 0.0) if anomaly_flag else 0.0,
                        confidence_score=intent.metadata.get("confidence_score", 0.0),
                    )
                except Exception as e:
                    logger.warning("Failed to record outcome decision: %s", e)

            logger.info(
                "ControlPlane: intent=%s completed tx=%s receipt=%s",
                intent.intent_id, intent.tx_hash, receipt.receipt_id,
            )

            result_data = dict(tx_result)
            if anomaly_flag is not None:
                result_data.update(anomaly_flag)

            return ExecutionResult(
                intent_id=intent.intent_id,
                success=True,
                status=IntentStatus.COMPLETED,
                tx_hash=intent.tx_hash,
                receipt_id=receipt.receipt_id,
                ledger_entry_id=intent.ledger_entry_id,
                data=result_data,
            )

        except Exception as e:
            intent.status = IntentStatus.FAILED
            intent.error = str(e)
            logger.exception(
                "ControlPlane: intent=%s failed: %s", intent.intent_id, e,
            )
            return ExecutionResult(
                intent_id=intent.intent_id,
                success=False,
                status=IntentStatus.FAILED,
                error=str(e),
            )

    async def simulate(self, intent: ExecutionIntent) -> SimulationResult:
        """Dry-run an intent without executing on chain.

        Returns all reachable failure reasons.
        """
        failure_reasons: list[str] = []
        policy_result = None
        compliance_result = None

        # Check policy
        if self._policy:
            try:
                policy_result = await self._policy.evaluate(intent)
                if not policy_result.get("allowed", True):
                    failure_reasons.append(f"Policy: {policy_result.get('reason', 'denied')}")
            except Exception as e:
                failure_reasons.append(f"Policy error: {e}")

        # Check compliance
        if self._compliance:
            try:
                compliance_result = await self._compliance.check(intent)
                if not compliance_result.get("allowed", True):
                    failure_reasons.append(f"Compliance: {compliance_result.get('reason', 'failed')}")
            except Exception as e:
                failure_reasons.append(f"Compliance error: {e}")

        # Check caps
        cap_check = None
        try:
            from sardis_guardrails.transaction_caps import get_transaction_cap_engine
            engine = get_transaction_cap_engine()
            # Use check-only (don't record)
            daily_spend = await engine._get_daily_spend("org", intent.org_id)
            cap_check = {
                "daily_spend": str(daily_spend),
                "amount": str(intent.amount),
            }
        except Exception:
            pass

        # Check kill switches
        ks_status = None
        try:
            from sardis_guardrails.kill_switch import get_kill_switch
            ks = get_kill_switch()
            active = await ks.get_active_switches()
            if active.get("global"):
                failure_reasons.append("Kill switch: global active")
            ks_status = {
                "global_active": active.get("global") is not None,
                "org_active": intent.org_id in (active.get("organizations") or {}),
            }
        except Exception:
            pass

        intent.status = IntentStatus.SIMULATED

        return SimulationResult(
            intent_id=intent.intent_id,
            would_succeed=len(failure_reasons) == 0,
            failure_reasons=failure_reasons,
            policy_result=policy_result,
            compliance_result=compliance_result,
            cap_check=cap_check,
            kill_switch_status=ks_status,
        )
