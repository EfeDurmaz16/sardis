"""
Per-agent transaction rate limiting for mandate verification.

Prevents abuse by limiting the number of mandates an agent can submit
within configurable time windows.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    # Maximum mandates per minute per agent
    max_per_minute: int = 60
    
    # Maximum mandates per hour per agent
    max_per_hour: int = 1000
    
    # Maximum mandates per day per agent
    max_per_day: int = 10000
    
    # Window sizes in seconds
    minute_window: int = 60
    hour_window: int = 3600
    day_window: int = 86400
    
    # Whether to enable rate limiting
    enabled: bool = True


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    reason: Optional[str] = None
    remaining_minute: Optional[int] = None
    remaining_hour: Optional[int] = None
    remaining_day: Optional[int] = None
    reset_at: Optional[float] = None


@dataclass
class AgentRateState:
    """Rate limit state for an agent."""
    # Sliding window counters: (count, window_start_time)
    minute_counter: Tuple[int, float] = field(default_factory=lambda: (0, time.time()))
    hour_counter: Tuple[int, float] = field(default_factory=lambda: (0, time.time()))
    day_counter: Tuple[int, float] = field(default_factory=lambda: (0, time.time()))
    
    # Last request timestamp
    last_request: float = 0.0
    
    # Total requests (for stats)
    total_requests: int = 0
    
    # Total rejections
    total_rejections: int = 0


class AgentRateLimiter:
    """
    Per-agent rate limiter using sliding window counters.
    
    Supports in-memory state (for single instance) or can be backed
    by Redis for distributed deployments.
    """
    
    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        redis_client: Optional[object] = None,
    ):
        self._config = config or RateLimitConfig()
        self._redis = redis_client
        self._state: Dict[str, AgentRateState] = {}
    
    def check(self, agent_id: str) -> RateLimitResult:
        """
        Check if an agent is within rate limits.
        
        Does NOT increment counters. Use check_and_increment for that.
        """
        if not self._config.enabled:
            return RateLimitResult(allowed=True)
        
        state = self._get_state(agent_id)
        now = time.time()
        
        # Check minute limit
        minute_count, minute_start = self._get_window_count(
            state.minute_counter, now, self._config.minute_window
        )
        if minute_count >= self._config.max_per_minute:
            reset_at = minute_start + self._config.minute_window
            return RateLimitResult(
                allowed=False,
                reason="rate_limit_minute",
                remaining_minute=0,
                reset_at=reset_at,
            )
        
        # Check hour limit
        hour_count, hour_start = self._get_window_count(
            state.hour_counter, now, self._config.hour_window
        )
        if hour_count >= self._config.max_per_hour:
            reset_at = hour_start + self._config.hour_window
            return RateLimitResult(
                allowed=False,
                reason="rate_limit_hour",
                remaining_hour=0,
                reset_at=reset_at,
            )
        
        # Check day limit
        day_count, day_start = self._get_window_count(
            state.day_counter, now, self._config.day_window
        )
        if day_count >= self._config.max_per_day:
            reset_at = day_start + self._config.day_window
            return RateLimitResult(
                allowed=False,
                reason="rate_limit_day",
                remaining_day=0,
                reset_at=reset_at,
            )
        
        return RateLimitResult(
            allowed=True,
            remaining_minute=self._config.max_per_minute - minute_count,
            remaining_hour=self._config.max_per_hour - hour_count,
            remaining_day=self._config.max_per_day - day_count,
        )
    
    def check_and_increment(self, agent_id: str) -> RateLimitResult:
        """
        Check rate limits and increment counters if allowed.
        
        This is the main method to use for rate limiting.
        """
        result = self.check(agent_id)
        
        if result.allowed:
            self._increment(agent_id)
        else:
            state = self._get_state(agent_id)
            state.total_rejections += 1
            logger.warning(
                f"Rate limit exceeded for agent {agent_id}: {result.reason}"
            )
        
        return result
    
    def _get_state(self, agent_id: str) -> AgentRateState:
        """Get or create state for an agent."""
        if agent_id not in self._state:
            self._state[agent_id] = AgentRateState()
        return self._state[agent_id]
    
    def _get_window_count(
        self,
        counter: Tuple[int, float],
        now: float,
        window_size: int,
    ) -> Tuple[int, float]:
        """Get the count for a sliding window, resetting if needed."""
        count, window_start = counter
        
        if now - window_start >= window_size:
            # Window expired, start new one
            return (0, now)
        
        return (count, window_start)
    
    def _increment(self, agent_id: str) -> None:
        """Increment counters for an agent."""
        state = self._get_state(agent_id)
        now = time.time()
        
        # Update minute counter
        minute_count, minute_start = self._get_window_count(
            state.minute_counter, now, self._config.minute_window
        )
        state.minute_counter = (minute_count + 1, minute_start if minute_count > 0 else now)
        
        # Update hour counter
        hour_count, hour_start = self._get_window_count(
            state.hour_counter, now, self._config.hour_window
        )
        state.hour_counter = (hour_count + 1, hour_start if hour_count > 0 else now)
        
        # Update day counter
        day_count, day_start = self._get_window_count(
            state.day_counter, now, self._config.day_window
        )
        state.day_counter = (day_count + 1, day_start if day_count > 0 else now)
        
        state.last_request = now
        state.total_requests += 1
    
    def get_stats(self, agent_id: str) -> Dict[str, int]:
        """Get rate limit stats for an agent."""
        state = self._get_state(agent_id)
        now = time.time()
        
        minute_count, _ = self._get_window_count(
            state.minute_counter, now, self._config.minute_window
        )
        hour_count, _ = self._get_window_count(
            state.hour_counter, now, self._config.hour_window
        )
        day_count, _ = self._get_window_count(
            state.day_counter, now, self._config.day_window
        )
        
        return {
            "requests_this_minute": minute_count,
            "requests_this_hour": hour_count,
            "requests_this_day": day_count,
            "total_requests": state.total_requests,
            "total_rejections": state.total_rejections,
        }
    
    def reset(self, agent_id: str) -> None:
        """Reset rate limit state for an agent."""
        if agent_id in self._state:
            del self._state[agent_id]
    
    def reset_all(self) -> None:
        """Reset all rate limit state."""
        self._state.clear()


# Global rate limiter instance
_rate_limiter: Optional[AgentRateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> AgentRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = AgentRateLimiter(config)
    
    return _rate_limiter


