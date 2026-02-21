"""
Custom policy plugin for evaluating JSON-defined policy rules.

Supports time restrictions, amount limits, merchant blocklists,
and velocity limits defined as JSON rules.
"""

from datetime import datetime, time, timedelta
from typing import Any

from ..base import PolicyDecision, PolicyPlugin, PluginMetadata, PluginType


class CustomPolicyPlugin(PolicyPlugin):
    """
    Evaluate custom policy rules defined as JSON.

    Supports:
    - Time restrictions (no weekends, business hours only)
    - Amount limits per transaction
    - Merchant blocklists
    - Velocity limits (max transactions per time period)
    """

    def __init__(self):
        """Initialize custom policy plugin."""
        super().__init__()
        self._rules: list[dict[str, Any]] = []
        self._transaction_history: list[dict[str, Any]] = []

    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        return PluginMetadata(
            name="custom-policy",
            version="1.0.0",
            author="Sardis",
            description="Evaluate custom policy rules from JSON configuration",
            plugin_type=PluginType.POLICY,
            config_schema={
                "rules": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "enum": [
                                    "time_restriction",
                                    "amount_limit",
                                    "merchant_blocklist",
                                    "velocity_limit",
                                ]
                            },
                            "config": {"type": "object"},
                        },
                    },
                }
            },
        )

    async def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize plugin with policy rules.

        Args:
            config: Must contain rules list
        """
        await super().initialize(config)

        self._rules = config.get("rules", [])
        if not self._rules:
            raise ValueError("At least one rule is required for custom policy plugin")

    async def evaluate(self, transaction: dict[str, Any]) -> PolicyDecision:
        """
        Evaluate transaction against all configured rules.

        Args:
            transaction: Transaction to evaluate

        Returns:
            PolicyDecision - approved only if all rules pass
        """
        # Evaluate each rule
        for rule in self._rules:
            rule_type = rule.get("type")
            rule_config = rule.get("config", {})

            decision = await self._evaluate_rule(rule_type, rule_config, transaction)

            if not decision.approved:
                # First failure rejects the transaction
                return decision

        # All rules passed
        return PolicyDecision(
            approved=True,
            reason="All custom policy rules passed",
            plugin_name=self.metadata.name,
        )

    async def _evaluate_rule(
        self, rule_type: str, rule_config: dict[str, Any], transaction: dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate a single rule."""
        if rule_type == "time_restriction":
            return self._evaluate_time_restriction(rule_config, transaction)
        elif rule_type == "amount_limit":
            return self._evaluate_amount_limit(rule_config, transaction)
        elif rule_type == "merchant_blocklist":
            return self._evaluate_merchant_blocklist(rule_config, transaction)
        elif rule_type == "velocity_limit":
            return self._evaluate_velocity_limit(rule_config, transaction)
        else:
            return PolicyDecision(
                approved=False,
                reason=f"Unknown rule type: {rule_type}",
                plugin_name=self.metadata.name,
            )

    def _evaluate_time_restriction(
        self, config: dict[str, Any], transaction: dict[str, Any]
    ) -> PolicyDecision:
        """
        Evaluate time-based restrictions.

        Config:
            - no_weekends: bool - Reject transactions on Sat/Sun
            - business_hours_only: bool - Only allow 9am-5pm
            - allowed_days: list[int] - Allowed days (0=Mon, 6=Sun)
            - allowed_hours: dict - {start: 9, end: 17}
        """
        now = datetime.utcnow()

        # Check weekends
        if config.get("no_weekends", False):
            if now.weekday() >= 5:  # Saturday=5, Sunday=6
                return PolicyDecision(
                    approved=False,
                    reason="Transactions not allowed on weekends",
                    plugin_name=self.metadata.name,
                    metadata={"day": now.strftime("%A")},
                )

        # Check allowed days
        allowed_days = config.get("allowed_days")
        if allowed_days is not None:
            if now.weekday() not in allowed_days:
                return PolicyDecision(
                    approved=False,
                    reason=f"Transactions not allowed on {now.strftime('%A')}",
                    plugin_name=self.metadata.name,
                    metadata={"day": now.strftime("%A")},
                )

        # Check business hours
        if config.get("business_hours_only", False):
            business_start = time(9, 0)
            business_end = time(17, 0)
            current_time = now.time()

            if not (business_start <= current_time <= business_end):
                return PolicyDecision(
                    approved=False,
                    reason="Transactions only allowed during business hours (9am-5pm UTC)",
                    plugin_name=self.metadata.name,
                    metadata={"current_time": current_time.isoformat()},
                )

        # Check custom allowed hours
        allowed_hours = config.get("allowed_hours")
        if allowed_hours:
            start_hour = allowed_hours.get("start", 0)
            end_hour = allowed_hours.get("end", 23)
            current_hour = now.hour

            if not (start_hour <= current_hour <= end_hour):
                return PolicyDecision(
                    approved=False,
                    reason=f"Transactions only allowed between {start_hour}:00 and {end_hour}:00 UTC",
                    plugin_name=self.metadata.name,
                    metadata={"current_hour": current_hour},
                )

        return PolicyDecision(
            approved=True, reason="Time restriction passed", plugin_name=self.metadata.name
        )

    def _evaluate_amount_limit(
        self, config: dict[str, Any], transaction: dict[str, Any]
    ) -> PolicyDecision:
        """
        Evaluate amount limits.

        Config:
            - max_amount: float - Maximum transaction amount
            - min_amount: float - Minimum transaction amount
            - currency: str - Currency code (optional)
        """
        amount = transaction.get("amount", 0)
        currency = transaction.get("currency", "USD")

        # Check currency match if specified
        required_currency = config.get("currency")
        if required_currency and currency != required_currency:
            return PolicyDecision(
                approved=False,
                reason=f"Transaction currency {currency} does not match required {required_currency}",
                plugin_name=self.metadata.name,
                metadata={"currency": currency, "required": required_currency},
            )

        # Check max amount
        max_amount = config.get("max_amount")
        if max_amount is not None and amount > max_amount:
            return PolicyDecision(
                approved=False,
                reason=f"Amount {amount} {currency} exceeds maximum {max_amount}",
                plugin_name=self.metadata.name,
                metadata={"amount": amount, "max": max_amount, "currency": currency},
            )

        # Check min amount
        min_amount = config.get("min_amount")
        if min_amount is not None and amount < min_amount:
            return PolicyDecision(
                approved=False,
                reason=f"Amount {amount} {currency} below minimum {min_amount}",
                plugin_name=self.metadata.name,
                metadata={"amount": amount, "min": min_amount, "currency": currency},
            )

        return PolicyDecision(
            approved=True, reason="Amount limit passed", plugin_name=self.metadata.name
        )

    def _evaluate_merchant_blocklist(
        self, config: dict[str, Any], transaction: dict[str, Any]
    ) -> PolicyDecision:
        """
        Evaluate merchant blocklist.

        Config:
            - blocked_merchants: list[str] - List of blocked merchant names/IDs
            - blocked_categories: list[str] - List of blocked MCC categories
        """
        merchant = transaction.get("merchant", "")
        merchant_name = transaction.get("merchant_name", "")
        merchant_category = transaction.get("merchant_category", "")

        # Check blocked merchants
        blocked_merchants = config.get("blocked_merchants", [])
        for blocked in blocked_merchants:
            if (
                blocked.lower() in merchant.lower()
                or blocked.lower() in merchant_name.lower()
            ):
                return PolicyDecision(
                    approved=False,
                    reason=f"Merchant '{merchant_name or merchant}' is blocked",
                    plugin_name=self.metadata.name,
                    metadata={"merchant": merchant_name or merchant},
                )

        # Check blocked categories
        blocked_categories = config.get("blocked_categories", [])
        if merchant_category and merchant_category in blocked_categories:
            return PolicyDecision(
                approved=False,
                reason=f"Merchant category '{merchant_category}' is blocked",
                plugin_name=self.metadata.name,
                metadata={"category": merchant_category},
            )

        return PolicyDecision(
            approved=True,
            reason="Merchant blocklist passed",
            plugin_name=self.metadata.name,
        )

    def _evaluate_velocity_limit(
        self, config: dict[str, Any], transaction: dict[str, Any]
    ) -> PolicyDecision:
        """
        Evaluate velocity limits.

        Config:
            - max_transactions: int - Max number of transactions
            - time_window_minutes: int - Time window in minutes
            - per_merchant: bool - Apply limit per merchant (default: global)
        """
        max_transactions = config.get("max_transactions", 10)
        time_window_minutes = config.get("time_window_minutes", 60)
        per_merchant = config.get("per_merchant", False)

        # Calculate time window
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=time_window_minutes)

        # Filter recent transactions
        recent_transactions = [
            tx
            for tx in self._transaction_history
            if tx.get("timestamp", now) >= window_start
        ]

        # Filter by merchant if needed
        if per_merchant:
            merchant = transaction.get("merchant", "")
            recent_transactions = [
                tx for tx in recent_transactions if tx.get("merchant") == merchant
            ]

        # Check velocity limit
        if len(recent_transactions) >= max_transactions:
            scope = (
                f"for merchant {transaction.get('merchant')}"
                if per_merchant
                else "globally"
            )
            return PolicyDecision(
                approved=False,
                reason=f"Velocity limit exceeded: {len(recent_transactions)} transactions in {time_window_minutes} minutes {scope}",
                plugin_name=self.metadata.name,
                metadata={
                    "count": len(recent_transactions),
                    "max": max_transactions,
                    "window_minutes": time_window_minutes,
                },
            )

        # Add transaction to history
        self._transaction_history.append(
            {
                **transaction,
                "timestamp": now,
            }
        )

        # Cleanup old transactions
        self._transaction_history = [
            tx for tx in self._transaction_history if tx.get("timestamp", now) >= window_start
        ]

        return PolicyDecision(
            approved=True,
            reason="Velocity limit passed",
            plugin_name=self.metadata.name,
        )
