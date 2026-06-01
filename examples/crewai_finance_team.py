#!/usr/bin/env python3
"""
CrewAI multi-agent team + Sardis tools
======================================

A small CrewAI crew (a researcher and a purchaser) sharing one Sardis wallet.
Sardis enforces the spending policy on every payment the crew attempts.

Concept: `create_sardis_tools(client=..., wallet_id=...)` returns CrewAI tools;
attach them to whichever agents are allowed to spend.

Prerequisites:
    pip install "sardis[crewai]" crewai

Run:
    export OPENAI_API_KEY=sk-...
    export SARDIS_API_KEY=sk_live_...
    python examples/crewai_finance_team.py
"""
from __future__ import annotations

import os
import sys

from crewai import Agent, Crew, Task

from sardis import Sardis
from sardis.integrations.crewai import create_sardis_tools


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)
    sardis_agent = client.agents.create(name="crewai-procurement")
    wallet = client.wallets.create(name="crewai-wallet", chain="base")

    client.policies.apply(
        natural_language="max $50 per transaction, $1000 per day, block gambling and entertainment",
        agent_id=sardis_agent.agent_id,
    )

    tools = create_sardis_tools(client=client, wallet_id=wallet.wallet_id)

    researcher = Agent(
        role="Researcher",
        goal="Find the cheapest API-credit vendor and estimate the cost",
        backstory="You scope purchases before the team spends.",
        tools=[t for t in tools if "balance" in t.name.lower() or "policy" in t.name.lower()],
    )
    purchaser = Agent(
        role="Purchaser",
        goal="Execute approved purchases within policy",
        backstory="You hold the wallet and pay vendors.",
        tools=tools,
    )

    crew = Crew(
        agents=[researcher, purchaser],
        tasks=[
            Task(description="Check the wallet balance and the policy.", agent=researcher,
                 expected_output="Balance and policy summary."),
            Task(description="Pay $5 of OpenAI credits to openai.com.", agent=purchaser,
                 expected_output="Payment status and tx hash."),
        ],
    )
    print(crew.kickoff())


if __name__ == "__main__":
    main()
