"""Sardis Policy Playground — Test Policies Locally

Parse natural language spending policies and test them against hypothetical payments.
"""
import asyncio
import os

from sardis_sdk import AsyncSardisClient


async def main():
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        print("Set SARDIS_API_KEY environment variable.")
        return

    async with AsyncSardisClient(api_key=api_key) as client:
        # Parse a natural language policy
        policies = [
            "Max $100 per transaction, $1000 per day",
            "Only allow payments to OpenAI and Anthropic APIs",
            "No transactions over $500, require approval above $200",
        ]

        for policy_text in policies:
            print(f"\nPolicy: '{policy_text}'")
            policy = await client.policies.parse(text=policy_text)
            print(f"  Parsed: {policy.summary}")
            print(f"  Limits: per_tx={policy.limit_per_tx}, daily={policy.daily_limit}")

        # Simulate policy checks
        print("\n--- Simulating payments ---")
        simulations = [
            ("OpenAI API", "50.00"),
            ("AWS Compute", "150.00"),
            ("Unknown Merchant", "25.00"),
        ]

        for merchant, amount in simulations:
            result = await client.simulation.check_payment(
                amount=amount,
                merchant=merchant,
            )
            status = "ALLOWED" if result.allowed else "BLOCKED"
            print(f"  ${amount} to {merchant}: {status} — {result.reason}")


if __name__ == "__main__":
    asyncio.run(main())
