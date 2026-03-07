"""
Procurement Crew Example - Sardis + CrewAI

A simple multi-agent crew where a procurement agent checks budgets and
makes purchases on behalf of the team, while an auditor verifies spend.

Run without any API keys (simulation mode):
    python examples/procurement_crew.py
"""
from __future__ import annotations

import os

from sardis import SardisClient

# ---------------------------------------------------------------------------
# 1. Set up Sardis client and wallet (simulation mode - no real API key needed)
# ---------------------------------------------------------------------------
client = SardisClient(api_key=os.getenv("SARDIS_API_KEY"))
wallet = client.wallets.create(
    name="procurement-bot",
    chain="base",
    policy="Max $200 per transaction, $500 per day",
)

print(f"Created wallet: {wallet.wallet_id}")

# ---------------------------------------------------------------------------
# 2. Build Sardis tools
# ---------------------------------------------------------------------------
from sardis_crewai import create_sardis_toolkit  # noqa: E402

tools = create_sardis_toolkit(
    api_key=os.getenv("SARDIS_API_KEY"),
    wallet_id=wallet.wallet_id,
)

# ---------------------------------------------------------------------------
# 3. Define the crew (requires `crewai` installed)
# ---------------------------------------------------------------------------
try:
    from crewai import Agent, Crew, Task

    # Procurement agent - makes purchases
    procurement_agent = Agent(
        role="Procurement Specialist",
        goal=(
            "Source and purchase software tools and API credits for the engineering team "
            "within approved budget limits."
        ),
        backstory=(
            "You are a careful procurement specialist who always checks budget availability "
            "before committing to any purchase. You document every transaction clearly."
        ),
        tools=tools,
        verbose=True,
    )

    # Audit agent - read-only policy and balance checks
    from sardis_crewai import SardisBalanceTool, SardisPolicyCheckTool

    audit_tools = [
        SardisBalanceTool(
            api_key=os.getenv("SARDIS_API_KEY"),
            wallet_id=wallet.wallet_id,
        ),
        SardisPolicyCheckTool(
            api_key=os.getenv("SARDIS_API_KEY"),
            wallet_id=wallet.wallet_id,
        ),
    ]

    audit_agent = Agent(
        role="Financial Auditor",
        goal="Verify that all purchases comply with spending policy and report on remaining budget.",
        backstory=(
            "You review every purchase for policy compliance and produce a concise budget summary "
            "so management always knows where the team stands financially."
        ),
        tools=audit_tools,
        verbose=True,
    )

    # Tasks
    purchase_task = Task(
        description=(
            "Purchase the following software subscriptions for the engineering team:\n"
            "1. OpenAI API credits - $50 (purpose: LLM inference)\n"
            "2. GitHub Copilot Business - $19 (purpose: developer tooling)\n\n"
            "Before each purchase, check the policy to confirm it will be approved. "
            "Report the transaction ID for each successful payment."
        ),
        expected_output=(
            "A list of completed purchases with transaction IDs, or a clear explanation "
            "of any payments that were blocked by policy."
        ),
        agent=procurement_agent,
    )

    audit_task = Task(
        description=(
            "After the procurement agent finishes, check the current wallet balance and "
            "remaining daily limit. Confirm all purchases were within policy."
        ),
        expected_output=(
            "A short audit report with: current balance, remaining daily limit, "
            "and a compliance verdict (PASS / FAIL)."
        ),
        agent=audit_agent,
    )

    # Assemble and run
    crew = Crew(
        agents=[procurement_agent, audit_agent],
        tasks=[purchase_task, audit_task],
        verbose=True,
    )

    result = crew.kickoff()
    print("\n=== Crew Result ===")
    print(result)

except ImportError:
    # crewai not installed - demonstrate tools directly
    print("\ncrewai not installed. Demonstrating tools directly:\n")

    pay_tool = tools[0]
    balance_tool = tools[1]
    policy_tool = tools[2]

    print("1. Check policy for $50 payment to openai.com:")
    print("  ", policy_tool._run(amount=50.0, merchant="openai.com"))

    print("\n2. Pay $50 to openai.com:")
    print("  ", pay_tool._run(amount=50.0, merchant="openai.com", purpose="LLM inference"))

    print("\n3. Pay $19 to github.com:")
    print("  ", pay_tool._run(amount=19.0, merchant="github.com", purpose="Developer tooling"))

    print("\n4. Check remaining balance:")
    print("  ", balance_tool._run(token="USDC"))
