"""
Policy enforcement for agent payments.

Policies define rules for what transactions are allowed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .wallet import Wallet


@dataclass
class PolicyResult:
    """Result of a policy check."""
    approved: bool
    reason: Optional[str] = None
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        status = "approved" if self.approved else "rejected"
        return f"PolicyResult({status})"


@dataclass
class Policy:
    """
    Spending policy for AI agents.
    
    Policies enforce limits on transactions:
    - Maximum per transaction
    - Allowed destinations (merchants/categories)
    - Token restrictions
    - Time-based limits
    
    Example:
        >>> policy = Policy(max_per_tx=50, allowed_destinations={"openai:*", "anthropic:*"})
        >>> result = policy.check(amount=25, destination="openai:api")
        >>> print(result.approved)  # True
    """
    
    max_per_tx: Decimal = field(default_factory=lambda: Decimal("100.00"))
    max_total: Decimal = field(default_factory=lambda: Decimal("1000.00"))
    allowed_destinations: Optional[Set[str]] = None  # None = allow all
    blocked_destinations: Set[str] = field(default_factory=set)
    allowed_tokens: Set[str] = field(default_factory=lambda: {"USDC", "USDT", "PYUSD"})
    require_purpose: bool = False
    
    def __init__(
        self,
        max_per_tx: float | Decimal = 100,
        max_total: float | Decimal = 1000,
        allowed_destinations: Optional[Set[str]] = None,
        blocked_destinations: Optional[Set[str]] = None,
        allowed_tokens: Optional[Set[str]] = None,
        require_purpose: bool = False,
    ):
        """
        Create a spending policy.
        
        Args:
            max_per_tx: Maximum amount per transaction
            max_total: Maximum total spending
            allowed_destinations: Whitelist of allowed destinations (None = all)
            blocked_destinations: Blacklist of blocked destinations
            allowed_tokens: Set of allowed token types
            require_purpose: Whether transactions must have a purpose
        """
        self.max_per_tx = Decimal(str(max_per_tx))
        self.max_total = Decimal(str(max_total))
        self.allowed_destinations = allowed_destinations
        self.blocked_destinations = blocked_destinations or set()
        self.allowed_tokens = allowed_tokens or {"USDC", "USDT", "PYUSD"}
        self.require_purpose = require_purpose
    
    def check(
        self,
        amount: Decimal | float,
        wallet: Optional["Wallet"] = None,
        destination: Optional[str] = None,
        token: str = "USDC",
        purpose: Optional[str] = None,
    ) -> PolicyResult:
        """
        Check if a transaction is allowed by this policy.
        
        Args:
            amount: Transaction amount
            wallet: Source wallet (optional)
            destination: Destination identifier
            token: Token type
            purpose: Transaction purpose
            
        Returns:
            PolicyResult with approval status and details
        """
        amount = Decimal(str(amount))
        checks_passed = []
        checks_failed = []
        
        # Check amount limit
        if amount <= self.max_per_tx:
            checks_passed.append("amount_limit")
        else:
            checks_failed.append("amount_limit")
            return PolicyResult(
                approved=False,
                reason=f"Amount {amount} exceeds limit {self.max_per_tx}",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        
        # Check token
        if token in self.allowed_tokens:
            checks_passed.append("token_allowed")
        else:
            checks_failed.append("token_allowed")
            return PolicyResult(
                approved=False,
                reason=f"Token {token} not allowed",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        
        # Check destination blocklist
        if destination and destination in self.blocked_destinations:
            checks_failed.append("destination_blocked")
            return PolicyResult(
                approved=False,
                reason=f"Destination {destination} is blocked",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        checks_passed.append("destination_not_blocked")
        
        # Check destination allowlist
        if self.allowed_destinations is not None and destination:
            allowed = self._check_destination_pattern(destination, self.allowed_destinations)
            if allowed:
                checks_passed.append("destination_allowed")
            else:
                checks_failed.append("destination_allowed")
                return PolicyResult(
                    approved=False,
                    reason=f"Destination {destination} not in allowed list",
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
        
        # Check purpose requirement
        if self.require_purpose and not purpose:
            checks_failed.append("purpose_required")
            return PolicyResult(
                approved=False,
                reason="Transaction purpose is required",
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )
        if self.require_purpose:
            checks_passed.append("purpose_provided")
        
        # Check wallet limits if provided
        if wallet:
            if wallet.can_spend(amount):
                checks_passed.append("wallet_limit")
            else:
                checks_failed.append("wallet_limit")
                return PolicyResult(
                    approved=False,
                    reason="Wallet spending limit exceeded",
                    checks_passed=checks_passed,
                    checks_failed=checks_failed,
                )
        
        return PolicyResult(
            approved=True,
            reason="All policy checks passed",
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )
    
    def _check_destination_pattern(self, destination: str, patterns: Set[str]) -> bool:
        """Check if destination matches any pattern (supports wildcards)."""
        for pattern in patterns:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if destination.startswith(prefix):
                    return True
            elif destination == pattern:
                return True
        return False
    
    def __repr__(self) -> str:
        return f"Policy(max_per_tx={self.max_per_tx})"
