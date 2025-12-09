# Payments

Execute and manage stablecoin payments on supported chains.

## Execute Payment

```python
result = await client.payments.execute(
    from_wallet="wallet_001",
    destination="0x1234567890123456789012345678901234567890",
    amount=100.00,
    token="USDC",
    chain="base_sepolia",
    purpose="Product purchase",
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_wallet` | str | Yes | Source wallet ID |
| `destination` | str | Yes | Destination address |
| `amount` | float | Yes | Amount to send |
| `token` | str | No | Token (default: USDC) |
| `chain` | str | No | Chain (default: base_sepolia) |
| `purpose` | str | No | Payment description |
| `idempotency_key` | str | No | Unique key for deduplication |

### Response

```python
PaymentResult(
    ledger_tx_id="tx_abc123...",
    chain_tx_hash="0x1234...",
    chain="base_sepolia",
    status="confirmed",
    amount="100.00",
    token="USDC",
    compliance_provider="rules",
)
```

## Execute AP2 Mandate

Execute a full AP2 mandate bundle with intent, cart, and payment mandates:

```python
result = await client.payments.execute_mandate(
    intent={
        "mandate_id": "intent_001",
        "issuer": "user_123",
        "subject": "agent_456",
        # ... full intent mandate
    },
    cart={
        "mandate_id": "cart_001",
        # ... full cart mandate
    },
    payment={
        "mandate_id": "payment_001",
        # ... full payment mandate
    },
)
```

## Get Payment Status

```python
status = await client.payments.get_status(
    tx_hash="0x1234567890abcdef...",
    chain="base_sepolia",
)

print(f"Status: {status.status}")  # pending, confirming, confirmed, failed
print(f"Confirmations: {status.confirmations}")
```

## Estimate Gas

```python
estimate = await client.payments.estimate_gas(
    chain="base_sepolia",
    amount=100.00,
    token="USDC",
)

print(f"Gas limit: {estimate.gas_limit}")
print(f"Estimated cost: {estimate.estimated_cost_wei} wei")
```

## Supported Chains

| Chain | Chain ID | Tokens |
|-------|----------|--------|
| `base_sepolia` | 84532 | USDC |
| `base` | 8453 | USDC |
| `polygon_amoy` | 80002 | USDC |
| `polygon` | 137 | USDC, USDT |
| `ethereum_sepolia` | 11155111 | USDC |

## Idempotency

Use idempotency keys to prevent duplicate payments:

```python
# First call
result1 = await client.payments.execute(
    from_wallet="wallet_001",
    destination="0x...",
    amount=100.00,
    idempotency_key="order_12345",
)

# Second call with same key returns cached result
result2 = await client.payments.execute(
    from_wallet="wallet_001",
    destination="0x...",
    amount=100.00,
    idempotency_key="order_12345",
)

assert result1.ledger_tx_id == result2.ledger_tx_id
```

