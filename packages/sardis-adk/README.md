# sardis-adk

Google Agent Development Kit (ADK) integration for [Sardis](https://sardis.sh) -- the Payment OS for the Agent Economy.

Give your Google ADK agents the ability to make real payments, check balances, enforce spending policies, and review transaction history through Sardis.

## Installation

```bash
pip install sardis-adk
```

## Quick Start

### Option 1: Pre-configured Agent

The fastest way to get a payment-capable agent:

```python
from sardis_adk import create_sardis_agent

agent = create_sardis_agent(
    api_key="sk_test_...",
    wallet_id="wallet_abc123",
    model="gemini-2.0-flash",
)

# Use with ADK runner
from google.adk.runners import InMemoryRunner

runner = InMemoryRunner(agent=agent)
```

### Option 2: Toolkit (Bring Your Own Agent)

Add Sardis tools to any existing ADK agent:

```python
from google.adk import Agent
from sardis_adk import SardisToolkit

toolkit = SardisToolkit(api_key="sk_test_...", wallet_id="wallet_abc123")

agent = Agent(
    name="my_agent",
    model="gemini-2.0-flash",
    tools=toolkit.get_tools(),
    instruction="You are a helpful assistant that can make payments.",
)
```

### Option 3: Individual Tools

Use specific tools without the toolkit:

```python
from sardis_adk.tools import sardis_pay, sardis_check_balance, configure
from sardis import SardisClient

client = SardisClient(api_key="sk_test_...")
wallet = client.wallets.create(name="my-agent", chain="base", policy="Max $100/day")

configure(client, wallet.id)

# Now use tools directly
result = sardis_pay(to="openai.com", amount="25.00", purpose="API credits")
print(result["success"])  # True
```

## Available Tools

| Tool | Description |
|------|-------------|
| `sardis_pay` | Execute a payment with automatic policy enforcement |
| `sardis_check_balance` | Check wallet balance and spending limits |
| `sardis_check_policy` | Validate whether a payment would be allowed (dry-run) |
| `sardis_set_policy` | Set or update spending policy using natural language |
| `sardis_list_transactions` | View recent transaction history |

## Tool Details

### sardis_pay

```python
sardis_pay(
    to="openai.com",        # Recipient address or merchant
    amount="25.00",          # Payment amount
    token="USDC",            # Token type (USDC, USDT, PYUSD, EURC)
    purpose="API credits",   # Reason for payment
)
# Returns: {"success": True, "tx_id": "tx_...", "balance_after": 975.0, ...}
```

### sardis_check_balance

```python
sardis_check_balance(token="USDC", chain="base")
# Returns: {"balance": 1000.0, "remaining": 900.0, "limit_per_tx": 100.0, ...}
```

### sardis_check_policy

```python
sardis_check_policy(to="openai.com", amount="25.00", token="USDC")
# Returns: {"allowed": True, "reason": "All policy checks passed", ...}
```

### sardis_set_policy

```python
sardis_set_policy(policy_text="Max $50 per transaction, daily limit $500")
# Returns: {"success": True, "limit_per_tx": 50.0, "limit_total": 500.0, ...}
```

### sardis_list_transactions

```python
sardis_list_transactions(limit=10)
# Returns: {"count": 3, "transactions": [{"tx_id": "tx_...", ...}, ...]}
```

## Simulation Mode

By default, Sardis runs in simulation mode -- no real money moves and no API key is required. This is ideal for development and testing:

```python
from sardis_adk import SardisToolkit

# Simulation mode (no real transactions)
toolkit = SardisToolkit(api_key="sk_test_demo", wallet_id="wallet_abc")
tools = toolkit.get_tools()
```

When you are ready for production, use a real API key and Sardis will execute on-chain transactions through non-custodial MPC wallets.

## Combining with Other Tools

Sardis tools work alongside any other ADK tools:

```python
from google.adk import Agent
from google.adk.tools import google_search
from sardis_adk import SardisToolkit

toolkit = SardisToolkit(api_key="sk_test_...", wallet_id="wallet_abc")

agent = Agent(
    name="research_and_pay",
    model="gemini-2.0-flash",
    tools=[google_search, *toolkit.get_tools()],
    instruction="Research products and make purchases when instructed.",
)
```

## Requirements

- Python 3.11+
- `sardis >= 0.3`
- `google-adk >= 0.3`

## Links

- [Sardis Documentation](https://sardis.sh/docs)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [GitHub Repository](https://github.com/EfeDurmaz16/sardis)
