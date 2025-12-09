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

## Supported Chains

- Base (mainnet & Sepolia testnet)
- Polygon (mainnet & Amoy testnet)
- Ethereum (mainnet & Sepolia testnet)

## Supported Tokens

- USDC
- USDT
- PYUSD
- EURC

## License

MIT
