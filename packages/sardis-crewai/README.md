# sardis-crewai

CrewAI integration for [Sardis](https://sardis.sh) -- the Payment OS for the Agent Economy.

Build multi-agent financial workflows where AI agents can make real payments, enforce spending policies, and maintain audit trails through the Sardis platform.

## Installation

```bash
pip install sardis-crewai
```

## Quick Start

### Using Individual Tools

```python
from sardis import SardisClient
from sardis_crewai import SardisPayTool, SardisCheckBalanceTool

client = SardisClient(api_key="sk_test_...")
wallet = client.wallets.create(name="my-agent", chain="base", policy="Max $100/day")

# Create tools
pay = SardisPayTool(client=client, wallet_id=wallet.wallet_id)
balance = SardisCheckBalanceTool(client=client, wallet_id=wallet.wallet_id)

# Use with any CrewAI agent
from crewai import Agent

agent = Agent(
    role="Buyer",
    goal="Purchase API credits",
    backstory="You buy software for the team.",
    tools=[pay, balance],
)
```

### Using Pre-configured Agents

```python
from sardis import SardisClient
from sardis_crewai import create_finance_agent, create_audit_agent
from sardis_crewai import create_payment_task, create_audit_task
from crewai import Crew

client = SardisClient(api_key="sk_test_...")
wallet = client.wallets.create(name="finance-bot", chain="base")

# Create agents with sensible defaults
finance = create_finance_agent(client=client, wallet_id=wallet.wallet_id)
auditor = create_audit_agent(client=client, wallet_id=wallet.wallet_id)

# Create tasks
pay_task = create_payment_task(
    agent=finance,
    recipient="openai.com",
    amount="25.00",
    purpose="Monthly API credits",
)
audit_task = create_audit_task(agent=auditor)

# Run the crew
crew = Crew(agents=[finance, auditor], tasks=[pay_task, audit_task])
result = crew.kickoff()
```

### Multi-Agent Team with Group Budgets

```python
from sardis import SardisClient
from sardis_crewai import (
    create_procurement_agent,
    create_audit_agent,
    create_bulk_payment_task,
    create_budget_review_task,
)
from crewai import Crew

client = SardisClient(api_key="sk_test_...")

# Create a shared group budget
group = client.groups.create(
    name="engineering",
    budget={"per_transaction": "200", "daily": "1000", "monthly": "30000"},
)

# Create wallets attached to the group
buyer_wallet = client.wallets.create(
    name="buyer", chain="base", group_id=group.group_id,
)
auditor_wallet = client.wallets.create(
    name="auditor", chain="base", group_id=group.group_id,
)

# Create agents
buyer = create_procurement_agent(
    client=client, wallet_id=buyer_wallet.wallet_id, group_id=group.group_id,
)
auditor = create_audit_agent(
    client=client, wallet_id=auditor_wallet.wallet_id, group_id=group.group_id,
)

# Define tasks
purchase_task = create_bulk_payment_task(
    agent=buyer,
    payments=[
        {"to": "openai.com", "amount": "30.00", "purpose": "API credits"},
        {"to": "anthropic.com", "amount": "25.00", "purpose": "API credits"},
        {"to": "github.com", "amount": "19.00", "purpose": "Copilot subscription"},
    ],
)
review_task = create_budget_review_task(agent=auditor, group_id=group.group_id)

crew = Crew(agents=[buyer, auditor], tasks=[purchase_task, review_task])
result = crew.kickoff()
```

## Available Tools

| Tool | Description |
|------|-------------|
| `SardisPayTool` | Execute payments with policy enforcement and audit logging |
| `SardisCheckBalanceTool` | Check wallet balance, limits, and remaining budget |
| `SardisCheckPolicyTool` | Validate payments against policy without executing |
| `SardisSetPolicyTool` | Set spending policy from natural language description |
| `SardisGroupBudgetTool` | Check shared group budget status across agents |

### Tool Factory

Use `create_sardis_tools()` to generate a tool set in one call:

```python
from sardis_crewai import create_sardis_tools

# All tools (read + write)
tools = create_sardis_tools(client, wallet_id=wallet.wallet_id)

# Read-only tools (for audit agents)
tools = create_sardis_tools(client, wallet_id=wallet.wallet_id, read_only=True)

# With group budget monitoring
tools = create_sardis_tools(client, wallet_id=wallet.wallet_id, group_id="group_abc")
```

## Pre-configured Agents

| Agent Factory | Role | Capabilities |
|---------------|------|-------------|
| `create_finance_agent()` | Finance Manager | Full payment + policy + audit |
| `create_procurement_agent()` | Procurement Specialist | Vendor payments + budget checks |
| `create_audit_agent()` | Financial Auditor | Read-only balance + policy checks |

All agent factories accept `**agent_kwargs` to override any `crewai.Agent` parameter.

## Task Templates

| Task Factory | Purpose |
|-------------|---------|
| `create_payment_task()` | Single payment with pre-checks |
| `create_bulk_payment_task()` | Batch payment execution |
| `create_budget_review_task()` | Group budget status report |
| `create_audit_task()` | Compliance audit of recent transactions |
| `create_policy_setup_task()` | Configure policy from natural language |

## Simulation Mode

By default, Sardis runs in simulation mode -- all payments execute locally without real blockchain transactions. This is ideal for developing and testing CrewAI workflows:

```python
# No API key needed for simulation
client = SardisClient()
wallet = client.wallets.create(name="test-agent", chain="base", initial_balance=1000)
```

To use production mode, provide a real API key and install `sardis-sdk`:

```bash
pip install sardis-sdk
```

```python
client = SardisClient(api_key="sk_live_...")
```

## Links

- [Sardis Documentation](https://sardis.sh/docs)
- [CrewAI Documentation](https://docs.crewai.com)
- [Full Example](https://github.com/EfeDurmaz16/sardis/blob/main/examples/crewai_finance_team.py)
