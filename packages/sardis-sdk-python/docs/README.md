# Sardis Python SDK Documentation

The official Python SDK for interacting with the Sardis payment platform.

## Installation

```bash
pip install sardis-sdk
```

## Quick Start

```python
from sardis_sdk import SardisClient

# Initialize client
client = SardisClient(
    api_key="sk_your_api_key",
    base_url="https://api.sardis.network",  # Optional
)

# Execute a payment
result = await client.payments.execute(
    from_wallet="wallet_001",
    destination="0x1234567890123456789012345678901234567890",
    amount=100.00,
    token="USDC",
    chain="base_sepolia",
)

print(f"Transaction: {result.chain_tx_hash}")
```

## Configuration

### Environment Variables

```bash
SARDIS_API_KEY=sk_your_api_key
SARDIS_API_BASE_URL=https://api.sardis.network
```

### Client Options

```python
client = SardisClient(
    api_key="sk_...",
    base_url="https://api.sardis.network",
    timeout=30.0,
    max_retries=3,
    retry_delay=1.0,
)
```

## Resources

- [Payments](./payments.md) - Execute and manage payments
- [Holds](./holds.md) - Pre-authorization and captures
- [Webhooks](./webhooks.md) - Event subscriptions
- [Marketplace](./marketplace.md) - A2A service marketplace
- [Transactions](./transactions.md) - Transaction status and history
- [Ledger](./ledger.md) - Audit trail access
- [Error Handling](./errors.md) - Exception handling

## Error Handling

```python
from sardis_sdk.models.errors import APIError, AuthenticationError, RateLimitError

try:
    result = await client.payments.execute(...)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```

## Async Support

The SDK is fully async-native:

```python
import asyncio
from sardis_sdk import SardisClient

async def main():
    client = SardisClient(api_key="sk_...")
    
    # All methods are async
    result = await client.payments.execute(...)
    
    # Close client when done
    await client.close()

asyncio.run(main())
```

## Context Manager

```python
async with SardisClient(api_key="sk_...") as client:
    result = await client.payments.execute(...)
# Client automatically closed
```

