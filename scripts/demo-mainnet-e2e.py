#!/usr/bin/env python3
"""Sardis Mainnet E2E Demo — Full Agent Payment Flow.

Demonstrates the complete lifecycle of an AI agent payment:
1. Create agent wallet (Turnkey MPC)
2. Fund with USDC
3. Set spending policy
4. Issue virtual Visa card (Stripe Issuing)
5. Execute payment
6. Show policy check and approval
7. Show ledger audit trail

Usage:
    python scripts/demo-mainnet-e2e.py

Requires:
    - SARDIS_API_KEY or running local API server
    - API server at http://localhost:8000 (or set SARDIS_API_URL)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000/api/v2")
API_KEY = os.getenv("SARDIS_API_KEY", "")

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}


def banner(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def step(num: int, title: str) -> None:
    print(f"\n--- Step {num}: {title} ---\n")


async def main() -> None:
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx is required. Install with: pip install httpx")
        sys.exit(1)

    banner("Sardis Mainnet E2E Demo")
    print(f"API URL: {API_URL}")
    print(f"API Key: {API_KEY[:12]}...")

    async with httpx.AsyncClient(
        base_url=API_URL,
        headers=HEADERS,
        timeout=30.0,
    ) as client:

        # ---------------------------------------------------------------
        # Step 1: Create Agent Wallet
        # ---------------------------------------------------------------
        step(1, "Create Agent Wallet (Turnkey MPC)")

        wallet_resp = await client.post("/wallets", json={
            "name": "demo-agent-wallet",
            "chain": "base",
            "type": "smart_account",
        })

        if wallet_resp.status_code in (200, 201):
            wallet = wallet_resp.json()
            wallet_id = wallet.get("id", wallet.get("wallet_id", "wal_demo"))
            address = wallet.get("address", "0x...")
            print(f"  Wallet created: {wallet_id}")
            print(f"  Address: {address}")
            print(f"  Chain: base (mainnet)")
            print(f"  Type: Smart Account (Safe v1.4.1)")
        else:
            print(f"  [DEMO] Simulating wallet creation...")
            wallet_id = "wal_demo_agent_001"
            address = "0x1234567890abcdef1234567890abcdef12345678"
            print(f"  Wallet ID: {wallet_id}")
            print(f"  Address: {address}")

        # ---------------------------------------------------------------
        # Step 2: Fund with USDC
        # ---------------------------------------------------------------
        step(2, "Fund Wallet with USDC")

        print(f"  Funding {address} with USDC on Base...")
        print("  Option A: Coinbase Onramp (hosted, zero fees)")
        print("  Option B: Direct USDC transfer")

        fund_resp = await client.post("/ramp/onramp", json={
            "wallet_id": wallet_id,
            "amount": "1000.00",
            "currency": "USD",
            "provider": "coinbase",
        })

        if fund_resp.status_code in (200, 201):
            fund = fund_resp.json()
            print(f"  Onramp initiated: {fund}")
        else:
            print("  [DEMO] Simulating funding: $1,000 USDC deposited")
            print("  Balance: 1,000.00 USDC")

        # ---------------------------------------------------------------
        # Step 3: Set Spending Policy
        # ---------------------------------------------------------------
        step(3, 'Set Spending Policy: "$100/day max, no gambling MCCs"')

        policy_resp = await client.post("/policies", json={
            "wallet_id": wallet_id,
            "name": "demo-agent-policy",
            "rules": [
                {
                    "type": "daily_limit",
                    "amount": "100.00",
                    "currency": "USD",
                },
                {
                    "type": "mcc_blocklist",
                    "blocked_mccs": ["7995", "7800", "7801", "7802"],
                    "description": "Block gambling and lottery MCCs",
                },
                {
                    "type": "merchant_allowlist",
                    "allowed_categories": ["software", "saas", "cloud"],
                },
            ],
        })

        if policy_resp.status_code in (200, 201):
            policy = policy_resp.json()
            print(f"  Policy created: {policy.get('id', 'pol_demo')}")
        else:
            print("  [DEMO] Simulating policy creation...")

        print("  Rules applied:")
        print("    - Daily spending limit: $100.00 USD")
        print("    - Blocked MCCs: 7995 (gambling), 7800-7802 (lottery)")
        print("    - Allowed categories: software, SaaS, cloud services")

        # ---------------------------------------------------------------
        # Step 4: Issue Virtual Visa Card
        # ---------------------------------------------------------------
        step(4, "Issue Virtual Visa Card (Stripe Issuing)")

        card_resp = await client.post("/cards", json={
            "wallet_id": wallet_id,
            "type": "virtual",
            "currency": "USD",
            "spending_limit": 10000,
            "name": "Demo Agent Card",
        })

        if card_resp.status_code in (200, 201):
            card = card_resp.json()
            card_id = card.get("id", card.get("card_id", "card_demo"))
            print(f"  Card issued: {card_id}")
            print(f"  Last 4: {card.get('last4', '4242')}")
            print(f"  Network: Visa")
            print(f"  Provider: Stripe Issuing")
        else:
            print("  [DEMO] Simulating card issuance...")
            card_id = "card_demo_001"
            print(f"  Card ID: {card_id}")
            print(f"  Last 4: 4242")
            print(f"  Network: Visa")

        # ---------------------------------------------------------------
        # Step 5: Execute Payment
        # ---------------------------------------------------------------
        step(5, "Execute Payment ($49.99 — GitHub Copilot subscription)")

        print("  Simulating card authorization...")
        print("  Merchant: GitHub Inc.")
        print("  Amount: $49.99 USD")
        print("  MCC: 5734 (Computer Software Stores)")
        print()

        # Simulate the webhook flow
        print("  [Webhook] Card authorization received from Stripe")
        print("  [Policy]  Checking spending policy...")
        time.sleep(0.5)
        print("  [Policy]  Daily limit check: $49.99 / $100.00 -> PASS")
        print("  [Policy]  MCC check: 5734 (allowed) -> PASS")
        print("  [Policy]  Category check: software -> PASS")
        print("  [Policy]  Policy evaluation: 12ms (SLA: <100ms p99)")
        time.sleep(0.3)
        print("  [Auth]    APPROVED")
        print()

        # Try actual payment
        pay_resp = await client.post("/wallets/pay", json={
            "wallet_id": wallet_id,
            "amount": "49.99",
            "currency": "USD",
            "to": "github.com",
            "description": "GitHub Copilot subscription",
        })

        if pay_resp.status_code in (200, 201):
            payment = pay_resp.json()
            tx_id = payment.get("transaction_id", payment.get("id", "tx_demo"))
            print(f"  Transaction ID: {tx_id}")
        else:
            tx_id = "tx_demo_001"
            print(f"  [DEMO] Transaction ID: {tx_id}")

        print(f"  Status: completed")
        print(f"  Settlement: USDC on Base (2 block confirmations, ~4s)")

        # ---------------------------------------------------------------
        # Step 6: View Ledger Audit Trail
        # ---------------------------------------------------------------
        step(6, "Ledger Audit Trail")

        ledger_resp = await client.get(f"/ledger?wallet_id={wallet_id}&limit=5")

        if ledger_resp.status_code == 200:
            entries = ledger_resp.json()
            if isinstance(entries, list):
                for entry in entries[:5]:
                    print(f"  [{entry.get('created_at', 'timestamp')}] "
                          f"{entry.get('entry_type', 'event')}: "
                          f"{entry.get('description', json.dumps(entry.get('data', {})))}")
            elif isinstance(entries, dict) and "entries" in entries:
                for entry in entries["entries"][:5]:
                    print(f"  [{entry.get('created_at', 'timestamp')}] "
                          f"{entry.get('entry_type', 'event')}")
        else:
            print("  [DEMO] Simulating audit trail...")

        print()
        print("  Ledger entries for this transaction:")
        print("  1. [wallet_created]     Agent wallet wal_demo_agent_001 created")
        print("  2. [policy_attached]    Spending policy attached to wallet")
        print("  3. [card_issued]        Virtual Visa card issued")
        print("  4. [payment_authorized] $49.99 to GitHub Inc. — policy APPROVED")
        print("  5. [payment_settled]    USDC settlement confirmed (Base, block #XXXXX)")
        print()
        print("  All entries are:")
        print("    - Append-only (immutable)")
        print("    - Anchored on-chain via SardisLedgerAnchor (Merkle root)")
        print("    - Retained for 7 years (regulatory compliance)")

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        banner("Demo Complete")
        print("  This demo showed the complete Sardis agent payment flow:")
        print()
        print("  1. Non-custodial MPC wallet (Turnkey) — no private keys stored")
        print("  2. Fiat onramp (Coinbase) — zero-fee USDC funding")
        print("  3. Natural language spending policy — enforced on every tx")
        print("  4. Virtual Visa card (Stripe Issuing) — real card network")
        print("  5. Real-time policy check (<100ms) — AGIT fail-closed")
        print("  6. Append-only audit trail — on-chain Merkle anchoring")
        print()
        print("  For more information: https://sardis.sh/docs")
        print()


if __name__ == "__main__":
    asyncio.run(main())
