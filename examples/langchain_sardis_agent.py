#!/usr/bin/env python3
"""
LangChain Agent + Sardis Payment Tool
======================================

This example shows how to use Sardis as a LangChain tool, allowing
a ReAct agent to reason about purchases and execute policy-checked
payments.

The agent receives a request, reasons about whether to purchase,
calls the Sardis tool, and gets a policy-enforced result.

Prerequisites:
    pip install langchain langchain-openai sardis

Run:
    export OPENAI_API_KEY=sk-...
    export SARDIS_API_KEY=sk_...
    python examples/langchain_sardis_agent.py
"""

import os

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from sardis import SardisClient

# --- Sardis Setup -----------------------------------------------------------

sardis = SardisClient(api_key=os.environ.get("SARDIS_API_KEY", "sim_demo"))

wallet = sardis.wallets.create(
    name="langchain-agent",
    chain="base",
    token="USDC",
    policy="""
        Max $200 per transaction.
        Daily limit $1000.
        Only allow software, cloud, and API categories.
        Require justification for purchases over $50.
    """,
)


# --- LangChain Tools --------------------------------------------------------

@tool
def sardis_pay(to: str, amount: str, token: str, purpose: str) -> str:
    """Execute a payment through Sardis with policy enforcement.

    Args:
        to: Recipient address or merchant identifier (e.g. 'openai.com')
        amount: Amount in USD (e.g. '25.00')
        token: Stablecoin to use - one of USDC, USDT, EURC
        purpose: Reason for the payment
    """
    result = sardis.payments.send(
        wallet_id=wallet.id,
        to=to,
        amount=amount,
        token=token,
        memo=purpose,
    )
    return (
        f"Status: {result.status} | "
        f"Amount: {result.amount} {token} | "
        f"TX: {result.tx_hash} | "
        f"Policy: {result.policy_result}"
    )


@tool
def sardis_balance() -> str:
    """Check the current wallet balance and spending limits."""
    info = sardis.wallets.get_balance(wallet.id)
    return (
        f"Balance: {info['balance']} USDC | "
        f"Spent: {info['spent_total']} | "
        f"Limit: {info['limit_total']} | "
        f"Remaining: {info['remaining']}"
    )


# --- Agent Setup -------------------------------------------------------------

PROMPT = PromptTemplate.from_template("""You are a procurement agent with a Sardis wallet.
You can make payments for software tools, API credits, and cloud services.

Before making any payment:
1. State what you're purchasing and why
2. Check the wallet balance if needed
3. Execute the payment with a clear purpose

You have access to the following tools:

{tools}

Tool names: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: think about what to do
Action: the action to take (one of [{tool_names}])
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer to the question

Begin!

Question: {input}
Thought:{agent_scratchpad}""")


def run_agent(task: str):
    """Run a LangChain ReAct agent with Sardis payment tools."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = [sardis_pay, sardis_balance]

    agent = create_react_agent(llm, tools, PROMPT)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
    )

    print(f"Task: {task}\n{'=' * 60}\n")
    result = executor.invoke({"input": task})
    print(f"\n{'=' * 60}")
    print(f"Result: {result['output']}")


if __name__ == "__main__":
    run_agent(
        "I need to purchase $30 of Anthropic API credits and $15 of "
        "GitHub Copilot for our development team. Check the balance first."
    )
