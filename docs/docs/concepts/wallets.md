# Agent Wallets

Non-custodial MPC wallets that enable AI agents to make real financial transactions safely.

## Overview

Every AI agent gets its own **Sardis Wallet** - a non-custodial wallet powered by Turnkey's MPC (Multi-Party Computation) infrastructure. The agent can initiate transactions, but:

- Private keys never leave secure enclaves
- Spending policies enforced before signing
- Full audit trail of all actions
- You maintain custody (not Sardis)

## Wallet Architecture

```
┌─────────────────────────────────────┐
│         AI Agent                    │
│  (OpenAI, Claude, LangChain, etc)   │
└──────────────┬──────────────────────┘
               │
               │ API Request
               ▼
┌─────────────────────────────────────┐
│      Sardis Policy Engine           │
│  • Validate spending policy         │
│  • Check KYA trust score            │
│  • Verify compliance                │
└──────────────┬──────────────────────┘
               │
               │ Approved
               ▼
┌─────────────────────────────────────┐
│      Turnkey MPC Wallet             │
│  • Generate signature in enclave    │
│  • Never expose private key         │
└──────────────┬──────────────────────┘
               │
               │ Signed TX
               ▼
┌─────────────────────────────────────┐
│         Blockchain                  │
│  Base, Polygon, Ethereum, etc       │
└─────────────────────────────────────┘
```

## Creating a Wallet

=== "Python"

    ```python
    from sardis import SardisClient

    client = SardisClient(api_key="sk_...")

    wallet = client.wallets.create(
        name="my-agent-wallet",
        chain="base",
        policy="Max $500/day, only SaaS vendors"
    )

    print(f"Wallet ID: {wallet.id}")
    print(f"Address: {wallet.address}")
    print(f"Chain: {wallet.chain}")
    ```

=== "TypeScript"

    ```typescript
    import { SardisClient } from '@sardis/sdk';

    const client = new SardisClient({ apiKey: 'sk_...' });

    const wallet = await client.wallets.create({
      name: 'my-agent-wallet',
      chain: 'base',
      policy: 'Max $500/day, only SaaS vendors',
    });

    console.log(`Wallet: ${wallet.id}`);
    console.log(`Address: ${wallet.address}`);
    ```

=== "CLI"

    ```bash
    sardis wallets create \
      --name my-agent-wallet \
      --chain base \
      --policy "Max $500/day, only SaaS vendors"
    ```

## Wallet Properties

```python
wallet = client.wallets.get("wallet_abc123")

# Core properties
wallet.id              # "wallet_abc123"
wallet.name            # "my-agent-wallet"
wallet.address         # "0x1234..."
wallet.chain           # "base"

# Policy & trust
wallet.policy          # "Max $500/day, only SaaS vendors"
wallet.trust_score     # 85

# Balances (multi-token)
wallet.balances        # {"USDC": "1500.00", "EURC": "200.00"}

# Status
wallet.status          # "active" | "frozen" | "suspended"
wallet.created_at      # "2026-02-21T10:00:00Z"
```

## Multi-Chain Support

Sardis wallets can be created on any supported chain:

| Chain | Network ID | Testnet |
|-------|-----------|---------|
| Base | `base` | `base_sepolia` |
| Polygon | `polygon` | `polygon_amoy` |
| Ethereum | `ethereum` | `ethereum_sepolia` |
| Arbitrum | `arbitrum` | `arbitrum_sepolia` |
| Optimism | `optimism` | `optimism_sepolia` |

```python
# Create wallets on different chains
base_wallet = client.wallets.create(name="base-agent", chain="base")
polygon_wallet = client.wallets.create(name="polygon-agent", chain="polygon")
eth_wallet = client.wallets.create(name="eth-agent", chain="ethereum")
```

## Funding Wallets

Send stablecoins to the wallet address:

```python
wallet = client.wallets.create(name="agent", chain="base")

print(f"Send USDC to: {wallet.address}")
# Send USDC on Base network to this address

# Check balance
balance = client.wallets.get_balance(wallet.id, token="USDC")
print(f"Balance: {balance} USDC")
```

For testing, use testnets:

```python
# Create testnet wallet
wallet = client.wallets.create(
    name="test-agent",
    chain="base_sepolia"  # Testnet
)

# Get testnet USDC from faucet (link provided in response)
print(wallet.faucet_url)
```

## Making Payments

```python
# Execute a payment
result = client.payments.execute(
    wallet_id=wallet.id,
    to="0x1234...merchant_address",
    amount=50,
    token="USDC",
    purpose="API credits"
)

print(f"Transaction: {result.tx_hash}")
print(f"Status: {result.status}")  # "success"
print(f"Block: {result.block_number}")
```

## Wallet Operations

### Get Wallet

```python
wallet = client.wallets.get("wallet_abc123")
```

### List Wallets

```python
wallets = client.wallets.list()

for wallet in wallets:
    print(f"{wallet.name}: {wallet.address}")
```

### Update Policy

```python
client.wallets.update_policy(
    wallet_id="wallet_abc123",
    policy="Max $1000/day, SaaS and cloud providers only"
)
```

### Freeze Wallet

Temporarily disable all transactions:

```python
client.wallets.freeze(
    wallet_id="wallet_abc123",
    reason="Suspected compromise"
)
```

### Unfreeze Wallet

```python
client.wallets.unfreeze("wallet_abc123")
```

### Delete Wallet

**Warning:** This is permanent. Funds should be withdrawn first.

```python
# Withdraw all funds first
client.payments.execute(
    wallet_id=wallet.id,
    to="your_safe_address",
    amount=wallet.balances["USDC"],
    token="USDC"
)

# Then delete
client.wallets.delete("wallet_abc123")
```

## Transaction History

```python
# Get all transactions for a wallet
txs = client.wallets.transactions(wallet_id="wallet_abc123")

for tx in txs:
    print(f"{tx.created_at}: {tx.amount} {tx.token} to {tx.recipient}")

# Filter by date
txs = client.wallets.transactions(
    wallet_id="wallet_abc123",
    start_date="2026-02-01",
    end_date="2026-02-28"
)

# Filter by status
pending_txs = client.wallets.transactions(
    wallet_id="wallet_abc123",
    status="pending"
)
```

## Multi-Token Wallets

A single wallet can hold multiple tokens:

```python
wallet = client.wallets.create(name="multi-token", chain="base")

# Fund with multiple tokens
# Send USDC to wallet.address
# Send EURC to wallet.address (same address)

# Check all balances
balances = client.wallets.get_balances(wallet.id)
print(balances)  # {"USDC": "1000.00", "EURC": "500.00"}

# Pay with specific token
client.payments.execute(
    wallet_id=wallet.id,
    to="0x...",
    amount=50,
    token="EURC"  # Specify token
)
```

## Wallet Metadata

Store custom metadata with wallets:

```python
wallet = client.wallets.create(
    name="procurement-agent",
    chain="base",
    metadata={
        "department": "engineering",
        "cost_center": "CC-1234",
        "owner_email": "team@example.com",
        "environment": "production"
    }
)

# Retrieve metadata
wallet = client.wallets.get(wallet.id)
print(wallet.metadata["department"])  # "engineering"
```

## Wallet Events & Webhooks

Subscribe to wallet events:

```python
# Configure webhook
client.webhooks.create(
    url="https://your-app.com/sardis-webhook",
    events=[
        "wallet.created",
        "wallet.funded",
        "wallet.payment.success",
        "wallet.payment.failed",
        "wallet.frozen",
        "wallet.policy.violated"
    ]
)
```

Webhook payload example:

```json
{
  "event": "wallet.payment.success",
  "wallet_id": "wallet_abc123",
  "payment": {
    "id": "payment_xyz789",
    "amount": "50.00",
    "token": "USDC",
    "to": "0x1234...",
    "tx_hash": "0xabcd...",
    "timestamp": "2026-02-21T10:30:00Z"
  }
}
```

## Gas Management

Sardis automatically manages gas for all transactions:

- Gas fees paid in native token (ETH, MATIC, etc)
- Sardis subsidizes gas for wallets with high trust scores
- Gas estimates provided before execution

```python
# Get gas estimate
estimate = client.payments.estimate_gas(
    wallet_id=wallet.id,
    to="0x...",
    amount=50,
    token="USDC"
)

print(f"Estimated gas: {estimate.gas_price} gwei")
print(f"Total cost: {estimate.total_cost_usd} USD")
```

## Security Features

1. **Non-Custodial** - You control the wallet, not Sardis
2. **MPC Signing** - Private keys never reconstructed
3. **Policy Firewall** - Every transaction validated
4. **Rate Limiting** - Prevent transaction spam
5. **Anomaly Detection** - Behavioral monitoring via KYA
6. **Audit Trail** - Immutable transaction history

## Best Practices

1. **Start with testnet** - Use `base_sepolia` for testing
2. **One wallet per agent** - Don't share wallets between agents
3. **Set conservative policies** - Start restrictive, expand later
4. **Monitor trust scores** - Low scores indicate issues
5. **Use metadata** - Tag wallets for accounting/tracking
6. **Enable webhooks** - Real-time monitoring
7. **Withdraw funds regularly** - Don't keep large balances
8. **Test policies in simulation** - Validate before production

## Troubleshooting

### Wallet Not Funded

```python
# Check balance
balance = client.wallets.get_balance(wallet.id, token="USDC")

if balance == 0:
    print(f"Send USDC to: {wallet.address}")
    print(f"Network: {wallet.chain}")
```

### Transaction Failed

```python
try:
    result = client.payments.execute(...)
except PolicyViolationError as e:
    print(f"Policy violation: {e.message}")
except InsufficientBalanceError as e:
    print(f"Insufficient balance: {e.message}")
except GasEstimationError as e:
    print(f"Gas error: {e.message}")
```

### Wallet Frozen

```python
wallet = client.wallets.get(wallet_id)

if wallet.status == "frozen":
    print(f"Reason: {wallet.freeze_reason}")
    # Contact support or unfreeze if authorized
    client.wallets.unfreeze(wallet_id)
```

## Next Steps

- [Spending Policies](policies.md) - Define transaction guardrails
- [KYA Trust Scoring](kya.md) - Behavioral monitoring
- [API Reference](../api/rest.md) - Complete wallet API docs
