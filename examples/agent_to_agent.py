#!/usr/bin/env python3
"""
Agent-to-Agent Payment Demo
============================

This example demonstrates how two AI agents can transact with each other
using the Sardis payment protocol, with full policy enforcement.

Run:
    python examples/agent_to_agent.py
"""

import sys
sys.path.insert(0, ".")

from sardis import Agent, Policy

def main():
    print("=" * 60)
    print("Sardis Payment Protocol - Agent-to-Agent Demo")
    print("=" * 60)
    print()
    
    # =========================================
    # Step 1: Create two agents with wallets
    # =========================================
    print("STEP 1: Creating AI Agents")
    print("-" * 40)
    
    # Alice: A shopping assistant agent
    alice = Agent(
        name="Alice",
        description="Shopping assistant that finds deals",
        policy=Policy(max_per_tx=100, max_total=500)
    )
    alice.create_wallet(initial_balance=200, currency="USDC")
    print(f"  Created: {alice}")
    print(f"    Wallet: {alice.primary_wallet.wallet_id}")
    print(f"    Balance: ${alice.total_balance} USDC")
    print()
    
    # Bob: A merchant agent that provides services
    bob = Agent(
        name="Bob",
        description="Data analysis service provider",
        policy=Policy(max_per_tx=500, max_total=5000)
    )
    bob.create_wallet(initial_balance=50, currency="USDC")
    print(f"  Created: {bob}")
    print(f"    Wallet: {bob.primary_wallet.wallet_id}")
    print(f"    Balance: ${bob.total_balance} USDC")
    print()
    
    # =========================================
    # Step 2: Alice pays Bob for a service
    # =========================================
    print("STEP 2: Alice Pays Bob for Data Analysis")
    print("-" * 40)
    
    payment_amount = 25
    print(f"  Alice requests data analysis service for ${payment_amount}...")
    print()
    
    # Execute payment from Alice to Bob
    result = alice.pay(
        to=bob.agent_id,
        amount=payment_amount,
        purpose="Data analysis service"
    )
    
    print(f"  Transaction ID: {result.tx_id}")
    print(f"  Status: {result.status.value.upper()}")
    print(f"  TX Hash: {result.tx_hash}")
    print()
    
    if result.success:
        # Simulate Bob receiving the funds
        bob.primary_wallet.deposit(payment_amount)
        print("  ✓ Payment successful!")
        print(f"    Alice's new balance: ${alice.total_balance} USDC")
        print(f"    Bob's new balance: ${bob.total_balance} USDC")
    print()
    
    # =========================================
    # Step 3: Policy enforcement demo
    # =========================================
    print("STEP 3: Policy Enforcement Demo")
    print("-" * 40)
    
    # Try to exceed per-transaction limit
    print("  Attempting payment of $150 (exceeds Alice's $100 per-tx limit)...")
    result2 = alice.pay(
        to=bob.agent_id,
        amount=150,
        purpose="Large purchase"
    )
    
    print(f"  Status: {result2.status.value.upper()}")
    print(f"  Reason: {result2.message}")
    print()
    
    if not result2.success:
        print("  ✓ Policy correctly blocked the transaction!")
    print()
    
    # =========================================
    # Step 4: Multiple transactions
    # =========================================
    print("STEP 4: Multiple Transactions")
    print("-" * 40)
    
    transactions = [
        ("API call 1", 5),
        ("API call 2", 10),
        ("Premium service", 30),
    ]
    
    for purpose, amount in transactions:
        result = alice.pay(
            to=bob.agent_id,
            amount=amount,
            purpose=purpose
        )
        status_icon = "✓" if result.success else "✗"
        print(f"  {status_icon} ${amount} for '{purpose}' - {result.status.value}")
        if result.success:
            bob.primary_wallet.deposit(amount)
    
    print()
    
    # =========================================
    # Final Summary
    # =========================================
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print()
    print(f"  Alice ({alice.name}):")
    print(f"    Final Balance: ${alice.total_balance} USDC")
    print(f"    Total Spent: ${alice.primary_wallet.spent_total}")
    print(f"    Remaining Limit: ${alice.primary_wallet.remaining_limit()}")
    print()
    print(f"  Bob ({bob.name}):")
    print(f"    Final Balance: ${bob.total_balance} USDC")
    print()
    print("✓ Agent-to-Agent demo completed successfully!")
    print()
    print("This demonstrates:")
    print("  • Programmable wallets for AI agents")
    print("  • Policy-enforced spending limits")
    print("  • Agent-to-agent transactions")
    print("  • Transaction logging and receipts")

if __name__ == "__main__":
    main()



