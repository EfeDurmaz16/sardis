# Python SDK

Official Python SDK for Sardis Payment OS.

## Installation

```bash
pip install sardis-sdk
```

Or with specific integrations:

```bash
# With LangChain
pip install sardis[langchain]

# With OpenAI
pip install sardis[openai]

# With CrewAI
pip install sardis[crewai]

# All integrations
pip install sardis[all]
```

## Quick Start

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")

# Create wallet
wallet = client.wallets.create(
    name="my-agent",
    chain="base",
    policy="Max $500/day"
)

# Execute payment
payment = client.payments.execute(
    wallet_id=wallet.id,
    to="0x1234...",
    amount=50,
    token="USDC"
)

print(f"TX: {payment.tx_hash}")
```

## Client Initialization

### Basic

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")
```

### With Options

```python
client = SardisClient(
    api_key="sk_...",
    environment="production",  # or "testnet"
    timeout=30,                # Request timeout in seconds
    max_retries=3,             # Retry failed requests
    simulation=False           # Enable simulation mode
)
```

### Environment Variables

```python
import os

# Set API key via environment
os.environ["SARDIS_API_KEY"] = "sk_..."

# Client auto-detects from environment
client = SardisClient()
```

## Wallets

### Create Wallet

```python
wallet = client.wallets.create(
    name="my-agent-wallet",
    chain="base",
    policy="Max $500/day, only SaaS vendors",
    metadata={
        "department": "engineering",
        "cost_center": "CC-1234"
    }
)

print(f"Wallet ID: {wallet.id}")
print(f"Address: {wallet.address}")
```

### Get Wallet

```python
wallet = client.wallets.get("wallet_abc123")

print(f"Name: {wallet.name}")
print(f"Chain: {wallet.chain}")
print(f"Policy: {wallet.policy}")
print(f"Trust Score: {wallet.trust_score}")
```

### List Wallets

```python
wallets = client.wallets.list(limit=100, offset=0)

for wallet in wallets:
    print(f"{wallet.name}: {wallet.address}")
```

### Update Policy

```python
client.wallets.update_policy(
    wallet_id="wallet_abc123",
    policy="Max $1000/day, SaaS and cloud only"
)
```

### Freeze/Unfreeze

```python
# Freeze
client.wallets.freeze(
    wallet_id="wallet_abc123",
    reason="Suspected compromise"
)

# Unfreeze
client.wallets.unfreeze("wallet_abc123")
```

### Delete Wallet

```python
client.wallets.delete("wallet_abc123")
```

## Payments

### Execute Payment

```python
payment = client.payments.execute(
    wallet_id="wallet_abc123",
    to="0x1234567890abcdef1234567890abcdef12345678",
    amount=50.0,
    token="USDC",
    purpose="API credits",
    metadata={
        "invoice_id": "INV-001"
    }
)

print(f"Payment ID: {payment.id}")
print(f"TX Hash: {payment.tx_hash}")
print(f"Status: {payment.status}")
```

### Get Payment

```python
payment = client.payments.get("payment_xyz789")

print(f"Amount: {payment.amount} {payment.token}")
print(f"Status: {payment.status}")
print(f"Block: {payment.block_number}")
```

### List Payments

```python
payments = client.payments.list(
    wallet_id="wallet_abc123",
    status="success",
    limit=50
)

for payment in payments:
    print(f"{payment.created_at}: {payment.amount} {payment.token}")
```

### Simulate Payment

Test without executing:

```python
result = client.payments.simulate(
    wallet_id="wallet_abc123",
    to="0x...",
    amount=5000,
    token="USDC"
)

if result.would_succeed:
    print("Payment would succeed")
else:
    print(f"Would fail: {result.violation.message}")
```

### Estimate Gas

```python
estimate = client.payments.estimate_gas(
    wallet_id="wallet_abc123",
    to="0x...",
    amount=50,
    token="USDC"
)

print(f"Gas cost: ${estimate.total_cost_usd}")
```

## Balances

### Get Balance

```python
balance = client.balances.get(
    wallet_id="wallet_abc123",
    token="USDC"
)

print(f"Balance: {balance} USDC")
```

### Get All Balances

```python
balances = client.balances.get_all("wallet_abc123")

for token, amount in balances.items():
    print(f"{token}: {amount}")
```

## Trust & KYA

### Get Trust Score

```python
trust = client.kya.get_trust_score("wallet_abc123")

print(f"Score: {trust.score}/100")
print(f"Level: {trust.level}")  # excellent, good, moderate, poor
```

### Trust History

```python
history = client.kya.trust_history(
    wallet_id="wallet_abc123",
    days=30
)

for entry in history:
    print(f"{entry.date}: {entry.score} ({entry.reason})")
```

### KYA Analysis

```python
analysis = client.kya.analyze("wallet_abc123")

print(f"Trust Score: {analysis.trust_score}")
print(f"Risk Factors: {analysis.risk_factors}")
print(f"Recommendations: {analysis.recommendations}")
```

## Ledger

### List Entries

```python
entries = client.ledger.list(
    wallet_id="wallet_abc123",
    start_date="2026-02-01",
    end_date="2026-02-28"
)

for entry in entries:
    print(f"{entry.timestamp}: {entry.type} {entry.amount} {entry.token}")
```

### Reconcile

```python
report = client.ledger.reconcile(
    wallet_id="wallet_abc123",
    date="2026-02-21"
)

print(f"Opening: {report.opening_balance}")
print(f"Credits: {report.total_credits}")
print(f"Debits: {report.total_debits}")
print(f"Closing: {report.closing_balance}")
```

### Export

```python
export = client.ledger.export(
    wallet_id="wallet_abc123",
    format="csv",
    start_date="2026-01-01",
    end_date="2026-12-31"
)

# Wait for export to complete
while export.status == "processing":
    time.sleep(2)
    export = client.ledger.get_export(export.id)

# Download
if export.status == "complete":
    print(f"Download: {export.download_url}")
```

## Webhooks

### Create Webhook

```python
webhook = client.webhooks.create(
    url="https://your-app.com/sardis-webhook",
    events=[
        "wallet.payment.success",
        "wallet.payment.failed",
        "wallet.policy.violated"
    ],
    secret="whsec_example_placeholder"  # nosecret
)

print(f"Webhook ID: {webhook.id}")
```

### List Webhooks

```python
webhooks = client.webhooks.list()

for webhook in webhooks:
    print(f"{webhook.id}: {webhook.url}")
```

### Delete Webhook

```python
client.webhooks.delete("webhook_abc123")
```

## Error Handling

```python
from sardis.exceptions import (
    SardisException,
    PolicyViolationError,
    InsufficientBalanceError,
    InvalidRequestError,
    AuthenticationError
)

try:
    payment = client.payments.execute(
        wallet_id="wallet_abc123",
        to="0x...",
        amount=10000,
        token="USDC"
    )
except PolicyViolationError as e:
    print(f"Policy error: {e.message}")
    print(f"Limit: {e.limit}")
    print(f"Attempted: {e.attempted}")
except InsufficientBalanceError as e:
    print(f"Balance error: {e.message}")
except AuthenticationError as e:
    print(f"Auth error: {e.message}")
except SardisException as e:
    print(f"Error: {e.message}")
```

## Async Support

```python
import asyncio
from sardis import AsyncSardisClient

async def main():
    client = AsyncSardisClient(api_key="sk_...")

    wallet = await client.wallets.create(
        name="async-wallet",
        chain="base"
    )

    payment = await client.payments.execute(
        wallet_id=wallet.id,
        to="0x...",
        amount=50,
        token="USDC"
    )

    print(f"Payment: {payment.tx_hash}")

asyncio.run(main())
```

## Type Hints

Full type hint support:

```python
from typing import List
from sardis import SardisClient
from sardis.models import Wallet, Payment

client: SardisClient = SardisClient(api_key="sk_...")

wallet: Wallet = client.wallets.create(
    name="typed-wallet",
    chain="base"
)

payments: List[Payment] = client.payments.list(
    wallet_id=wallet.id
)
```

## Context Manager

```python
from sardis import SardisClient

with SardisClient(api_key="sk_...") as client:
    wallet = client.wallets.create(name="temp-wallet", chain="base")
    # Client auto-closes on exit
```

## Pagination

```python
# Manual pagination
offset = 0
limit = 100

while True:
    payments = client.payments.list(
        wallet_id="wallet_abc123",
        limit=limit,
        offset=offset
    )

    if not payments:
        break

    for payment in payments:
        print(payment.id)

    offset += limit

# Or use iterator
for payment in client.payments.iterate(wallet_id="wallet_abc123"):
    print(payment.id)
```

## Logging

```python
import logging
from sardis import SardisClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("sardis")

client = SardisClient(api_key="sk_...", logger=logger)
```

## Testing

```python
import pytest
from sardis import SardisClient

@pytest.fixture
def client():
    return SardisClient(
        api_key="sk_test_...",
        simulation=True  # No real transactions
    )

def test_create_wallet(client):
    wallet = client.wallets.create(
        name="test-wallet",
        chain="base_sepolia"
    )

    assert wallet.id.startswith("wallet_")
    assert wallet.chain == "base_sepolia"
```

## Best Practices

1. **Use environment variables** for API keys
2. **Handle errors explicitly** - Don't catch generic exceptions
3. **Enable retries** for production
4. **Use async** for high-throughput applications
5. **Set timeouts** appropriately
6. **Enable logging** for debugging
7. **Use simulation mode** for testing

## Next Steps

- [TypeScript SDK](typescript.md) - Node.js/TypeScript SDK
- [CLI Reference](cli.md) - Command-line tool
- [API Reference](../api/rest.md) - Raw HTTP API
