#!/usr/bin/env python3
"""
Google ADK Agent + Sardis Payments
==================================

This example shows how to use Sardis as a Google Agent Development Kit
(ADK) tool, allowing a Gemini-powered agent to make policy-checked
payments autonomously.

The agent receives a purchasing task, reasons about costs, checks the
wallet balance, and executes payments through Sardis.

Prerequisites:
    pip install "sardis[adk]" google-adk

Run:
    export GOOGLE_API_KEY=...
    export SARDIS_API_KEY=sk_...
    python examples/google_adk_agent.py
"""

import os
import sys

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from sardis.integrations.adk import SardisToolkit

# --- Sardis Setup -----------------------------------------------------------

_api_key = os.environ.get("SARDIS_API_KEY")
_wallet_id = os.environ.get("SARDIS_WALLET_ID")
if not _api_key or not _wallet_id:
    sys.exit("Set SARDIS_API_KEY and SARDIS_WALLET_ID and retry.")

# Create the toolkit - this configures all Sardis tools with your API key
# and a default wallet for the agent to use.
toolkit = SardisToolkit(api_key=_api_key, wallet_id=_wallet_id)

# Get ADK FunctionTool instances
sardis_tools = toolkit.get_tools()

# --- Agent Setup ------------------------------------------------------------

agent = Agent(
    name="procurement-agent",
    model="gemini-2.0-flash",
    description="A procurement agent that purchases software and API credits.",
    instruction=(
        "You are a procurement agent with a Sardis wallet for making payments. "
        "You help purchase software tools, API credits, and cloud services.\n\n"
        "Before making any payment:\n"
        "1. Check the wallet balance to see available funds\n"
        "2. Check the policy to verify the payment would be allowed\n"
        "3. Execute the payment with a clear purpose\n"
        "4. Report the result including transaction ID\n\n"
        "Always explain your reasoning before taking action."
    ),
    tools=sardis_tools,
)


# --- Run the Agent ----------------------------------------------------------

async def main():
    """Run the ADK agent with a sample procurement task."""
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="sardis-demo", session_service=session_service)

    session = await session_service.create_session(
        app_name="sardis-demo",
        user_id="demo-user",
    )

    print("=" * 60)
    print("Google ADK Agent + Sardis Payments")
    print("=" * 60)
    print()

    task = (
        "I need to purchase $25 of Anthropic API credits for our research "
        "project. Check the balance first and make sure our policy allows it."
    )
    print(f"Task: {task}\n")

    from google.genai import types

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=task)],
    )

    async for event in runner.run_async(
        user_id="demo-user",
        session_id=session.id,
        new_message=user_message,
    ):
        if event.is_final_response():
            for part in event.content.parts:
                if part.text:
                    print(f"\nAgent: {part.text}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
