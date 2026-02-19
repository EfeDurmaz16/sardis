"""
Pre-configured CrewAI agent definitions for common Sardis workflows.

Each factory function creates a CrewAI ``Agent`` wired with the appropriate
Sardis tools.  Agents are opinionated defaults -- callers can override any
parameter via keyword arguments.

Example::

    from sardis import SardisClient
    from sardis_crewai.agents import create_finance_agent

    client = SardisClient(api_key="sk_test_...")
    wallet = client.wallets.create(name="finance-bot", chain="base")

    agent = create_finance_agent(client=client, wallet_id=wallet.wallet_id)
"""
from __future__ import annotations

from typing import Any, Optional

from crewai import Agent

from sardis import SardisClient

from .tools import (
    SardisCheckBalanceTool,
    SardisCheckPolicyTool,
    SardisGroupBudgetTool,
    SardisPayTool,
    SardisSetPolicyTool,
    create_sardis_tools,
)


def create_finance_agent(
    client: SardisClient,
    wallet_id: str,
    *,
    group_id: Optional[str] = None,
    verbose: bool = True,
    **agent_kwargs: Any,
) -> Agent:
    """Create a finance-focused agent with full Sardis payment capabilities.

    The finance agent can check balances, validate policies, execute payments,
    set spending policies, and monitor group budgets.  It is designed for
    general-purpose financial operations.

    Args:
        client: Initialized SardisClient.
        wallet_id: Wallet this agent operates on.
        group_id: Optional group ID for budget monitoring.
        verbose: Enable verbose logging (default True).
        **agent_kwargs: Additional keyword arguments forwarded to ``crewai.Agent``.

    Returns:
        Configured CrewAI Agent with all Sardis tools.
    """
    tools = create_sardis_tools(client, wallet_id, group_id=group_id)

    defaults = dict(
        role="Finance Manager",
        goal=(
            "Manage payments, monitor budgets, and ensure all financial "
            "transactions comply with spending policies. Always check the "
            "balance and policy before executing payments."
        ),
        backstory=(
            "You are an experienced finance manager responsible for managing "
            "AI agent payments through the Sardis platform. You have access to "
            "a programmable wallet with spending policies and audit logging. "
            "You always verify budget availability before spending, provide "
            "clear justifications for each payment, and flag any policy "
            "violations immediately."
        ),
        tools=tools,
        verbose=verbose,
    )
    defaults.update(agent_kwargs)
    return Agent(**defaults)


def create_procurement_agent(
    client: SardisClient,
    wallet_id: str,
    *,
    group_id: Optional[str] = None,
    verbose: bool = True,
    **agent_kwargs: Any,
) -> Agent:
    """Create a procurement agent specialized in vendor payments.

    The procurement agent can execute payments, check balances, and validate
    policies.  It is configured with a backstory focused on vendor management,
    cost optimization, and purchase justification.

    Args:
        client: Initialized SardisClient.
        wallet_id: Wallet this agent operates on.
        group_id: Optional group ID for budget monitoring.
        verbose: Enable verbose logging (default True).
        **agent_kwargs: Additional keyword arguments forwarded to ``crewai.Agent``.

    Returns:
        Configured CrewAI Agent for procurement workflows.
    """
    tools = create_sardis_tools(client, wallet_id, group_id=group_id)

    defaults = dict(
        role="Procurement Specialist",
        goal=(
            "Execute approved vendor payments within budget constraints. "
            "Always check group budget before each purchase and provide "
            "clear purchase justifications."
        ),
        backstory=(
            "You are a procurement specialist with a Sardis-managed wallet. "
            "You handle vendor payments for software licenses, API credits, "
            "cloud services, and other operational expenses. You only purchase "
            "items that have been researched and justified. You always check "
            "the budget before spending and ensure each payment has a clear "
            "business purpose recorded in the audit trail."
        ),
        tools=tools,
        verbose=verbose,
    )
    defaults.update(agent_kwargs)
    return Agent(**defaults)


def create_audit_agent(
    client: SardisClient,
    wallet_id: str,
    *,
    group_id: Optional[str] = None,
    verbose: bool = True,
    **agent_kwargs: Any,
) -> Agent:
    """Create a read-only audit agent for reviewing transactions and compliance.

    The audit agent has no payment capabilities -- it can only check balances,
    validate policies, and review group budget status.  This makes it safe for
    compliance monitoring without risk of unauthorized spending.

    Args:
        client: Initialized SardisClient.
        wallet_id: Wallet to audit (read-only access).
        group_id: Optional group ID for budget monitoring.
        verbose: Enable verbose logging (default True).
        **agent_kwargs: Additional keyword arguments forwarded to ``crewai.Agent``.

    Returns:
        Configured CrewAI Agent with read-only Sardis tools.
    """
    tools = create_sardis_tools(
        client, wallet_id, group_id=group_id, read_only=True
    )

    defaults = dict(
        role="Financial Auditor",
        goal=(
            "Review all spending for compliance and budget adherence. "
            "Verify that payments align with policies, flag anomalies, "
            "and produce clear audit reports."
        ),
        backstory=(
            "You are a financial auditor who reviews AI agent spending. "
            "You have read-only access to wallet balances and group budgets "
            "through the Sardis platform. You check that purchases align with "
            "policy, identify budget overruns or suspicious patterns, and "
            "produce compliance summary reports. You cannot execute payments -- "
            "you only observe and report."
        ),
        tools=tools,
        verbose=verbose,
    )
    defaults.update(agent_kwargs)
    return Agent(**defaults)
