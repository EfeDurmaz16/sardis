"""Risk scoring and fraud prevention service."""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
import threading

from sardis_core.models.risk import (
    RiskScore,
    RiskLevel,
    RiskFactor,
    AgentRiskProfile
)


class RiskDecision(str, Enum):
    """Decision from risk evaluation."""
    APPROVE = "approve"
    DENY = "deny"
    REVIEW = "review"


@dataclass
class RiskEvaluation:
    """Complete risk evaluation result."""
    decision: RiskDecision
    score: float
    factors: list[str]
    details: dict
    rule_results: list[dict]  # Results from individual rules
    
    @classmethod
    def approve(cls, score: float, factors: list, details: dict, rule_results: list):
        return cls(RiskDecision.APPROVE, score, factors, details, rule_results)
    
    @classmethod
    def deny(cls, score: float, factors: list, details: dict, rule_results: list):
        return cls(RiskDecision.DENY, score, factors, details, rule_results)
    
    @classmethod
    def review(cls, score: float, factors: list, details: dict, rule_results: list):
        return cls(RiskDecision.REVIEW, score, factors, details, rule_results)


@dataclass
class RiskConfig:
    """Configuration for risk scoring."""
    
    # Velocity limits
    max_transactions_per_hour: int = 20
    max_transactions_per_day: int = 100
    
    # Amount thresholds
    large_transaction_threshold: Decimal = Decimal("100.00")
    very_large_transaction_threshold: Decimal = Decimal("500.00")
    
    # Age thresholds (in hours)
    new_wallet_age_hours: int = 24
    
    # Score weights
    velocity_weight: float = 20.0
    amount_weight: float = 15.0
    new_wallet_weight: float = 10.0
    failed_tx_weight: float = 25.0
    
    # Thresholds
    block_threshold: float = 90.0  # Block transactions above this score
    alert_threshold: float = 70.0  # Send alerts above this score
    review_threshold: float = 50.0  # Flag for review above this score
    
    # Rule weights (for modular engine)
    rule_weights: dict = None
    
    def __post_init__(self):
        if self.rule_weights is None:
            self.rule_weights = {
                "velocity": 1.5,
                "amount_anomaly": 1.2,
                "merchant_reputation": 1.0,
                "behavior_fingerprint": 1.0,
                "failure_pattern": 1.3,
            }


class RiskService:
    """
    Service for assessing and managing risk.
    
    Provides:
    - Transaction risk scoring (via modular rules engine)
    - Agent risk profiling
    - Fraud prevention checks
    - Service authorization
    
    Uses modular rules that can be configured and weighted independently.
    """
    
    def __init__(self, config: Optional[RiskConfig] = None, enable_modular_rules: bool = True):
        """Initialize the risk service."""
        self.config = config or RiskConfig()
        self._profiles: dict[str, AgentRiskProfile] = {}
        self._lock = threading.RLock()
        self._enable_modular_rules = enable_modular_rules
        
        # Initialize modular rules if enabled
        self._rules = []
        if enable_modular_rules:
            self._init_modular_rules()
    
    def _init_modular_rules(self):
        """Initialize the modular risk rules."""
        try:
            from .risk_rules import (
                VelocityRule,
                AmountAnomalyRule,
                MerchantReputationRule,
                BehaviorFingerprintRule,
                FailurePatternRule,
            )
            
            weights = self.config.rule_weights
            
            self._rules = [
                VelocityRule(weight=weights.get("velocity", 1.5)),
                AmountAnomalyRule(weight=weights.get("amount_anomaly", 1.2)),
                MerchantReputationRule(weight=weights.get("merchant_reputation", 1.0)),
                BehaviorFingerprintRule(weight=weights.get("behavior_fingerprint", 1.0)),
                FailurePatternRule(weight=weights.get("failure_pattern", 1.3)),
            ]
        except ImportError:
            # Fallback if rules not available
            self._rules = []
    
    def get_or_create_profile(self, agent_id: str) -> AgentRiskProfile:
        """Get or create a risk profile for an agent."""
        with self._lock:
            if agent_id not in self._profiles:
                self._profiles[agent_id] = AgentRiskProfile(agent_id=agent_id)
            return self._profiles[agent_id]
    
    def get_profile(self, agent_id: str) -> Optional[AgentRiskProfile]:
        """Get a risk profile by agent ID."""
        return self._profiles.get(agent_id)
    
    def assess_transaction(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_id: str,
        wallet_created_at: datetime
    ) -> RiskScore:
        """
        Assess the risk of a proposed transaction.
        
        Args:
            agent_id: The agent making the transaction
            amount: Transaction amount
            recipient_id: Recipient wallet/merchant ID
            wallet_created_at: When the agent's wallet was created
            
        Returns:
            RiskScore with assessment details
        """
        profile = self.get_or_create_profile(agent_id)
        
        score = 0.0
        factors = []
        details = {}
        
        # Check velocity (transactions per hour)
        if profile.transactions_last_hour >= self.config.max_transactions_per_hour:
            score += self.config.velocity_weight
            factors.append(RiskFactor.HIGH_VELOCITY)
            details["velocity"] = f"{profile.transactions_last_hour} transactions in last hour"
        
        # Check transaction amount
        if amount >= self.config.very_large_transaction_threshold:
            score += self.config.amount_weight * 2
            factors.append(RiskFactor.LARGE_AMOUNT)
            details["amount"] = f"Very large transaction: {amount}"
        elif amount >= self.config.large_transaction_threshold:
            score += self.config.amount_weight
            factors.append(RiskFactor.LARGE_AMOUNT)
            details["amount"] = f"Large transaction: {amount}"
        
        # Check wallet age
        wallet_age = datetime.now(timezone.utc) - wallet_created_at.replace(tzinfo=timezone.utc)
        if wallet_age < timedelta(hours=self.config.new_wallet_age_hours):
            score += self.config.new_wallet_weight
            factors.append(RiskFactor.NEW_WALLET)
            details["wallet_age"] = f"Wallet is {wallet_age.total_seconds() / 3600:.1f} hours old"
        
        # Check failed transaction ratio
        if profile.total_transactions > 5:
            fail_ratio = profile.failed_transactions / profile.total_transactions
            if fail_ratio > 0.3:
                score += self.config.failed_tx_weight
                factors.append(RiskFactor.FAILED_ATTEMPTS)
                details["failures"] = f"{fail_ratio:.0%} transaction failure rate"
        
        # Check if amount is unusual compared to history
        if profile.total_transactions > 10:
            avg = profile.average_transaction_amount
            if avg > 0 and amount > avg * 5:
                score += 15.0
                factors.append(RiskFactor.PATTERN_ANOMALY)
                details["pattern"] = f"Amount is {amount / avg:.1f}x the average"
        
        # Check service authorization
        if not profile.is_service_authorized(recipient_id):
            score += 10.0
            factors.append(RiskFactor.UNAUTHORIZED_SERVICE)
            details["authorization"] = f"Service {recipient_id} not pre-authorized"
        
        # Cap score at 100
        score = min(score, 100.0)
        
        return RiskScore.from_score(score, factors, details)
    
    def evaluate(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        merchant_category: Optional[str] = None,
        wallet_created_at: Optional[datetime] = None
    ) -> RiskEvaluation:
        """
        Evaluate a payment using the modular rules engine.
        
        This is the primary entry point for the new risk engine.
        It runs all configured rules and aggregates their results.
        
        Args:
            agent_id: Agent making the payment
            amount: Transaction amount
            recipient_id: Wallet receiving the payment
            merchant_id: Optional merchant ID
            merchant_category: Optional merchant category
            wallet_created_at: When agent's wallet was created
            
        Returns:
            RiskEvaluation with decision and detailed breakdown
        """
        profile = self.get_or_create_profile(agent_id)
        
        # Build payment context for rules
        from .risk_rules.base import PaymentContext, RiskAction
        
        context = PaymentContext(
            agent_id=agent_id,
            wallet_id=f"wallet_{agent_id}",  # Simplified
            wallet_created_at=wallet_created_at,
            amount=amount,
            recipient_id=recipient_id,
            merchant_id=merchant_id,
            merchant_category=merchant_category,
            total_transactions=profile.total_transactions,
            failed_transactions=profile.failed_transactions,
            transactions_last_hour=profile.transactions_last_hour,
            transactions_last_day=profile.transactions_last_day if hasattr(profile, 'transactions_last_day') else 0,
            total_volume=profile.total_volume,
            average_transaction=profile.average_transaction_amount,
            recent_transaction_amounts=[],  # Would come from history
            recent_recipients=[],  # Would come from transaction history
        )
        
        # Run all rules
        rule_results = []
        total_weighted_score = 0.0
        total_weight = 0.0
        all_factors = []
        all_details = {}
        recommended_actions = []
        
        for rule in self._rules:
            if rule.enabled:
                result = rule.evaluate(context)
                rule_results.append({
                    "rule": result.rule_name,
                    "score": result.score,
                    "weight": result.weight,
                    "weighted_score": result.weighted_score(),
                    "factors": result.factors,
                    "triggered": result.triggered,
                    "action": result.recommended_action.value,
                })
                
                total_weighted_score += result.weighted_score()
                total_weight += result.weight
                all_factors.extend(result.factors)
                all_details[result.rule_name] = result.details
                
                if result.triggered:
                    recommended_actions.append(result.recommended_action)
        
        # Calculate final score (normalized to 0-100)
        final_score = (total_weighted_score / total_weight * 100) if total_weight > 0 else 0.0
        final_score = min(100.0, final_score)
        
        # Determine decision based on actions and thresholds
        if RiskAction.DENY in recommended_actions or final_score >= self.config.block_threshold:
            decision = RiskDecision.DENY
        elif RiskAction.REVIEW in recommended_actions or final_score >= self.config.review_threshold:
            decision = RiskDecision.REVIEW
        else:
            decision = RiskDecision.APPROVE
        
        return RiskEvaluation(
            decision=decision,
            score=final_score,
            factors=list(set(all_factors)),  # Dedupe
            details=all_details,
            rule_results=rule_results,
        )
    
    def update_rule_profiles(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        category: Optional[str] = None,
        success: bool = True
    ):
        """
        Update rule-specific profiles after a transaction.
        
        This should be called after a transaction completes
        to keep behavioral profiles up to date.
        """
        for rule in self._rules:
            rule_name = getattr(rule, 'name', '')
            
            if rule_name == 'behavior_fingerprint' and hasattr(rule, 'update_profile'):
                rule.update_profile(agent_id, amount, recipient_id, category)
            
            if rule_name == 'failure_pattern' and hasattr(rule, 'record_outcome'):
                rule.record_outcome(agent_id, success)
            
            if rule_name == 'merchant_reputation' and hasattr(rule, 'update_reputation'):
                if merchant_id:
                    rule.update_reputation(merchant_id, success)
    
    def assess_agent(self, agent_id: str) -> RiskScore:
        """
        Assess the overall risk level of an agent.
        
        Args:
            agent_id: The agent to assess
            
        Returns:
            RiskScore for the agent
        """
        profile = self.get_or_create_profile(agent_id)
        
        score = 0.0
        factors = []
        details = {}
        
        # Base score from current profile
        score = profile.current_score
        
        # Adjust based on transaction history
        if profile.total_transactions > 0:
            fail_ratio = profile.failed_transactions / profile.total_transactions
            if fail_ratio > 0.2:
                score += 20.0
                factors.append(RiskFactor.FAILED_ATTEMPTS)
                details["failures"] = f"{fail_ratio:.0%} failure rate"
        
        # Check if flagged
        if profile.is_flagged:
            score += 30.0
            details["flagged"] = profile.flag_reason or "Account flagged"
        
        # Check velocity
        if profile.transactions_last_hour > self.config.max_transactions_per_hour * 0.8:
            factors.append(RiskFactor.HIGH_VELOCITY)
            details["velocity"] = "High transaction velocity"
        
        score = min(score, 100.0)
        
        return RiskScore.from_score(score, factors, details)
    
    def record_transaction(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_id: str,
        success: bool
    ):
        """
        Record a transaction in the agent's risk profile.
        
        Args:
            agent_id: The agent that made the transaction
            amount: Transaction amount
            recipient_id: Recipient ID
            success: Whether the transaction succeeded
        """
        profile = self.get_or_create_profile(agent_id)
        
        # Update profile
        profile.update_from_transaction(amount, recipient_id, success)
        
        # Update hourly velocity (simplified - in production use time windows)
        if profile.last_transaction_at:
            time_since_last = datetime.now(timezone.utc) - profile.last_transaction_at.replace(tzinfo=timezone.utc)
            if time_since_last > timedelta(hours=1):
                profile.transactions_last_hour = 1
            else:
                profile.transactions_last_hour += 1
        else:
            profile.transactions_last_hour = 1
        
        # Update current risk score
        risk = self.assess_agent(agent_id)
        profile.current_score = risk.score
        profile.current_level = risk.level
    
    def should_block_transaction(
        self,
        agent_id: str,
        amount: Decimal,
        recipient_id: str,
        wallet_created_at: datetime
    ) -> tuple[bool, str]:
        """
        Check if a transaction should be blocked.
        
        Returns:
            Tuple of (should_block, reason)
        """
        profile = self.get_or_create_profile(agent_id)
        
        # Always block if flagged
        if profile.is_flagged:
            return True, f"Account is flagged: {profile.flag_reason}"
        
        # Assess transaction risk
        risk = self.assess_transaction(agent_id, amount, recipient_id, wallet_created_at)
        
        if risk.score >= self.config.block_threshold:
            return True, f"Risk score {risk.score:.0f} exceeds threshold. Factors: {', '.join(f.value for f in risk.factors)}"
        
        return False, ""
    
    def authorize_service(self, agent_id: str, service_id: str):
        """Authorize a service for an agent."""
        profile = self.get_or_create_profile(agent_id)
        profile.authorize_service(service_id)
    
    def revoke_service(self, agent_id: str, service_id: str) -> bool:
        """Revoke a service authorization."""
        profile = self.get_or_create_profile(agent_id)
        return profile.revoke_service(service_id)
    
    def list_authorized_services(self, agent_id: str) -> list[str]:
        """List authorized services for an agent."""
        profile = self.get_or_create_profile(agent_id)
        return profile.authorized_services.copy()
    
    def flag_agent(self, agent_id: str, reason: str):
        """Flag an agent for review."""
        profile = self.get_or_create_profile(agent_id)
        profile.flag(reason)
    
    def unflag_agent(self, agent_id: str):
        """Remove flag from an agent."""
        profile = self.get_or_create_profile(agent_id)
        profile.unflag()


# Global risk service instance
_risk_service: Optional[RiskService] = None


def get_risk_service() -> RiskService:
    """Get the global risk service instance."""
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskService()
    return _risk_service

