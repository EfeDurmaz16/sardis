#!/usr/bin/env python3
"""
Simple Payment Demo
===================

This example shows how to create a wallet and execute a payment
using the Sardis payment protocol.

Run:
    python examples/simple_payment.py
"""

import sys
sys.path.insert(0, ".")

from sardis import Wallet, Transaction

def main():
    print("=" * 50)
    print("Sardis Payment Protocol - Simple Demo")
    print("=" * 50)
    print()
    
    # Create a wallet with initial balance
    print("1. Creating wallet with $50 USDC...")
    wallet = Wallet(initial_balance=50, currency="USDC")
    print(f"   Wallet ID: {wallet.wallet_id}")
    print(f"   Balance: ${wallet.balance} {wallet.currency}")
    print()
    
    # Create and execute a transaction
    print("2. Executing payment of $2 to OpenAI API...")
    tx = Transaction(
        from_wallet=wallet,
        to="openai:api",
        amount=2,
        purpose="GPT-4 API call"
    )
    
    result = tx.execute()
    print(f"   Transaction ID: {result.tx_id}")
    print(f"   Status: {result.status.value}")
    print(f"   TX Hash: {result.tx_hash}")
    print()
    
    # Check new balance
    print("3. Checking wallet balance...")
    print(f"   New Balance: ${wallet.balance} {wallet.currency}")
    print(f"   Total Spent: ${wallet.spent_total}")
    print()
    
    # Execute another payment
    print("4. Executing another payment of $5 to Anthropic...")
    tx2 = Transaction(
        from_wallet=wallet,
        to="anthropic:claude",
        amount=5,
        purpose="Claude API call"
    )
    
    result2 = tx2.execute()
    print(f"   Status: {result2.status.value}")
    print(f"   TX Hash: {result2.tx_hash}")
    print()
    
    # Final summary
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"   Final Balance: ${wallet.balance} {wallet.currency}")
    print(f"   Total Spent: ${wallet.spent_total}")
    print(f"   Remaining Limit: ${wallet.remaining_limit()}")
    print()
    print("✓ Demo completed successfully!")

if __name__ == "__main__":
    main()
