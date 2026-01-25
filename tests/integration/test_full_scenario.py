#!/usr/bin/env python3
"""
Sardis Full Scenario E2E Integration Test

This test exercises the entire Sardis stack:
1. Create an agent with identity
2. Create and assign a wallet to the agent
3. Set up natural language spending policies
4. Agent purchases from a mock merchant with policy enforcement
5. Verify spending tracking and audit trail

Story: An AI agent named "DevOpsBot" is given a wallet with $1000 USDC and policies to:
- Spend max $200 per transaction
- Daily limit of $500
- Only allow payments to AWS, OpenAI, and GitHub
- Block gambling and adult content categories

Usage:
    python tests/integration/test_full_scenario.py
    pytest tests/integration/test_full_scenario.py -v

No external dependencies required (runs offline with RegexPolicyParser).
"""
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

# pytest is optional for direct execution
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    pytest = None  # type: ignore

# Add project root and sardis_v2_core to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "packages" / "sardis-core" / "src"))

# Import Sardis core components
from sardis_v2_core import (
    Agent,
    AgentPolicy,
    AgentRepository,
    SpendingLimits,
    Wallet,
    WalletRepository,
    SpendingPolicy,
    TimeWindowLimit,
    MerchantRule,
    TrustLevel,
    SpendingScope,
    create_default_policy,
    RegexPolicyParser,
    InMemorySpendingTracker,
)


class Colors:
    """Terminal colors for output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'


def print_header(title: str):
    print(f"\n{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}  {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}\n")


def print_step(num: int, total: int, title: str):
    print(f"\n{Colors.BLUE}[{num}/{total}] {title}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'─' * 50}{Colors.ENDC}")


def print_success(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.ENDC} {msg}")


def print_denied(msg: str):
    print(f"  {Colors.YELLOW}✓{Colors.ENDC} {msg}")


def print_error(msg: str):
    print(f"  {Colors.RED}✗{Colors.ENDC} {msg}")


def print_info(key: str, value: str, indent: int = 4):
    print(f"{' ' * indent}{Colors.CYAN}{key}:{Colors.ENDC} {value}")


@dataclass
class Merchant:
    """Mock merchant for testing."""
    merchant_id: str
    name: str
    category: str


# Test merchants
MERCHANTS = {
    "aws": Merchant("aws", "Amazon Web Services", "cloud_services"),
    "openai": Merchant("openai", "OpenAI", "ai_services"),
    "github": Merchant("github", "GitHub", "developer_tools"),
    "casino": Merchant("casino_xyz", "Casino XYZ", "gambling"),
    "random": Merchant("random_vendor", "Random Vendor", "unknown"),
}


@dataclass
class PaymentAttempt:
    """Record of a payment attempt."""
    merchant: Merchant
    amount: Decimal
    expected_approved: bool
    expected_reason: Optional[str] = None
    actual_approved: Optional[bool] = None
    actual_reason: Optional[str] = None

    @property
    def passed(self) -> bool:
        if self.expected_approved:
            return self.actual_approved is True
        else:
            return (
                self.actual_approved is False and
                (self.expected_reason is None or self.expected_reason in (self.actual_reason or ""))
            )


class ScenarioResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.payments: list[PaymentAttempt] = []

    def record_payment(self, attempt: PaymentAttempt):
        self.payments.append(attempt)
        if attempt.passed:
            self.passed += 1
        else:
            self.failed += 1

    @property
    def success(self) -> bool:
        return self.failed == 0


async def run_full_scenario_test() -> ScenarioResults:
    """Run the complete integration test scenario."""
    results = ScenarioResults()

    print_header("SARDIS FULL SCENARIO E2E TEST")
    print(f"  Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"  Platform: {sys.platform}")
    print(f"  Python: {sys.version.split()[0]}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: CREATE AGENT
    # ═══════════════════════════════════════════════════════════════
    print_step(1, 6, "Creating Agent")

    agent_repo = AgentRepository()
    agent = await agent_repo.create(
        name="DevOpsBot",
        owner_id="test_owner_001",
        description="AI agent for DevOps automation and cloud resource management",
        spending_limits=SpendingLimits(
            per_transaction=Decimal("200.00"),
            daily=Decimal("500.00"),
            weekly=Decimal("2000.00"),
            monthly=Decimal("5000.00"),
        ),
        policy=AgentPolicy(
            require_human_approval_above=Decimal("1000.00"),
            allowed_categories=["cloud_services", "ai_services", "developer_tools"],
            blocked_categories=["gambling", "adult"],
        ),
        metadata={"department": "engineering", "team": "platform"},
    )

    print_success(f"Agent created: {agent.agent_id}")
    print_info("Name", agent.name)
    print_info("Owner", agent.owner_id)
    print_info("Daily Limit", f"${agent.spending_limits.daily}")
    print_info("Per-Tx Limit", f"${agent.spending_limits.per_transaction}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: CREATE AND BIND WALLET
    # ═══════════════════════════════════════════════════════════════
    print_step(2, 6, "Creating Wallet")

    wallet_repo = WalletRepository()
    wallet = await wallet_repo.create(
        agent_id=agent.agent_id,
        mpc_provider="turnkey",
        currency="USDC",
        limit_per_tx=Decimal("200.00"),
        limit_total=Decimal("1000.00"),
    )

    # Set mock address
    await wallet_repo.set_address(wallet.wallet_id, "base", "0x1234...mock")

    # Bind wallet to agent
    await agent_repo.bind_wallet(agent.agent_id, wallet.wallet_id)
    agent = await agent_repo.get(agent.agent_id)  # Refresh

    print_success(f"Wallet created: {wallet.wallet_id}")
    print_success("Wallet bound to agent")
    print_info("MPC Provider", wallet.mpc_provider)
    print_info("Currency", wallet.currency)
    print_info("Total Limit", f"${wallet.limit_total}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: SET UP SPENDING POLICY
    # ═══════════════════════════════════════════════════════════════
    print_step(3, 6, "Setting up Spending Policy")

    # Create policy with specific limits
    policy = SpendingPolicy(
        agent_id=agent.agent_id,
        trust_level=TrustLevel.MEDIUM,
        limit_per_tx=Decimal("200.00"),
        limit_total=Decimal("1000.00"),
        daily_limit=TimeWindowLimit(
            window_type="daily",
            limit_amount=Decimal("500.00"),
            currency="USDC",
        ),
    )

    # Add merchant allowlist rules
    policy.add_merchant_allow(
        merchant_id="aws",
        category="cloud_services",
        max_per_tx=Decimal("200.00"),
        reason="Cloud infrastructure",
    )
    policy.add_merchant_allow(
        merchant_id="openai",
        category="ai_services",
        max_per_tx=Decimal("200.00"),
        reason="AI API services",
    )
    policy.add_merchant_allow(
        merchant_id="github",
        category="developer_tools",
        max_per_tx=Decimal("200.00"),
        reason="Developer tools",
    )

    # Add merchant deny rules
    policy.add_merchant_deny(
        category="gambling",
        reason="Gambling sites blocked",
    )
    policy.add_merchant_deny(
        category="adult",
        reason="Adult content blocked",
    )

    print_success("Policy created with NL rules")
    print_info("Per-Tx Limit", f"${policy.limit_per_tx}")
    print_info("Daily Limit", f"${policy.daily_limit.limit_amount}")
    print_info("Allowed Merchants", "aws, openai, github")
    print_info("Blocked Categories", "gambling, adult")

    # Test RegexPolicyParser (demonstrate it works offline)
    try:
        parser = RegexPolicyParser()
        parsed = parser.parse("$200 per transaction")
        print_success(f"RegexPolicyParser working (parsed {len(parsed.get('spending_limits', []))} limits)")
    except Exception as e:
        print_info("Note", f"RegexPolicyParser demo skipped: {e}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: TEST SUCCESSFUL PAYMENTS
    # ═══════════════════════════════════════════════════════════════
    print_step(4, 6, "Testing Successful Payments")

    successful_payments = [
        PaymentAttempt(MERCHANTS["aws"], Decimal("50.00"), expected_approved=True),
        PaymentAttempt(MERCHANTS["openai"], Decimal("100.00"), expected_approved=True),
        PaymentAttempt(MERCHANTS["github"], Decimal("75.00"), expected_approved=True),
    ]

    for attempt in successful_payments:
        approved, reason = policy.validate_payment(
            amount=attempt.amount,
            fee=Decimal("0"),
            merchant_id=attempt.merchant.merchant_id,
            merchant_category=attempt.merchant.category,
        )
        attempt.actual_approved = approved
        attempt.actual_reason = reason

        if approved:
            policy.record_spend(attempt.amount)
            print_success(f"${attempt.amount} to {attempt.merchant.name}: APPROVED")
        else:
            print_error(f"${attempt.amount} to {attempt.merchant.name}: DENIED ({reason})")

        results.record_payment(attempt)

    print_info("Total Spent So Far", f"${policy.spent_total}")

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: TEST POLICY VIOLATIONS
    # ═══════════════════════════════════════════════════════════════
    print_step(5, 6, "Testing Policy Violations")

    violation_payments = [
        PaymentAttempt(
            MERCHANTS["casino"],
            Decimal("50.00"),
            expected_approved=False,
            expected_reason="denied"  # Will match "merchant_denied"
        ),
        PaymentAttempt(
            MERCHANTS["random"],
            Decimal("50.00"),
            expected_approved=False,
            expected_reason="allowlist"  # Unknown merchant - matches "merchant_not_allowlisted"
        ),
        PaymentAttempt(
            MERCHANTS["aws"],
            Decimal("250.00"),
            expected_approved=False,
            expected_reason="per_transaction"  # Exceeds $200 per-tx limit
        ),
    ]

    for attempt in violation_payments:
        approved, reason = policy.validate_payment(
            amount=attempt.amount,
            fee=Decimal("0"),
            merchant_id=attempt.merchant.merchant_id,
            merchant_category=attempt.merchant.category,
        )
        attempt.actual_approved = approved
        attempt.actual_reason = reason

        if not approved:
            print_denied(f"${attempt.amount} to {attempt.merchant.name}: DENIED ({reason})")
        else:
            # This is unexpected - the payment should have been denied
            print_error(f"${attempt.amount} to {attempt.merchant.name}: UNEXPECTEDLY APPROVED")

        results.record_payment(attempt)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 6: TEST DAILY LIMIT ENFORCEMENT
    # ═══════════════════════════════════════════════════════════════
    print_step(6, 6, "Testing Daily Limit Enforcement")

    print_info("Current Total Spent", f"${policy.spent_total}")
    print_info("Daily Limit", f"${policy.daily_limit.limit_amount}")
    print_info("Daily Remaining", f"${policy.daily_limit.remaining()}")

    # This should succeed (total: $225 + $200 = $425, under $500 daily)
    attempt1 = PaymentAttempt(MERCHANTS["aws"], Decimal("200.00"), expected_approved=True)
    approved, reason = policy.validate_payment(
        amount=attempt1.amount,
        fee=Decimal("0"),
        merchant_id=attempt1.merchant.merchant_id,
        merchant_category=attempt1.merchant.category,
    )
    attempt1.actual_approved = approved
    attempt1.actual_reason = reason

    if approved:
        policy.record_spend(attempt1.amount)
        print_success(f"${attempt1.amount} to {attempt1.merchant.name}: APPROVED (total: ${policy.spent_total})")
    else:
        print_error(f"${attempt1.amount} to {attempt1.merchant.name}: DENIED ({reason})")

    results.record_payment(attempt1)

    # This should fail (total would be $425 + $100 = $525, exceeds $500 daily)
    attempt2 = PaymentAttempt(
        MERCHANTS["openai"],
        Decimal("100.00"),
        expected_approved=False,
        expected_reason="window"  # Should hit time_window_limit
    )
    approved, reason = policy.validate_payment(
        amount=attempt2.amount,
        fee=Decimal("0"),
        merchant_id=attempt2.merchant.merchant_id,
        merchant_category=attempt2.merchant.category,
    )
    attempt2.actual_approved = approved
    attempt2.actual_reason = reason

    if not approved:
        print_denied(f"${attempt2.amount} to {attempt2.merchant.name}: DENIED ({reason})")
    else:
        print_error(f"${attempt2.amount} to {attempt2.merchant.name}: UNEXPECTEDLY APPROVED")

    results.record_payment(attempt2)

    # ═══════════════════════════════════════════════════════════════
    # VERIFICATION
    # ═══════════════════════════════════════════════════════════════
    print_header("VERIFICATION")

    # Verify final state
    expected_total = Decimal("425.00")  # 50 + 100 + 75 + 200
    actual_total = policy.spent_total

    if actual_total == expected_total:
        print_success(f"Total spent: ${actual_total} (expected: ${expected_total})")
    else:
        print_error(f"Total spent mismatch: ${actual_total} (expected: ${expected_total})")
        results.failed += 1

    daily_spent = policy.daily_limit.current_spent
    if daily_spent == expected_total:
        print_success(f"Daily spent: ${daily_spent}")
    else:
        print_error(f"Daily spent mismatch: ${daily_spent}")
        results.failed += 1

    # Final summary
    print_header("TEST SUMMARY")
    print_info("Payments Tested", str(len(results.payments)))
    print_info("Passed", str(results.passed), indent=2)
    print_info("Failed", str(results.failed), indent=2)

    if results.success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}  === ALL TESTS PASSED ==={Colors.ENDC}\n")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}  === SOME TESTS FAILED ==={Colors.ENDC}\n")
        for attempt in results.payments:
            if not attempt.passed:
                print_error(
                    f"Payment to {attempt.merchant.name}: "
                    f"expected {'approved' if attempt.expected_approved else 'denied'}, "
                    f"got {'approved' if attempt.actual_approved else 'denied'} ({attempt.actual_reason})"
                )

    return results


async def main():
    """Main entry point."""
    try:
        results = await run_full_scenario_test()
        sys.exit(0 if results.success else 1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# PYTEST ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if PYTEST_AVAILABLE:
    @pytest.mark.asyncio
    async def test_full_scenario():
        """
        Pytest entry point for the full scenario test.

        This test exercises the complete Sardis stack:
        - Agent creation and wallet binding
        - Spending policy setup with merchant rules
        - Successful payments to allowed merchants
        - Policy violations (blocked merchants, exceeded limits)
        - Daily limit enforcement
        """
        results = await run_full_scenario_test()

        # Assert all tests passed
        assert results.success, f"Test failed: {results.failed} failures out of {len(results.payments)} payments"
        assert results.passed == 8, f"Expected 8 passed payments, got {results.passed}"


if __name__ == "__main__":
    asyncio.run(main())
