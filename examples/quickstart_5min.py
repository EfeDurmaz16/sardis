#!/usr/bin/env python3
"""
Sardis Quickstart — First Payment in 5 Minutes
===============================================

This example shows the complete path from install to first payment.

SIMULATION MODE (no setup required):
    pip install sardis
    python examples/quickstart_5min.py

PRODUCTION MODE (requires API key):
    1. Sign up at https://app.sardis.sh/signup
    2. Create an API key at https://app.sardis.sh/api-keys
    3. Set env: export SARDIS_API_KEY=your_api_key_here
    4. python examples/quickstart_5min.py --production
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, ".")


def run_simulation():
    """Simulation mode — works instantly, no setup needed."""
    from sardis import Transaction, Wallet

    print("Mode: SIMULATION (no API key needed)")
    print()

    # Step 1: Create a wallet
    wallet = Wallet(initial_balance=100, currency="USDC")
    print(f"1. Wallet created: {wallet.wallet_id}")
    print(f"   Balance: ${wallet.balance} USDC")
    print()

    # Step 2: Make a payment
    print("2. Making first payment...")
    tx = Transaction(
        from_wallet=wallet,
        to="openai:api",
        amount=5,
        purpose="GPT-4 API call",
    )
    result = tx.execute()
    print("   To: openai:api")
    print("   Amount: $5 USDC")
    print(f"   Status: {result.status.value}")
    print(f"   TX: {result.tx_hash}")
    print()

    # Step 3: Make another payment
    tx2 = Transaction(
        from_wallet=wallet,
        to="anthropic:claude",
        amount=3,
        purpose="Claude API call",
    )
    result2 = tx2.execute()
    print("3. Second payment:")
    print("   To: anthropic:claude")
    print("   Amount: $3 USDC")
    print(f"   Status: {result2.status.value}")
    print()

    # Step 4: Check balance
    print(f"4. Final balance: ${wallet.balance} USDC")
    print(f"   Total spent: ${wallet.spent_total}")
    print()

    print("Done! To use real payments:")
    print("  1. Sign up: https://app.sardis.sh/signup")
    print("  2. Get API key: https://app.sardis.sh/api-keys")
    print("  3. Run: python examples/quickstart_5min.py --production")


def run_production():
    """Production mode — requires SARDIS_API_KEY."""
    import os

    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        print("ERROR: SARDIS_API_KEY not set")
        print()
        print("To get an API key:")
        print("  1. Sign up at https://app.sardis.sh/signup")
        print("  2. Create a key at https://app.sardis.sh/api-keys")
        print("  3. export SARDIS_API_KEY=your_api_key_here")
        sys.exit(1)

    print(f"Mode: PRODUCTION (key: {api_key[:12]}...)")
    print()

    # In production, use the full SDK
    try:
        sys.path.insert(0, "packages/sardis-sdk-python/src")
        from sardis_sdk import SardisClient

        client = SardisClient(api_key=api_key)
        print("1. Connected to Sardis API")
        print()

        # Create agent + wallet
        agent = client.agents.create(name="quickstart-agent")
        print(f"2. Agent created: {agent.agent_id}")

        wallet = client.wallets.create(agent_id=agent.agent_id)
        print(f"3. Wallet created: {wallet.wallet_id}")
        print(f"   Address: {wallet.address}")
        print()

        # Set spending mandate
        mandate = client.mandates.create(
            agent_id=agent.agent_id,
            amount_per_tx="10.00",
            amount_daily="50.00",
            merchant_scope={"allowed": ["openai.com", "anthropic.com"]},
        )
        print(f"4. Mandate created: {mandate.mandate_id}")
        print("   Per-tx: $10, Daily: $50")
        print()

        # Fund wallet (testnet)
        print("5. Fund your wallet on Base Sepolia:")
        print(f"   Address: {wallet.address}")
        print("   Faucet: https://faucet.circle.com/ (select Base Sepolia, USDC)")
        print()

        print("6. Once funded, make a payment:")
        print(f'   client.pay(wallet_id="{wallet.wallet_id}",')
        print('              to="openai.com", amount="5.00")')

    except ImportError:
        print("Full SDK not found. Install: pip install sardis-sdk")
        print("Or use simulation mode (no --production flag)")


def main():
    parser = argparse.ArgumentParser(description="Sardis Quickstart")
    parser.add_argument("--production", action="store_true", help="Use production mode with real API")
    args = parser.parse_args()

    print()
    print("Sardis — First Payment in 5 Minutes")
    print("=" * 40)
    print()

    if args.production:
        run_production()
    else:
        run_simulation()


if __name__ == "__main__":
    main()
