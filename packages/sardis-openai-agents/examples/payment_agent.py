"""Example: OpenAI Agent with Sardis payment tools.

Run with:
    SARDIS_API_KEY=sk_... SARDIS_WALLET_ID=wid_... python examples/payment_agent.py

Requires: pip install 'sardis-openai-agents[agents]' openai
"""
from __future__ import annotations

import asyncio
import os

from agents import Agent, Runner

from sardis_openai_agents import configure, get_sardis_tools

# Optional: configure programmatically instead of via env vars
# configure(api_key="sk_...", wallet_id="wid_...")

SYSTEM_PROMPT = """You are a procurement agent with access to a Sardis payment wallet.
You can check your balance, verify spending policy, and execute payments to merchants.
Always check policy before executing a payment. Never exceed spending limits."""


async def main():
    agent = Agent(
        name="ProcurementAgent",
        instructions=SYSTEM_PROMPT,
        tools=get_sardis_tools(),
    )

    print("Sardis Payment Agent ready. Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if not user_input:
            continue

        result = await Runner.run(agent, user_input)
        print(f"Agent: {result.final_output}\n")


if __name__ == "__main__":
    asyncio.run(main())
