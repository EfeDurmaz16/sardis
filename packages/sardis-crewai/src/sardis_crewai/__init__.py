"""
sardis-crewai: CrewAI integration for Sardis agent payments.

Provides CrewAI-compatible tools, pre-configured agents, and task templates
for building multi-agent financial workflows on the Sardis platform.

Quick start::

    from sardis import SardisClient
    from sardis_crewai import SardisPayTool, create_finance_agent

    client = SardisClient(api_key="sk_test_...")
    wallet = client.wallets.create(name="finance-bot", chain="base")

    # Use individual tools
    pay_tool = SardisPayTool(client=client, wallet_id=wallet.wallet_id)

    # Or use pre-configured agents
    agent = create_finance_agent(client=client, wallet_id=wallet.wallet_id)
"""
__version__ = "1.0.0"

# Tools
from .tools import (
    SardisPayTool,
    SardisCheckBalanceTool,
    SardisCheckPolicyTool,
    SardisSetPolicyTool,
    SardisGroupBudgetTool,
    create_sardis_tools,
)

# Input schemas
from .tools import (
    SardisPayInput,
    SardisCheckBalanceInput,
    SardisCheckPolicyInput,
    SardisSetPolicyInput,
    SardisGroupBudgetInput,
)

# Pre-configured agents
from .agents import (
    create_finance_agent,
    create_procurement_agent,
    create_audit_agent,
)

# Task templates
from .tasks import (
    create_payment_task,
    create_bulk_payment_task,
    create_budget_review_task,
    create_audit_task,
    create_policy_setup_task,
)

__all__ = [
    # Tools
    "SardisPayTool",
    "SardisCheckBalanceTool",
    "SardisCheckPolicyTool",
    "SardisSetPolicyTool",
    "SardisGroupBudgetTool",
    "create_sardis_tools",
    # Input schemas
    "SardisPayInput",
    "SardisCheckBalanceInput",
    "SardisCheckPolicyInput",
    "SardisSetPolicyInput",
    "SardisGroupBudgetInput",
    # Agents
    "create_finance_agent",
    "create_procurement_agent",
    "create_audit_agent",
    # Tasks
    "create_payment_task",
    "create_bulk_payment_task",
    "create_budget_review_task",
    "create_audit_task",
    "create_policy_setup_task",
]
