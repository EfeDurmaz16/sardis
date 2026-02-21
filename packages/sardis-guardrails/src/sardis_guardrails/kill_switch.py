"""Emergency kill switch for stopping agent payments.

Provides global, per-agent, and per-organization kill switches for immediate shutdown.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class ActivationReason(str, Enum):
    """Reasons for activating a kill switch."""

    MANUAL = "manual"  # Human operator intervention
    ANOMALY = "anomaly"  # Behavioral anomaly detected
    COMPLIANCE = "compliance"  # Compliance violation
    FRAUD = "fraud"  # Suspected fraud
    RATE_LIMIT = "rate_limit"  # Rate limit breach
    POLICY_VIOLATION = "policy_violation"  # Spending policy violation


@dataclass
class KillSwitchActivation:
    """Record of a kill switch activation."""

    reason: ActivationReason
    activated_at: float = field(default_factory=time.time)
    activated_by: str | None = None  # User ID or system component
    notes: str | None = None
    auto_reactivate_at: float | None = None  # Optional automatic reactivation time


class KillSwitchError(Exception):
    """Raised when kill switch is active and blocks execution."""

    pass


class KillSwitch:
    """Emergency stop mechanism for agent payments.

    Supports three scopes:
    - Global: Stop ALL agent payments across all organizations
    - Organization: Stop all agents in a specific organization
    - Agent: Stop a specific agent

    Thread-safe and async-compatible.

    Example:
        kill_switch = KillSwitch()

        # Activate global kill switch
        await kill_switch.activate_global(
            reason=ActivationReason.MANUAL,
            activated_by="admin-user-123",
            notes="Suspicious activity detected"
        )

        # Check before payment
        await kill_switch.check(agent_id="agent-123", org_id="org-456")
        # Raises KillSwitchError if any kill switch is active
    """

    def __init__(self) -> None:
        """Initialize kill switch manager."""
        self._global_activation: KillSwitchActivation | None = None
        self._org_activations: Dict[str, KillSwitchActivation] = {}
        self._agent_activations: Dict[str, KillSwitchActivation] = {}
        self._lock = asyncio.Lock()

    async def activate_global(
        self,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate global kill switch - stops ALL agents.

        Args:
            reason: Reason for activation
            activated_by: User ID or system component that activated
            notes: Optional notes about the activation
            auto_reactivate_after: Optional seconds until automatic reactivation
        """
        async with self._lock:
            auto_reactivate_at = None
            if auto_reactivate_after is not None:
                auto_reactivate_at = time.time() + auto_reactivate_after

            self._global_activation = KillSwitchActivation(
                reason=reason,
                activated_by=activated_by,
                notes=notes,
                auto_reactivate_at=auto_reactivate_at,
            )

    async def activate_organization(
        self,
        org_id: str,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate kill switch for all agents in an organization.

        Args:
            org_id: Organization identifier
            reason: Reason for activation
            activated_by: User ID or system component that activated
            notes: Optional notes about the activation
            auto_reactivate_after: Optional seconds until automatic reactivation
        """
        async with self._lock:
            auto_reactivate_at = None
            if auto_reactivate_after is not None:
                auto_reactivate_at = time.time() + auto_reactivate_after

            self._org_activations[org_id] = KillSwitchActivation(
                reason=reason,
                activated_by=activated_by,
                notes=notes,
                auto_reactivate_at=auto_reactivate_at,
            )

    async def activate_agent(
        self,
        agent_id: str,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate kill switch for a specific agent.

        Args:
            agent_id: Agent identifier
            reason: Reason for activation
            activated_by: User ID or system component that activated
            notes: Optional notes about the activation
            auto_reactivate_after: Optional seconds until automatic reactivation
        """
        async with self._lock:
            auto_reactivate_at = None
            if auto_reactivate_after is not None:
                auto_reactivate_at = time.time() + auto_reactivate_after

            self._agent_activations[agent_id] = KillSwitchActivation(
                reason=reason,
                activated_by=activated_by,
                notes=notes,
                auto_reactivate_at=auto_reactivate_at,
            )

    async def deactivate_global(self) -> None:
        """Deactivate global kill switch."""
        async with self._lock:
            self._global_activation = None

    async def deactivate_organization(self, org_id: str) -> None:
        """Deactivate organization kill switch.

        Args:
            org_id: Organization identifier
        """
        async with self._lock:
            self._org_activations.pop(org_id, None)

    async def deactivate_agent(self, agent_id: str) -> None:
        """Deactivate agent kill switch.

        Args:
            agent_id: Agent identifier
        """
        async with self._lock:
            self._agent_activations.pop(agent_id, None)

    async def check(self, agent_id: str, org_id: str) -> None:
        """Check if any kill switch blocks this agent.

        Args:
            agent_id: Agent identifier
            org_id: Organization identifier

        Raises:
            KillSwitchError: If any kill switch is active for this agent
        """
        async with self._lock:
            # Check for auto-reactivation
            await self._check_auto_reactivations()

            # Check global kill switch
            if self._global_activation is not None:
                raise KillSwitchError(
                    f"Global kill switch active. Reason: {self._global_activation.reason}. "
                    f"Activated at: {self._global_activation.activated_at}. "
                    f"Notes: {self._global_activation.notes or 'None'}"
                )

            # Check organization kill switch
            if org_id in self._org_activations:
                activation = self._org_activations[org_id]
                raise KillSwitchError(
                    f"Organization kill switch active for {org_id}. "
                    f"Reason: {activation.reason}. "
                    f"Activated at: {activation.activated_at}. "
                    f"Notes: {activation.notes or 'None'}"
                )

            # Check agent kill switch
            if agent_id in self._agent_activations:
                activation = self._agent_activations[agent_id]
                raise KillSwitchError(
                    f"Agent kill switch active for {agent_id}. "
                    f"Reason: {activation.reason}. "
                    f"Activated at: {activation.activated_at}. "
                    f"Notes: {activation.notes or 'None'}"
                )

    async def is_active_global(self) -> bool:
        """Check if global kill switch is active.

        Returns:
            True if global kill switch is active
        """
        async with self._lock:
            await self._check_auto_reactivations()
            return self._global_activation is not None

    async def is_active_organization(self, org_id: str) -> bool:
        """Check if organization kill switch is active.

        Args:
            org_id: Organization identifier

        Returns:
            True if organization kill switch is active
        """
        async with self._lock:
            await self._check_auto_reactivations()
            return org_id in self._org_activations

    async def is_active_agent(self, agent_id: str) -> bool:
        """Check if agent kill switch is active.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent kill switch is active
        """
        async with self._lock:
            await self._check_auto_reactivations()
            return agent_id in self._agent_activations

    async def get_active_switches(self) -> Dict[str, Any]:
        """Get all currently active kill switches.

        Returns:
            Dictionary with active switches by scope
        """
        async with self._lock:
            await self._check_auto_reactivations()

            return {
                "global": self._global_activation,
                "organizations": dict(self._org_activations),
                "agents": dict(self._agent_activations),
            }

    async def _check_auto_reactivations(self) -> None:
        """Check and perform automatic reactivations if timeouts have passed."""
        current_time = time.time()

        # Check global
        if self._global_activation is not None:
            if (
                self._global_activation.auto_reactivate_at is not None
                and current_time >= self._global_activation.auto_reactivate_at
            ):
                self._global_activation = None

        # Check organizations
        expired_orgs = [
            org_id
            for org_id, activation in self._org_activations.items()
            if activation.auto_reactivate_at is not None
            and current_time >= activation.auto_reactivate_at
        ]
        for org_id in expired_orgs:
            del self._org_activations[org_id]

        # Check agents
        expired_agents = [
            agent_id
            for agent_id, activation in self._agent_activations.items()
            if activation.auto_reactivate_at is not None
            and current_time >= activation.auto_reactivate_at
        ]
        for agent_id in expired_agents:
            del self._agent_activations[agent_id]


# Singleton instance for global access
_global_kill_switch: KillSwitch | None = None


def get_kill_switch() -> KillSwitch:
    """Get the global kill switch singleton instance.

    Returns:
        Global KillSwitch instance
    """
    global _global_kill_switch
    if _global_kill_switch is None:
        _global_kill_switch = KillSwitch()
    return _global_kill_switch
