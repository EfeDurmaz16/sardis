"""Issue a virtual card to an AI agent and watch policy gate card authorizations.

Public-surface demo. Talks to a hosted Sardis deployment via the `sardis`
client SDK — there is no local engine, no card-provider keys, no PCI flow in
this process.

Lifecycle exercised:
  1. Create an agent.
  2. Create the agent's non-custodial wallet (card funding source).
  3. Attach a natural-language spending policy (per-tx cap + blocked MCCs).
  4. Issue a multi-use virtual card with on-card limits.
  5. Inject Lithic/Stripe-style ASA (Authorization Stream Access) requests via
     `cards.simulate_purchase` and print the server's real APPROVE/DECLINE
     decision for each.

Requires a Sardis API key (this client talks to a Sardis deployment):
    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    make demo
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

from sardis import Sardis


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)

    # 1. Agent + 2. wallet (the card's funding source).
    agent = client.agents.create(
        name="research-bot",
        description="Buys AI APIs and dev tools on behalf of a human.",
    )
    wallet = client.wallets.create(agent_id=agent.id, currency="USDC")
    print(f"[agent]  {agent.id}")
    print(f"[wallet] {wallet.id}")

    # 3. Natural-language spending policy: per-tx cap + blocked categories.
    #    The server parses this into structured limits and merchant/MCC rules.
    client.policies.apply(
        agent_id=agent.id,
        natural_language=(
            "Allow up to $250 per transaction. "
            "Block gambling and pawn shops."
        ),
    )
    print("[policy] applied: $250 per-tx cap, gambling + pawn shops blocked")

    # 4. Issue a multi-use virtual card with on-card limits.
    card = client.cards.issue(
        wallet_id=wallet.id,
        card_type="multi_use",
        limit_per_tx=Decimal("250.00"),
        limit_daily=Decimal("1000.00"),
        limit_monthly=Decimal("5000.00"),
    )
    print(
        f"[card]   id={card.card_id} status={card.status} "
        f"per_tx={card.limit_per_tx} daily={card.limit_daily} "
        f"monthly={card.limit_monthly}"
    )

    # 5. ASA auth simulation. Each call injects an authorization the way the
    #    card network would; the server evaluates it against the live policy and
    #    returns the decision in `resp.policy`.
    auth_requests = [
        ("Anthropic API", "7372", Decimal("42.50")),   # software -> approve
        ("Lottery House", "7995", Decimal("10.00")),    # gambling -> decline
        ("AWS EC2", "7399", Decimal("310.00")),         # over per-tx -> decline
        ("Vercel Pro", "7372", Decimal("20.00")),       # approve
    ]

    print("\n--- ASA auth simulation (server-side policy decision) ---")
    approved = declined = 0
    for merchant, mcc, amount in auth_requests:
        resp = client.cards.simulate_purchase(
            card.card_id,
            amount=amount,
            merchant_name=merchant,
            mcc_code=mcc,
        )
        decision = "APPROVE" if resp.transaction.status == "approved" else "DECLINE"
        reason = resp.policy.get("reason") or resp.transaction.decline_reason or "ok"
        if decision == "APPROVE":
            approved += 1
        else:
            declined += 1
        print(
            f"[asa] {decision:7} {merchant:18} mcc={mcc} "
            f"amount=${amount:>7} -> {reason}"
        )

    print(f"\n[summary] card={card.card_id} approved={approved} declined={declined}")
    print("[demo] OK -- virtual card lifecycle (issue -> policy -> auth -> decision)")


if __name__ == "__main__":
    main()
