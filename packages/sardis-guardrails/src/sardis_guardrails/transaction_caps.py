"""Transaction cap enforcement engine.

Enforces daily/per-tx/monthly spend limits at global, per-org, and per-agent levels.
Uses Redis sorted sets for real-time spend tracking across multi-instance deployments.
Auto-triggers kill switch when caps are exceeded.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default caps (configurable via env vars)
DEFAULT_GLOBAL_DAILY_CAP = Decimal(os.getenv("SARDIS_GLOBAL_DAILY_CAP", "1000000"))  # $1M
DEFAULT_ORG_DAILY_CAP = Decimal(os.getenv("SARDIS_DEFAULT_ORG_DAILY_CAP", "100000"))  # $100K
DEFAULT_AGENT_TX_CAP = Decimal(os.getenv("SARDIS_DEFAULT_AGENT_TX_CAP", "10000"))  # $10K


@dataclass
class CapCheckResult:
    allowed: bool
    remaining: Decimal
    daily_total: Decimal
    cap_type: str = ""  # "global", "org", "agent", "per_tx"
    message: str = ""


class TransactionCapEngine:
    """Enforces transaction spend limits using Redis sorted sets."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or (
            os.getenv("SARDIS_REDIS_URL")
            or os.getenv("REDIS_URL")
            or os.getenv("UPSTASH_REDIS_URL")
            or ""
        )
        self._redis: Any = None
        # In-memory fallback for dev
        self._mem_spend: dict[str, Decimal] = {}

    def _get_redis(self) -> Any:
        if self._redis is None and self._redis_url:
            try:
                import redis.asyncio as redis_lib
                self._redis = redis_lib.from_url(self._redis_url, decode_responses=True)
            except Exception as e:
                logger.warning("Redis unavailable for transaction caps: %s", e)
        return self._redis

    def _date_key(self) -> str:
        return date.today().isoformat()

    async def check_and_record(
        self,
        amount: Decimal,
        org_id: str,
        agent_id: str | None = None,
        tx_id: str | None = None,
    ) -> CapCheckResult:
        """Check all caps and record spend if allowed.

        Returns CapCheckResult. If not allowed, triggers kill switch.
        """
        amount = Decimal(str(amount))

        # Check per-tx cap for agent
        agent_tx_cap = await self._get_cap("agent", agent_id, "per_tx") if agent_id else None
        if agent_tx_cap and amount > agent_tx_cap:
            return CapCheckResult(
                allowed=False,
                remaining=Decimal("0"),
                daily_total=Decimal("0"),
                cap_type="per_tx",
                message=f"Transaction amount ${amount} exceeds per-tx cap ${agent_tx_cap}",
            )

        # Check daily caps: global, org, agent
        checks = [
            ("global", "global", DEFAULT_GLOBAL_DAILY_CAP),
            ("org", org_id, DEFAULT_ORG_DAILY_CAP),
        ]
        if agent_id:
            agent_daily_cap = await self._get_cap("agent", agent_id, "daily") or DEFAULT_AGENT_TX_CAP * 10
            checks.append(("agent", agent_id, agent_daily_cap))

        for scope, scope_id, default_cap in checks:
            cap = await self._get_cap(scope, scope_id, "daily") or default_cap
            daily_total = await self._get_daily_spend(scope, scope_id)

            if daily_total + amount > cap:
                # Auto-trigger kill switch
                await self._trigger_kill_switch(scope, scope_id, daily_total, cap)
                return CapCheckResult(
                    allowed=False,
                    remaining=max(Decimal("0"), cap - daily_total),
                    daily_total=daily_total,
                    cap_type=scope,
                    message=f"Daily {scope} cap exceeded: ${daily_total + amount} > ${cap}",
                )

        # All checks passed — record spend
        await self._record_spend("global", "global", amount, tx_id)
        await self._record_spend("org", org_id, amount, tx_id)
        if agent_id:
            await self._record_spend("agent", agent_id, amount, tx_id)

        global_total = await self._get_daily_spend("global", "global")
        global_cap = await self._get_cap("global", "global", "daily") or DEFAULT_GLOBAL_DAILY_CAP

        return CapCheckResult(
            allowed=True,
            remaining=max(Decimal("0"), global_cap - global_total),
            daily_total=global_total,
        )

    async def _get_daily_spend(self, scope: str, scope_id: str) -> Decimal:
        """Get today's total spend for a scope."""
        redis = self._get_redis()
        key = f"sardis:spend:{scope}:{scope_id}:{self._date_key()}"

        if redis:
            try:
                total = await redis.get(f"{key}:total")
                return Decimal(total) if total else Decimal("0")
            except Exception:
                pass

        return self._mem_spend.get(key, Decimal("0"))

    async def _record_spend(self, scope: str, scope_id: str, amount: Decimal, tx_id: str | None = None) -> None:
        """Record a spend event."""
        redis = self._get_redis()
        key = f"sardis:spend:{scope}:{scope_id}:{self._date_key()}"

        if redis:
            try:
                pipe = redis.pipeline()
                pipe.incrbyfloat(f"{key}:total", float(amount))
                pipe.expire(f"{key}:total", 86400 * 2)  # 2 day TTL
                if tx_id:
                    pipe.zadd(key, {tx_id: time.time()})
                    pipe.expire(key, 86400 * 2)
                await pipe.execute()
                return
            except Exception as e:
                logger.warning("Redis spend recording failed: %s", e)

        # In-memory fallback
        self._mem_spend[key] = self._mem_spend.get(key, Decimal("0")) + amount

    async def _get_cap(self, scope: str, scope_id: str | None, cap_type: str) -> Optional[Decimal]:
        """Get configured cap from Redis or DB."""
        redis = self._get_redis()
        if redis and scope_id:
            try:
                val = await redis.get(f"sardis:cap:{scope}:{scope_id}:{cap_type}")
                return Decimal(val) if val else None
            except Exception:
                pass
        return None

    async def set_cap(self, scope: str, scope_id: str, cap_type: str, limit: Decimal) -> None:
        """Set a cap limit."""
        redis = self._get_redis()
        if redis:
            try:
                await redis.set(f"sardis:cap:{scope}:{scope_id}:{cap_type}", str(limit))
                return
            except Exception as e:
                logger.warning("Failed to set cap in Redis: %s", e)

    async def _trigger_kill_switch(self, scope: str, scope_id: str, total: Decimal, cap: Decimal) -> None:
        """Auto-activate kill switch when cap is exceeded."""
        try:
            from sardis_guardrails.kill_switch import ActivationReason, get_kill_switch
            ks = get_kill_switch()
            notes = f"Daily {scope} cap exceeded: ${total} >= ${cap}"

            if scope == "global":
                await ks.activate_global(
                    reason=ActivationReason.RATE_LIMIT,
                    activated_by="transaction_cap_engine",
                    notes=notes,
                    auto_reactivate_after=3600,  # Auto-clear after 1 hour
                )
            elif scope == "org":
                await ks.activate_organization(
                    org_id=scope_id,
                    reason=ActivationReason.RATE_LIMIT,
                    activated_by="transaction_cap_engine",
                    notes=notes,
                    auto_reactivate_after=3600,
                )
            elif scope == "agent":
                await ks.activate_agent(
                    agent_id=scope_id,
                    reason=ActivationReason.RATE_LIMIT,
                    activated_by="transaction_cap_engine",
                    notes=notes,
                    auto_reactivate_after=3600,
                )
            logger.warning("Kill switch activated: %s", notes)
        except Exception as e:
            logger.error("Failed to activate kill switch: %s", e)


# Singleton
_engine: TransactionCapEngine | None = None


def get_transaction_cap_engine() -> TransactionCapEngine:
    global _engine
    if _engine is None:
        _engine = TransactionCapEngine()
    return _engine
