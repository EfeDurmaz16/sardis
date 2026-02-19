# sardis-langchain

LangChain integration for **Sardis** -- the Payment OS for the Agent Economy.

Gives your LangChain agents the ability to make real, policy-enforced stablecoin payments through Sardis MPC wallets.

## Installation

```bash
pip install sardis-langchain
```

## Quick Start

```python
from sardis import SardisClient
from sardis_langchain import SardisToolkit

# 1. Initialize Sardis
client = SardisClient(api_key="sk_...")
wallet = client.wallets.create(
    name="procurement-agent",
    chain="base",
    policy="Max $100 per transaction, daily limit $500",
)

# 2. Create LangChain tools
toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
tools = toolkit.get_tools()

# 3. Attach to any LangChain agent
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_react_agent(llm, tools, your_prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "Pay $30 to Anthropic for API credits and $15 to GitHub for Copilot"
})
```

## Available Tools

| Tool | Name | Description |
|------|------|-------------|
| `SardisPayTool` | `sardis_pay` | Execute a policy-enforced payment |
| `SardisCheckBalanceTool` | `sardis_check_balance` | Check wallet balance and limits |
| `SardisCheckPolicyTool` | `sardis_check_policy` | Dry-run a payment against policy |
| `SardisSetPolicyTool` | `sardis_set_policy` | Set spending policy from natural language |
| `SardisListTransactionsTool` | `sardis_list_transactions` | View recent transaction history |

## Toolkit Options

### Full toolkit (all 5 tools)

```python
toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
tools = toolkit.get_tools()
```

### Payment-only tools (3 tools)

```python
tools = toolkit.get_payment_tools()  # pay + balance + policy check
```

### Individual tools

```python
from sardis_langchain import SardisPayTool, SardisCheckBalanceTool

pay_tool = SardisPayTool(client=client, wallet_id=wallet.id)
balance_tool = SardisCheckBalanceTool(client=client, wallet_id=wallet.id)
```

## Callback Handler

Track Sardis operations with the built-in callback handler:

```python
from sardis_langchain import SardisCallbackHandler

handler = SardisCallbackHandler()
executor = AgentExecutor(agent=agent, tools=tools, callbacks=[handler])

# After execution, inspect the audit trail
for record in handler.get_payment_records():
    print(record)
```

## How Policy Enforcement Works

Every payment goes through Sardis's policy engine before execution:

```
Agent calls sardis_pay(to="openai.com", amount="25.00")
    |
    v
Policy Engine checks:
    1. Per-transaction limit  -> Is $25 under the cap?
    2. Balance check          -> Enough funds?
    3. Total spending limit   -> Under lifetime cap?
    4. Wallet active          -> Is the wallet enabled?
    |
    v
PASS -> Execute payment, return tx_hash
FAIL -> Return rejection reason (no funds move)
```

## Simulation Mode

By default, `SardisClient` runs in simulation mode -- all operations execute locally without network calls. This is ideal for prototyping and testing agent payment flows.

```python
# No API key needed for simulation
client = SardisClient()
wallet = client.wallets.create(name="test-agent", chain="base", policy="Max $50/tx")

toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
# All tools work locally -- no real money moves
```

## Links

- [Sardis Documentation](https://sardis.sh/docs)
- [GitHub Repository](https://github.com/EfeDurmaz16/sardis)
- [LangChain Documentation](https://python.langchain.com/)
