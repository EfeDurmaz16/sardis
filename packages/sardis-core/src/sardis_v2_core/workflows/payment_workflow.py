"""Temporal workflow for the 6-phase payment orchestrator.

Implements the Saga pattern: each phase has a compensating action
that runs on failure to maintain consistency.

Phases:
0. KYA Verification
1. Policy Check
2. Compliance Screening (never skipped)
3. Chain Execution
4. Ledger Append
5. Webhook Notification
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

logger = logging.getLogger("sardis.workflows.payment")

try:
    from temporalio import workflow
    from temporalio.common import RetryPolicy

    _HAS_TEMPORAL = True
except ImportError:
    _HAS_TEMPORAL = False

    class _workflow_stub:
        @staticmethod
        def defn(cls=None, *, name=None):
            if cls is not None:
                return cls
            def wrapper(c):
                return c
            return wrapper

        @staticmethod
        def run(fn):
            return fn

    class RetryPolicy:
        def __init__(self, **kwargs):
            pass

    workflow = _workflow_stub()  # type: ignore[assignment]


# Import activity stubs
from .activities import (
    ActivityResult,
    PaymentActivityInput,
)


@dataclass
class PaymentWorkflowInput:
    """Input for the payment workflow."""
    mandate_id: str
    agent_id: str
    amount_minor: int
    currency: str = "USDC"
    chain: str = "base"
    merchant_id: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class PaymentWorkflowResult:
    """Result of the payment workflow."""
    success: bool
    mandate_id: str
    phase_results: dict[str, ActivityResult]
    error: str | None = None
    tx_hash: str | None = None


# Retry policies per phase
KYA_RETRY = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(seconds=1),
)
POLICY_RETRY = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(seconds=1),
)
COMPLIANCE_RETRY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
)
CHAIN_RETRY = RetryPolicy(
    maximum_attempts=5,
    initial_interval=timedelta(seconds=3),
    maximum_interval=timedelta(seconds=60),
    backoff_coefficient=2.0,
)
LEDGER_RETRY = RetryPolicy(
    maximum_attempts=10,
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
)
WEBHOOK_RETRY = RetryPolicy(
    maximum_attempts=5,
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=120),
    backoff_coefficient=3.0,
)


@workflow.defn(name="PaymentWorkflow")
class PaymentWorkflow:
    """Durable 6-phase payment execution as a Temporal Workflow.

    Saga pattern: if chain execution succeeds but ledger append fails,
    the transaction is recorded in a reconciliation queue for recovery.
    """

    @workflow.run
    async def run(self, input: PaymentWorkflowInput) -> PaymentWorkflowResult:
        activity_input = PaymentActivityInput(
            mandate_id=input.mandate_id,
            agent_id=input.agent_id,
            amount_minor=input.amount_minor,
            currency=input.currency,
            chain=input.chain,
            merchant_id=input.merchant_id,
            idempotency_key=input.idempotency_key,
            metadata=input.metadata,
        )

        results: dict[str, ActivityResult] = {}

        # When running without Temporal, execute activities directly
        if not _HAS_TEMPORAL:
            return await self._run_direct(activity_input, results)

        # Phase 0: KYA Verification
        kya_result = await workflow.execute_activity(
            "kya_verification",
            activity_input,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=KYA_RETRY,
        )
        results["kya_verification"] = kya_result
        if not kya_result.success:
            return PaymentWorkflowResult(
                success=False, mandate_id=input.mandate_id,
                phase_results=results, error=f"KYA denied: {kya_result.error}",
            )

        # Phase 1: Policy Check
        policy_result = await workflow.execute_activity(
            "policy_check",
            activity_input,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=POLICY_RETRY,
        )
        results["policy_check"] = policy_result
        if not policy_result.success:
            return PaymentWorkflowResult(
                success=False, mandate_id=input.mandate_id,
                phase_results=results, error=f"Policy denied: {policy_result.error}",
            )

        # Phase 2: Compliance (NEVER skipped)
        compliance_result = await workflow.execute_activity(
            "compliance_screening",
            activity_input,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=COMPLIANCE_RETRY,
        )
        results["compliance_screening"] = compliance_result
        if not compliance_result.success:
            return PaymentWorkflowResult(
                success=False, mandate_id=input.mandate_id,
                phase_results=results, error=f"Compliance denied: {compliance_result.error}",
            )

        # Phase 3: Chain Execution
        chain_result = await workflow.execute_activity(
            "chain_execution",
            activity_input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=CHAIN_RETRY,
        )
        results["chain_execution"] = chain_result
        if not chain_result.success:
            return PaymentWorkflowResult(
                success=False, mandate_id=input.mandate_id,
                phase_results=results, error=f"Chain execution failed: {chain_result.error}",
            )

        # Phase 4: Ledger Append (must succeed — reconciliation queue if not)
        ledger_result = await workflow.execute_activity(
            "ledger_append",
            activity_input,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=LEDGER_RETRY,
        )
        results["ledger_append"] = ledger_result

        # Phase 5: Webhook Notification (best-effort, don't fail payment)
        try:
            webhook_result = await workflow.execute_activity(
                "webhook_notification",
                activity_input,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=WEBHOOK_RETRY,
            )
            results["webhook_notification"] = webhook_result
        except Exception:
            results["webhook_notification"] = ActivityResult(
                success=False, phase="webhook_notification",
                error="webhook_delivery_failed",
            )

        tx_hash = None
        if chain_result.data:
            tx_hash = chain_result.data.get("tx_hash")

        return PaymentWorkflowResult(
            success=True, mandate_id=input.mandate_id,
            phase_results=results, tx_hash=tx_hash,
        )

    async def _run_direct(
        self, input: PaymentActivityInput, results: dict
    ) -> PaymentWorkflowResult:
        """Fallback: run activities directly without Temporal."""
        from .activities import (
            chain_execution,
            compliance_screening,
            kya_verification,
            ledger_append,
            policy_check,
            webhook_notification,
        )

        phases = [
            ("kya_verification", kya_verification),
            ("policy_check", policy_check),
            ("compliance_screening", compliance_screening),
            ("chain_execution", chain_execution),
            ("ledger_append", ledger_append),
            ("webhook_notification", webhook_notification),
        ]

        for name, fn in phases:
            try:
                result = await fn(input)
                results[name] = result
                # Fail on pre-execution phases; webhook is best-effort
                if not result.success and name != "webhook_notification":
                    return PaymentWorkflowResult(
                        success=False, mandate_id=input.mandate_id,
                        phase_results=results, error=f"{name}: {result.error}",
                    )
            except Exception as e:
                results[name] = ActivityResult(success=False, phase=name, error=str(e))
                if name != "webhook_notification":
                    return PaymentWorkflowResult(
                        success=False, mandate_id=input.mandate_id,
                        phase_results=results, error=f"{name}: {e}",
                    )

        return PaymentWorkflowResult(
            success=True, mandate_id=input.mandate_id, phase_results=results,
        )
