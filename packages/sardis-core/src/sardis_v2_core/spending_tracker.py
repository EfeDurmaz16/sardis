"""Real-time Spending Tracker for Sardis.

This module provides Redis-backed spending aggregation for policy enforcement.
Tracks spending by wallet, vendor, category, and time period (daily/weekly/monthly).

Example:
    >>> tracker = SpendingTracker(redis_url="redis://localhost:6379")
    >>> await tracker.record_transaction("wallet_123", "AWS", 50.0, "cloud")
    >>> spent = await tracker.get_spending("wallet_123", "AWS", "daily")
    >>> print(spent)  # 50.0
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

try:
    import redis.asyncio as aioredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SpendingSummary:
    """Summary of spending for a wallet."""
    wallet_id: str
    daily_total: Decimal = field(default_factory=lambda: Decimal("0"))
    weekly_total: Decimal = field(default_factory=lambda: Decimal("0"))
    monthly_total: Decimal = field(default_factory=lambda: Decimal("0"))
    by_vendor: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    by_category: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TransactionRecord:
    """Record of a transaction for tracking."""
    wallet_id: str
    vendor: str
    amount: Decimal
    category: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tx_id: Optional[str] = None
    chain: Optional[str] = None


# ============================================================================
# Spending Tracker Implementation
# ============================================================================

class SpendingTracker:
    """
    Real-time spending tracker using Redis for aggregation.

    Tracks spending across multiple dimensions:
    - By wallet
    - By vendor
    - By category
    - By time period (daily, weekly, monthly)

    All data auto-expires to prevent unbounded growth.
    """

    # Key prefixes
    PREFIX = "sardis:spending"

    # TTLs for different periods (with buffer)
    TTL_DAILY = 86400 * 2      # 2 days
    TTL_WEEKLY = 86400 * 14    # 2 weeks
    TTL_MONTHLY = 86400 * 62   # ~2 months

    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize the spending tracker.

        Args:
            redis_url: Redis connection URL (or uses REDIS_URL / UPSTASH_REDIS_URL env var)
            redis_client: Existing Redis client (optional)
        """
        if not HAS_REDIS:
            raise ImportError(
                "redis package required for spending tracking. "
                "Install with: pip install redis"
            )

        if redis_client:
            self.redis = redis_client
        else:
            url = redis_url or os.environ.get("REDIS_URL") or os.environ.get("UPSTASH_REDIS_URL")
            if not url:
                raise ValueError("Redis URL required. Set REDIS_URL env var or pass redis_url.")
            self.redis = aioredis.from_url(url, decode_responses=True)

    # ========================================================================
    # Core Methods
    # ========================================================================

    async def record_transaction(
        self,
        wallet_id: str,
        vendor: str,
        amount: float,
        category: str,
        tx_id: Optional[str] = None,
        chain: Optional[str] = None,
    ) -> None:
        """
        Record a transaction for spending tracking.

        Args:
            wallet_id: Wallet identifier
            vendor: Vendor name (e.g., "AWS", "OpenAI")
            amount: Transaction amount in USD
            category: Merchant category (e.g., "cloud", "ai", "saas")
            tx_id: Transaction ID (optional)
            chain: Blockchain chain (optional)
        """
        now = datetime.now(timezone.utc)
        vendor_lower = vendor.lower()
        category_lower = category.lower()

        # Generate time-based keys
        daily_suffix = now.strftime('%Y-%m-%d')
        weekly_suffix = now.strftime('%Y-W%W')
        monthly_suffix = now.strftime('%Y-%m')

        # Keys for vendor spending
        vendor_daily = f"{self.PREFIX}:{wallet_id}:vendor:{vendor_lower}:daily:{daily_suffix}"
        vendor_weekly = f"{self.PREFIX}:{wallet_id}:vendor:{vendor_lower}:weekly:{weekly_suffix}"
        vendor_monthly = f"{self.PREFIX}:{wallet_id}:vendor:{vendor_lower}:monthly:{monthly_suffix}"

        # Keys for category spending
        cat_daily = f"{self.PREFIX}:{wallet_id}:category:{category_lower}:daily:{daily_suffix}"
        cat_weekly = f"{self.PREFIX}:{wallet_id}:category:{category_lower}:weekly:{weekly_suffix}"
        cat_monthly = f"{self.PREFIX}:{wallet_id}:category:{category_lower}:monthly:{monthly_suffix}"

        # Keys for total spending
        total_daily = f"{self.PREFIX}:{wallet_id}:total:daily:{daily_suffix}"
        total_weekly = f"{self.PREFIX}:{wallet_id}:total:weekly:{weekly_suffix}"
        total_monthly = f"{self.PREFIX}:{wallet_id}:total:monthly:{monthly_suffix}"

        # Execute all increments in a pipeline
        pipe = self.redis.pipeline()

        # Vendor tracking
        pipe.incrbyfloat(vendor_daily, amount)
        pipe.expire(vendor_daily, self.TTL_DAILY)
        pipe.incrbyfloat(vendor_weekly, amount)
        pipe.expire(vendor_weekly, self.TTL_WEEKLY)
        pipe.incrbyfloat(vendor_monthly, amount)
        pipe.expire(vendor_monthly, self.TTL_MONTHLY)

        # Category tracking
        pipe.incrbyfloat(cat_daily, amount)
        pipe.expire(cat_daily, self.TTL_DAILY)
        pipe.incrbyfloat(cat_weekly, amount)
        pipe.expire(cat_weekly, self.TTL_WEEKLY)
        pipe.incrbyfloat(cat_monthly, amount)
        pipe.expire(cat_monthly, self.TTL_MONTHLY)

        # Total tracking
        pipe.incrbyfloat(total_daily, amount)
        pipe.expire(total_daily, self.TTL_DAILY)
        pipe.incrbyfloat(total_weekly, amount)
        pipe.expire(total_weekly, self.TTL_WEEKLY)
        pipe.incrbyfloat(total_monthly, amount)
        pipe.expire(total_monthly, self.TTL_MONTHLY)

        # Store transaction in recent list (for audit)
        if tx_id:
            recent_key = f"{self.PREFIX}:{wallet_id}:recent"
            tx_data = f"{now.isoformat()}|{vendor}|{amount}|{category}|{tx_id}|{chain or ''}"
            pipe.lpush(recent_key, tx_data)
            pipe.ltrim(recent_key, 0, 999)  # Keep last 1000
            pipe.expire(recent_key, self.TTL_MONTHLY)

        await pipe.execute()

        logger.debug(
            f"Recorded spending: wallet={wallet_id}, vendor={vendor}, "
            f"amount={amount}, category={category}"
        )

    async def get_spending(
        self,
        wallet_id: str,
        vendor: str,
        period: str,
    ) -> float:
        """
        Get current spending for a specific vendor and period.

        Args:
            wallet_id: Wallet identifier
            vendor: Vendor name
            period: Period type ("daily", "weekly", "monthly")

        Returns:
            Current spending amount as float
        """
        now = datetime.now(timezone.utc)
        vendor_lower = vendor.lower()

        if period == "daily":
            suffix = now.strftime('%Y-%m-%d')
        elif period == "weekly":
            suffix = now.strftime('%Y-W%W')
        elif period == "monthly":
            suffix = now.strftime('%Y-%m')
        else:
            return 0.0

        key = f"{self.PREFIX}:{wallet_id}:vendor:{vendor_lower}:{period}:{suffix}"
        result = await self.redis.get(key)

        return float(result) if result else 0.0

    async def get_category_spending(
        self,
        wallet_id: str,
        category: str,
        period: str,
    ) -> float:
        """
        Get current spending for a specific category and period.

        Args:
            wallet_id: Wallet identifier
            category: Category name
            period: Period type ("daily", "weekly", "monthly")

        Returns:
            Current spending amount as float
        """
        now = datetime.now(timezone.utc)
        category_lower = category.lower()

        if period == "daily":
            suffix = now.strftime('%Y-%m-%d')
        elif period == "weekly":
            suffix = now.strftime('%Y-W%W')
        elif period == "monthly":
            suffix = now.strftime('%Y-%m')
        else:
            return 0.0

        key = f"{self.PREFIX}:{wallet_id}:category:{category_lower}:{period}:{suffix}"
        result = await self.redis.get(key)

        return float(result) if result else 0.0

    async def get_total_spending(
        self,
        wallet_id: str,
        period: str,
    ) -> float:
        """
        Get total spending across all vendors for a period.

        Args:
            wallet_id: Wallet identifier
            period: Period type ("daily", "weekly", "monthly")

        Returns:
            Total spending amount as float
        """
        now = datetime.now(timezone.utc)

        if period == "daily":
            suffix = now.strftime('%Y-%m-%d')
        elif period == "weekly":
            suffix = now.strftime('%Y-W%W')
        elif period == "monthly":
            suffix = now.strftime('%Y-%m')
        else:
            return 0.0

        key = f"{self.PREFIX}:{wallet_id}:total:{period}:{suffix}"
        result = await self.redis.get(key)

        return float(result) if result else 0.0

    async def get_spending_summary(self, wallet_id: str) -> SpendingSummary:
        """
        Get complete spending summary for a wallet.

        Args:
            wallet_id: Wallet identifier

        Returns:
            SpendingSummary with all spending data
        """
        now = datetime.now(timezone.utc)
        pattern = f"{self.PREFIX}:{wallet_id}:*"

        summary = SpendingSummary(wallet_id=wallet_id)

        # Get total spending for each period
        summary.daily_total = Decimal(str(await self.get_total_spending(wallet_id, "daily")))
        summary.weekly_total = Decimal(str(await self.get_total_spending(wallet_id, "weekly")))
        summary.monthly_total = Decimal(str(await self.get_total_spending(wallet_id, "monthly")))

        # Scan for vendor and category breakdowns
        async for key in self.redis.scan_iter(match=pattern):
            parts = key.split(":")
            if len(parts) >= 6:
                # Format: sardis:spending:{wallet}:{type}:{name}:{period}:{date}
                spending_type = parts[3]  # vendor or category
                name = parts[4]
                period = parts[5]

                value = await self.redis.get(key)
                amount = Decimal(str(float(value))) if value else Decimal("0")

                if spending_type == "vendor":
                    if name not in summary.by_vendor:
                        summary.by_vendor[name] = {}
                    summary.by_vendor[name][period] = amount
                elif spending_type == "category":
                    if name not in summary.by_category:
                        summary.by_category[name] = {}
                    summary.by_category[name][period] = amount

        summary.last_updated = now
        return summary

    async def get_spending_data_for_policy(self, wallet_id: str) -> Dict[str, Dict[str, float]]:
        """
        Get spending data formatted for policy evaluation (OPA compatible).

        Args:
            wallet_id: Wallet identifier

        Returns:
            Dict in format: {"vendor_name": {"daily": amount, "weekly": amount, ...}}
        """
        summary = await self.get_spending_summary(wallet_id)

        # Convert to simple float dict for OPA
        result = {}
        for vendor, periods in summary.by_vendor.items():
            result[vendor] = {
                period: float(amount) for period, amount in periods.items()
            }

        return result

    async def get_recent_transactions(
        self,
        wallet_id: str,
        limit: int = 50,
    ) -> list[TransactionRecord]:
        """
        Get recent transactions for a wallet.

        Args:
            wallet_id: Wallet identifier
            limit: Maximum number of transactions to return

        Returns:
            List of TransactionRecord objects
        """
        key = f"{self.PREFIX}:{wallet_id}:recent"
        items = await self.redis.lrange(key, 0, limit - 1)

        records = []
        for item in items:
            parts = item.split("|")
            if len(parts) >= 5:
                records.append(TransactionRecord(
                    wallet_id=wallet_id,
                    vendor=parts[1],
                    amount=Decimal(parts[2]),
                    category=parts[3],
                    tx_id=parts[4] if parts[4] else None,
                    chain=parts[5] if len(parts) > 5 and parts[5] else None,
                    timestamp=datetime.fromisoformat(parts[0]),
                ))

        return records

    # ========================================================================
    # Policy Integration Methods
    # ========================================================================

    async def check_vendor_limit(
        self,
        wallet_id: str,
        vendor: str,
        amount: float,
        limit: float,
        period: str,
    ) -> tuple[bool, str]:
        """
        Check if a transaction would exceed vendor spending limit.

        Args:
            wallet_id: Wallet identifier
            vendor: Vendor name
            amount: Transaction amount
            limit: Spending limit for the period
            period: Period type ("daily", "weekly", "monthly")

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        current = await self.get_spending(wallet_id, vendor, period)

        if current + amount > limit:
            return False, f"{vendor} {period} limit exceeded: ${current + amount:.2f} > ${limit:.2f}"

        return True, "OK"

    async def check_total_limit(
        self,
        wallet_id: str,
        amount: float,
        limit: float,
        period: str,
    ) -> tuple[bool, str]:
        """
        Check if a transaction would exceed total spending limit.

        Args:
            wallet_id: Wallet identifier
            amount: Transaction amount
            limit: Total spending limit for the period
            period: Period type ("daily", "weekly", "monthly")

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        current = await self.get_total_spending(wallet_id, period)

        if current + amount > limit:
            return False, f"Total {period} limit exceeded: ${current + amount:.2f} > ${limit:.2f}"

        return True, "OK"

    async def close(self) -> None:
        """Close the Redis connection."""
        await self.redis.close()


# ============================================================================
# In-Memory Fallback (for testing)
# ============================================================================

class InMemorySpendingTracker:
    """
    In-memory spending tracker for testing and development.

    Does not require Redis. Data is lost on restart.
    """

    def __init__(self):
        self._data: Dict[str, float] = {}
        self._recent: Dict[str, list] = {}

    async def record_transaction(
        self,
        wallet_id: str,
        vendor: str,
        amount: float,
        category: str,
        tx_id: Optional[str] = None,
        chain: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        vendor_lower = vendor.lower()
        category_lower = category.lower()

        # Generate keys
        daily_suffix = now.strftime('%Y-%m-%d')
        weekly_suffix = now.strftime('%Y-W%W')
        monthly_suffix = now.strftime('%Y-%m')

        # Update vendor spending
        for period, suffix in [("daily", daily_suffix), ("weekly", weekly_suffix), ("monthly", monthly_suffix)]:
            key = f"{wallet_id}:vendor:{vendor_lower}:{period}:{suffix}"
            self._data[key] = self._data.get(key, 0.0) + amount

        # Update category spending
        for period, suffix in [("daily", daily_suffix), ("weekly", weekly_suffix), ("monthly", monthly_suffix)]:
            key = f"{wallet_id}:category:{category_lower}:{period}:{suffix}"
            self._data[key] = self._data.get(key, 0.0) + amount

        # Update total spending
        for period, suffix in [("daily", daily_suffix), ("weekly", weekly_suffix), ("monthly", monthly_suffix)]:
            key = f"{wallet_id}:total:{period}:{suffix}"
            self._data[key] = self._data.get(key, 0.0) + amount

        # Store recent transaction
        if wallet_id not in self._recent:
            self._recent[wallet_id] = []
        self._recent[wallet_id].insert(0, TransactionRecord(
            wallet_id=wallet_id,
            vendor=vendor,
            amount=Decimal(str(amount)),
            category=category,
            tx_id=tx_id,
            chain=chain,
            timestamp=now,
        ))
        self._recent[wallet_id] = self._recent[wallet_id][:1000]

    async def get_spending(self, wallet_id: str, vendor: str, period: str) -> float:
        now = datetime.now(timezone.utc)
        vendor_lower = vendor.lower()

        if period == "daily":
            suffix = now.strftime('%Y-%m-%d')
        elif period == "weekly":
            suffix = now.strftime('%Y-W%W')
        elif period == "monthly":
            suffix = now.strftime('%Y-%m')
        else:
            return 0.0

        key = f"{wallet_id}:vendor:{vendor_lower}:{period}:{suffix}"
        return self._data.get(key, 0.0)

    async def get_total_spending(self, wallet_id: str, period: str) -> float:
        now = datetime.now(timezone.utc)

        if period == "daily":
            suffix = now.strftime('%Y-%m-%d')
        elif period == "weekly":
            suffix = now.strftime('%Y-W%W')
        elif period == "monthly":
            suffix = now.strftime('%Y-%m')
        else:
            return 0.0

        key = f"{wallet_id}:total:{period}:{suffix}"
        return self._data.get(key, 0.0)

    async def check_vendor_limit(
        self,
        wallet_id: str,
        vendor: str,
        amount: float,
        limit: float,
        period: str,
    ) -> tuple[bool, str]:
        current = await self.get_spending(wallet_id, vendor, period)
        if current + amount > limit:
            return False, f"{vendor} {period} limit exceeded"
        return True, "OK"

    async def check_total_limit(
        self,
        wallet_id: str,
        amount: float,
        limit: float,
        period: str,
    ) -> tuple[bool, str]:
        current = await self.get_total_spending(wallet_id, period)
        if current + amount > limit:
            return False, f"Total {period} limit exceeded"
        return True, "OK"

    async def get_recent_transactions(
        self,
        wallet_id: str,
        limit: int = 50,
    ) -> list[TransactionRecord]:
        return self._recent.get(wallet_id, [])[:limit]

    async def close(self) -> None:
        pass


# ============================================================================
# Factory Function
# ============================================================================

def create_spending_tracker(
    redis_url: Optional[str] = None,
    use_memory: bool = False,
) -> SpendingTracker | InMemorySpendingTracker:
    """
    Create appropriate spending tracker based on configuration.

    Args:
        redis_url: Redis connection URL
        use_memory: If True, use in-memory tracker (for testing)

    Returns:
        Spending tracker instance
    """
    if use_memory:
        return InMemorySpendingTracker()

    try:
        return SpendingTracker(redis_url=redis_url)
    except (ImportError, ValueError) as e:
        logger.warning(f"Failed to create Redis tracker, using in-memory: {e}")
        return InMemorySpendingTracker()
