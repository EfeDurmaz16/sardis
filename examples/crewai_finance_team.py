#!/usr/bin/env python3
"""
CrewAI Multi-Agent Finance Team + Sardis Group Budgets
======================================================

This example demonstrates CrewAI's multi-agent orchestration with Sardis
group governance. Three agents share a team budget enforced by Sardis:

  - Researcher: Finds tools and estimates costs
  - Purchaser: Executes approved purchases
  - Auditor: Reviews spending and compliance

The AgentGroup enforces a shared daily budget across all agents.

Prerequisites:
    pip install crewai sardis

Run:
    export OPENAI_API_KEY=sk-...
    export SARDIS_API_KEY=sk_...
    python examples/crewai_finance_team.py
"""

import os
from decimal import Decimal

from crewai import Agent, Crew, Task
from crewai.tools import tool

from sardis import SardisClient
from sardis import AgentGroup as SardisAgentGroup

# --- Sardis Setup -----------------------------------------------------------

sardis = SardisClient(api_key=os.environ.get("SARDIS_API_KEY", "sim_demo"))

# Create a shared group budget for the finance team
group = sardis.groups.create(
    name="engineering-procurement",
    budget_per_tx=Decimal("200.00"),
    budget_daily=Decimal("1000.00"),
    policy="""
        Only allow software tools, API credits, and cloud services.
        Block retail, entertainment, and gambling categories.
        Require justification for any purchase over $50.
    """,
)

# Create individual wallets under the group
researcher_wallet = sardis.wallets.create(
    name="researcher-agent",
    chain="base",
    token="USDC",
    group_id=group.id,
    policy="Max $50 per transaction. Read-only market research.",
)

purchaser_wallet = sardis.wallets.create(
    name="purchaser-agent",
    chain="base",
    token="USDC",
    group_id=group.id,
    policy="Max $200 per transaction. Execute approved purchases only.",
)

auditor_wallet = sardis.wallets.create(
    name="auditor-agent",
    chain="base",
    token="USDC",
    group_id=group.id,
    policy="Read-only. No spending allowed.",
)


# --- CrewAI Tools -----------------------------------------------------------

@tool("sardis_pay")
def sardis_pay(to: str, amount: str, token: str, purpose: str) -> str:
    """Execute a payment through Sardis with group budget enforcement.

    Args:
        to: Recipient address or merchant identifier
        amount: Amount in USD (e.g. '25.00')
        token: Stablecoin to use - one of USDC, USDT, EURC
        purpose: Reason for the payment
    """
    result = sardis.payments.send(
        wallet_id=purchaser_wallet.id,
        to=to,
        amount=amount,
        token=token,
        memo=purpose,
    )
    return (
        f"Status: {result.status} | "
        f"Amount: {result.amount} {token} | "
        f"TX: {result.tx_hash} | "
        f"Policy: {result.policy_result} | "
        f"Group budget remaining: {result.group_remaining}"
    )


@tool("sardis_group_status")
def sardis_group_status() -> str:
    """Check the group budget status including spending across all agents."""
    info = sardis.groups.get_status(group.id)
    return (
        f"Group: {info['name']}\n"
        f"Daily budget: ${info['budget_daily']}\n"
        f"Spent today: ${info['spent_daily']}\n"
        f"Remaining: ${info['daily_remaining']}\n"
        f"Active agents: {info['agent_count']}\n"
        f"Transactions today: {info['tx_count_daily']}"
    )


@tool("sardis_audit_log")
def sardis_audit_log() -> str:
    """Retrieve recent transaction audit log for the group."""
    entries = sardis.ledger.list(group_id=group.id, limit=10)
    if not entries:
        return "No transactions yet."
    lines = []
    for entry in entries:
        lines.append(
            f"  [{entry.timestamp:%H:%M}] {entry.agent_name}: "
            f"${entry.amount} to {entry.merchant} — {entry.status}"
        )
    return "Recent transactions:\n" + "\n".join(lines)


# --- CrewAI Agents ----------------------------------------------------------

researcher = Agent(
    role="Research Analyst",
    goal="Find the best software tools and API services for the team",
    backstory=(
        "You are a technical researcher who evaluates software tools. "
        "You identify what the team needs and estimate costs before "
        "recommending purchases."
    ),
    tools=[sardis_group_status],
    verbose=True,
)

purchaser = Agent(
    role="Procurement Specialist",
    goal="Execute approved purchases within the group budget",
    backstory=(
        "You are a procurement specialist with a Sardis wallet. "
        "You only purchase items that have been researched and justified. "
        "You always check the group budget before spending."
    ),
    tools=[sardis_pay, sardis_group_status],
    verbose=True,
)

auditor = Agent(
    role="Financial Auditor",
    goal="Review all spending for compliance and budget adherence",
    backstory=(
        "You are a financial auditor who reviews all team spending. "
        "You check that purchases align with policy, flag anomalies, "
        "and produce a summary report."
    ),
    tools=[sardis_audit_log, sardis_group_status],
    verbose=True,
)

# --- Tasks ------------------------------------------------------------------

research_task = Task(
    description=(
        "Research and recommend API credits to purchase for the team. "
        "We need: OpenAI API credits (~$30), Anthropic API credits (~$25), "
        "and a GitHub Copilot subscription (~$19/month). "
        "Check the group budget first and provide cost estimates."
    ),
    expected_output="A list of recommended purchases with costs and justifications.",
    agent=researcher,
)

purchase_task = Task(
    description=(
        "Execute the purchases recommended by the researcher. "
        "Check the group budget before each purchase. "
        "Pay for each item individually with clear purpose descriptions."
    ),
    expected_output="Confirmation of each purchase with transaction details.",
    agent=purchaser,
)

audit_task = Task(
    description=(
        "Review all purchases made today. Check: "
        "1) Each purchase has a valid justification, "
        "2) Spending is within group budget limits, "
        "3) No policy violations occurred. "
        "Produce a compliance summary."
    ),
    expected_output="An audit report summarizing spending and compliance status.",
    agent=auditor,
)

# --- Crew Execution ---------------------------------------------------------

if __name__ == "__main__":
    crew = Crew(
        agents=[researcher, purchaser, auditor],
        tasks=[research_task, purchase_task, audit_task],
        verbose=True,
    )

    print("=" * 60)
    print("CrewAI Finance Team + Sardis Group Budgets")
    print("=" * 60)
    print()
    print(f"Group: {group.name} ({group.id})")
    print(f"Daily budget: $1,000")
    print(f"Agents: researcher, purchaser, auditor")
    print()

    result = crew.kickoff()

    print()
    print("=" * 60)
    print("CREW RESULT")
    print("=" * 60)
    print(result)
