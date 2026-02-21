#!/usr/bin/env python3
"""
Sardis Trust Scoring Demo
=========================

This demo showcases KYA (Know Your Agent) trust scoring:
1. Register a new agent with basic identity
2. Build trust through successful transactions
3. Watch spending limits increase with trust tier upgrades
4. View detailed trust score breakdown

Features:
- Visual trust score progression
- Tier-based spending limits
- Trust factor breakdown
- Mock mode support

Usage:
    python demos/demo_trust_scoring.py              # Mock mode
    SARDIS_API_KEY=sk_... python demos/demo_trust_scoring.py  # Production mode
"""

import os
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Try to import rich for beautiful output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.tree import Tree
    from rich import box
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install 'rich' for beautiful output: pip install rich")
    print("   Running with basic output...\n")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sardis import SardisClient


# Trust tier definitions
TRUST_TIERS = {
    "NEW": {
        "score_min": 0,
        "score_max": 25,
        "daily_limit": Decimal("100"),
        "tx_limit": Decimal("25"),
        "color": "red",
        "emoji": "🔴",
    },
    "BASIC": {
        "score_min": 25,
        "score_max": 50,
        "daily_limit": Decimal("500"),
        "tx_limit": Decimal("100"),
        "color": "yellow",
        "emoji": "🟡",
    },
    "TRUSTED": {
        "score_min": 50,
        "score_max": 75,
        "daily_limit": Decimal("2500"),
        "tx_limit": Decimal("500"),
        "color": "blue",
        "emoji": "🔵",
    },
    "VERIFIED": {
        "score_min": 75,
        "score_max": 100,
        "daily_limit": Decimal("10000"),
        "tx_limit": Decimal("2500"),
        "color": "green",
        "emoji": "🟢",
    },
}


class TrustScoreCalculator:
    """Calculate trust scores based on agent behavior."""

    @staticmethod
    def get_tier(score: int) -> str:
        """Get trust tier for a given score."""
        for tier, config in TRUST_TIERS.items():
            if config["score_min"] <= score < config["score_max"]:
                return tier
        return "VERIFIED"  # Max tier

    @staticmethod
    def calculate_score(
        tx_count: int,
        total_volume: Decimal,
        days_active: int,
        kyc_verified: bool,
        failures: int,
        chargebacks: int,
    ) -> dict:
        """Calculate trust score and breakdown."""
        score = 0
        factors = {}

        # Transaction history (0-30 points)
        if tx_count >= 50:
            tx_points = 30
        elif tx_count >= 20:
            tx_points = 20
        elif tx_count >= 5:
            tx_points = 10
        else:
            tx_points = tx_count * 2
        score += tx_points
        factors["transaction_history"] = {
            "points": tx_points,
            "max": 30,
            "detail": f"{tx_count} successful transactions"
        }

        # Transaction volume (0-25 points)
        volume_usd = float(total_volume)
        if volume_usd >= 10000:
            volume_points = 25
        elif volume_usd >= 5000:
            volume_points = 20
        elif volume_usd >= 1000:
            volume_points = 15
        elif volume_usd >= 100:
            volume_points = 10
        else:
            volume_points = int(volume_usd / 10)
        score += volume_points
        factors["transaction_volume"] = {
            "points": volume_points,
            "max": 25,
            "detail": f"${total_volume:,.2f} total volume"
        }

        # Account age (0-20 points)
        if days_active >= 90:
            age_points = 20
        elif days_active >= 30:
            age_points = 15
        elif days_active >= 7:
            age_points = 10
        else:
            age_points = days_active
        score += age_points
        factors["account_age"] = {
            "points": age_points,
            "max": 20,
            "detail": f"{days_active} days active"
        }

        # KYC verification (0-15 points)
        kyc_points = 15 if kyc_verified else 0
        score += kyc_points
        factors["kyc_verification"] = {
            "points": kyc_points,
            "max": 15,
            "detail": "Verified" if kyc_verified else "Not verified"
        }

        # Reliability (0-10 points)
        if failures == 0 and chargebacks == 0:
            reliability_points = 10
        elif failures <= 2 and chargebacks == 0:
            reliability_points = 7
        elif failures <= 5:
            reliability_points = 5
        else:
            reliability_points = max(0, 10 - failures - (chargebacks * 3))
        score += reliability_points
        factors["reliability"] = {
            "points": reliability_points,
            "max": 10,
            "detail": f"{failures} failures, {chargebacks} chargebacks"
        }

        return {
            "score": min(score, 100),
            "tier": TrustScoreCalculator.get_tier(score),
            "factors": factors,
        }


class DemoDisplay:
    """Handle display output."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.mock_mode = os.getenv('SARDIS_API_KEY') is None

    def header(self, title: str):
        if RICH_AVAILABLE:
            self.console.print(Panel(
                f"[bold magenta]{title}[/bold magenta]",
                box=box.DOUBLE,
                style="magenta"
            ))
        else:
            print("\n" + "=" * 60)
            print(f"  {title}")
            print("=" * 60 + "\n")

    def step(self, number: int, title: str):
        if RICH_AVAILABLE:
            self.console.print(Panel(
                f"[bold green]Step {number}:[/bold green] [bold]{title}[/bold]",
                box=box.ROUNDED,
                border_style="green"
            ))
        else:
            print(f"\n{'─' * 50}")
            print(f"Step {number}: {title}")
            print('─' * 50)

    def trust_score_visual(self, score: int, tier: str):
        """Display visual trust score."""
        tier_config = TRUST_TIERS[tier]

        if RICH_AVAILABLE:
            # Create progress bar
            progress = Progress(
                TextColumn("[bold]{task.description}"),
                BarColumn(complete_style=tier_config["color"]),
                TextColumn("[bold]{task.percentage:>3.0f}%"),
                console=self.console
            )
            with progress:
                task = progress.add_task(
                    f"{tier_config['emoji']} Trust Score",
                    total=100,
                    completed=score
                )
                time.sleep(0.5)

            # Display tier info
            self.console.print(f"\n[bold]Current Tier:[/bold] [{tier_config['color']}]{tier}[/{tier_config['color']}]")
            self.console.print(f"[bold]Score:[/bold] {score}/100")
        else:
            bar_length = 40
            filled = int((score / 100) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\nTrust Score: [{bar}] {score}/100")
            print(f"Tier: {tier}")

    def trust_breakdown(self, factors: dict):
        """Display trust factor breakdown."""
        if RICH_AVAILABLE:
            tree = Tree("[bold]Trust Score Breakdown[/bold]")

            for factor_name, factor_data in factors.items():
                points = factor_data["points"]
                max_points = factor_data["max"]
                detail = factor_data["detail"]
                percentage = (points / max_points * 100) if max_points > 0 else 0

                # Color based on percentage
                if percentage >= 80:
                    color = "green"
                elif percentage >= 50:
                    color = "yellow"
                else:
                    color = "red"

                label = factor_name.replace("_", " ").title()
                tree.add(
                    f"[{color}]{label}[/{color}]: {points}/{max_points} pts - {detail}"
                )

            self.console.print(tree)
        else:
            print("\nTrust Score Breakdown:")
            for factor_name, factor_data in factors.items():
                points = factor_data["points"]
                max_points = factor_data["max"]
                detail = factor_data["detail"]
                label = factor_name.replace("_", " ").title()
                print(f"  • {label}: {points}/{max_points} pts - {detail}")

    def tier_limits_table(self):
        """Display tier limits table."""
        if RICH_AVAILABLE:
            table = Table(title="Trust Tier Spending Limits", box=box.ROUNDED)
            table.add_column("Tier", style="bold")
            table.add_column("Score Range", style="cyan")
            table.add_column("Daily Limit", style="green")
            table.add_column("Per-TX Limit", style="yellow")

            for tier, config in TRUST_TIERS.items():
                table.add_row(
                    f"{config['emoji']} {tier}",
                    f"{config['score_min']}-{config['score_max']}",
                    f"${config['daily_limit']:,.0f}",
                    f"${config['tx_limit']:,.0f}",
                )

            self.console.print(table)
        else:
            print("\nTrust Tier Spending Limits:")
            print(f"{'Tier':<12} {'Score':<12} {'Daily Limit':<15} {'Per-TX Limit'}")
            print("-" * 60)
            for tier, config in TRUST_TIERS.items():
                print(
                    f"{tier:<12} "
                    f"{config['score_min']}-{config['score_max']:<9} "
                    f"${config['daily_limit']:>12,.0f}  "
                    f"${config['tx_limit']:>12,.0f}"
                )

    def simulate_activity(self, description: str):
        """Simulate an activity."""
        if RICH_AVAILABLE:
            with Progress(console=self.console) as progress:
                task = progress.add_task(f"[cyan]{description}...", total=100)
                for _ in range(100):
                    time.sleep(0.01)
                    progress.update(task, advance=1)
        else:
            print(f"  {description}... ", end="", flush=True)
            time.sleep(0.3)
            print("Done")


def main():
    """Run the trust scoring demo."""
    display = DemoDisplay()

    display.header("Sardis Trust Scoring Demo (KYA)")

    # Show tier system
    display.step(0, "Trust Tier System Overview")
    display.tier_limits_table()

    # Initialize client
    api_key = os.getenv('SARDIS_API_KEY', 'mock_key')
    client = SardisClient(api_key=api_key)

    # ================================================================
    # Step 1: Register New Agent
    # ================================================================
    display.step(1, "Register New Agent")

    display.simulate_activity("Creating agent identity")

    agent_id = "did:web:example.com:agents:shopping-bot-001"
    agent_data = {
        "tx_count": 0,
        "total_volume": Decimal("0"),
        "days_active": 0,
        "kyc_verified": False,
        "failures": 0,
        "chargebacks": 0,
    }

    # Calculate initial score
    result = TrustScoreCalculator.calculate_score(**agent_data)

    if RICH_AVAILABLE:
        display.console.print(f"\n[bold]Agent Registered:[/bold] shopping-bot-001")
        display.console.print(f"[bold]Registration Date:[/bold] {datetime.now().strftime('%Y-%m-%d')}")
    else:
        print("\nAgent Registered: shopping-bot-001")
        print(f"Registration Date: {datetime.now().strftime('%Y-%m-%d')}")

    print()
    display.trust_score_visual(result["score"], result["tier"])
    print()
    display.trust_breakdown(result["factors"])

    tier_config = TRUST_TIERS[result["tier"]]
    if RICH_AVAILABLE:
        display.console.print(f"\n[bold]Current Spending Limits:[/bold]")
        display.console.print(f"  • Daily: [green]${tier_config['daily_limit']}[/green]")
        display.console.print(f"  • Per Transaction: [green]${tier_config['tx_limit']}[/green]")
    else:
        print(f"\nCurrent Spending Limits:")
        print(f"  • Daily: ${tier_config['daily_limit']}")
        print(f"  • Per Transaction: ${tier_config['tx_limit']}")

    # ================================================================
    # Step 2: Complete Transactions
    # ================================================================
    display.step(2, "Build Trust Through Transactions")

    if RICH_AVAILABLE:
        display.console.print("[dim]Simulating 7 days of agent activity...[/dim]\n")
    else:
        print("Simulating 7 days of agent activity...\n")

    # Simulate transactions over 7 days
    agent_data["tx_count"] = 8
    agent_data["total_volume"] = Decimal("450.00")
    agent_data["days_active"] = 7

    display.simulate_activity("Processing 8 successful transactions")

    result = TrustScoreCalculator.calculate_score(**agent_data)

    print()
    display.trust_score_visual(result["score"], result["tier"])
    print()
    display.trust_breakdown(result["factors"])

    tier_config = TRUST_TIERS[result["tier"]]
    if RICH_AVAILABLE:
        display.console.print(f"\n[bold green]✓ Tier Upgrade![/bold green] {TRUST_TIERS['NEW']['emoji']} NEW → {tier_config['emoji']} {result['tier']}")
        display.console.print(f"\n[bold]New Spending Limits:[/bold]")
        display.console.print(f"  • Daily: [green]${tier_config['daily_limit']}[/green] (was ${TRUST_TIERS['NEW']['daily_limit']})")
        display.console.print(f"  • Per Transaction: [green]${tier_config['tx_limit']}[/green] (was ${TRUST_TIERS['NEW']['tx_limit']})")
    else:
        print(f"\n✓ Tier Upgrade! NEW → {result['tier']}")
        print(f"\nNew Spending Limits:")
        print(f"  • Daily: ${tier_config['daily_limit']} (was ${TRUST_TIERS['NEW']['daily_limit']})")
        print(f"  • Per Transaction: ${tier_config['tx_limit']} (was ${TRUST_TIERS['NEW']['tx_limit']})")

    # ================================================================
    # Step 3: Complete KYC
    # ================================================================
    display.step(3, "Complete KYC Verification")

    display.simulate_activity("Submitting identity documents")
    display.simulate_activity("Verifying with Persona API")

    agent_data["kyc_verified"] = True

    result = TrustScoreCalculator.calculate_score(**agent_data)

    print()
    display.trust_score_visual(result["score"], result["tier"])
    print()
    display.trust_breakdown(result["factors"])

    if RICH_AVAILABLE:
        display.console.print(f"\n[bold green]✓ KYC Verified![/bold green] +15 trust points")
    else:
        print("\n✓ KYC Verified! +15 trust points")

    # ================================================================
    # Step 4: Long-term Growth
    # ================================================================
    display.step(4, "Long-term Trust Growth")

    if RICH_AVAILABLE:
        display.console.print("[dim]Fast-forwarding 90 days...[/dim]\n")
    else:
        print("Fast-forwarding 90 days...\n")

    # Simulate 90 days of activity
    agent_data["tx_count"] = 55
    agent_data["total_volume"] = Decimal("8500.00")
    agent_data["days_active"] = 90

    display.simulate_activity("Processing 55 total transactions")

    result = TrustScoreCalculator.calculate_score(**agent_data)

    print()
    display.trust_score_visual(result["score"], result["tier"])
    print()
    display.trust_breakdown(result["factors"])

    tier_config = TRUST_TIERS[result["tier"]]
    if RICH_AVAILABLE:
        display.console.print(f"\n[bold green]✓ Tier Upgrade![/bold green] {TRUST_TIERS['BASIC']['emoji']} BASIC → {tier_config['emoji']} {result['tier']}")
        display.console.print(f"\n[bold]New Spending Limits:[/bold]")
        display.console.print(f"  • Daily: [green]${tier_config['daily_limit']:,}[/green]")
        display.console.print(f"  • Per Transaction: [green]${tier_config['tx_limit']:,}[/green]")
    else:
        print(f"\n✓ Tier Upgrade! BASIC → {result['tier']}")
        print(f"\nNew Spending Limits:")
        print(f"  • Daily: ${tier_config['daily_limit']:,}")
        print(f"  • Per Transaction: ${tier_config['tx_limit']:,}")

    # ================================================================
    # Step 5: Impact Demonstration
    # ================================================================
    display.step(5, "Impact on Agent Capabilities")

    if RICH_AVAILABLE:
        comparison_table = Table(title="Spending Limit Growth", box=box.ROUNDED)
        comparison_table.add_column("Metric", style="bold")
        comparison_table.add_column("Day 1", style="red")
        comparison_table.add_column("Day 90", style="green")
        comparison_table.add_column("Growth", style="cyan")

        day1_daily = TRUST_TIERS["NEW"]["daily_limit"]
        day90_daily = tier_config["daily_limit"]
        daily_growth = ((day90_daily / day1_daily) - 1) * 100

        day1_tx = TRUST_TIERS["NEW"]["tx_limit"]
        day90_tx = tier_config["tx_limit"]
        tx_growth = ((day90_tx / day1_tx) - 1) * 100

        comparison_table.add_row(
            "Daily Limit",
            f"${day1_daily}",
            f"${day90_daily:,}",
            f"+{daily_growth:.0f}%"
        )
        comparison_table.add_row(
            "Per-TX Limit",
            f"${day1_tx}",
            f"${day90_tx:,}",
            f"+{tx_growth:.0f}%"
        )
        comparison_table.add_row(
            "Trust Score",
            "0",
            str(result["score"]),
            f"+{result['score']}"
        )

        display.console.print(comparison_table)
    else:
        print("\nSpending Limit Growth:")
        day1_daily = TRUST_TIERS["NEW"]["daily_limit"]
        day90_daily = tier_config["daily_limit"]
        print(f"  Daily Limit: ${day1_daily} → ${day90_daily:,}")
        day1_tx = TRUST_TIERS["NEW"]["tx_limit"]
        day90_tx = tier_config["tx_limit"]
        print(f"  Per-TX Limit: ${day1_tx} → ${day90_tx:,}")
        print(f"  Trust Score: 0 → {result['score']}")

    # ================================================================
    # Summary
    # ================================================================
    display.header("Demo Complete!")

    if RICH_AVAILABLE:
        summary = f"""
## Trust Scoring Journey

🔴 **Day 1**: NEW tier - $100/day limit
🟡 **Day 7**: BASIC tier - $500/day limit
🔵 **Day 90**: TRUSTED tier - ${tier_config['daily_limit']:,}/day limit

## Key Factors for Trust Growth

1. **Transaction History** - Consistent, successful payments
2. **Transaction Volume** - Total value processed
3. **Account Age** - Time since registration
4. **KYC Verification** - Identity verification via Persona
5. **Reliability** - Low failure and chargeback rates

## Benefits

✓ Higher spending limits without manual approval
✓ Lower transaction fees for trusted agents
✓ Access to premium features (escrow, multi-sig)
✓ Faster settlement times
✓ Priority support

## Next Steps

• Try `demo_payment_flow.py` to see policies in action
• Read KYA docs: https://sardis.sh/docs/kya
• Implement in your agent: https://sardis.sh/docs/sdk
        """
        display.console.print(Markdown(summary))
    else:
        print("\nTrust Scoring Journey:")
        print("  Day 1: NEW tier - $100/day limit")
        print("  Day 7: BASIC tier - $500/day limit")
        print(f"  Day 90: TRUSTED tier - ${tier_config['daily_limit']:,}/day limit")
        print("\nKey Factors:")
        print("  1. Transaction History")
        print("  2. Transaction Volume")
        print("  3. Account Age")
        print("  4. KYC Verification")
        print("  5. Reliability")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
