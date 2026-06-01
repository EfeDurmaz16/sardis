#!/usr/bin/env python3
"""
Agent-to-agent payment
=======================

Two agents, each with its own Sardis wallet and policy; one pays the other for
a service. The payer's policy is enforced before the transfer settles.

Concept: agent-to-agent is just two `Sardis` identities — create a wallet per
agent, set a policy, then `client.pay.execute(to=<other wallet>)`.

Requires a Sardis API key:
    export SARDIS_API_KEY=sk_live_...
    python examples/agent_to_agent.py
"""
from __future__ import annotations

import os
import sys

from sardis import Sardis


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)

    # Alice — a shopping agent that pays for services.
    alice = client.agents.create(name="alice-shopper")
    alice_wallet = client.wallets.create(name="alice-wallet", chain="base")
    client.policies.apply(
        natural_language="max $100 per transaction, $500 per day",
        agent_id=alice.agent_id,
    )

    # Bob — a service-provider agent that receives payment.
    bob = client.agents.create(name="bob-service")
    bob_wallet = client.wallets.create(name="bob-wallet", chain="base")

    print(f"alice={alice.agent_id} ({alice_wallet.wallet_id})")
    print(f"bob  ={bob.agent_id} ({bob_wallet.wallet_id})")

    # Alice pays Bob for a data-analysis job. Policy-checked before it settles.
    result = client.pay.execute(
        to=bob_wallet.wallet_id, amount="40.00", currency="USDC", chain="base"
    )
    print(f"pay: status={result.get('status')} tx={result.get('tx_hash')}")


if __name__ == "__main__":
    main()
