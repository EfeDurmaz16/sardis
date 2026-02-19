#!/usr/bin/env python3
"""
Anthropic Claude Agent + Sardis Payments
========================================

This example shows how to build a Claude agent with Sardis payment
tools using the sardis-agent-sdk package. The toolkit handles tool
definitions, result parsing, and the full agent loop automatically.

Two modes are demonstrated:
  1. Manual loop — you control each turn
  2. run_agent_loop() — fully automated conversation

Prerequisites:
    pip install anthropic sardis-agent-sdk

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    export SARDIS_API_KEY=sk_...
    python examples/anthropic_agent_sdk.py
"""

import os

import anthropic

from sardis import SardisClient
from sardis_agent_sdk import SardisToolkit

# --- Sardis Setup -----------------------------------------------------------

sardis = SardisClient(api_key=os.environ.get("SARDIS_API_KEY", "sk_test_demo"))

# Create an agent and wallet
agent = sardis.agents.create(
    name="claude-procurement-agent",
    description="Claude-powered procurement agent with Sardis wallet",
)
wallet = sardis.wallets.create(
    agent_id=agent.agent_id,
    chain="base_sepolia",
    currency="USDC",
)

# Create the toolkit
toolkit = SardisToolkit(
    client=sardis,
    wallet_id=wallet.wallet_id,
)

# --- Example 1: Automated Agent Loop ---------------------------------------

def run_automated():
    """Use run_agent_loop() for a fully managed conversation."""
    print("=" * 60)
    print("Example 1: Automated Agent Loop")
    print("=" * 60)
    print()

    client = anthropic.Anthropic()

    result = toolkit.run_agent_loop(
        client=client,
        model="claude-sonnet-4-5-20250929",
        system_prompt=(
            "You are a procurement agent with a Sardis wallet. "
            "You help purchase software tools and API credits. "
            "Always check the balance before making payments, and "
            "explain your reasoning clearly."
        ),
        user_message=(
            "I need to purchase $30 of OpenAI API credits. "
            "Check my balance and policy first, then make the payment."
        ),
        max_turns=5,
    )

    print(f"Agent response: {result['response']}")
    print(f"Tool calls made: {len(result['tool_calls'])}")
    print(f"Turns taken: {result['turns']}")
    print()

    for i, call in enumerate(result["tool_calls"], 1):
        print(f"  Tool call {i}: {call['tool_name']}")
        print(f"    Input: {call['tool_input']}")
        print(f"    Result: {call['result']}")
        print()


# --- Example 2: Manual Agent Loop ------------------------------------------

def run_manual():
    """Manually manage the conversation loop for full control."""
    print("=" * 60)
    print("Example 2: Manual Agent Loop")
    print("=" * 60)
    print()

    client = anthropic.Anthropic()
    tools = toolkit.get_tools()

    messages = [
        {
            "role": "user",
            "content": "What's my current wallet balance? Then check if I can pay $50 to anthropic.com",
        }
    ]

    system_prompt = (
        "You are a helpful assistant with access to a Sardis payment wallet. "
        "Use the available tools to check balances, verify policies, and "
        "execute payments when asked."
    )

    for turn in range(5):
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        # Check if the model wants to use tools
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Final text response
            for block in response.content:
                if block.type == "text":
                    print(f"Agent: {block.text}")
            break

        # Append assistant message
        messages.append({"role": "assistant", "content": response.content})

        # Process each tool call
        tool_results = []
        for block in tool_use_blocks:
            print(f"  Tool: {block.name}({block.input})")
            result = toolkit.handle_tool_call(block)
            tool_results.append(result)
            print(f"  Result: {result['content']}")
            print()

        # Send tool results back
        messages.append({"role": "user", "content": tool_results})


# --- Example 3: Read-Only Observer Agent ------------------------------------

def run_read_only():
    """Create a read-only toolkit for observer/auditor agents."""
    print("=" * 60)
    print("Example 3: Read-Only Observer Agent")
    print("=" * 60)
    print()

    # Read-only toolkit cannot make payments
    observer_toolkit = SardisToolkit(
        client=sardis,
        wallet_id=wallet.wallet_id,
        read_only=True,
    )

    client = anthropic.Anthropic()

    result = observer_toolkit.run_agent_loop(
        client=client,
        model="claude-sonnet-4-5-20250929",
        system_prompt=(
            "You are a financial auditor. You can check balances and "
            "review transaction history, but you cannot make payments. "
            "Analyze the wallet's spending patterns and report any concerns."
        ),
        user_message="Review this wallet's balance and recent transactions. Flag anything unusual.",
        max_turns=3,
    )

    print(f"Auditor report: {result['response']}")
    print(f"Tools used: {len(result['tool_calls'])}")


# --- Main -------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("Anthropic Claude Agent + Sardis Payments")
    print("=" * 60)
    print()

    run_automated()
    print()
    run_manual()
    print()
    run_read_only()
