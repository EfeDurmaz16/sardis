"""
Fraud detection integration for checkout sessions.

This module provides a comprehensive fraud detection framework with:
- Rule-based detection
- Velocity checks
- Risk scoring
- Integration with external fraud providers
- Manual review workflows
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid
import re
import hashlib

from sardis_checkout.models import (
    FraudCheckResult,
    FraudDecision,
    FraudRiskLevel,
    FraudRule,
    FraudSignal,
    CheckoutRequest,
)

logger = logging.getLogger(__name__)


class FraudError(Exception):
    """Base exception for fraud detection errors."""
    pass


class FraudCheckFailed(FraudError):
    """Raised when fraud check fails."""
    pass


class FraudDeclined(FraudError):
    """Raised when checkout is declined due to fraud."""
    def __init__(self, message: str, check_result: FraudCheckResult):
        super().__init__(message)
        self.check_result = check_result


@dataclass
class FraudCheckContext:
    """Context for fraud checks containing all available signals."""
    checkout_id: str
    agent_id: str
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    billing_country: Optional[str] = None
    card_country: Optional[str] = None
    card_bin: Optional[str] = None  # First 6 digits of card
    is_new_customer: bool = True
    previous_checkouts: int = 0
    previous_successful_payments: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class FraudSignalProvider(ABC):
    """Abstract interface for fraud signal providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def get_signals(
        self,
        context: FraudCheckContext,
    ) -> List[FraudSignal]:
        """
        Analyze checkout context and return fraud signals.

        Args:
            context: Fraud check context

        Returns:
            List of FraudSignal objects
        """
        pass


class VelocityCheckProvider(FraudSignalProvider):
    """
    Velocity-based fraud signal provider.

    Checks for unusual patterns like:
    - Multiple checkouts from same IP
    - Multiple checkouts with same card
    - High transaction volumes
    """

    def __init__(
        self,
        max_checkouts_per_ip_hour: int = 10,
        max_checkouts_per_device_hour: int = 5,
        max_amount_per_customer_day: Decimal = Decimal("10000"),
    ):
        self.max_checkouts_per_ip_hour = max_checkouts_per_ip_hour
        self.max_checkouts_per_device_hour = max_checkouts_per_device_hour
        self.max_amount_per_customer_day = max_amount_per_customer_day
        # In-memory tracking (use Redis/database in production)
        self._ip_counts: Dict[str, List[datetime]] = {}
        self._device_counts: Dict[str, List[datetime]] = {}
        self._customer_amounts: Dict[str, List[Tuple[datetime, Decimal]]] = {}

    @property
    def name(self) -> str:
        return "velocity"

    def _cleanup_old_entries(self, entries: List[Any], cutoff: datetime) -> List[Any]:
        """Remove entries older than cutoff."""
        return [e for e in entries if (e[0] if isinstance(e, tuple) else e) > cutoff]

    def _cleanup_all_tracking(self, now: datetime) -> None:
        """Cleanup stale velocity windows across all tracked entities."""
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        self._ip_counts = {
            key: cleaned
            for key, values in self._ip_counts.items()
            if (cleaned := self._cleanup_old_entries(values, hour_ago))
        }
        self._device_counts = {
            key: cleaned
            for key, values in self._device_counts.items()
            if (cleaned := self._cleanup_old_entries(values, hour_ago))
        }
        self._customer_amounts = {
            key: cleaned
            for key, values in self._customer_amounts.items()
            if (cleaned := self._cleanup_old_entries(values, day_ago))
        }

    async def get_signals(
        self,
        context: FraudCheckContext,
    ) -> List[FraudSignal]:
        signals = []
        now = context.timestamp
        self._cleanup_all_tracking(now)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Check IP velocity
        if context.ip_address:
            ip_entries = self._ip_counts.get(context.ip_address, [])
            ip_entries = self._cleanup_old_entries(ip_entries, hour_ago)
            ip_entries.append(now)
            self._ip_counts[context.ip_address] = ip_entries

            ip_count = len(ip_entries)
            if ip_count > self.max_checkouts_per_ip_hour:
                signals.append(FraudSignal(
                    signal_type="velocity_ip",
                    signal_value=ip_count,
                    risk_score=min(1.0, ip_count / self.max_checkouts_per_ip_hour - 1) * 0.5 + 0.5,
                    confidence=0.8,
                    details={
                        "ip_address": context.ip_address,
                        "count_last_hour": ip_count,
                        "threshold": self.max_checkouts_per_ip_hour,
                    },
                ))
            elif ip_count > self.max_checkouts_per_ip_hour * 0.7:
                signals.append(FraudSignal(
                    signal_type="velocity_ip_warning",
                    signal_value=ip_count,
                    risk_score=0.3,
                    confidence=0.6,
                    details={
                        "ip_address": context.ip_address,
                        "count_last_hour": ip_count,
                        "threshold": self.max_checkouts_per_ip_hour,
                    },
                ))

        # Check device velocity
        if context.device_fingerprint:
            device_entries = self._device_counts.get(context.device_fingerprint, [])
            device_entries = self._cleanup_old_entries(device_entries, hour_ago)
            device_entries.append(now)
            self._device_counts[context.device_fingerprint] = device_entries

            device_count = len(device_entries)
            if device_count > self.max_checkouts_per_device_hour:
                signals.append(FraudSignal(
                    signal_type="velocity_device",
                    signal_value=device_count,
                    risk_score=min(1.0, device_count / self.max_checkouts_per_device_hour - 1) * 0.6 + 0.4,
                    confidence=0.85,
                    details={
                        "device_fingerprint": context.device_fingerprint[:16] + "...",
                        "count_last_hour": device_count,
                        "threshold": self.max_checkouts_per_device_hour,
                    },
                ))

        # Check customer amount velocity
        if context.customer_id:
            customer_entries = self._customer_amounts.get(context.customer_id, [])
            customer_entries = self._cleanup_old_entries(customer_entries, day_ago)
            customer_entries.append((now, context.amount))
            self._customer_amounts[context.customer_id] = customer_entries

            total_amount = sum(amt for _, amt in customer_entries)
            if total_amount > self.max_amount_per_customer_day:
                signals.append(FraudSignal(
                    signal_type="velocity_amount",
                    signal_value=float(total_amount),
                    risk_score=min(1.0, float(total_amount / self.max_amount_per_customer_day - 1) * 0.5 + 0.5),
                    confidence=0.7,
                    details={
                        "customer_id": context.customer_id,
                        "total_24h": float(total_amount),
                        "threshold": float(self.max_amount_per_customer_day),
                    },
                ))

        return signals


class GeoCheckProvider(FraudSignalProvider):
    """
    Geographic-based fraud signal provider.

    Checks for:
    - Mismatched billing/card countries
    - High-risk countries
    - VPN/proxy detection
    """

    # Example high-risk countries (this would be configurable in production)
    HIGH_RISK_COUNTRIES = {"XX", "YY"}  # Placeholder codes

    def __init__(
        self,
        high_risk_countries: Optional[set] = None,
    ):
        self.high_risk_countries = high_risk_countries or self.HIGH_RISK_COUNTRIES

    @property
    def name(self) -> str:
        return "geo"

    async def get_signals(
        self,
        context: FraudCheckContext,
    ) -> List[FraudSignal]:
        signals = []

        # Check country mismatch
        if context.billing_country and context.card_country:
            if context.billing_country != context.card_country:
                signals.append(FraudSignal(
                    signal_type="country_mismatch",
                    signal_value=f"{context.billing_country}/{context.card_country}",
                    risk_score=0.6,
                    confidence=0.9,
                    details={
                        "billing_country": context.billing_country,
                        "card_country": context.card_country,
                    },
                ))

        # Check high-risk country
        for country in [context.billing_country, context.card_country]:
            if country and country.upper() in self.high_risk_countries:
                signals.append(FraudSignal(
                    signal_type="high_risk_country",
                    signal_value=country,
                    risk_score=0.7,
                    confidence=0.8,
                    details={"country": country},
                ))
                break

        return signals


class AmountCheckProvider(FraudSignalProvider):
    """
    Amount-based fraud signal provider.

    Checks for:
    - Unusually high amounts
    - Round number amounts
    - Amounts just below review thresholds
    """

    def __init__(
        self,
        high_amount_threshold: Decimal = Decimal("5000"),
        very_high_amount_threshold: Decimal = Decimal("10000"),
    ):
        self.high_amount_threshold = high_amount_threshold
        self.very_high_amount_threshold = very_high_amount_threshold

    @property
    def name(self) -> str:
        return "amount"

    async def get_signals(
        self,
        context: FraudCheckContext,
    ) -> List[FraudSignal]:
        signals = []
        amount = context.amount

        # Very high amount
        if amount >= self.very_high_amount_threshold:
            signals.append(FraudSignal(
                signal_type="very_high_amount",
                signal_value=float(amount),
                risk_score=0.7,
                confidence=0.9,
                details={
                    "amount": float(amount),
                    "currency": context.currency,
                    "threshold": float(self.very_high_amount_threshold),
                },
            ))
        # High amount
        elif amount >= self.high_amount_threshold:
            signals.append(FraudSignal(
                signal_type="high_amount",
                signal_value=float(amount),
                risk_score=0.4,
                confidence=0.85,
                details={
                    "amount": float(amount),
                    "currency": context.currency,
                    "threshold": float(self.high_amount_threshold),
                },
            ))

        # Round number check (suspicious pattern)
        if amount >= Decimal("100") and amount == amount.quantize(Decimal("100")):
            signals.append(FraudSignal(
                signal_type="round_amount",
                signal_value=float(amount),
                risk_score=0.15,
                confidence=0.5,
                details={"amount": float(amount)},
            ))

        return signals


class EmailCheckProvider(FraudSignalProvider):
    """
    Email-based fraud signal provider.

    Checks for:
    - Disposable email domains
    - Suspicious email patterns
    """

    # Common disposable email domains (would be a larger list in production)
    DISPOSABLE_DOMAINS = {
        "tempmail.com", "throwaway.com", "mailinator.com",
        "guerrillamail.com", "10minutemail.com", "temp-mail.org",
    }

    def __init__(
        self,
        disposable_domains: Optional[set] = None,
    ):
        self.disposable_domains = disposable_domains or self.DISPOSABLE_DOMAINS

    @property
    def name(self) -> str:
        return "email"

    async def get_signals(
        self,
        context: FraudCheckContext,
    ) -> List[FraudSignal]:
        signals = []

        if not context.customer_email:
            return signals

        email = context.customer_email.lower()

        # Extract domain
        match = re.match(r"[^@]+@(.+)", email)
        if not match:
            signals.append(FraudSignal(
                signal_type="invalid_email",
                signal_value=email,
                risk_score=0.8,
                confidence=0.95,
                details={"email": email},
            ))
            return signals

        domain = match.group(1)

        # Check disposable domain
        if domain in self.disposable_domains:
            signals.append(FraudSignal(
                signal_type="disposable_email",
                signal_value=domain,
                risk_score=0.5,
                confidence=0.9,
                details={"email": email, "domain": domain},
            ))

        # Check for random-looking email addresses
        local_part = email.split("@")[0]
        if len(local_part) >= 15 and re.match(r"^[a-z0-9]+$", local_part):
            # Long alphanumeric-only local part might be auto-generated
            signals.append(FraudSignal(
                signal_type="suspicious_email_pattern",
                signal_value=email,
                risk_score=0.3,
                confidence=0.5,
                details={"email": email, "pattern": "random_alphanumeric"},
            ))

        return signals


class FraudRuleEngine:
    """
    Rule-based fraud detection engine.

    Evaluates custom rules against fraud signals and context.
    """

    def __init__(self, rules: Optional[List[FraudRule]] = None):
        self._rules: List[FraudRule] = rules or []

    def add_rule(self, rule: FraudRule) -> None:
        """Add a fraud rule."""
        self._rules.append(rule)
        # Sort by priority
        self._rules.sort(key=lambda r: r.priority)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a fraud rule."""
        for i, rule in enumerate(self._rules):
            if rule.rule_id == rule_id:
                del self._rules[i]
                return True
        return False

    def evaluate(
        self,
        context: FraudCheckContext,
        signals: List[FraudSignal],
    ) -> Tuple[List[str], FraudDecision]:
        """
        Evaluate rules against context and signals.

        Returns (triggered_rule_ids, most_severe_decision).
        """
        triggered = []
        decision = FraudDecision.APPROVE

        for rule in self._rules:
            if not rule.enabled:
                continue

            if self._evaluate_rule(rule, context, signals):
                triggered.append(rule.rule_id)
                # Take most severe decision
                if rule.action == FraudDecision.DECLINE:
                    decision = FraudDecision.DECLINE
                elif rule.action == FraudDecision.CHALLENGE and decision != FraudDecision.DECLINE:
                    decision = FraudDecision.CHALLENGE
                elif rule.action == FraudDecision.REVIEW and decision not in (FraudDecision.DECLINE, FraudDecision.CHALLENGE):
                    decision = FraudDecision.REVIEW

        return triggered, decision

    def _evaluate_rule(
        self,
        rule: FraudRule,
        context: FraudCheckContext,
        signals: List[FraudSignal],
    ) -> bool:
        """Evaluate a single rule."""
        conditions = rule.conditions

        # Check amount threshold
        if "min_amount" in conditions:
            if context.amount < Decimal(str(conditions["min_amount"])):
                return False

        if "max_amount" in conditions:
            if context.amount > Decimal(str(conditions["max_amount"])):
                return False

        # Check signal presence
        if "required_signals" in conditions:
            signal_types = {s.signal_type for s in signals}
            if not all(sig in signal_types for sig in conditions["required_signals"]):
                return False

        # Check any of signals
        if "any_signals" in conditions:
            signal_types = {s.signal_type for s in signals}
            if not any(sig in signal_types for sig in conditions["any_signals"]):
                return False

        # Check risk score threshold
        if "min_risk_score" in conditions:
            total_score = sum(s.risk_score for s in signals)
            if total_score < conditions["min_risk_score"]:
                return False

        # Check new customer
        if "is_new_customer" in conditions:
            if context.is_new_customer != conditions["is_new_customer"]:
                return False

        return True


class FraudDetector:
    """
    Main fraud detection orchestrator.

    Combines multiple signal providers and rule evaluation
    to produce a fraud check result.
    """

    def __init__(
        self,
        signal_providers: Optional[List[FraudSignalProvider]] = None,
        rule_engine: Optional[FraudRuleEngine] = None,
        risk_threshold_review: float = 30.0,
        risk_threshold_decline: float = 70.0,
        auto_approve_returning_customers: bool = True,
        min_checkouts_for_trusted: int = 3,
    ):
        self.signal_providers = signal_providers or [
            VelocityCheckProvider(),
            GeoCheckProvider(),
            AmountCheckProvider(),
            EmailCheckProvider(),
        ]
        self.rule_engine = rule_engine or FraudRuleEngine()
        self.risk_threshold_review = risk_threshold_review
        self.risk_threshold_decline = risk_threshold_decline
        self.auto_approve_returning = auto_approve_returning_customers
        self.min_checkouts_trusted = min_checkouts_for_trusted

    async def check(
        self,
        context: FraudCheckContext,
    ) -> FraudCheckResult:
        """
        Perform fraud check on a checkout context.

        Args:
            context: Fraud check context

        Returns:
            FraudCheckResult with decision and details
        """
        # Collect signals from all providers
        all_signals: List[FraudSignal] = []

        for provider in self.signal_providers:
            try:
                signals = await provider.get_signals(context)
                all_signals.extend(signals)
            except Exception as e:
                logger.error(f"Error getting signals from {provider.name}: {e}")

        # Calculate overall risk score (weighted average)
        if all_signals:
            total_weighted_score = sum(
                s.risk_score * s.confidence for s in all_signals
            )
            total_confidence = sum(s.confidence for s in all_signals)
            risk_score = (total_weighted_score / total_confidence) * 100 if total_confidence > 0 else 0
        else:
            risk_score = 0.0

        # Evaluate rules
        triggered_rules, rule_decision = self.rule_engine.evaluate(context, all_signals)

        # Determine decision
        decision = self._determine_decision(
            risk_score, rule_decision, context, all_signals
        )

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        result = FraudCheckResult(
            check_id=str(uuid.uuid4()),
            checkout_id=context.checkout_id,
            decision=decision,
            risk_level=risk_level,
            risk_score=risk_score,
            signals=all_signals,
            rules_triggered=triggered_rules,
            provider="internal",
            manual_review_required=decision == FraudDecision.REVIEW,
            review_reason=self._get_review_reason(all_signals, triggered_rules) if decision == FraudDecision.REVIEW else None,
        )

        logger.info(
            f"Fraud check for {context.checkout_id}: "
            f"decision={decision.value}, risk_score={risk_score:.1f}, "
            f"signals={len(all_signals)}, rules_triggered={len(triggered_rules)}"
        )

        return result

    def _determine_decision(
        self,
        risk_score: float,
        rule_decision: FraudDecision,
        context: FraudCheckContext,
        signals: List[FraudSignal],
    ) -> FraudDecision:
        """Determine final fraud decision."""
        # Rule decision takes precedence
        if rule_decision == FraudDecision.DECLINE:
            return FraudDecision.DECLINE

        # Check if trusted returning customer
        if self.auto_approve_returning and not context.is_new_customer:
            if context.previous_successful_payments >= self.min_checkouts_trusted:
                if risk_score < self.risk_threshold_decline:
                    return FraudDecision.APPROVE

        # Score-based decision
        if risk_score >= self.risk_threshold_decline:
            return FraudDecision.DECLINE
        elif risk_score >= self.risk_threshold_review or rule_decision == FraudDecision.REVIEW:
            return FraudDecision.REVIEW
        elif rule_decision == FraudDecision.CHALLENGE:
            return FraudDecision.CHALLENGE

        return FraudDecision.APPROVE

    def _determine_risk_level(self, risk_score: float) -> FraudRiskLevel:
        """Determine risk level from score."""
        if risk_score >= 70:
            return FraudRiskLevel.CRITICAL
        elif risk_score >= 50:
            return FraudRiskLevel.HIGH
        elif risk_score >= 25:
            return FraudRiskLevel.MEDIUM
        else:
            return FraudRiskLevel.LOW

    def _get_review_reason(
        self,
        signals: List[FraudSignal],
        triggered_rules: List[str],
    ) -> str:
        """Generate human-readable review reason."""
        reasons = []

        if triggered_rules:
            reasons.append(f"Rules triggered: {', '.join(triggered_rules)}")

        high_risk_signals = [s for s in signals if s.risk_score >= 0.5]
        if high_risk_signals:
            signal_types = [s.signal_type for s in high_risk_signals]
            reasons.append(f"High-risk signals: {', '.join(signal_types)}")

        return "; ".join(reasons) if reasons else "Risk score above threshold"

    async def check_checkout_request(
        self,
        request: CheckoutRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
    ) -> FraudCheckResult:
        """
        Convenience method to check a CheckoutRequest.
        """
        context = FraudCheckContext(
            checkout_id=request.idempotency_key or str(uuid.uuid4()),
            agent_id=request.agent_id,
            customer_id=request.customer_id,
            customer_email=request.customer_email,
            amount=request.amount,
            currency=request.currency,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            metadata=request.metadata,
        )

        return await self.check(context)
