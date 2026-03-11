"""GoRules Zen Engine integration for fraud rule evaluation.

Provides a hot-reloadable, sub-millisecond rule engine using GoRules' Rust-based
Zen Engine with Python bindings. Rules are defined as JSON Decision Models (JDM)
and can be loaded from filesystem, database, or remote storage.

Requires: pip install zen-engine
Docs: https://docs.gorules.io/reference/python
License: MIT
Cost: $0 — open source, runs in-process.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FraudAction(str, Enum):
    """Action determined by fraud rule evaluation."""
    APPROVE = "approve"
    FLAG = "flag"
    CHALLENGE = "challenge"  # Require additional verification (MFA, approval)
    BLOCK = "block"


@dataclass
class FraudRuleResult:
    """Result of fraud rule evaluation."""
    action: FraudAction
    risk_score: float  # 0.0-1.0
    rule_id: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    trace: dict[str, Any] | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def should_block(self) -> bool:
        return self.action == FraudAction.BLOCK

    @property
    def requires_review(self) -> bool:
        return self.action in (FraudAction.FLAG, FraudAction.CHALLENGE)


# ---------------------------------------------------------------------------
# Default fraud rules (embedded JDM)
# ---------------------------------------------------------------------------

DEFAULT_FRAUD_RULES: dict[str, Any] = {
    "nodes": [
        {
            "id": "input",
            "type": "inputNode",
            "name": "Transaction Input",
            "position": {"x": 0, "y": 0},
        },
        {
            "id": "fraud-table",
            "type": "decisionTableNode",
            "name": "Fraud Risk Assessment",
            "position": {"x": 250, "y": 0},
            "content": {
                "hitPolicy": "first",
                "rules": [
                    # Rule 1: Very large amount + high velocity + geo anomaly = block
                    {
                        "_id": "r1",
                        "amount": "> 50000",
                        "velocity_score": "> 0.9",
                        "geo_anomalous": "true",
                        "account_age_days": "",
                        "is_new_merchant": "",
                        "action": "\"block\"",
                        "risk_score": "0.98",
                    },
                    # Rule 2: Large amount + very high velocity
                    {
                        "_id": "r2",
                        "amount": "> 10000",
                        "velocity_score": "> 0.8",
                        "geo_anomalous": "",
                        "account_age_days": "",
                        "is_new_merchant": "",
                        "action": "\"challenge\"",
                        "risk_score": "0.85",
                    },
                    # Rule 3: New account + medium amount + geo anomaly
                    {
                        "_id": "r3",
                        "amount": "> 5000",
                        "velocity_score": "",
                        "geo_anomalous": "true",
                        "account_age_days": "< 7",
                        "is_new_merchant": "",
                        "action": "\"challenge\"",
                        "risk_score": "0.75",
                    },
                    # Rule 4: New merchant + above-average amount
                    {
                        "_id": "r4",
                        "amount": "> 1000",
                        "velocity_score": "",
                        "geo_anomalous": "",
                        "account_age_days": "",
                        "is_new_merchant": "true",
                        "action": "\"flag\"",
                        "risk_score": "0.45",
                    },
                    # Rule 5: High velocity alone
                    {
                        "_id": "r5",
                        "amount": "",
                        "velocity_score": "> 0.7",
                        "geo_anomalous": "",
                        "account_age_days": "",
                        "is_new_merchant": "",
                        "action": "\"flag\"",
                        "risk_score": "0.40",
                    },
                    # Default: approve
                    {
                        "_id": "r6",
                        "amount": "",
                        "velocity_score": "",
                        "geo_anomalous": "",
                        "account_age_days": "",
                        "is_new_merchant": "",
                        "action": "\"approve\"",
                        "risk_score": "0.05",
                    },
                ],
                "inputs": [
                    {"id": "amount", "name": "Transaction Amount", "field": "amount", "type": "expression"},
                    {"id": "velocity_score", "name": "Velocity Score", "field": "velocity_score", "type": "expression"},
                    {"id": "geo_anomalous", "name": "Geographic Anomaly", "field": "geo_anomalous", "type": "expression"},
                    {"id": "account_age_days", "name": "Account Age (days)", "field": "account_age_days", "type": "expression"},
                    {"id": "is_new_merchant", "name": "New Merchant", "field": "is_new_merchant", "type": "expression"},
                ],
                "outputs": [
                    {"id": "action", "name": "Action", "field": "action", "type": "expression"},
                    {"id": "risk_score", "name": "Risk Score", "field": "risk_score", "type": "expression"},
                ],
            },
        },
        {
            "id": "output",
            "type": "outputNode",
            "name": "Decision Output",
            "position": {"x": 500, "y": 0},
        },
    ],
    "edges": [
        {
            "id": "edge-1",
            "sourceId": "input",
            "targetId": "fraud-table",
            "sourceHandle": "output",
            "targetHandle": "input",
        },
        {
            "id": "edge-2",
            "sourceId": "fraud-table",
            "targetId": "output",
            "sourceHandle": "output",
            "targetHandle": "input",
        },
    ],
}


class ZenFraudEngine:
    """Fraud rule evaluation engine powered by GoRules Zen Engine.

    Evaluates transactions against configurable JSON Decision Model (JDM)
    rules with sub-millisecond latency. Rules can be hot-reloaded from
    filesystem, database, or any custom loader.

    Example::

        engine = ZenFraudEngine()
        result = engine.evaluate({
            "amount": 5000,
            "velocity_score": 0.65,
            "geo_anomalous": False,
            "account_age_days": 45,
            "is_new_merchant": False,
        })
        print(result.action)  # FraudAction.APPROVE
    """

    def __init__(
        self,
        rules_dir: str | Path | None = None,
        rules_content: str | None = None,
        loader: Any | None = None,
    ):
        """Initialize the Zen Fraud Engine.

        Args:
            rules_dir: Directory containing .json JDM rule files.
                Falls back to SARDIS_FRAUD_RULES_DIR env var.
            rules_content: Raw JDM JSON string to use directly.
            loader: Custom loader function (key: str) -> str for the Zen engine.
        """
        self._rules_dir = Path(
            rules_dir
            or os.getenv("SARDIS_FRAUD_RULES_DIR", "")
            or ""
        ) if (rules_dir or os.getenv("SARDIS_FRAUD_RULES_DIR")) else None

        self._rules_content = rules_content
        self._custom_loader = loader
        self._engine = None
        self._decision = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy-initialize the Zen engine."""
        if self._initialized:
            return

        try:
            import zen
        except ImportError:
            raise ImportError(
                "zen-engine package is required for ZenFraudEngine. "
                "Install it with: pip install zen-engine"
            )

        if self._custom_loader:
            self._engine = zen.ZenEngine({"loader": self._custom_loader})
            self._initialized = True
            return

        # Determine rule content
        content = self._rules_content
        if not content and self._rules_dir:
            default_file = self._rules_dir / "fraud-rules.json"
            if default_file.exists():
                content = default_file.read_text()
                logger.info("Loaded fraud rules from %s", default_file)

        if not content:
            content = json.dumps(DEFAULT_FRAUD_RULES)
            logger.info("Using default embedded fraud rules")

        self._engine = zen.ZenEngine()
        self._decision = self._engine.create_decision(content)
        self._initialized = True

    def evaluate(
        self,
        context: dict[str, Any],
        *,
        trace: bool = False,
        rule_key: str | None = None,
    ) -> FraudRuleResult:
        """Evaluate transaction context against fraud rules.

        Args:
            context: Transaction context dict with fields like:
                - amount: float — transaction amount
                - velocity_score: float (0-1) — tx velocity anomaly score
                - geo_anomalous: bool — geographic anomaly flag
                - account_age_days: int — days since account creation
                - is_new_merchant: bool — first transaction with merchant
            trace: Enable execution tracing for debugging.
            rule_key: Rule file key (for loader-based engines).

        Returns:
            FraudRuleResult with action, risk_score, and optional trace.
        """
        self._ensure_initialized()

        # Normalize Decimal values to float for JSON serialization
        normalized = {}
        for k, v in context.items():
            if isinstance(v, Decimal):
                normalized[k] = float(v)
            else:
                normalized[k] = v

        options = {"trace": trace} if trace else {}

        try:
            if rule_key and self._engine and not self._decision:
                # Loader-based engine
                raw = self._engine.evaluate(rule_key, normalized, options)
            elif self._decision:
                raw = self._decision.evaluate(normalized, options)
            else:
                raise RuntimeError("Zen engine not properly initialized")
        except Exception as e:
            logger.error("Zen engine evaluation failed: %s", e)
            # Fail-closed: block on engine error
            return FraudRuleResult(
                action=FraudAction.BLOCK,
                risk_score=1.0,
                reason=f"Rule engine error: {e}",
            )

        result_data = raw.get("result", {}) if isinstance(raw, dict) else {}
        trace_data = raw.get("trace") if isinstance(raw, dict) and trace else None

        action_str = str(result_data.get("action", "approve")).strip('"')
        try:
            action = FraudAction(action_str)
        except ValueError:
            action = FraudAction.FLAG
            logger.warning("Unknown fraud action '%s', defaulting to FLAG", action_str)

        risk_score = float(result_data.get("risk_score", 0.0))

        return FraudRuleResult(
            action=action,
            risk_score=risk_score,
            rule_id=result_data.get("rule_id"),
            reason=result_data.get("reason"),
            metadata={k: v for k, v in result_data.items() if k not in ("action", "risk_score", "rule_id", "reason")},
            trace=trace_data,
        )

    async def async_evaluate(
        self,
        context: dict[str, Any],
        *,
        trace: bool = False,
        rule_key: str | None = None,
    ) -> FraudRuleResult:
        """Async wrapper for evaluate (Zen engine is CPU-bound, runs in thread)."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.evaluate(context, trace=trace, rule_key=rule_key)
        )

    def reload_rules(self, content: str | None = None) -> None:
        """Hot-reload rules from new content or re-read from filesystem.

        Args:
            content: New JDM JSON string. If None, re-reads from rules_dir.
        """
        self._initialized = False
        if content:
            self._rules_content = content
        elif self._rules_dir:
            # Clear cached content so _ensure_initialized re-reads from disk
            self._rules_content = None
        self._decision = None
        logger.info("Fraud rules scheduled for reload")

    def load_rules_from_dict(self, rules: dict[str, Any]) -> None:
        """Load rules from a Python dict (converted to JDM JSON)."""
        self._rules_content = json.dumps(rules)
        self._initialized = False
        self._decision = None


class ZenFraudProvider:
    """Wraps ZenFraudEngine as a compliance-compatible fraud detection provider.

    Can be plugged into the ComplianceEngine or used standalone in the
    payment orchestrator's preflight pipeline.

    Example::

        provider = ZenFraudProvider()
        result = await provider.assess_transaction(
            agent_id="agent-123",
            amount=Decimal("5000"),
            merchant_id="merchant-xyz",
            velocity_score=0.65,
            geo_anomalous=False,
            account_age_days=45,
        )
        if result.should_block:
            raise ComplianceViolationError("Fraud rule blocked transaction")
    """

    def __init__(
        self,
        engine: ZenFraudEngine | None = None,
        **engine_kwargs: Any,
    ):
        self._engine = engine or ZenFraudEngine(**engine_kwargs)

    async def assess_transaction(
        self,
        agent_id: str,
        amount: Decimal,
        merchant_id: str | None = None,
        velocity_score: float = 0.0,
        geo_anomalous: bool = False,
        account_age_days: int = 365,
        is_new_merchant: bool = False,
        extra_context: dict[str, Any] | None = None,
        trace: bool = False,
    ) -> FraudRuleResult:
        """Assess a transaction for fraud risk.

        Builds context from parameters and evaluates against loaded rules.
        """
        context: dict[str, Any] = {
            "agent_id": agent_id,
            "amount": float(amount),
            "merchant_id": merchant_id or "",
            "velocity_score": velocity_score,
            "geo_anomalous": geo_anomalous,
            "account_age_days": account_age_days,
            "is_new_merchant": is_new_merchant,
        }
        if extra_context:
            context.update(extra_context)

        return await self._engine.async_evaluate(context, trace=trace)
