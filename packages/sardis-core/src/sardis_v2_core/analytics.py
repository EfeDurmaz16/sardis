"""
Sardis Analytics Module

Basic analytics tracking for wallets, transactions, and API usage.
Designed for monitoring and investor metrics dashboard.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Analytics event types."""
    # Wallet events
    WALLET_CREATED = "wallet.created"
    WALLET_FUNDED = "wallet.funded"
    WALLET_ACTIVATED = "wallet.activated"

    # Transaction events
    TRANSACTION_INITIATED = "transaction.initiated"
    TRANSACTION_COMPLETED = "transaction.completed"
    TRANSACTION_FAILED = "transaction.failed"
    TRANSACTION_POLICY_BLOCKED = "transaction.policy_blocked"

    # Policy events
    POLICY_CREATED = "policy.created"
    POLICY_EVALUATED = "policy.evaluated"
    POLICY_UPDATED = "policy.updated"

    # API events
    API_REQUEST = "api.request"
    API_ERROR = "api.error"

    # MCP events
    MCP_TOOL_CALLED = "mcp.tool_called"
    MCP_SESSION_STARTED = "mcp.session_started"

    # Compliance events
    KYC_STARTED = "kyc.started"
    KYC_COMPLETED = "kyc.completed"
    AML_CHECK_PERFORMED = "aml.check_performed"

    # Card events
    CARD_ISSUED = "card.issued"
    CARD_TRANSACTION = "card.transaction"

    # Fiat events
    FIAT_ONRAMP = "fiat.onramp"
    FIAT_OFFRAMP = "fiat.offramp"


@dataclass
class AnalyticsEvent:
    """Structured analytics event."""
    event_type: EventType
    timestamp: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    wallet_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "properties": self.properties,
            "user_id": self.user_id,
            "wallet_id": self.wallet_id,
            "session_id": self.session_id,
        }


@dataclass
class MetricsSummary:
    """Aggregated metrics summary for dashboard."""
    period_start: datetime
    period_end: datetime

    # Wallet metrics
    total_wallets: int = 0
    new_wallets: int = 0
    active_wallets: int = 0  # Transacted in period

    # Transaction metrics
    total_transactions: int = 0
    successful_transactions: int = 0
    failed_transactions: int = 0
    blocked_transactions: int = 0
    total_volume_usd: float = 0.0
    average_transaction_usd: float = 0.0

    # API metrics
    api_requests: int = 0
    api_errors: int = 0
    api_error_rate: float = 0.0

    # MCP metrics
    mcp_tool_calls: int = 0
    mcp_sessions: int = 0

    # Compliance metrics
    kyc_completions: int = 0
    aml_checks: int = 0

    # Card metrics
    cards_issued: int = 0
    card_transactions: int = 0
    card_volume_usd: float = 0.0

    # Fiat metrics
    fiat_onramp_volume: float = 0.0
    fiat_offramp_volume: float = 0.0


class AnalyticsService:
    """
    Analytics service for tracking and aggregating metrics.

    Supports:
    - In-memory storage (default, for development)
    - Redis storage (for production)
    - PostHog integration (optional)
    """

    def __init__(
        self,
        storage_backend: str = "memory",
        redis_url: Optional[str] = None,
        posthog_api_key: Optional[str] = None,
    ):
        self.storage_backend = storage_backend
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.posthog_api_key = posthog_api_key or os.getenv("POSTHOG_API_KEY")

        # In-memory storage
        self._events: List[AnalyticsEvent] = []
        self._metrics: Dict[str, int] = defaultdict(int)
        self._volumes: Dict[str, float] = defaultdict(float)

        # Initialize backends
        self._redis = None
        self._posthog = None

        if self.storage_backend == "redis" and self.redis_url:
            self._init_redis()

        if self.posthog_api_key:
            self._init_posthog()

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis
            self._redis = redis.from_url(self.redis_url)
            logger.info("Analytics: Redis backend initialized")
        except ImportError:
            logger.warning("Analytics: redis package not installed, falling back to memory")
        except Exception as e:
            logger.error(f"Analytics: Redis connection failed: {e}")

    def _init_posthog(self):
        """Initialize PostHog client."""
        try:
            import posthog
            posthog.project_api_key = self.posthog_api_key
            self._posthog = posthog
            logger.info("Analytics: PostHog initialized")
        except ImportError:
            logger.warning("Analytics: posthog package not installed")
        except Exception as e:
            logger.error(f"Analytics: PostHog initialization failed: {e}")

    async def track(
        self,
        event_type: EventType,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Track an analytics event."""
        event = AnalyticsEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            properties=properties or {},
            user_id=user_id,
            wallet_id=wallet_id,
            session_id=session_id,
        )

        # Store event
        await self._store_event(event)

        # Update counters
        await self._update_counters(event)

        # Send to PostHog if configured
        if self._posthog:
            self._posthog.capture(
                distinct_id=user_id or wallet_id or "anonymous",
                event=event_type.value,
                properties=properties,
            )

        logger.debug(f"Analytics: Tracked {event_type.value}")

    async def _store_event(self, event: AnalyticsEvent) -> None:
        """Store event in backend."""
        if self._redis:
            # Store in Redis with TTL of 90 days
            key = f"analytics:events:{event.timestamp.strftime('%Y-%m-%d')}"
            self._redis.rpush(key, json.dumps(event.to_dict()))
            self._redis.expire(key, 90 * 24 * 60 * 60)
        else:
            # In-memory storage
            self._events.append(event)
            # Keep only last 10000 events in memory
            if len(self._events) > 10000:
                self._events = self._events[-10000:]

    async def _update_counters(self, event: AnalyticsEvent) -> None:
        """Update metric counters."""
        date_key = event.timestamp.strftime('%Y-%m-%d')
        counter_key = f"{event.event_type.value}:{date_key}"

        if self._redis:
            self._redis.incr(f"analytics:count:{counter_key}")

            # Track volume for transaction events
            if event.event_type == EventType.TRANSACTION_COMPLETED:
                amount = event.properties.get("amount_usd", 0)
                self._redis.incrbyfloat(f"analytics:volume:{date_key}", amount)
        else:
            self._metrics[counter_key] += 1

            if event.event_type == EventType.TRANSACTION_COMPLETED:
                amount = event.properties.get("amount_usd", 0)
                self._volumes[date_key] += amount

    async def get_metrics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> MetricsSummary:
        """Get aggregated metrics for a time period."""
        end_date = end_date or datetime.utcnow()
        start_date = start_date or (end_date - timedelta(days=30))

        summary = MetricsSummary(
            period_start=start_date,
            period_end=end_date,
        )

        if self._redis:
            # Aggregate from Redis
            current = start_date
            while current <= end_date:
                date_key = current.strftime('%Y-%m-%d')

                # Count events
                for event_type in EventType:
                    count_key = f"analytics:count:{event_type.value}:{date_key}"
                    count = int(self._redis.get(count_key) or 0)

                    if event_type == EventType.WALLET_CREATED:
                        summary.new_wallets += count
                    elif event_type == EventType.TRANSACTION_COMPLETED:
                        summary.successful_transactions += count
                    elif event_type == EventType.TRANSACTION_FAILED:
                        summary.failed_transactions += count
                    elif event_type == EventType.TRANSACTION_POLICY_BLOCKED:
                        summary.blocked_transactions += count
                    elif event_type == EventType.API_REQUEST:
                        summary.api_requests += count
                    elif event_type == EventType.API_ERROR:
                        summary.api_errors += count
                    elif event_type == EventType.MCP_TOOL_CALLED:
                        summary.mcp_tool_calls += count
                    elif event_type == EventType.MCP_SESSION_STARTED:
                        summary.mcp_sessions += count
                    elif event_type == EventType.KYC_COMPLETED:
                        summary.kyc_completions += count
                    elif event_type == EventType.AML_CHECK_PERFORMED:
                        summary.aml_checks += count
                    elif event_type == EventType.CARD_ISSUED:
                        summary.cards_issued += count

                # Get volume
                volume_key = f"analytics:volume:{date_key}"
                volume = float(self._redis.get(volume_key) or 0)
                summary.total_volume_usd += volume

                current += timedelta(days=1)
        else:
            # Aggregate from memory
            for event in self._events:
                if start_date <= event.timestamp <= end_date:
                    if event.event_type == EventType.WALLET_CREATED:
                        summary.new_wallets += 1
                    elif event.event_type == EventType.TRANSACTION_COMPLETED:
                        summary.successful_transactions += 1
                        summary.total_volume_usd += event.properties.get("amount_usd", 0)
                    elif event.event_type == EventType.TRANSACTION_FAILED:
                        summary.failed_transactions += 1
                    elif event.event_type == EventType.TRANSACTION_POLICY_BLOCKED:
                        summary.blocked_transactions += 1
                    elif event.event_type == EventType.API_REQUEST:
                        summary.api_requests += 1
                    elif event.event_type == EventType.API_ERROR:
                        summary.api_errors += 1
                    elif event.event_type == EventType.MCP_TOOL_CALLED:
                        summary.mcp_tool_calls += 1

        # Calculate derived metrics
        summary.total_transactions = (
            summary.successful_transactions +
            summary.failed_transactions +
            summary.blocked_transactions
        )

        if summary.successful_transactions > 0:
            summary.average_transaction_usd = (
                summary.total_volume_usd / summary.successful_transactions
            )

        if summary.api_requests > 0:
            summary.api_error_rate = summary.api_errors / summary.api_requests

        return summary

    async def get_realtime_stats(self) -> Dict[str, Any]:
        """Get real-time stats for dashboard."""
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        summary = await self.get_metrics_summary(start_date=today, end_date=now)

        return {
            "timestamp": now.isoformat(),
            "today": {
                "wallets_created": summary.new_wallets,
                "transactions": summary.total_transactions,
                "volume_usd": round(summary.total_volume_usd, 2),
                "api_requests": summary.api_requests,
                "mcp_calls": summary.mcp_tool_calls,
            },
            "success_rate": (
                summary.successful_transactions / max(summary.total_transactions, 1)
            ) * 100,
        }


# Global analytics instance
_analytics: Optional[AnalyticsService] = None


def get_analytics() -> AnalyticsService:
    """Get or create the global analytics service."""
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsService(
            storage_backend=os.getenv("ANALYTICS_BACKEND", "memory"),
            redis_url=os.getenv("REDIS_URL"),
            posthog_api_key=os.getenv("POSTHOG_API_KEY"),
        )
    return _analytics


# Convenience functions
async def track_wallet_created(wallet_id: str, chain: str, user_id: Optional[str] = None):
    """Track wallet creation."""
    await get_analytics().track(
        EventType.WALLET_CREATED,
        properties={"chain": chain},
        wallet_id=wallet_id,
        user_id=user_id,
    )


async def track_transaction(
    wallet_id: str,
    amount_usd: float,
    success: bool,
    chain: str,
    tx_hash: Optional[str] = None,
    blocked_by_policy: bool = False,
):
    """Track transaction."""
    if blocked_by_policy:
        event_type = EventType.TRANSACTION_POLICY_BLOCKED
    elif success:
        event_type = EventType.TRANSACTION_COMPLETED
    else:
        event_type = EventType.TRANSACTION_FAILED

    await get_analytics().track(
        event_type,
        properties={
            "amount_usd": amount_usd,
            "chain": chain,
            "tx_hash": tx_hash,
        },
        wallet_id=wallet_id,
    )


async def track_mcp_tool_call(tool_name: str, session_id: Optional[str] = None):
    """Track MCP tool call."""
    await get_analytics().track(
        EventType.MCP_TOOL_CALLED,
        properties={"tool": tool_name},
        session_id=session_id,
    )


async def track_api_request(endpoint: str, method: str, status_code: int):
    """Track API request."""
    event_type = EventType.API_ERROR if status_code >= 400 else EventType.API_REQUEST
    await get_analytics().track(
        event_type,
        properties={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
        },
    )
