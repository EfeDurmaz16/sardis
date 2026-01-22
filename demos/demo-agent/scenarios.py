"""
Demo Payment Scenarios for Sardis Agent

Defines test scenarios that demonstrate policy enforcement.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class PaymentScenario:
    """A payment scenario to demonstrate."""

    name: str
    vendor: str
    amount: float
    purpose: str
    category: str
    expected_result: Literal["APPROVED", "BLOCKED"]
    explanation: str


# Demo scenarios showcasing policy enforcement
DEMO_SCENARIOS = [
    PaymentScenario(
        name="SaaS Subscription - OpenAI",
        vendor="OpenAI",
        amount=20.00,
        purpose="API credits for GPT-4 usage",
        category="saas",
        expected_result="APPROVED",
        explanation="Within daily limit, approved vendor category",
    ),
    PaymentScenario(
        name="Cloud Infrastructure - Vercel",
        vendor="Vercel",
        amount=50.00,
        purpose="Pro plan subscription",
        category="saas",
        expected_result="APPROVED",
        explanation="SaaS category allowed, amount within limits",
    ),
    PaymentScenario(
        name="Development Tools - GitHub",
        vendor="GitHub",
        amount=45.00,
        purpose="GitHub Copilot subscription",
        category="devtools",
        expected_result="APPROVED",
        explanation="Development tools category allowed",
    ),
    PaymentScenario(
        name="Blocked Category - Amazon",
        vendor="Amazon",
        amount=150.00,
        purpose="Office supplies purchase",
        category="retail",
        expected_result="BLOCKED",
        explanation="Retail category not in allowlist",
    ),
    PaymentScenario(
        name="Over Transaction Limit",
        vendor="Anthropic",
        amount=600.00,
        purpose="Claude API credits bulk purchase",
        category="saas",
        expected_result="BLOCKED",
        explanation="Exceeds per-transaction limit of $500",
    ),
    PaymentScenario(
        name="Infrastructure - AWS",
        vendor="AWS",
        amount=200.00,
        purpose="EC2 and S3 usage",
        category="cloud",
        expected_result="APPROVED",
        explanation="Cloud infrastructure allowed",
    ),
    PaymentScenario(
        name="Blocked Merchant - Gambling",
        vendor="BetOnline",
        amount=50.00,
        purpose="Entertainment",
        category="gambling",
        expected_result="BLOCKED",
        explanation="Gambling merchants explicitly blocked",
    ),
    PaymentScenario(
        name="Small Purchase - Figma",
        vendor="Figma",
        amount=15.00,
        purpose="Design tool subscription",
        category="saas",
        expected_result="APPROVED",
        explanation="Small SaaS purchase within all limits",
    ),
]


# Default policy for demo
DEFAULT_POLICY = {
    "daily_limit": 500.00,
    "per_transaction_limit": 500.00,
    "monthly_limit": 5000.00,
    "allowed_categories": ["saas", "cloud", "devtools", "api"],
    "blocked_merchants": ["gambling", "adult", "crypto_exchange"],
    "require_purpose": True,
}


def get_scenario_by_name(name: str) -> PaymentScenario | None:
    """Get a scenario by name."""
    for scenario in DEMO_SCENARIOS:
        if scenario.name.lower() == name.lower():
            return scenario
    return None


def get_scenarios_by_result(result: str) -> list[PaymentScenario]:
    """Get all scenarios with a specific expected result."""
    return [s for s in DEMO_SCENARIOS if s.expected_result == result]
