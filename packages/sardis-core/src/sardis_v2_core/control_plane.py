"""Central control plane for payment execution.

Orchestrates the full pipeline: policy → compliance → chain → ledger.
All payment flows (A2A, AP2, checkout) submit ExecutionIntents here.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Protocol

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
        policy_evaluator: Optional[PolicyEvaluator] = None,
        compliance_checker: Optional[ComplianceChecker] = None,
        chain_executor: Optional[ChainExecutor] = None,
        ledger_recorder: Optional[LedgerRecorder] = None,
    ) -> None:
        self._policy = policy_evaluator
        self._compliance = compliance_checker
        self._chain = chain_executor
        self._ledger = ledger_recorder

    async def submit(self, intent: ExecutionIntent) -> ExecutionResult:
        """Execute an intent through the full pipeline."""
        logger.info(
            "ControlPlane: submitting intent=%s source=%s amount=%s chain=%s",
            intent.intent_id, intent.source.value, intent.amount, intent.chain,
        )

        try:
            # Step 1: Policy evaluation
            if self._policy:
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

            # Step 2: Compliance
            if self._compliance:
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

            logger.info(
                "ControlPlane: intent=%s completed tx=%s receipt=%s",
                intent.intent_id, intent.tx_hash, receipt.receipt_id,
            )

            return ExecutionResult(
                intent_id=intent.intent_id,
                success=True,
                status=IntentStatus.COMPLETED,
                tx_hash=intent.tx_hash,
                receipt_id=receipt.receipt_id,
                ledger_entry_id=intent.ledger_entry_id,
                data=tx_result,
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
            from sardis_guardrails.transaction_caps import CapCheckResult
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
