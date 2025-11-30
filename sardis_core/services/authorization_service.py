"""
Authorization service for spending control enforcement.

Provides:
- Policy management per agent
- Payment authorization checks
- Merchant allowlist/denylist management
- Trust level upgrades
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import threading

from sardis_core.models.spending_policy import (
    SpendingPolicy,
    TrustLevel,
    SpendingScope,
    MerchantRule,
    TimeWindowLimit,
    create_default_policy,
)


@dataclass
class AuthorizationResult:
    """Result of an authorization check."""
    authorized: bool
    reason: str
    policy_id: Optional[str] = None
    requires_review: bool = False
    
    @classmethod
    def allowed(cls, policy_id: str) -> "AuthorizationResult":
        return cls(authorized=True, reason="OK", policy_id=policy_id)
    
    @classmethod
    def denied(cls, reason: str, policy_id: Optional[str] = None) -> "AuthorizationResult":
        return cls(authorized=False, reason=reason, policy_id=policy_id)
    
    @classmethod
    def needs_review(cls, reason: str, policy_id: Optional[str] = None) -> "AuthorizationResult":
        return cls(authorized=False, reason=reason, policy_id=policy_id, requires_review=True)


class AuthorizationService:
    """
    Service for managing spending policies and authorizing payments.
    
    This is the central point for all spending authorization decisions.
    It integrates with the payment service to enforce policies.
    """
    
    def __init__(self):
        """Initialize the authorization service."""
        self._lock = threading.RLock()
        
        # Policy storage: agent_id -> SpendingPolicy
        self._policies: dict[str, SpendingPolicy] = {}
    
    # ==================== Policy Management ====================
    
    def create_policy(
        self,
        agent_id: str,
        trust_level: TrustLevel = TrustLevel.LOW,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        daily_limit: Optional[Decimal] = None,
        weekly_limit: Optional[Decimal] = None,
        monthly_limit: Optional[Decimal] = None,
    ) -> SpendingPolicy:
        """
        Create a spending policy for an agent.
        
        Uses default values based on trust level unless overridden.
        """
        with self._lock:
            # Start with default policy for trust level
            policy = create_default_policy(agent_id, trust_level)
            
            # Override with custom values if provided
            if limit_per_tx is not None:
                policy.limit_per_tx = limit_per_tx
            if limit_total is not None:
                policy.limit_total = limit_total
            if daily_limit is not None:
                policy.daily_limit = TimeWindowLimit(
                    window_type="daily",
                    limit_amount=daily_limit,
                )
            if weekly_limit is not None:
                policy.weekly_limit = TimeWindowLimit(
                    window_type="weekly",
                    limit_amount=weekly_limit,
                )
            if monthly_limit is not None:
                policy.monthly_limit = TimeWindowLimit(
                    window_type="monthly",
                    limit_amount=monthly_limit,
                )
            
            self._policies[agent_id] = policy
            return policy
    
    def get_policy(self, agent_id: str) -> Optional[SpendingPolicy]:
        """Get the spending policy for an agent."""
        return self._policies.get(agent_id)
    
    def get_or_create_policy(
        self,
        agent_id: str,
        trust_level: TrustLevel = TrustLevel.LOW
    ) -> SpendingPolicy:
        """Get existing policy or create a default one."""
        with self._lock:
            if agent_id not in self._policies:
                return self.create_policy(agent_id, trust_level)
            return self._policies[agent_id]
    
    def update_policy(
        self,
        agent_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        daily_limit: Optional[Decimal] = None,
        trust_level: Optional[TrustLevel] = None,
        require_preauth: Optional[bool] = None,
    ) -> Optional[SpendingPolicy]:
        """Update an existing policy."""
        with self._lock:
            policy = self._policies.get(agent_id)
            if not policy:
                return None
            
            if limit_per_tx is not None:
                policy.limit_per_tx = limit_per_tx
            if limit_total is not None:
                policy.limit_total = limit_total
            if daily_limit is not None:
                if policy.daily_limit:
                    policy.daily_limit.limit_amount = daily_limit
                else:
                    policy.daily_limit = TimeWindowLimit(
                        window_type="daily",
                        limit_amount=daily_limit,
                    )
            if trust_level is not None:
                policy.trust_level = trust_level
            if require_preauth is not None:
                policy.require_preauth = require_preauth
            
            policy.updated_at = datetime.now(timezone.utc)
            return policy
    
    def delete_policy(self, agent_id: str) -> bool:
        """Delete an agent's policy."""
        with self._lock:
            if agent_id in self._policies:
                del self._policies[agent_id]
                return True
            return False
    
    # ==================== Authorization ====================
    
    def authorize_payment(
        self,
        agent_id: str,
        amount: Decimal,
        fee: Decimal = Decimal("0"),
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        scope: SpendingScope = SpendingScope.ALL
    ) -> AuthorizationResult:
        """
        Check if a payment is authorized by the agent's policy.
        
        This should be called before processing any payment.
        """
        with self._lock:
            policy = self._policies.get(agent_id)
            
            if not policy:
                # No policy = use most restrictive defaults
                policy = create_default_policy(agent_id, TrustLevel.LOW)
                self._policies[agent_id] = policy
            
            # Check if pre-auth is required
            if policy.require_preauth:
                return AuthorizationResult.needs_review(
                    "Policy requires pre-authorization",
                    policy.policy_id
                )
            
            # Validate against policy
            allowed, reason = policy.validate_payment(
                amount=amount,
                fee=fee,
                merchant_id=merchant_id,
                merchant_category=merchant_category,
                scope=scope,
            )
            
            if allowed:
                return AuthorizationResult.allowed(policy.policy_id)
            else:
                return AuthorizationResult.denied(reason, policy.policy_id)
    
    def record_spend(self, agent_id: str, amount: Decimal) -> None:
        """Record a successful spend against the policy."""
        with self._lock:
            policy = self._policies.get(agent_id)
            if policy:
                policy.record_spend(amount)
    
    # ==================== Merchant Rules ====================
    
    def add_to_allowlist(
        self,
        agent_id: str,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        max_per_tx: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Optional[MerchantRule]:
        """Add a merchant or category to the agent's allowlist."""
        with self._lock:
            policy = self._policies.get(agent_id)
            if not policy:
                return None
            
            return policy.add_merchant_allow(
                merchant_id=merchant_id,
                category=category,
                max_per_tx=max_per_tx,
                reason=reason,
            )
    
    def add_to_denylist(
        self,
        agent_id: str,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[MerchantRule]:
        """Add a merchant or category to the agent's denylist."""
        with self._lock:
            policy = self._policies.get(agent_id)
            if not policy:
                return None
            
            return policy.add_merchant_deny(
                merchant_id=merchant_id,
                category=category,
                reason=reason,
                expires_at=expires_at,
            )
    
    def remove_rule(self, agent_id: str, rule_id: str) -> bool:
        """Remove a merchant rule."""
        with self._lock:
            policy = self._policies.get(agent_id)
            if not policy:
                return False
            return policy.remove_rule(rule_id)
    
    def list_rules(self, agent_id: str) -> list[MerchantRule]:
        """List all merchant rules for an agent."""
        policy = self._policies.get(agent_id)
        if not policy:
            return []
        return list(policy.merchant_rules)
    
    # ==================== Trust Level Management ====================
    
    def upgrade_trust_level(
        self,
        agent_id: str,
        new_level: TrustLevel,
        reason: Optional[str] = None
    ) -> Optional[SpendingPolicy]:
        """
        Upgrade an agent's trust level.
        
        This increases their default limits.
        """
        with self._lock:
            policy = self._policies.get(agent_id)
            if not policy:
                return None
            
            if new_level.value <= policy.trust_level.value:
                return policy  # Can't downgrade with this method
            
            # Get new limits for the trust level
            new_defaults = create_default_policy(agent_id, new_level)
            
            # Update limits (only increase, never decrease)
            policy.trust_level = new_level
            policy.limit_per_tx = max(policy.limit_per_tx, new_defaults.limit_per_tx)
            policy.limit_total = max(policy.limit_total, new_defaults.limit_total)
            
            if new_defaults.daily_limit:
                if policy.daily_limit:
                    policy.daily_limit.limit_amount = max(
                        policy.daily_limit.limit_amount,
                        new_defaults.daily_limit.limit_amount
                    )
                else:
                    policy.daily_limit = new_defaults.daily_limit
            
            policy.updated_at = datetime.now(timezone.utc)
            return policy
    
    def downgrade_trust_level(
        self,
        agent_id: str,
        new_level: TrustLevel,
        reason: Optional[str] = None
    ) -> Optional[SpendingPolicy]:
        """
        Downgrade an agent's trust level.
        
        This decreases their limits.
        """
        with self._lock:
            policy = self._policies.get(agent_id)
            if not policy:
                return None
            
            # Get new limits for the trust level
            new_defaults = create_default_policy(agent_id, new_level)
            
            # Update to new lower limits
            policy.trust_level = new_level
            policy.limit_per_tx = new_defaults.limit_per_tx
            policy.limit_total = new_defaults.limit_total
            policy.daily_limit = new_defaults.daily_limit
            policy.weekly_limit = new_defaults.weekly_limit
            policy.monthly_limit = new_defaults.monthly_limit
            
            policy.updated_at = datetime.now(timezone.utc)
            return policy
    
    # ==================== Reporting ====================
    
    def get_spending_summary(self, agent_id: str) -> Optional[dict]:
        """Get a summary of an agent's spending status."""
        policy = self._policies.get(agent_id)
        if not policy:
            return None
        
        summary = {
            "agent_id": agent_id,
            "trust_level": policy.trust_level.value,
            "limits": {
                "per_transaction": str(policy.limit_per_tx),
                "total": str(policy.limit_total),
                "daily": str(policy.daily_limit.limit_amount) if policy.daily_limit else None,
                "weekly": str(policy.weekly_limit.limit_amount) if policy.weekly_limit else None,
                "monthly": str(policy.monthly_limit.limit_amount) if policy.monthly_limit else None,
            },
            "spent": {
                "total": str(policy.spent_total),
                "daily": str(policy.daily_limit.current_spent) if policy.daily_limit else None,
                "weekly": str(policy.weekly_limit.current_spent) if policy.weekly_limit else None,
                "monthly": str(policy.monthly_limit.current_spent) if policy.monthly_limit else None,
            },
            "remaining": {
                "total": str(policy.remaining_total()),
                "daily": str(policy.remaining_daily()) if policy.daily_limit else None,
            },
            "merchant_rules_count": len(policy.merchant_rules),
            "allowed_scopes": [s.value for s in policy.allowed_scopes],
            "require_preauth": policy.require_preauth,
        }
        
        return summary


# Global authorization service instance
_auth_service: Optional[AuthorizationService] = None


def get_authorization_service() -> AuthorizationService:
    """Get the global authorization service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthorizationService()
    return _auth_service

