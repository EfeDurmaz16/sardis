"""
Pre-configured Google ADK agent with Sardis payment tools.

Provides a one-call factory that returns a ready-to-use ``google.adk.Agent``
wired up with all Sardis payment tools.

Usage::

    from sardis_adk import create_sardis_agent

    agent = create_sardis_agent(
        api_key="sk_test_...",
        wallet_id="wallet_abc123",
    )

    # Use with ADK runner
    from google.adk.runners import InMemoryRunner
    runner = InMemoryRunner(agent=agent)
"""
from __future__ import annotations

from typing import Any

from .toolkit import SardisToolkit

_DEFAULT_INSTRUCTION = """\
You are a financial AI agent powered by Sardis, the Payment OS for the Agent Economy.

You can execute payments, check balances, enforce spending policies, and review
transaction history on behalf of the user.

Guidelines:
- Always confirm payment details with the user before executing a payment.
- When asked to pay, use sardis_pay.  Include the purpose when relevant.
- When asked about balance or limits, use sardis_check_balance.
- When the user wants to verify if a payment is allowed, use sardis_check_policy first.
- When asked to change spending rules, use sardis_set_policy.
- When asked about past transactions, use sardis_list_transactions.
- If a payment is rejected, explain the policy violation clearly.
- Always report amounts with their token type (e.g. "25.00 USDC").
"""


def create_sardis_agent(
    api_key: str,
    wallet_id: str,
    *,
    model: str = "gemini-2.0-flash",
    instruction: str | None = None,
    name: str = "sardis_payment_agent",
    description: str = "An AI agent that can make payments, check balances, and enforce spending policies through Sardis.",
    base_url: str | None = None,
) -> Any:
    """Create a Google ADK Agent pre-loaded with Sardis payment tools.

    Args:
        api_key: Sardis API key.
        wallet_id: Default wallet ID for the agent to operate on.
        model: LLM model to use (default: gemini-2.0-flash).
        instruction: Custom system instruction. If None, uses a sensible
            default that covers payment, balance, and policy workflows.
        name: Agent name (default: sardis_payment_agent).
        description: Agent description for ADK discovery.
        base_url: Optional Sardis API base URL override.

    Returns:
        A ``google.adk.Agent`` instance ready for use with ADK runners.
    """
    from google.adk import Agent

    toolkit = SardisToolkit(
        api_key=api_key,
        wallet_id=wallet_id,
        base_url=base_url,
    )

    return Agent(
        name=name,
        model=model,
        description=description,
        instruction=instruction or _DEFAULT_INSTRUCTION,
        tools=toolkit.get_tools(),
    )
