"""
Common CrewAI task templates for Sardis payment workflows.

Each factory function creates a ``crewai.Task`` pre-configured with a
description and expected output.  The caller must supply the ``agent`` that
will execute the task.

Example::

    from crewai import Crew
    from sardis_crewai.agents import create_finance_agent, create_audit_agent
    from sardis_crewai.tasks import create_payment_task, create_audit_task

    finance = create_finance_agent(client=client, wallet_id=wallet.wallet_id)
    auditor = create_audit_agent(client=client, wallet_id=wallet.wallet_id)

    pay_task = create_payment_task(
        agent=finance,
        recipient="openai.com",
        amount="25.00",
        purpose="Monthly API credits",
    )
    audit_task = create_audit_task(agent=auditor)

    crew = Crew(agents=[finance, auditor], tasks=[pay_task, audit_task])
    crew.kickoff()
"""
from __future__ import annotations

from typing import Any, List, Optional

from crewai import Agent, Task


def create_payment_task(
    agent: Agent,
    recipient: str,
    amount: str,
    *,
    purpose: str = "",
    token: str = "USDC",
    **task_kwargs: Any,
) -> Task:
    """Create a task to execute a single payment.

    Args:
        agent: CrewAI agent that will perform the payment.
        recipient: Payment destination (address or merchant).
        amount: Payment amount as a string (e.g. ``'25.00'``).
        purpose: Reason for the payment.
        token: Token type (default ``USDC``).
        **task_kwargs: Additional keyword arguments forwarded to ``crewai.Task``.

    Returns:
        Configured Task for a single payment execution.
    """
    purpose_text = f" Purpose: {purpose}." if purpose else ""
    description = (
        f"Execute a payment of {amount} {token} to {recipient}.{purpose_text} "
        f"Before paying, check the wallet balance and verify the payment "
        f"passes policy checks. Report the transaction result including "
        f"TX ID and remaining budget."
    )

    defaults = dict(
        description=description,
        expected_output=(
            "Transaction confirmation with TX ID, amount, recipient, "
            "status, and remaining wallet balance."
        ),
        agent=agent,
    )
    defaults.update(task_kwargs)
    return Task(**defaults)


def create_bulk_payment_task(
    agent: Agent,
    payments: List[dict],
    **task_kwargs: Any,
) -> Task:
    """Create a task to execute multiple payments in sequence.

    Args:
        agent: CrewAI agent that will perform the payments.
        payments: List of payment dicts, each with ``to``, ``amount``,
            and optionally ``token`` and ``purpose`` keys.
        **task_kwargs: Additional keyword arguments forwarded to ``crewai.Task``.

    Returns:
        Configured Task for batch payment execution.
    """
    lines = []
    for i, p in enumerate(payments, 1):
        token = p.get("token", "USDC")
        purpose = p.get("purpose", "")
        purpose_text = f" ({purpose})" if purpose else ""
        lines.append(f"  {i}. {p['amount']} {token} to {p['to']}{purpose_text}")

    payment_list = "\n".join(lines)
    description = (
        f"Execute the following payments in order. Check the wallet balance "
        f"before starting and verify policy compliance for each payment. "
        f"Stop immediately if any payment is rejected.\n\n"
        f"Payments:\n{payment_list}\n\n"
        f"Report results for each payment including TX IDs."
    )

    defaults = dict(
        description=description,
        expected_output=(
            "A summary table of all payments with TX ID, amount, recipient, "
            "status (success/rejected), and final wallet balance."
        ),
        agent=agent,
    )
    defaults.update(task_kwargs)
    return Task(**defaults)


def create_budget_review_task(
    agent: Agent,
    group_id: str,
    **task_kwargs: Any,
) -> Task:
    """Create a task to review group budget status and spending.

    Args:
        agent: CrewAI agent that will perform the review.
        group_id: Group ID to review.
        **task_kwargs: Additional keyword arguments forwarded to ``crewai.Task``.

    Returns:
        Configured Task for budget review.
    """
    description = (
        f"Review the budget status for group '{group_id}'. Check:\n"
        f"  1. Current daily and monthly spending vs. limits\n"
        f"  2. Per-transaction budget caps\n"
        f"  3. Number of transactions today\n"
        f"  4. Remaining budget for the day\n\n"
        f"Produce a clear budget status report with recommendations "
        f"if spending is approaching limits."
    )

    defaults = dict(
        description=description,
        expected_output=(
            "Budget status report with current spending, limits, remaining "
            "budget, and recommendations if approaching limits."
        ),
        agent=agent,
    )
    defaults.update(task_kwargs)
    return Task(**defaults)


def create_audit_task(
    agent: Agent,
    *,
    group_id: Optional[str] = None,
    **task_kwargs: Any,
) -> Task:
    """Create a task to audit recent transactions for compliance.

    Args:
        agent: CrewAI agent (should be an audit agent with read-only tools).
        group_id: Optional group ID to scope the audit.
        **task_kwargs: Additional keyword arguments forwarded to ``crewai.Task``.

    Returns:
        Configured Task for compliance auditing.
    """
    scope = f" for group '{group_id}'" if group_id else ""
    description = (
        f"Audit all recent transactions{scope}. Check:\n"
        f"  1. Each payment has a valid business justification\n"
        f"  2. All spending is within policy limits\n"
        f"  3. No blocked merchants or categories received payments\n"
        f"  4. Group budget (if applicable) has not been exceeded\n"
        f"  5. No suspicious patterns (duplicate payments, unusual amounts)\n\n"
        f"Produce a compliance audit report with findings and recommendations."
    )

    defaults = dict(
        description=description,
        expected_output=(
            "Compliance audit report summarizing: total transactions reviewed, "
            "policy compliance status, any violations or anomalies found, "
            "and recommendations."
        ),
        agent=agent,
    )
    defaults.update(task_kwargs)
    return Task(**defaults)


def create_policy_setup_task(
    agent: Agent,
    policy_description: str,
    **task_kwargs: Any,
) -> Task:
    """Create a task to configure a spending policy from natural language.

    Args:
        agent: CrewAI agent with policy-setting capabilities.
        policy_description: Natural language policy to apply (e.g.
            ``'Max $100 per transaction, daily limit $500'``).
        **task_kwargs: Additional keyword arguments forwarded to ``crewai.Task``.

    Returns:
        Configured Task for policy configuration.
    """
    description = (
        f"Set up a spending policy: '{policy_description}'. "
        f"Apply the policy to the wallet and verify it was configured "
        f"correctly by checking the resulting limits. Report the final "
        f"policy configuration."
    )

    defaults = dict(
        description=description,
        expected_output=(
            "Confirmation of the applied policy with specific limits: "
            "per-transaction cap, daily limit, total limit, and any "
            "merchant restrictions."
        ),
        agent=agent,
    )
    defaults.update(task_kwargs)
    return Task(**defaults)
