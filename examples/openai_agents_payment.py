#!/usr/bin/env python3
"""
OpenAI Function Calling + Sardis Payment Example
=================================================

This example shows how to build an OpenAI agent that uses Sardis
to make real payments with policy enforcement.

The agent receives a task, decides it needs to purchase API credits,
and Sardis enforces the spending policy before executing.

Prerequisites:
    pip install openai sardis

Run:
    export OPENAI_API_KEY=sk-...
    export SARDIS_API_KEY=sk_...
    python examples/openai_agents_payment.py
"""

import json
import os
from decimal import Decimal

from openai import OpenAI

from sardis import SardisClient

# --- Sardis Setup -----------------------------------------------------------

sardis = SardisClient(api_key=os.environ.get("SARDIS_API_KEY", "sk_demo"))

# Create an agent + wallet for this workflow
agent = sardis.agents.create(
    name="openai-procurement-agent",
    description="OpenAI function-calling procurement agent",
)
wallet = sardis.wallets.create(
    agent_id=agent.agent_id,
    chain="base_sepolia",
    currency="USDC",
    limit_per_tx=Decimal("100.00"),
    limit_total=Decimal("500.00"),
)

# --- OpenAI Tool Definition --------------------------------------------------

SARDIS_PAY_TOOL = {
    "type": "function",
    "function": {
        "name": "sardis_pay",
        "description": (
            "Execute a payment through Sardis. The payment is checked against "
            "the wallet's spending policy before execution. Returns the "
            "transaction result including approval/denial reason."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient address or merchant identifier",
                },
                "amount": {
                    "type": "string",
                    "description": "Amount in USD (e.g. '25.00')",
                },
                "token": {
                    "type": "string",
                    "enum": ["USDC", "USDT", "EURC"],
                    "description": "Stablecoin to use for payment",
                },
                "purpose": {
                    "type": "string",
                    "description": "Reason for the payment",
                },
            },
            "required": ["to", "amount", "token", "purpose"],
        },
    },
}


def handle_sardis_pay(args: dict) -> str:
    """Execute a Sardis payment and return the result as JSON."""
    result = sardis.wallets.transfer(
        wallet.wallet_id,
        destination=args["to"],
        amount=Decimal(args["amount"]),
        token=args["token"],
        chain="base_sepolia",
        domain="openai.com",
        memo=args["purpose"],
    )
    return json.dumps({
        "status": result.status,
        "tx_hash": result.tx_hash,
        "amount": str(result.amount),
        "token": result.token,
        "chain": result.chain,
    })


# --- Agent Loop --------------------------------------------------------------

def run_agent(task: str):
    """Run an OpenAI agent that can make payments via Sardis."""
    client = OpenAI()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a procurement agent. You help purchase software tools "
                "and API credits. You have a Sardis wallet with a spending "
                "policy. Use the sardis_pay tool to execute payments. Always "
                "explain what you're purchasing and why before paying."
            ),
        },
        {"role": "user", "content": task},
    ]

    print(f"Task: {task}\n")

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=[SARDIS_PAY_TOOL],
        )

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

        # If the model wants to call a tool
        if message.tool_calls:
            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                print(f"Agent → sardis_pay({args['amount']} {args['token']} to {args['to']})")
                print(f"  Purpose: {args['purpose']}")

                result = handle_sardis_pay(args)
                print(f"  Result: {result}\n")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
        else:
            # Final response
            print(f"Agent: {message.content}")
            break


if __name__ == "__main__":
    run_agent("Purchase $20 of OpenAI API credits for our research project.")
