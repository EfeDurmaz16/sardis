"""Chain execution domains with isolated risk profiles.

Each chain domain has independent:
- Risk limits (max tx, max daily volume)
- Rate limits
- Kill switch keys
- Required confirmations
- Allowed tokens

Domain isolation ensures Ethereum failure does not block Base.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DomainRiskProfile:
    """Per-domain risk configuration."""
    max_single_tx: Decimal = Decimal("10000")    # Max single transaction
    max_daily_volume: Decimal = Decimal("100000")  # Max daily volume across domain
    required_confirmations: int = 1                # Block confirmations required
    allowed_tokens: list[str] = field(default_factory=lambda: ["USDC"])
    max_pending_txs: int = 100                    # Max concurrent pending transactions
    gas_price_ceiling_gwei: int = 500             # Reject if gas price exceeds this


# Default risk profiles per chain
DEFAULT_RISK_PROFILES: dict[str, DomainRiskProfile] = {
    "base": DomainRiskProfile(
        max_single_tx=Decimal("50000"),
        max_daily_volume=Decimal("500000"),
        required_confirmations=1,
        allowed_tokens=["USDC", "EURC"],
    ),
    "ethereum": DomainRiskProfile(
        max_single_tx=Decimal("100000"),
        max_daily_volume=Decimal("1000000"),
        required_confirmations=3,
        allowed_tokens=["USDC", "USDT", "PYUSD", "EURC"],
        gas_price_ceiling_gwei=200,
    ),
    "polygon": DomainRiskProfile(
        max_single_tx=Decimal("25000"),
        max_daily_volume=Decimal("250000"),
        required_confirmations=5,
        allowed_tokens=["USDC", "USDT", "EURC"],
    ),
    "arbitrum": DomainRiskProfile(
        max_single_tx=Decimal("50000"),
        max_daily_volume=Decimal("500000"),
        required_confirmations=1,
        allowed_tokens=["USDC", "USDT"],
    ),
    "optimism": DomainRiskProfile(
        max_single_tx=Decimal("50000"),
        max_daily_volume=Decimal("500000"),
        required_confirmations=1,
        allowed_tokens=["USDC", "USDT"],
    ),
}


@dataclass
class ChainDomain:
    """Isolated execution domain for a specific blockchain.

    Each domain has its own risk profile, rate limits, and kill switch scope.
    Domain failures are contained — one chain going down doesn't affect others.
    """

    chain: str
    risk_profile: DomainRiskProfile
    is_healthy: bool = True
    pending_tx_count: int = 0
    daily_volume: Decimal = Decimal("0")
    last_error: str = ""

    @property
    def kill_switch_key(self) -> str:
        """Kill switch key for this domain."""
        return f"chain:{self.chain}"

    def check_tx_allowed(self, amount: Decimal, token: str) -> tuple[bool, str]:
        """Pre-flight check whether a transaction is allowed in this domain.

        Returns (allowed, reason).
        """
        if not self.is_healthy:
            return False, f"Chain domain '{self.chain}' is unhealthy: {self.last_error}"

        if token not in self.risk_profile.allowed_tokens:
            return False, f"Token '{token}' not allowed on '{self.chain}'"

        if amount > self.risk_profile.max_single_tx:
            return False, (
                f"Amount {amount} exceeds max single tx "
                f"{self.risk_profile.max_single_tx} for '{self.chain}'"
            )

        if self.daily_volume + amount > self.risk_profile.max_daily_volume:
            return False, (
                f"Daily volume would exceed {self.risk_profile.max_daily_volume} "
                f"for '{self.chain}'"
            )

        if self.pending_tx_count >= self.risk_profile.max_pending_txs:
            return False, f"Max pending transactions reached for '{self.chain}'"

        return True, ""

    def record_tx(self, amount: Decimal) -> None:
        """Record a successful transaction in this domain."""
        self.daily_volume += amount
        self.pending_tx_count += 1

    def tx_completed(self) -> None:
        """Mark a pending transaction as completed."""
        self.pending_tx_count = max(0, self.pending_tx_count - 1)

    def mark_unhealthy(self, error: str) -> None:
        """Mark the domain as unhealthy (circuit breaker)."""
        self.is_healthy = False
        self.last_error = error
        logger.warning("Chain domain '%s' marked unhealthy: %s", self.chain, error)

    def mark_healthy(self) -> None:
        """Mark the domain as healthy."""
        self.is_healthy = True
        self.last_error = ""


class DomainRegistry:
    """Registry of all chain execution domains."""

    def __init__(self) -> None:
        self._domains: dict[str, ChainDomain] = {}

    def register(self, chain: str, risk_profile: Optional[DomainRiskProfile] = None) -> ChainDomain:
        """Register a chain domain with its risk profile."""
        profile = risk_profile or DEFAULT_RISK_PROFILES.get(chain, DomainRiskProfile())
        domain = ChainDomain(chain=chain, risk_profile=profile)
        self._domains[chain] = domain
        logger.info("Registered chain domain '%s'", chain)
        return domain

    def get(self, chain: str) -> Optional[ChainDomain]:
        """Get a chain domain."""
        return self._domains.get(chain)

    def get_or_register(self, chain: str) -> ChainDomain:
        """Get or auto-register a chain domain."""
        domain = self._domains.get(chain)
        if domain is None:
            domain = self.register(chain)
        return domain

    def list_healthy(self) -> list[ChainDomain]:
        """List all healthy domains."""
        return [d for d in self._domains.values() if d.is_healthy]

    def list_all(self) -> list[ChainDomain]:
        """List all registered domains."""
        return list(self._domains.values())

    def get_status(self) -> dict[str, Any]:
        """Get status of all domains."""
        return {
            chain: {
                "healthy": d.is_healthy,
                "pending_txs": d.pending_tx_count,
                "daily_volume": str(d.daily_volume),
                "max_daily_volume": str(d.risk_profile.max_daily_volume),
                "last_error": d.last_error,
            }
            for chain, d in self._domains.items()
        }


# Global registry singleton
_registry: Optional[DomainRegistry] = None


def get_domain_registry() -> DomainRegistry:
    """Get or create the global domain registry."""
    global _registry
    if _registry is None:
        _registry = DomainRegistry()
        # Auto-register all supported chains
        for chain in DEFAULT_RISK_PROFILES:
            _registry.register(chain)
    return _registry
