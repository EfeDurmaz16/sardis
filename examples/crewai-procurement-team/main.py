"""
CrewAI Procurement Team Example

A multi-agent procurement system using CrewAI + Sardis.

Setup:
    pip install sardis-crewai crewai crewai-tools

Usage:
    export SARDIS_API_KEY="sk_..."
    export OPENAI_API_KEY="sk-..."
    python main.py
"""
import os

from crewai import Agent, Task, Crew
from sardis import SardisClient
from sardis_crewai import get_sardis_tools


def main():
    # Initialize Sardis
    sardis = SardisClient(api_key=os.environ["SARDIS_API_KEY"])

    wallet = sardis.wallets.create(
        name="procurement-team",
        chain="base",
        policy="Max $500/day, only for SaaS and cloud services, require approval above $200"
    )

    tools = get_sardis_tools(client=sardis, wallet_id=wallet.id)

    # Define agents
    researcher = Agent(
        role="Vendor Researcher",
        goal="Find the best vendors and pricing for requested services",
        backstory="Expert at finding SaaS tools and comparing pricing plans.",
        verbose=True,
    )

    purchaser = Agent(
        role="Procurement Agent",
        goal="Execute approved purchases within budget constraints",
        backstory="Handles financial transactions with strict policy compliance.",
        tools=tools,
        verbose=True,
    )

    auditor = Agent(
        role="Spend Auditor",
        goal="Review all transactions and ensure compliance",
        backstory="Financial auditor ensuring all spend is within policy.",
        tools=tools,
        verbose=True,
    )

    # Define tasks
    research_task = Task(
        description="Research the best cloud GPU provider for AI training. Budget: $200/month max.",
        expected_output="Vendor recommendation with pricing comparison",
        agent=researcher,
    )

    purchase_task = Task(
        description="Based on the research, purchase the recommended service. Check wallet balance and policy first.",
        expected_output="Payment confirmation with transaction hash",
        agent=purchaser,
    )

    audit_task = Task(
        description="Review the purchase transaction. Verify it complies with our spending policy.",
        expected_output="Audit report confirming compliance",
        agent=auditor,
    )

    # Run crew
    crew = Crew(
        agents=[researcher, purchaser, auditor],
        tasks=[research_task, purchase_task, audit_task],
        verbose=True,
    )

    result = crew.kickoff()
    print(f"\nFinal result: {result}")


if __name__ == "__main__":
    main()
