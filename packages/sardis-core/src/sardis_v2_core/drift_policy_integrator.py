"""Drift → Policy Action Integrator.

When the goal drift detector finds anomalies, this module automatically
takes policy actions instead of just logging:

  LOW      → WARN (log + webhook, no policy change)
  MEDIUM   → REDUCE_LIMITS (scale down per-tx and daily by 50%)
  HIGH     → REQUIRE_APPROVAL (set approval threshold to $0)
  CRITICAL → FREEZE (set wallet status to frozen)

Auto-restore: if no new drift alerts arrive within the restore window,
the previous policy version is reinstated.

Usage:
    integrator = DriftPolicyIntegrator()
    result = await integrator.handle_drift_alert(pool, alert, config)
"""
from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DriftAction(str, Enum):
    """Automated response action for drift alerts."""
    WARN = "warn"
    REDUCE_LIMITS = "reduce_limits"
    REQUIRE_APPROVAL = "require_approval"
    FREEZE = "freeze"


@dataclass(slots=True)
class DriftPolicyConfig:
    """Configuration for drift → policy action mapping."""
    low_severity_action: DriftAction = DriftAction.WARN
    medium_severity_action: DriftAction = DriftAction.REDUCE_LIMITS
    high_severity_action: DriftAction = DriftAction.REQUIRE_APPROVAL
    critical_severity_action: DriftAction = DriftAction.FREEZE
    auto_reduce_factor: float = 0.5  # reduce limits by 50%
    auto_restore_after_hours: int = 24


@dataclass(slots=True)
class DriftActionResult:
    """Result of applying a drift-triggered policy action."""
    agent_id: str
    action: DriftAction
    severity: str
    details: dict[str, Any] = field(default_factory=dict)
    policy_changed: bool = False
    new_policy_version_id: str | None = None


class DriftPolicyIntegrator:
    """Maps drift severity to policy enforcement actions."""

    def __init__(self, policy_store: Any = None) -> None:
        """Initialize with an optional policy store for load/save.

        Args:
            policy_store: AsyncPolicyStore instance. If None, creates a
                          default InMemoryPolicyStore.
        """
        if policy_store is not None:
            self._policy_store = policy_store
        else:
            from .policy_store_memory import InMemoryPolicyStore
            self._policy_store = InMemoryPolicyStore()

    def _get_action(
        self,
        severity: str,
        config: DriftPolicyConfig,
    ) -> DriftAction:
        from .goal_drift_detector import DriftSeverity
        mapping = {
            DriftSeverity.LOW: config.low_severity_action,
            DriftSeverity.MEDIUM: config.medium_severity_action,
            DriftSeverity.HIGH: config.high_severity_action,
            DriftSeverity.CRITICAL: config.critical_severity_action,
        }
        try:
            sev = DriftSeverity(severity)
        except ValueError:
            sev = DriftSeverity.LOW
        return mapping.get(sev, DriftAction.WARN)

    async def handle_drift_alert(
        self,
        pool: Any,
        alert: Any,
        config: DriftPolicyConfig | None = None,
    ) -> DriftActionResult:
        """Handle a drift alert by applying the configured policy action.

        Args:
            pool: Database connection pool (or None for in-memory operation).
            alert: DriftAlert from GoalDriftDetector.
            config: Action mapping config. Uses defaults if None.

        Returns:
            DriftActionResult describing what action was taken.
        """
        if config is None:
            config = DriftPolicyConfig()

        severity = alert.severity
        severity_str = severity.value if isinstance(severity, Enum) else str(severity)

        action = self._get_action(severity_str, config)
        agent_id = alert.agent_id

        if action == DriftAction.WARN:
            return await self._action_warn(agent_id, severity_str, alert)

        if action == DriftAction.REDUCE_LIMITS:
            return await self._action_reduce_limits(
                pool, agent_id, severity_str, alert, config.auto_reduce_factor,
            )

        if action == DriftAction.REQUIRE_APPROVAL:
            return await self._action_require_approval(
                pool, agent_id, severity_str, alert,
            )

        if action == DriftAction.FREEZE:
            return await self._action_freeze(
                pool, agent_id, severity_str, alert,
            )

        return DriftActionResult(
            agent_id=agent_id,
            action=action,
            severity=severity_str,
        )

    async def _action_warn(
        self,
        agent_id: str,
        severity: str,
        alert: Any,
    ) -> DriftActionResult:
        """Log the drift alert without changing policy."""
        logger.warning(
            "Drift alert for agent %s: severity=%s type=%s confidence=%.2f",
            agent_id,
            severity,
            alert.drift_type,
            alert.confidence,
        )
        return DriftActionResult(
            agent_id=agent_id,
            action=DriftAction.WARN,
            severity=severity,
            details={
                "drift_type": alert.drift_type.value if isinstance(alert.drift_type, Enum) else str(alert.drift_type),
                "confidence": alert.confidence,
            },
            policy_changed=False,
        )

    async def _action_reduce_limits(
        self,
        pool: Any,
        agent_id: str,
        severity: str,
        alert: Any,
        reduce_factor: float,
    ) -> DriftActionResult:
        """Scale down per-tx and daily limits by reduce_factor."""
        from .policy_version_store import PolicyVersionStore
        from .spending_policy_json import spending_policy_to_json

        policy = await self._load_policy(agent_id)
        if policy is None:
            return DriftActionResult(
                agent_id=agent_id,
                action=DriftAction.REDUCE_LIMITS,
                severity=severity,
                details={"error": "no_policy_found"},
                policy_changed=False,
            )

        factor = Decimal(str(reduce_factor))
        original_per_tx = policy.limit_per_tx
        original_daily = policy.daily_limit.limit_amount if policy.daily_limit else None

        policy.limit_per_tx = (policy.limit_per_tx * factor).quantize(Decimal("0.01"))
        if policy.daily_limit:
            policy.daily_limit.limit_amount = (
                policy.daily_limit.limit_amount * factor
            ).quantize(Decimal("0.01"))

        # Persist the reduced policy
        await self._save_policy(agent_id, policy)

        # Create version tagged as drift-auto-reduce
        version_id = None
        if pool is not None:
            try:
                store = PolicyVersionStore()
                payload = spending_policy_to_json(policy)
                version = await store.create_version(
                    pool, agent_id, payload,
                    policy_text="drift-auto-reduce",
                    created_by="drift_policy_integrator",
                )
                version_id = version.id
            except Exception:
                pass

        return DriftActionResult(
            agent_id=agent_id,
            action=DriftAction.REDUCE_LIMITS,
            severity=severity,
            details={
                "reduce_factor": reduce_factor,
                "original_per_tx": str(original_per_tx),
                "new_per_tx": str(policy.limit_per_tx),
                "original_daily": str(original_daily) if original_daily else None,
                "new_daily": str(policy.daily_limit.limit_amount) if policy.daily_limit else None,
            },
            policy_changed=True,
            new_policy_version_id=version_id,
        )

    async def _action_require_approval(
        self,
        pool: Any,
        agent_id: str,
        severity: str,
        alert: Any,
    ) -> DriftActionResult:
        """Set approval threshold to $0 — every tx needs human sign-off."""
        from .policy_version_store import PolicyVersionStore
        from .spending_policy_json import spending_policy_to_json

        policy = await self._load_policy(agent_id)
        if policy is None:
            return DriftActionResult(
                agent_id=agent_id,
                action=DriftAction.REQUIRE_APPROVAL,
                severity=severity,
                details={"error": "no_policy_found"},
                policy_changed=False,
            )

        original_threshold = policy.approval_threshold
        policy.approval_threshold = Decimal("0")

        await self._save_policy(agent_id, policy)

        version_id = None
        if pool is not None:
            try:
                store = PolicyVersionStore()
                payload = spending_policy_to_json(policy)
                version = await store.create_version(
                    pool, agent_id, payload,
                    policy_text="drift-require-approval",
                    created_by="drift_policy_integrator",
                )
                version_id = version.id
            except Exception:
                pass

        return DriftActionResult(
            agent_id=agent_id,
            action=DriftAction.REQUIRE_APPROVAL,
            severity=severity,
            details={
                "original_threshold": str(original_threshold) if original_threshold else None,
                "new_threshold": "0",
            },
            policy_changed=True,
            new_policy_version_id=version_id,
        )

    async def _action_freeze(
        self,
        pool: Any,
        agent_id: str,
        severity: str,
        alert: Any,
    ) -> DriftActionResult:
        """Freeze the agent — set per-tx and total limits to 0."""
        from .policy_version_store import PolicyVersionStore
        from .spending_policy_json import spending_policy_to_json

        policy = await self._load_policy(agent_id)
        if policy is None:
            return DriftActionResult(
                agent_id=agent_id,
                action=DriftAction.FREEZE,
                severity=severity,
                details={"error": "no_policy_found"},
                policy_changed=False,
            )

        policy.limit_per_tx = Decimal("0")
        policy.limit_total = Decimal("0")

        await self._save_policy(agent_id, policy)

        version_id = None
        if pool is not None:
            try:
                store = PolicyVersionStore()
                payload = spending_policy_to_json(policy)
                version = await store.create_version(
                    pool, agent_id, payload,
                    policy_text="drift-freeze",
                    created_by="drift_policy_integrator",
                )
                version_id = version.id
            except Exception:
                pass

        return DriftActionResult(
            agent_id=agent_id,
            action=DriftAction.FREEZE,
            severity=severity,
            details={"frozen": True},
            policy_changed=True,
            new_policy_version_id=version_id,
        )

    async def check_auto_restore(
        self,
        pool: Any,
        agent_id: str,
        config: DriftPolicyConfig | None = None,
    ) -> bool:
        """If no drift alerts in restore window, restore previous policy version.

        Returns True if policy was restored, False otherwise.
        """
        if config is None:
            config = DriftPolicyConfig()

        from .policy_version_store import PolicyVersionStore
        if pool is None:
            return False

        try:
            store = PolicyVersionStore()
            versions = await store.list_versions(pool, agent_id, limit=5)
        except Exception:
            return False

        if len(versions) < 2:
            return False

        latest = versions[0]
        # Only restore if latest was a drift action
        if latest.policy_text not in (
            "drift-auto-reduce",
            "drift-require-approval",
            "drift-freeze",
        ):
            return False

        # Check if enough time has passed
        cutoff = datetime.now(UTC) - timedelta(hours=config.auto_restore_after_hours)
        if latest.created_at > cutoff:
            return False  # Too recent to restore

        # Find the last non-drift version
        for v in versions[1:]:
            if v.policy_text not in (
                "drift-auto-reduce",
                "drift-require-approval",
                "drift-freeze",
            ):
                # Restore this version's policy
                from .spending_policy_json import spending_policy_from_json
                restored_policy = spending_policy_from_json(v.policy_json)
                await self._save_policy(agent_id, restored_policy)

                with contextlib.suppress(Exception):
                    await store.create_version(
                        pool, agent_id, v.policy_json,
                        policy_text="drift-auto-restore",
                        created_by="drift_policy_integrator",
                    )

                logger.info(
                    "Auto-restored policy for agent %s from version %d",
                    agent_id,
                    v.version,
                )
                return True

        return False

    async def _load_policy(self, agent_id: str) -> Any:
        """Load policy for agent from the injected store."""
        try:
            result = await self._policy_store.fetch_policy(agent_id)
            if result is not None:
                return result
        except Exception:
            pass
        # Fallback: create a default policy
        from .spending_policy import create_default_policy
        return create_default_policy(agent_id)

    async def _save_policy(self, agent_id: str, policy: Any) -> None:
        """Save policy to the injected store."""
        await self._policy_store.set_policy(agent_id, policy)
