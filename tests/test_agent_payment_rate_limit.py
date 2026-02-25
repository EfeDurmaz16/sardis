from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from sardis_api.middleware.agent_payment_rate_limit import (
    AgentPaymentRateLimitConfig,
    InMemoryAgentSlidingWindowLimiter,
    enforce_agent_payment_rate_limit,
)


@dataclass
class _Settings:
    agent_payment_rate_limit_enabled: bool = True
    agent_payment_rate_limit_max_requests: int = 2
    agent_payment_rate_limit_window_seconds: int = 60
    redis_url: str = ""


@pytest.mark.asyncio
async def test_in_memory_limiter_denies_after_limit() -> None:
    limiter = InMemoryAgentSlidingWindowLimiter(
        AgentPaymentRateLimitConfig(enabled=True, max_requests=2, window_seconds=60)
    )

    first = await limiter.check_and_record("agent_1")
    second = await limiter.check_and_record("agent_1")
    third = await limiter.check_and_record("agent_1")

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after_seconds >= 1


@pytest.mark.asyncio
async def test_enforce_rate_limit_raises_http_429() -> None:
    settings = _Settings()

    await enforce_agent_payment_rate_limit(
        agent_id="agent_429",
        operation="wallets.transfer",
        settings=settings,
    )
    await enforce_agent_payment_rate_limit(
        agent_id="agent_429",
        operation="wallets.transfer",
        settings=settings,
    )

    with pytest.raises(HTTPException) as exc:
        await enforce_agent_payment_rate_limit(
            agent_id="agent_429",
            operation="wallets.transfer",
            settings=settings,
        )
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "agent_rate_limit_exceeded"
    assert exc.value.detail["retry_after_seconds"] >= 1


@pytest.mark.asyncio
async def test_disabled_rate_limit_allows_requests() -> None:
    settings = _Settings(agent_payment_rate_limit_enabled=False)

    result = await enforce_agent_payment_rate_limit(
        agent_id="agent_no_limit",
        operation="wallets.transfer",
        settings=settings,
    )
    assert result.allowed is True
    # Ensure no coroutine scheduling issue in disabled path.
    await asyncio.sleep(0)

