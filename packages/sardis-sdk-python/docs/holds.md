# Holds (Pre-Authorization)

Create, capture, and void holds (pre-authorizations) on wallets.

## Create Hold

Reserve funds for a future transaction:

```python
hold = await client.holds.create(
    wallet_id="wallet_001",
    amount=100.00,
    token="USDC",
    merchant_id="merchant_123",
    purpose="Restaurant pre-auth",
    expiration_hours=24,
)

print(f"Hold ID: {hold.hold_id}")
print(f"Expires: {hold.expires_at}")
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `wallet_id` | str | Yes | Wallet to hold funds from |
| `amount` | float | Yes | Amount to hold |
| `token` | str | No | Token (default: USDC) |
| `merchant_id` | str | No | Merchant identifier |
| `purpose` | str | No | Hold description |
| `expiration_hours` | int | No | Hours until expiry (default: 24) |

### Response

```python
Hold(
    hold_id="hold_abc123",
    wallet_id="wallet_001",
    amount="100.00",
    token="USDC",
    status="active",
    merchant_id="merchant_123",
    purpose="Restaurant pre-auth",
    expires_at="2025-12-09T00:00:00Z",
    created_at="2025-12-08T00:00:00Z",
)
```

## Get Hold

```python
hold = await client.holds.get("hold_abc123")

print(f"Status: {hold.status}")
print(f"Amount: {hold.amount} {hold.token}")
```

## Capture Hold

Capture all or part of a hold:

```python
# Full capture
result = await client.holds.capture("hold_abc123")

# Partial capture
result = await client.holds.capture(
    "hold_abc123",
    amount=75.00,  # Capture less than held amount
)

print(f"Captured: {result.captured_amount}")
print(f"Status: {result.status}")  # "captured"
```

## Void Hold

Cancel a hold and release funds:

```python
result = await client.holds.void("hold_abc123")

print(f"Status: {result.status}")  # "voided"
```

## List Holds

### By Wallet

```python
holds = await client.holds.list_by_wallet("wallet_001")

for hold in holds:
    print(f"{hold.hold_id}: {hold.amount} ({hold.status})")
```

### Active Holds

```python
active_holds = await client.holds.list_active()

for hold in active_holds:
    print(f"{hold.hold_id} expires at {hold.expires_at}")
```

## Hold Status Lifecycle

```
created → active → captured
                 ↘ voided
                 ↘ expired
```

## Error Handling

```python
from sardis_sdk.models.errors import APIError

try:
    # Try to capture already captured hold
    await client.holds.capture("hold_already_captured")
except APIError as e:
    if e.status_code == 400:
        print("Hold already captured or voided")
```

## Use Cases

### Hotel Pre-Authorization

```python
# Check-in: Create hold for incidentals
hold = await client.holds.create(
    wallet_id="guest_wallet",
    amount=500.00,
    merchant_id="hotel_123",
    purpose="Incidentals",
    expiration_hours=168,  # 7 days
)

# Check-out: Capture actual charges
result = await client.holds.capture(
    hold.hold_id,
    amount=127.50,  # Actual minibar charges
)
```

### Restaurant Pre-Auth

```python
# Create hold when presenting bill
hold = await client.holds.create(
    wallet_id="diner_wallet",
    amount=150.00,  # Estimated total + tip
    merchant_id="restaurant_456",
)

# Capture with tip included
final_amount = 127.50 + 25.00  # Bill + tip
result = await client.holds.capture(hold.hold_id, amount=final_amount)
```

