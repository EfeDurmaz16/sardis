#!/usr/bin/env python3
"""
Sardis End-to-End Payment Demo (public client SDK)

Walks the full authority path for an agent payment using ONLY the public
``sardis`` client SDK — the thin HTTP client that talks to a hosted Sardis
deployment. No local engine, no chain RPC, no keys live in this process; the
backend owns mandate verification, policy, compliance, signing and settlement.

Steps:
  1. Create an agent.
  2. Create the agent's non-custodial wallet.
  3. Attach a natural-language spending policy.
  4. Dry-run the payment with ``simulation.simulate`` (allow / requires_approval
     / deny + reason) — zero money moves.
  5. Execute the payment with ``pay.execute`` (mandate -> policy -> compliance ->
     sign -> on-chain settle -> signed ledger), unless ``--dry-run``.
  6. Print the returned route + ledger audit pointers.

Requires a Sardis API key:
    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com

Usage:
    python demos/full_payment_demo.py [--dry-run] [--chain base] [--amount 10.00]

Options:
    --dry-run   Stop after the policy simulation (Step 4). Nothing executes.
    --chain     Target chain (omit to let Sardis auto-route the cheapest).
    --amount    Payment amount (default: 10.00).
    --to        Recipient address or merchant domain.
"""

import argparse
import json
import os
import sys
from decimal import Decimal

from sardis import Sardis


def print_header(title: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}".center(width))
    print("=" * width + "\n")


def print_step(step_num: int, description: str) -> None:
    print(f"\n{'-' * 50}")
    print(f"  Step {step_num}: {description}")
    print(f"{'-' * 50}\n")


def run_demo(
    *,
    dry_run: bool,
    chain: str | None,
    amount: str,
    to: str,
) -> None:
    print_header("SARDIS PAYMENT DEMO (public client SDK)")
    print(f"Mode:   {'DRY-RUN (no execution)' if dry_run else 'EXECUTE'}")
    print(f"Chain:  {chain or 'auto-route (cheapest)'}")
    print(f"Amount: {amount} USDC")

    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)

    # Step 1: Agent
    print_step(1, "Create agent")
    agent = client.agents.create(
        name="payment-demo-bot",
        description="End-to-end payment demo agent.",
    )
    print(f"OK agent: {agent.id}")

    # Step 2: Wallet
    print_step(2, "Create non-custodial wallet")
    wallet = client.wallets.create(agent_id=agent.id, currency="USDC", chain=chain)
    print(f"OK wallet: {wallet.id}")

    # Step 3: Natural-language spending policy
    print_step(3, "Attach natural-language spending policy")
    client.policies.apply(
        agent_id=agent.id,
        natural_language=(
            f"Allow up to ${amount} per transaction, "
            "max $1000 per day. Require approval above $500."
        ),
    )
    print("OK policy: per-tx + daily caps, approval threshold applied")

    # Step 4: Dry-run via the policy simulator
    print_step(4, "Simulate (dry-run — no money moves)")
    sim = client.simulation.simulate(
        agent_id=agent.id,
        amount=Decimal(amount),
        currency="USDC",
        chain=chain,
        merchant_id=to,
    )
    decision = sim.get("decision") or sim.get("status") or sim
    print("Simulation result:")
    print(json.dumps(sim, indent=2, default=str))

    if dry_run:
        print("\nDry-run mode: stopping before execution.")
        print(f"Decision was: {decision}")
        return

    # Step 5: Execute
    print_step(5, "Execute payment")
    result = client.pay.execute(
        to=to,
        amount=amount,
        currency="USDC",
        chain=chain,  # None -> Sardis auto-routes the cheapest chain
    )
    print(f"status:   {result.get('status')}")
    print(f"tx_hash:  {result.get('tx_hash')}")
    print(f"chain:    {result.get('chain')}")
    print(f"ledger:   {result.get('ledger_tx_id')}")
    if result.get("route"):
        print(f"route:    {json.dumps(result['route'], default=str)}")
    if result.get("fx"):
        print(f"fx:       {json.dumps(result['fx'], default=str)}")

    # Step 6: Audit pointers
    print_step(6, "Audit trail")
    print("Every execution is recorded in the append-only ledger.")
    print(f"Ledger tx id: {result.get('ledger_tx_id')}")

    print_header("DEMO COMPLETE")
    print("Summary:")
    print(f"  - Agent:   {agent.id}")
    print(f"  - Wallet:  {wallet.id}")
    print("  - Policy:  natural-language caps applied")
    print(f"  - Payment: {amount} USDC -> {to}")
    print(f"  - Ledger:  {result.get('ledger_tx_id')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sardis End-to-End Payment Demo (public client SDK)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python demos/full_payment_demo.py --dry-run            # simulate only
    python demos/full_payment_demo.py                      # execute, auto-route
    python demos/full_payment_demo.py --amount 100         # custom amount
    python demos/full_payment_demo.py --chain base         # pin a chain
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="Stop after simulation")
    parser.add_argument("--chain", type=str, default=None, help="Target chain (default: auto-route)")
    parser.add_argument("--amount", type=str, default="10.00", help="Amount in USDC (default: 10.00)")
    parser.add_argument(
        "--to",
        type=str,
        default="0xRecipientAddressOrMerchantDomain",
        help="Recipient address or merchant domain",
    )
    args = parser.parse_args()

    run_demo(dry_run=args.dry_run, chain=args.chain, amount=args.amount, to=args.to)


if __name__ == "__main__":
    main()
