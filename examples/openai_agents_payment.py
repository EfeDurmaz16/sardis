#!/usr/bin/env python3
"""
OpenAI Agents SDK + Sardis tools
================================

Give an OpenAI Agents SDK agent Sardis payment tools (pay / check-balance /
check-policy), all policy-enforced by Sardis.

Concept: `configure(...)` sets the default Sardis client, then
`get_sardis_tools()` returns function tools you hand straight to an `Agent`.

Prerequisites:
    pip install "sardis[openai-agents]" openai-agents

Run:
    export OPENAI_API_KEY=sk-...
    export SARDIS_API_KEY=sk_live_...
    export SARDIS_WALLET_ID=wallet_...   # the wallet the tools spend from
    python examples/openai_agents_payment.py
"""
from __future__ import annotations

import os
import sys

from agents import Agent, Runner

from sardis.integrations.openai_agents import configure, get_sardis_tools


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    wallet_id = os.environ.get("SARDIS_WALLET_ID")
    if not api_key or not wallet_id:
        sys.exit("Set SARDIS_API_KEY and SARDIS_WALLET_ID and retry.")

    # Point the Sardis tools at your client + wallet.
    configure(api_key=api_key, wallet_id=wallet_id)

    agent = Agent(
        name="procurement-agent",
        instructions="You pay for API credits and SaaS. Every payment is policy-checked.",
        tools=get_sardis_tools(),
    )

    result = Runner.run_sync(
        agent, "Check the balance, then pay $5 of OpenAI credits to openai.com."
    )
    print(result.final_output)


if __name__ == "__main__":
    main()
