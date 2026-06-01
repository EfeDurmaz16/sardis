"""
Cheapest-route payments — public client SDK.

Sardis auto-routes a payment across supported chains to minimize cost. You don't
run a gas optimizer yourself: omit the `chain` argument and the backend picks the
cheapest route, returning the chosen chain + provider + fee in `result["route"]`.
This example contrasts auto-routing with pinning a specific chain.

Public surface only: the `sardis` client SDK talks to a hosted Sardis
deployment. Gas estimation and route selection are owned by the backend.

    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    python examples/gas_optimizer_demo.py
"""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    from sardis import Sardis

    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)

    to = os.environ.get("DEMO_RECIPIENT", "0xRecipientAddressOrMerchantDomain")
    amount = "100.00"

    # 1. Auto-route: omit `chain` and let Sardis choose the cheapest path.
    section("Auto-route (Sardis picks the cheapest chain)")
    result = client.pay.execute(to=to, amount=amount, currency="USDC")
    print(f"status:  {result.get('status')}")
    print(f"chain:   {result.get('chain')}  <- chosen by the optimizer")
    print(f"tx_hash: {result.get('tx_hash')}")
    print(f"ledger:  {result.get('ledger_tx_id')}")
    route = result.get("route")
    if route:
        print("route (chain / provider / fee metadata):")
        print(json.dumps(route, indent=2, default=str))

    # 2. Compare candidate chains with the simulator BEFORE paying — this is the
    #    public, money-free way to inspect routing per chain. simulate() returns
    #    the policy decision and any route/cost hints the deployment exposes.
    section("Per-chain dry-run comparison (no money moves)")
    # Use an agent's policy context for the simulation. Create a throwaway agent.
    agent = client.agents.create(name="route-compare-bot")
    for chain in ("base", "polygon", "arbitrum", "optimism"):
        sim = client.simulation.simulate(
            agent_id=agent.id,
            amount=Decimal(amount),
            currency="USDC",
            chain=chain,
            merchant_id=to,
        )
        decision = sim.get("decision") or sim.get("status") or "?"
        cost = sim.get("estimated_cost_usd") or sim.get("gas_cost_usd") or "n/a"
        print(f"  {chain:<10} decision={decision:<18} est_cost={cost}")

    section("Done")
    print("Omit `chain` to auto-route; pass `chain=` to pin one. The optimizer,")
    print("gas estimation, and route ranking all live in the private backend —")
    print("the client just declares intent and reads the chosen route back.")


if __name__ == "__main__":
    main()
