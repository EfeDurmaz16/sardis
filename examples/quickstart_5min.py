#!/usr/bin/env python3
"""
Quickstart — first payment in 5 minutes
=======================================

End-to-end path: connect -> create agent -> create wallet -> set a natural-
language spending policy -> execute a policy-checked payment.

Concept: the same `Sardis` client drives the whole authority lifecycle; the
policy is enforced fail-closed before any money moves.

Requires a Sardis API key:
    pip install sardis
    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    python examples/quickstart_5min.py
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

    # 1. Create an agent (its financial identity).
    agent = client.agents.create(name="quickstart-agent")
    print(f"1. agent:  {agent.agent_id}")

    # 2. Create a wallet for it.
    wallet = client.wallets.create(name="quickstart-wallet", chain="base")
    print(f"2. wallet: {wallet.wallet_id}")

    # 3. Set a spending policy in plain English. Compiled + enforced fail-closed.
    client.policies.apply(
        natural_language="max $10 per transaction, $50 per day, only openai.com and anthropic.com",
        agent_id=agent.agent_id,
    )
    print("3. policy: max $10/tx, $50/day, openai.com + anthropic.com only")

    # 4. Dry-run the policy before spending.
    check = client.policies.check(
        agent_id=agent.agent_id, amount=Decimal("5"), merchant_id="openai.com"
    )
    print(f"4. check:  allowed={getattr(check, 'allowed', check)}")

    # 5. Execute a payment (passes the full authority path).
    result = client.pay.execute(to="openai.com", amount="5.00", currency="USDC")
    print(f"5. pay:    status={result.get('status')} tx={result.get('tx_hash')}")


if __name__ == "__main__":
    main()
