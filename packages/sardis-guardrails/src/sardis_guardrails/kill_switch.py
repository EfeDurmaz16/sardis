"""Emergency kill switch for stopping agent payments.

Provides global, per-agent, and per-organization kill switches with
Redis-backed storage for multi-instance Cloud Run deployments.
Falls back to in-memory storage when Redis is unavailable.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


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

    def to_json(self) -> str:
        d = asdict(self)
        d["reason"] = self.reason.value
        return json.dumps(d)

    @classmethod
    def from_json(cls, data: str) -> "KillSwitchActivation":
        d = json.loads(data)
        d["reason"] = ActivationReason(d["reason"])
        return cls(**d)


class KillSwitchError(Exception):
    """Raised when kill switch is active and blocks execution."""

    pass


class KillSwitchBackend:
    """Abstract backend for kill switch state storage."""

    async def set_activation(self, key: str, activation: KillSwitchActivation, ttl: float | None = None) -> None:
        raise NotImplementedError

    async def get_activation(self, key: str) -> KillSwitchActivation | None:
        raise NotImplementedError

    async def delete_activation(self, key: str) -> None:
        raise NotImplementedError

    async def get_all_by_prefix(self, prefix: str) -> Dict[str, KillSwitchActivation]:
        raise NotImplementedError


class InMemoryBackend(KillSwitchBackend):
    """In-memory backend (single-instance only)."""

    def __init__(self) -> None:
        self._store: Dict[str, KillSwitchActivation] = {}
        self._lock = asyncio.Lock()

    async def set_activation(self, key: str, activation: KillSwitchActivation, ttl: float | None = None) -> None:
        async with self._lock:
            self._store[key] = activation

    async def get_activation(self, key: str) -> KillSwitchActivation | None:
        async with self._lock:
            activation = self._store.get(key)
            if activation and activation.auto_reactivate_at and time.time() >= activation.auto_reactivate_at:
                del self._store[key]
                return None
            return activation

    async def delete_activation(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def get_all_by_prefix(self, prefix: str) -> Dict[str, KillSwitchActivation]:
        async with self._lock:
            now = time.time()
            result = {}
            expired = []
            for k, v in self._store.items():
                if k.startswith(prefix):
                    if v.auto_reactivate_at and now >= v.auto_reactivate_at:
                        expired.append(k)
                    else:
                        result[k] = v
            for k in expired:
                del self._store[k]
            return result


class RedisBackend(KillSwitchBackend):
    """Redis-backed storage for multi-instance deployments."""

    KEY_PREFIX = "sardis:killswitch:"

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Any = None

    def _get_redis(self) -> Any:
        if self._redis is None:
            import redis.asyncio as redis_lib
            self._redis = redis_lib.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def set_activation(self, key: str, activation: KillSwitchActivation, ttl: float | None = None) -> None:
        redis = self._get_redis()
        full_key = f"{self.KEY_PREFIX}{key}"
        value = activation.to_json()
        if ttl and ttl > 0:
            await redis.setex(full_key, int(ttl), value)
        elif activation.auto_reactivate_at:
            remaining = activation.auto_reactivate_at - time.time()
            if remaining > 0:
                await redis.setex(full_key, int(remaining) + 1, value)
            else:
                return  # Already expired
        else:
            await redis.set(full_key, value)

    async def get_activation(self, key: str) -> KillSwitchActivation | None:
        redis = self._get_redis()
        full_key = f"{self.KEY_PREFIX}{key}"
        data = await redis.get(full_key)
        if not data:
            return None
        activation = KillSwitchActivation.from_json(data)
        if activation.auto_reactivate_at and time.time() >= activation.auto_reactivate_at:
            await redis.delete(full_key)
            return None
        return activation

    async def delete_activation(self, key: str) -> None:
        redis = self._get_redis()
        await redis.delete(f"{self.KEY_PREFIX}{key}")

    async def get_all_by_prefix(self, prefix: str) -> Dict[str, KillSwitchActivation]:
        redis = self._get_redis()
        full_prefix = f"{self.KEY_PREFIX}{prefix}"
        result = {}
        now = time.time()
        async for key in redis.scan_iter(match=f"{full_prefix}*"):
            data = await redis.get(key)
            if not data:
                continue
            activation = KillSwitchActivation.from_json(data)
            if activation.auto_reactivate_at and now >= activation.auto_reactivate_at:
                await redis.delete(key)
                continue
            short_key = key.removeprefix(self.KEY_PREFIX)
            result[short_key] = activation
        return result


def _create_backend() -> KillSwitchBackend:
    """Create appropriate backend based on environment."""
    redis_url = (
        os.getenv("SARDIS_REDIS_URL")
        or os.getenv("REDIS_URL")
        or os.getenv("UPSTASH_REDIS_URL")
        or ""
    )
    if redis_url:
        try:
            backend = RedisBackend(redis_url)
            backend._get_redis()  # validate connection
            logger.info("Kill switch using Redis backend for multi-instance support")
            return backend
        except Exception as e:
            logger.warning("Redis kill switch backend failed (%s), falling back to in-memory", e)

    env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
    if env in ("prod", "production"):
        raise RuntimeError(
            "CRITICAL: Redis is required for production kill switch. "
            "Set SARDIS_REDIS_URL, REDIS_URL, or UPSTASH_REDIS_URL."
        )

    return InMemoryBackend()


class KillSwitch:
    """Emergency stop mechanism for agent payments.

    Supports three scopes:
    - Global: Stop ALL agent payments across all organizations
    - Organization: Stop all agents in a specific organization
    - Agent: Stop a specific agent

    Uses Redis for multi-instance Cloud Run deployments, falls back to
    in-memory for development.

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

    def __init__(self, backend: KillSwitchBackend | None = None) -> None:
        """Initialize kill switch manager."""
        self._backend = backend or _create_backend()

    async def activate_global(
        self,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate global kill switch - stops ALL agents."""
        auto_reactivate_at = None
        if auto_reactivate_after is not None:
            auto_reactivate_at = time.time() + auto_reactivate_after

        activation = KillSwitchActivation(
            reason=reason,
            activated_by=activated_by,
            notes=notes,
            auto_reactivate_at=auto_reactivate_at,
        )
        await self._backend.set_activation("global", activation)

    async def activate_organization(
        self,
        org_id: str,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate kill switch for all agents in an organization."""
        auto_reactivate_at = None
        if auto_reactivate_after is not None:
            auto_reactivate_at = time.time() + auto_reactivate_after

        activation = KillSwitchActivation(
            reason=reason,
            activated_by=activated_by,
            notes=notes,
            auto_reactivate_at=auto_reactivate_at,
        )
        await self._backend.set_activation(f"org:{org_id}", activation)

    async def activate_agent(
        self,
        agent_id: str,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate kill switch for a specific agent."""
        auto_reactivate_at = None
        if auto_reactivate_after is not None:
            auto_reactivate_at = time.time() + auto_reactivate_after

        activation = KillSwitchActivation(
            reason=reason,
            activated_by=activated_by,
            notes=notes,
            auto_reactivate_at=auto_reactivate_at,
        )
        await self._backend.set_activation(f"agent:{agent_id}", activation)

    async def activate_rail(
        self,
        rail: str,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate kill switch for a specific payment rail (e.g. 'a2a', 'checkout', 'ap2')."""
        auto_reactivate_at = None
        if auto_reactivate_after is not None:
            auto_reactivate_at = time.time() + auto_reactivate_after

        activation = KillSwitchActivation(
            reason=reason,
            activated_by=activated_by,
            notes=notes,
            auto_reactivate_at=auto_reactivate_at,
        )
        await self._backend.set_activation(f"rail:{rail}", activation)

    async def activate_chain(
        self,
        chain: str,
        reason: ActivationReason,
        activated_by: str | None = None,
        notes: str | None = None,
        auto_reactivate_after: float | None = None,
    ) -> None:
        """Activate kill switch for a specific blockchain (e.g. 'base', 'ethereum')."""
        auto_reactivate_at = None
        if auto_reactivate_after is not None:
            auto_reactivate_at = time.time() + auto_reactivate_after

        activation = KillSwitchActivation(
            reason=reason,
            activated_by=activated_by,
            notes=notes,
            auto_reactivate_at=auto_reactivate_at,
        )
        await self._backend.set_activation(f"chain:{chain}", activation)

    async def deactivate_rail(self, rail: str) -> None:
        """Deactivate rail kill switch."""
        await self._backend.delete_activation(f"rail:{rail}")

    async def deactivate_chain(self, chain: str) -> None:
        """Deactivate chain kill switch."""
        await self._backend.delete_activation(f"chain:{chain}")

    async def check_rail(self, rail: str) -> None:
        """Check if a specific rail is blocked.

        Raises:
            KillSwitchError: If the rail kill switch is active
        """
        activation = await self._backend.get_activation(f"rail:{rail}")
        if activation is not None:
            raise KillSwitchError(
                f"Rail kill switch active for '{rail}'. "
                f"Reason: {activation.reason}. "
                f"Activated at: {activation.activated_at}. "
                f"Notes: {activation.notes or 'None'}"
            )

    async def check_chain(self, chain: str) -> None:
        """Check if a specific chain is blocked.

        Raises:
            KillSwitchError: If the chain kill switch is active
        """
        activation = await self._backend.get_activation(f"chain:{chain}")
        if activation is not None:
            raise KillSwitchError(
                f"Chain kill switch active for '{chain}'. "
                f"Reason: {activation.reason}. "
                f"Activated at: {activation.activated_at}. "
                f"Notes: {activation.notes or 'None'}"
            )

    async def is_active_rail(self, rail: str) -> bool:
        """Check if rail kill switch is active."""
        return await self._backend.get_activation(f"rail:{rail}") is not None

    async def is_active_chain(self, chain: str) -> bool:
        """Check if chain kill switch is active."""
        return await self._backend.get_activation(f"chain:{chain}") is not None

    async def deactivate_global(self) -> None:
        """Deactivate global kill switch."""
        await self._backend.delete_activation("global")

    async def deactivate_organization(self, org_id: str) -> None:
        """Deactivate organization kill switch."""
        await self._backend.delete_activation(f"org:{org_id}")

    async def deactivate_agent(self, agent_id: str) -> None:
        """Deactivate agent kill switch."""
        await self._backend.delete_activation(f"agent:{agent_id}")

    async def check(self, agent_id: str, org_id: str) -> None:
        """Check if any kill switch blocks this agent.

        Raises:
            KillSwitchError: If any kill switch is active for this agent
        """
        # Check global kill switch
        global_activation = await self._backend.get_activation("global")
        if global_activation is not None:
            raise KillSwitchError(
                f"Global kill switch active. Reason: {global_activation.reason}. "
                f"Activated at: {global_activation.activated_at}. "
                f"Notes: {global_activation.notes or 'None'}"
            )

        # Check organization kill switch
        org_activation = await self._backend.get_activation(f"org:{org_id}")
        if org_activation is not None:
            raise KillSwitchError(
                f"Organization kill switch active for {org_id}. "
                f"Reason: {org_activation.reason}. "
                f"Activated at: {org_activation.activated_at}. "
                f"Notes: {org_activation.notes or 'None'}"
            )

        # Check agent kill switch
        agent_activation = await self._backend.get_activation(f"agent:{agent_id}")
        if agent_activation is not None:
            raise KillSwitchError(
                f"Agent kill switch active for {agent_id}. "
                f"Reason: {agent_activation.reason}. "
                f"Activated at: {agent_activation.activated_at}. "
                f"Notes: {agent_activation.notes or 'None'}"
            )

    async def is_active_global(self) -> bool:
        """Check if global kill switch is active."""
        return await self._backend.get_activation("global") is not None

    async def is_active_organization(self, org_id: str) -> bool:
        """Check if organization kill switch is active."""
        return await self._backend.get_activation(f"org:{org_id}") is not None

    async def is_active_agent(self, agent_id: str) -> bool:
        """Check if agent kill switch is active."""
        return await self._backend.get_activation(f"agent:{agent_id}") is not None

    async def get_active_switches(self) -> Dict[str, Any]:
        """Get all currently active kill switches."""
        global_activation = await self._backend.get_activation("global")
        org_activations = await self._backend.get_all_by_prefix("org:")
        agent_activations = await self._backend.get_all_by_prefix("agent:")
        rail_activations = await self._backend.get_all_by_prefix("rail:")
        chain_activations = await self._backend.get_all_by_prefix("chain:")

        return {
            "global": global_activation,
            "organizations": {k.removeprefix("org:"): v for k, v in org_activations.items()},
            "agents": {k.removeprefix("agent:"): v for k, v in agent_activations.items()},
            "rails": {k.removeprefix("rail:"): v for k, v in rail_activations.items()},
            "chains": {k.removeprefix("chain:"): v for k, v in chain_activations.items()},
        }


# Singleton instance for global access
_global_kill_switch: KillSwitch | None = None


def get_kill_switch() -> KillSwitch:
    """Get the global kill switch singleton instance."""
    global _global_kill_switch
    if _global_kill_switch is None:
        _global_kill_switch = KillSwitch()
    return _global_kill_switch
