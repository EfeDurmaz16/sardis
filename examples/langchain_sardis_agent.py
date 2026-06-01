#!/usr/bin/env python3
"""
LangChain agent + Sardis toolkit
================================

Give a LangChain agent a bounded financial surface: the Sardis toolkit exposes
pay / check-balance / check-policy / set-policy / list-transactions as LangChain
tools, all enforced by the same policy engine.

Concept: `SardisToolkit(client, wallet_id).get_tools()` returns ready-to-use
LangChain `BaseTool`s — you do not hand-roll payment tools.

Prerequisites:
    pip install "sardis[langchain]" langchain langchain-openai

Run:
    export OPENAI_API_KEY=sk-...
    export SARDIS_API_KEY=sk_live_...
    python examples/langchain_sardis_agent.py
"""
from __future__ import annotations

import os
import sys

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from sardis import Sardis
from sardis.integrations.langchain import SardisToolkit

PROMPT = PromptTemplate.from_template(
    """You are a procurement agent with a Sardis wallet. You can pay for software,
API credits, and cloud services — every payment is policy-checked by Sardis.

You have access to the following tools:
{tools}

Tool names: {tool_names}

Use this format:
Question: the input question you must answer
Thought: think about what to do
Action: the action to take (one of [{tool_names}])
Action Input: the input to the action
Observation: the result of the action
... (repeat as needed)
Thought: I now know the final answer
Final Answer: the final answer

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)
    agent = client.agents.create(name="langchain-agent")
    wallet = client.wallets.create(name="langchain-wallet", chain="base")

    tools = SardisToolkit(client=client, wallet_id=wallet.wallet_id).get_tools()

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    executor = AgentExecutor(
        agent=create_react_agent(llm, tools, PROMPT),
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
    )

    task = "Check the wallet balance, then pay $5 of Anthropic API credits to anthropic.com."
    print(f"agent={agent.agent_id} wallet={wallet.wallet_id}\nTask: {task}\n{'=' * 60}")
    result = executor.invoke({"input": task})
    print(f"{'=' * 60}\nResult: {result['output']}")


if __name__ == "__main__":
    main()
