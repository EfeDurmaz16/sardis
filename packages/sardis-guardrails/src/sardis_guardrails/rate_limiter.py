"""Rate limiting for agent payment transactions.

Implements token bucket algorithm with sliding window counters.
"""

import asyncio
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    pass


@dataclass
class RateLimit:
    """Rate limit configuration."""

    max_transactions: int  # Maximum number of transactions
    window_seconds: float  # Time window in seconds
    max_amount: Decimal | None = None  # Optional maximum total amount in window


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(init=False)  # Current available tokens
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Initialize tokens to capacity."""
        self.tokens = float(self.capacity)

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        self.last_refill = now

    def available_tokens(self) -> int:
        """Get current number of available tokens.

        Returns:
            Number of available tokens
        """
        self._refill()
        return int(self.tokens)


@dataclass
class TransactionRecord:
    """Record of a transaction for sliding window tracking."""

    timestamp: float
    amount: Decimal


class RateLimiter:
    """Rate limiter for agent payments using token bucket and sliding window.

    Enforces both transaction count and total amount limits within configurable windows.

    Example:
        limiter = RateLimiter(agent_id="agent-123")

        # Configure limits
        limiter.add_limit(
            name="per_minute",
            max_transactions=10,
            window_seconds=60.0,
            max_amount=Decimal("1000.00")
        )

        # Check before transaction
        await limiter.check_and_record(
            limit_name="per_minute",
            amount=Decimal("50.00")
        )
    """

    def __init__(
        self,
        agent_id: str,
        burst_allowance: float = 1.5,
    ) -> None:
        """Initialize rate limiter for an agent.

        Args:
            agent_id: Unique identifier for the agent
            burst_allowance: Multiplier for burst capacity (e.g., 1.5 = 50% burst)
        """
        self.agent_id = agent_id
        self.burst_allowance = burst_allowance
        self._limits: Dict[str, RateLimit] = {}
        self._buckets: Dict[str, TokenBucket] = {}
        self._transactions: Dict[str, List[TransactionRecord]] = {}
        self._lock = asyncio.Lock()

    def add_limit(
        self,
        name: str,
        max_transactions: int,
        window_seconds: float,
        max_amount: Decimal | None = None,
    ) -> None:
        """Add a rate limit configuration.

        Args:
            name: Unique name for this limit (e.g., "per_minute", "per_hour")
            max_transactions: Maximum number of transactions in window
            window_seconds: Time window in seconds
            max_amount: Optional maximum total amount in window
        """
        self._limits[name] = RateLimit(
            max_transactions=max_transactions,
            window_seconds=window_seconds,
            max_amount=max_amount,
        )

        # Create token bucket with burst allowance
        capacity = int(max_transactions * self.burst_allowance)
        refill_rate = max_transactions / window_seconds

        self._buckets[name] = TokenBucket(
            capacity=capacity,
            refill_rate=refill_rate,
        )

        self._transactions[name] = []

    async def check_and_record(
        self,
        limit_name: str,
        amount: Decimal,
    ) -> None:
        """Check rate limits and record transaction if allowed.

        Args:
            limit_name: Name of the limit to check
            amount: Transaction amount

        Raises:
            RateLimitError: If rate limit is exceeded
            ValueError: If limit_name is not configured
        """
        if limit_name not in self._limits:
            raise ValueError(f"Rate limit '{limit_name}' not configured for agent {self.agent_id}")

        async with self._lock:
            limit = self._limits[limit_name]
            bucket = self._buckets[limit_name]

            # Clean old transactions outside window first
            now = time.time()
            cutoff = now - limit.window_seconds
            self._transactions[limit_name] = [
                tx for tx in self._transactions[limit_name] if tx.timestamp > cutoff
            ]

            # Check token bucket for burst control
            if not bucket.consume(1):
                raise RateLimitError(
                    f"Transaction rate limit exceeded for agent {self.agent_id}. "
                    f"Limit: {limit.max_transactions} transactions per "
                    f"{limit.window_seconds}s. "
                    f"Available tokens: {bucket.available_tokens()}"
                )

            # Check amount limit if configured
            if limit.max_amount is not None:
                current_total = sum(
                    tx.amount for tx in self._transactions[limit_name]
                )
                if current_total + amount > limit.max_amount:
                    raise RateLimitError(
                        f"Amount limit exceeded for agent {self.agent_id}. "
                        f"Limit: {limit.max_amount} per {limit.window_seconds}s window. "
                        f"Current total: {current_total}, attempted: {amount}"
                    )

            # Record transaction
            self._transactions[limit_name].append(
                TransactionRecord(timestamp=now, amount=amount)
            )

    async def check_all_limits(self, amount: Decimal) -> None:
        """Check all configured limits for a transaction.

        Args:
            amount: Transaction amount

        Raises:
            RateLimitError: If any rate limit is exceeded
        """
        for limit_name in self._limits:
            await self.check_and_record(limit_name, amount)

    async def get_remaining_capacity(
        self, limit_name: str
    ) -> Dict[str, int | Decimal | None]:
        """Get remaining capacity for a limit.

        Args:
            limit_name: Name of the limit to check

        Returns:
            Dictionary with remaining transactions and amount

        Raises:
            ValueError: If limit_name is not configured
        """
        if limit_name not in self._limits:
            raise ValueError(f"Rate limit '{limit_name}' not configured for agent {self.agent_id}")

        async with self._lock:
            limit = self._limits[limit_name]
            bucket = self._buckets[limit_name]

            # Clean old transactions
            now = time.time()
            cutoff = now - limit.window_seconds
            self._transactions[limit_name] = [
                tx for tx in self._transactions[limit_name] if tx.timestamp > cutoff
            ]

            remaining_transactions = limit.max_transactions - len(
                self._transactions[limit_name]
            )

            remaining_amount: Decimal | None = None
            if limit.max_amount is not None:
                current_total = sum(
                    tx.amount for tx in self._transactions[limit_name]
                )
                remaining_amount = limit.max_amount - current_total

            return {
                "remaining_transactions": max(0, remaining_transactions),
                "remaining_amount": remaining_amount,
                "available_tokens": bucket.available_tokens(),
            }

    async def reset(self, limit_name: str | None = None) -> None:
        """Reset rate limiter state.

        Args:
            limit_name: Optional specific limit to reset, or None for all limits
        """
        async with self._lock:
            if limit_name is None:
                # Reset all limits
                for name in self._limits:
                    self._transactions[name] = []
                    self._buckets[name] = TokenBucket(
                        capacity=int(self._limits[name].max_transactions * self.burst_allowance),
                        refill_rate=self._limits[name].max_transactions
                        / self._limits[name].window_seconds,
                    )
            else:
                # Reset specific limit
                if limit_name not in self._limits:
                    raise ValueError(
                        f"Rate limit '{limit_name}' not configured for agent {self.agent_id}"
                    )
                self._transactions[limit_name] = []
                self._buckets[limit_name] = TokenBucket(
                    capacity=int(self._limits[limit_name].max_transactions * self.burst_allowance),
                    refill_rate=self._limits[limit_name].max_transactions
                    / self._limits[limit_name].window_seconds,
                )
