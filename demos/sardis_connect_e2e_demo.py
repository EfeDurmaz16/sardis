"""Sardis Connect — agent-side end-to-end demo (public client SDK).

Shows how an AI agent consumes a Sardis-Connected, priced API: discover the
service, validate the spend against a natural-language policy (dry-run), then
pay. Settlement to the merchant (USD via Stripe Connect, USDC, x402, or MPP)
is handled by the Sardis backend — the agent never touches that machinery, and
neither does this script.

Public surface only: the `sardis` client SDK talks to a hosted Sardis
deployment. The merchant-onboarding / Stripe-Connect / settlement engine is
private and is intentionally NOT imported here.

Run:
    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    python demos/sardis_connect_e2e_demo.py
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal

from sardis import Sardis


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


# A priced service manifest is what an agent fetches from a merchant's
# /.well-known/sardis.json. We hard-code one here purely as demo input — it is
# plain data, not an engine object.
SERVICE_MANIFEST = {
    "name": "Acme AI API",
    "base_url": "https://api.acme-ai.com",
    "accepts": ["usdc", "x402", "card"],
    "endpoints": [
        {"path": "/api/generate", "method": "POST", "price": "0.05", "desc": "Generate text"},
        {"path": "/api/analyze", "method": "POST", "price": "0.10", "desc": "Sentiment/entities"},
        {"path": "/api/embed", "method": "POST", "price": "0.01", "desc": "Text embeddings"},
    ],
}


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)

    print("\n+----------------------------------------------------------+")
    print("|  SARDIS CONNECT - agent-side end-to-end demo             |")
    print("|  An agent discovers a priced API, checks policy, pays.   |")
    print("+----------------------------------------------------------+")

    # Step 1: Set up the paying agent + wallet + policy.
    separator("Step 1: Agent, wallet, natural-language policy")
    agent = client.agents.create(
        name="connect-research-bot",
        description="Pays per-call AI APIs for research.",
    )
    wallet = client.wallets.create(agent_id=agent.id, currency="USDC")
    client.policies.apply(
        agent_id=agent.id,
        natural_language=(
            "Spend at most $1 per transaction, $50 per day, $500 per month "
            "on AI API calls. Only pay api.acme-ai.com, openai.com and "
            "anthropic.com."
        ),
    )
    print(f"  agent:  {agent.id}")
    print(f"  wallet: {wallet.id}")
    print("  policy: $1/tx, $50/day, $500/mo; merchant allowlist applied")

    # Step 2: Agent discovers the merchant's priced API.
    separator("Step 2: Discover service (/.well-known/sardis.json)")
    print(f"  Service:   {SERVICE_MANIFEST['name']}")
    print(f"  Accepts:   {', '.join(SERVICE_MANIFEST['accepts'])}")
    for ep in SERVICE_MANIFEST["endpoints"]:
        print(f"    {ep['method']} {ep['path']} -- ${ep['price']} -- {ep['desc']}")

    # Step 3: Validate each candidate spend against policy (dry-run, no money).
    separator("Step 3: Policy simulation (dry-run, no money moves)")
    checks = [
        ("api.acme-ai.com", Decimal("0.05")),   # allowed + under cap
        ("api.acme-ai.com", Decimal("5.00")),   # over per-tx cap
        ("sketchy-api.com", Decimal("0.05")),   # not on allowlist
    ]
    for merchant, amount in checks:
        sim = client.simulation.simulate(
            agent_id=agent.id,
            amount=amount,
            currency="USD",
            merchant_id=merchant,
        )
        decision = sim.get("decision") or sim.get("status") or sim
        reason = sim.get("reason", "")
        print(f"  ${amount} -> {merchant:18} : {decision} {reason}")

    # Step 4: Execute the one spend that passed.
    separator("Step 4: Pay the allowed call")
    result = client.pay.execute(
        to="api.acme-ai.com",
        amount="0.05",
        currency="USDC",
    )
    print(f"  status:  {result.get('status')}")
    print(f"  tx_hash: {result.get('tx_hash')}")
    print(f"  chain:   {result.get('chain')}")
    print(f"  ledger:  {result.get('ledger_tx_id')}")
    if result.get("route"):
        print(f"  route:   {json.dumps(result['route'], default=str)}")

    separator("How the merchant gets paid (handled by Sardis, not the agent)")
    print("  The agent paid in USDC. Sardis settles to the merchant in their")
    print("  preferred form -- USD via Stripe Connect, USDC, x402, or MPP --")
    print("  and records the transaction in the append-only ledger.")
    print("  The merchant never sees wallets, chain IDs, or gas. The agent")
    print("  never sees the settlement rail. Sardis is the seam between them.")


if __name__ == "__main__":
    main()
