#!/usr/bin/env python3
"""
Claude (Anthropic SDK) + Sardis toolkit
=======================================

Give Claude a bounded financial surface and let it run the full tool loop:
the Sardis Anthropic toolkit defines the tools, parses tool_use blocks, and
drives the conversation — every payment is policy-checked.

Concept: `SardisToolkit(client, wallet_id).run_agent_loop(...)` handles the
whole Claude messages loop for you.

Prerequisites:
    pip install "sardis[anthropic]" anthropic

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    export SARDIS_API_KEY=sk_live_...
    python examples/anthropic_agent_sdk.py
"""
from __future__ import annotations

import os
import sys

import anthropic

from sardis import Sardis
from sardis.integrations.anthropic import SardisToolkit


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)
    agent = client.agents.create(name="claude-procurement")
    wallet = client.wallets.create(name="claude-wallet", chain="base")
    print(f"agent={agent.agent_id} wallet={wallet.wallet_id}")

    toolkit = SardisToolkit(client=client, wallet_id=wallet.wallet_id)

    result = toolkit.run_agent_loop(
        client=anthropic.Anthropic(),
        model="claude-sonnet-4-5-20250929",
        system_prompt="You pay for API credits and SaaS. Every payment is policy-checked by Sardis.",
        user_message="Check the wallet balance, then pay $5 of Anthropic credits to anthropic.com.",
    )
    print(result)


if __name__ == "__main__":
    main()
