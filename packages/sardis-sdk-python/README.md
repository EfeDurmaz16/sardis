# Sardis Python SDK

The official Python SDK for the Sardis stablecoin execution layer. Enables AI agents to execute programmable payments using stablecoins across multiple chains.

## Installation

```bash
pip install sardis-sdk
```

## Quick Start

```python
import asyncio
from decimal import Decimal
from sardis_sdk import SardisClient

async def main():
    async with SardisClient(
        base_url="https://api.sardis.network",
        api_key="your-api-key",
    ) as client:
        # Check API health
        health = await client.health()
        print(f"API Status: {health['status']}")
        
        # Execute a payment mandate
        result = await client.payments.execute_mandate({
            "mandate_id": "mandate_123",
            "subject": "wallet_abc",
            "destination": "0x...",
            "amount_minor": 10000000,  # $10.00 USDC (6 decimals)
            "token": "USDC",
            "chain": "base",
        })
        print(f"Payment executed: {result.tx_hash}")

asyncio.run(main())
```

## Features

### Payments

Execute single mandates or full AP2 payment bundles:

```python
# Execute AP2 bundle (Intent → Cart → Payment)
result = await client.payments.execute_ap2(
    intent=intent_mandate,
    cart=cart_mandate,
    payment=payment_mandate,
)
```

### Holds (Pre-Authorization)

Create, capture, and void pre-authorization holds:

```python
# Create a hold
hold = await client.holds.create(
    wallet_id="wallet_123",
    amount=Decimal("100.00"),
    token="USDC",
    merchant_id="merchant_456",
    duration_hours=24,
)

# Capture the hold (complete payment)
captured = await client.holds.capture(hold.hold_id, amount=Decimal("95.00"))

# Or void the hold (cancel)
voided = await client.holds.void(hold.hold_id)
```

### Webhooks

Manage webhook subscriptions for real-time events:

```python
# Create a webhook subscription
webhook = await client.webhooks.create(
    url="https://your-server.com/webhooks",
    events=["payment.completed", "hold.captured"],
)

# List deliveries
deliveries = await client.webhooks.list_deliveries(webhook.webhook_id)
```

### Marketplace (A2A)

Discover and interact with agent-to-agent services:

```python
# List available services
services = await client.marketplace.list_services(
    category=ServiceCategory.AI,
)

# Create an offer
offer = await client.marketplace.create_offer(
    service_id="service_123",
    consumer_agent_id="agent_456",
    total_amount=Decimal("50.00"),
)

# Accept an offer (as provider)
await client.marketplace.accept_offer(offer.offer_id)
```

### Transactions

Get gas estimates and transaction status:

```python
# Estimate gas
estimate = await client.transactions.estimate_gas(
    chain="base",
    to_address="0x...",
    amount=Decimal("100.00"),
    token="USDC",
)
print(f"Estimated cost: {estimate.estimated_cost_wei} wei")

# Check transaction status
status = await client.transactions.get_status(
    tx_hash="0x...",
    chain="base",
)
```

### Ledger

Query the append-only ledger:

```python
# List ledger entries
entries = await client.ledger.list_entries(wallet_id="wallet_123")

# Verify an entry
verification = await client.ledger.verify_entry(tx_id="tx_123")
```

## Error Handling

The SDK provides typed exceptions for common error cases:

```python
from sardis_sdk import (
    SardisError,
    APIError,
    AuthenticationError,
    RateLimitError,
    InsufficientBalanceError,
)

try:
    result = await client.payments.execute_mandate(mandate)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after} seconds")
except InsufficientBalanceError as e:
    print(f"Need {e.required} {e.currency}, have {e.available}")
except APIError as e:
    print(f"API error [{e.code}]: {e.message}")
```

## Configuration

```python
client = SardisClient(
    base_url="https://api.sardis.network",  # API base URL
    api_key="sk_live_...",                   # Your API key
    timeout=30,                              # Request timeout (seconds)
    max_retries=3,                           # Max retry attempts
)
```

## Agents

Create and manage AI agents with spending policies:

```python
# Create an agent
agent = await client.agents.create(
    name="Invoice Processing Agent",
    description="Processes invoices and pays vendors",
    spending_limits={
        "per_transaction": "500.00",
        "daily": "5000.00",
        "monthly": "50000.00",
    },
    policy={
        "blocked_categories": ["gambling", "adult"],
        "approval_threshold": "1000.00",
    },
)

# Update spending limits
await client.agents.update(
    agent.agent_id,
    spending_limits={"daily": "10000.00"},
)

# List agents
agents = await client.agents.list(is_active=True, limit=50)
```

## Wallets

Manage non-custodial MPC wallets:

```python
# Create a wallet for an agent
wallet = await client.wallets.create(
    agent_id=agent.agent_id,
    mpc_provider="turnkey",  # or "fireblocks"
    limit_per_tx="500.00",
    limit_total="10000.00",
)

# Get wallet balance (read from chain)
balance = await client.wallets.get_balance(
    wallet_id=wallet.wallet_id,
    chain="base",
    token="USDC",
)
print(f"Balance: {balance.balance} USDC")

# Set chain address
await client.wallets.set_address(
    wallet_id=wallet.wallet_id,
    chain="base",
    address="0x...",
)
```

## Supported Chains

| Chain | Mainnet | Testnet |
|-------|---------|---------|
| Base | `base` | `base_sepolia` |
| Polygon | `polygon` | `polygon_amoy` |
| Ethereum | `ethereum` | `ethereum_sepolia` |
| Arbitrum | `arbitrum` | `arbitrum_sepolia` |
| Optimism | `optimism` | `optimism_sepolia` |

> **Note:** Solana support is planned but not yet implemented.

## Supported Tokens

- **USDC** - USD Coin (Circle)
- **USDT** - Tether USD
- **PYUSD** - PayPal USD
- **EURC** - Euro Coin (Circle)

## Type Hints

The SDK is fully typed with Python type hints:

```python
from sardis_sdk.models import (
    Chain,           # Literal type for supported chains
    Token,           # Literal type for supported tokens
    MPCProvider,     # Literal type for MPC providers
    ChainEnum,       # Enum for chain selection
    Payment,
    Wallet,
    Agent,
)

# Use type hints for better IDE support
chain: Chain = "base"
token: Token = "USDC"
```

## Framework Integrations

### LangChain

```python
from sardis_sdk.integrations.langchain import SardisToolkit

toolkit = SardisToolkit(client=client)
tools = toolkit.get_tools()

# Use with LangChain agent
agent = create_openai_functions_agent(llm, tools, prompt)
```

### LlamaIndex

```python
from sardis_sdk.integrations.llamaindex import SardisToolSpec

tool_spec = SardisToolSpec(client=client)
tools = tool_spec.to_tool_list()

# Use with LlamaIndex agent
agent = OpenAIAgent.from_tools(tools)
```

### OpenAI Function Calling

```python
from sardis_sdk.integrations.openai import sardis_functions, handle_sardis_call

# Get function definitions
functions = sardis_functions(client)

# Handle function calls
result = await handle_sardis_call(client, function_name, arguments)
```

## License

MIT
