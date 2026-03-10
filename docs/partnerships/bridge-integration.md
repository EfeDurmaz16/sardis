# Bridge Integration Spec

## Partner: Bridge.xyz (USDC-to-Fiat Off-Ramp)

**Status:** Production-ready
**Package:** `packages/sardis-cards/src/sardis_cards/offramp.py`
**Provider Class:** `BridgeOfframpProvider` (implements `OfframpProviderBase`)

---

## 1. Overview

Bridge.xyz provides the primary stablecoin-to-fiat off-ramp infrastructure for Sardis. The `BridgeOfframpProvider` enables Sardis to convert USDC and other stablecoins into fiat currency (USD, EUR, BRL) and deliver funds via multiple payment rails including ACH, SEPA, PIX, and wire transfer. This is a critical component of the card funding pipeline: stablecoins held in agent wallets are off-ramped to fiat to fund Stripe Issuing balances for virtual card spending.

### Key Capabilities

| Feature | Status | Details |
|---------|--------|---------|
| USDC-to-USD off-ramp | Production | Primary flow for USD card funding |
| USDC-to-EUR off-ramp | Production | Via Bridge FX; EUR cards via Striga |
| Multi-rail delivery | Production | ACH, wire, SEPA, PIX |
| Quote system | Production | 5-minute quote validity |
| Deposit address generation | Production | Per-chain, per-token deposit addresses |
| HMAC-SHA256 authentication | Production | Signed API requests |
| Velocity limits | Production | Configurable daily/weekly/monthly caps |
| Sandbox environment | Available | Full test flow without real funds |

---

## 2. Architecture

### 2.1 Off-Ramp Pipeline

```
Agent USDC Wallet (Base, Polygon, Ethereum, etc.)
    |
    v (1) Get Quote
BridgeOfframpProvider.get_quote()
    |-- source: USDC on Base
    |-- destination: USD via ACH
    |-- returns: OfframpQuote (quote_id, exchange_rate, fee, expiry)
    |
    v (2) Execute Off-Ramp
BridgeOfframpProvider.execute_offramp()
    |-- Sardis sends USDC to Bridge deposit address
    |-- Bridge converts and initiates fiat transfer
    |-- returns: OfframpTransaction (transaction_id, status=PROCESSING)
    |
    v (3) Fiat Settlement
Bridge delivers USD to destination:
    +-- ACH transfer to bank account (1-2 days)
    +-- Wire transfer (same day)
    +-- SEPA transfer for EUR (1 day)
    +-- PIX for BRL (instant)
    |
    v (4) Card Funding
StripeIssuingProvider.fund_card()
    |-- Fiat deposited to Stripe Issuing balance
    |-- Card spending limits updated
    |
    v
Card ready for agent spending
```

### 2.2 Provider Interface

`BridgeOfframpProvider` implements the `OfframpProviderBase` abstract class:

```python
class OfframpProviderBase(ABC):
    @abstractmethod
    async def get_quote(self, input_token, input_amount_minor, input_chain, output_currency) -> OfframpQuote

    @abstractmethod
    async def execute_offramp(self, quote, source_address, destination_account) -> OfframpTransaction

    @abstractmethod
    async def get_transaction_status(self, transaction_id) -> OfframpTransaction

    @abstractmethod
    async def get_deposit_address(self, chain, token) -> str
```

---

## 3. API Integration

### 3.1 Authentication

Bridge uses HMAC-SHA256 request signing:

```
Signature = HMAC-SHA256(
    key = API_SECRET,
    message = TIMESTAMP + METHOD + PATH + BODY
)

Headers:
    Content-Type: application/json
    Api-Key: <API_KEY>
    Api-Timestamp: <UNIX_TIMESTAMP>
    Api-Signature: <HMAC_SIGNATURE>
```

### 3.2 Quote Flow

```python
provider = BridgeOfframpProvider(
    api_key="bridge_api_key",
    api_secret="bridge_api_secret",
    environment="production",  # or "sandbox"
)

# Get a quote for converting 1000 USDC to USD
quote = await provider.get_quote(
    input_token="USDC",
    input_amount_minor=1_000_000_000,  # 1000 USDC in minor units (6 decimals)
    input_chain="base",
    output_currency="USD",
)

# quote.quote_id: "bridge_quote_..."
# quote.output_amount_cents: 99500  ($995.00 after 0.5% fee)
# quote.exchange_rate: Decimal("1.0")
# quote.fee_cents: 500  ($5.00)
# quote.expires_at: datetime (5 minutes from now)
```

### 3.3 Execution Flow

```python
# Execute the off-ramp
tx = await provider.execute_offramp(
    quote=quote,
    source_address="0xAgentWalletAddress",
    destination_account="bank_account_id",
)

# tx.transaction_id: "bridge_transfer_..."
# tx.status: OfframpStatus.PROCESSING
# tx.provider: OfframpProvider.BRIDGE
```

### 3.4 Status Polling

```python
tx = await provider.get_transaction_status("bridge_transfer_...")

# Status transitions:
# PENDING -> PROCESSING -> COMPLETED
# PENDING -> PROCESSING -> FAILED
```

### 3.5 Deposit Address Generation

```python
address = await provider.get_deposit_address(
    chain="base",
    token="USDC",
)
# Returns a Bridge-managed deposit address for the specified chain/token
```

---

## 4. Multi-Rail Support

### 4.1 Payment Rails

| Rail | Currencies | Settlement Time | Fee | Best For |
|------|-----------|-----------------|-----|----------|
| **ACH** | USD | 1-2 business days | 0.5% | Standard USD withdrawals |
| **Wire** | USD | Same day | 0.5% + $15 | Large/urgent USD transfers |
| **SEPA** | EUR | 1 business day | 0.5% | European EUR withdrawals |
| **PIX** | BRL | Instant | 0.5% | Brazilian Real withdrawals |

### 4.2 Rail Selection

Bridge automatically selects the appropriate rail based on `output_currency` and `destination_payment_rail` parameter:

```python
# Default: ACH for USD
quote = await provider.get_quote(
    input_token="USDC",
    input_amount_minor=1_000_000_000,
    input_chain="base",
    output_currency="USD",
)

# The quote request includes: "destination_payment_rail": "ach"
# For large amounts (>$50,000), consider wire: "destination_payment_rail": "wire"
```

### 4.3 Priority Routing

Sardis implements priority routing for off-ramp providers based on currency and urgency:

| Scenario | Primary Provider | Fallback |
|----------|-----------------|----------|
| USD standard | Bridge (ACH) | Lightspark Grid |
| USD instant | Lightspark Grid (RTP/FedNow) | Bridge (wire) |
| EUR | Striga (SEPA) | Bridge (SEPA) |
| BRL | Bridge (PIX) | -- |

---

## 5. Velocity Limits

### 5.1 OfframpService Layer

The `OfframpService` wraps the provider with velocity limit enforcement:

```python
service = OfframpService(
    provider=bridge_provider,
    daily_limit_cents=10_000_00,     # $10,000/day
    weekly_limit_cents=50_000_00,    # $50,000/week
    monthly_limit_cents=200_000_00,  # $200,000/month
)

# Check limits before executing
limits = service.get_velocity_limits("wal_abc123")
# {
#     "daily": {"used_usd": 2500.00, "limit_usd": 10000.00, "remaining_usd": 7500.00},
#     "weekly": {"used_usd": 15000.00, "limit_usd": 50000.00, "remaining_usd": 35000.00},
#     "monthly": {"used_usd": 45000.00, "limit_usd": 200000.00, "remaining_usd": 155000.00},
# }
```

### 5.2 Limit Enforcement

If an off-ramp would exceed velocity limits, `VelocityLimitExceeded` is raised before the transaction reaches Bridge:

```python
try:
    tx = await service.execute(
        quote=quote,
        source_address="0x...",
        destination_account="bank_...",
        wallet_id="wal_abc123",
    )
except VelocityLimitExceeded as e:
    # "Daily off-ramp limit exceeded. Used: $8,500.00, Limit: $10,000.00, Requested: $2,000.00"
    pass
```

### 5.3 Quote Caching

The service caches quotes by ID for later validation:

```python
# Get and cache a quote
quote = await service.get_quote("USDC", 1_000_000_000, "base")

# Later: retrieve cached quote (returns None if expired)
cached = service.get_cached_quote(quote.quote_id)
```

---

## 6. Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BRIDGE_API_KEY` | Yes | Bridge API key |
| `BRIDGE_API_SECRET` | Yes | Bridge API secret for HMAC signing |
| `BRIDGE_ENVIRONMENT` | No | `sandbox` or `production` (default: sandbox) |

### API Endpoints

| Environment | Base URL |
|-------------|----------|
| Sandbox | `https://api.sandbox.bridge.xyz` |
| Production | `https://api.bridge.xyz` |

---

## 7. Data Models

### OfframpQuote

| Field | Type | Description |
|-------|------|-------------|
| `quote_id` | `str` | Bridge quote identifier |
| `provider` | `OfframpProvider` | `BRIDGE` |
| `input_token` | `str` | Source token (USDC, USDT) |
| `input_amount_minor` | `int` | Amount in token minor units (6 decimals for USDC) |
| `input_chain` | `str` | Source chain (base, polygon, ethereum) |
| `output_currency` | `str` | Destination fiat currency (USD, EUR, BRL) |
| `output_amount_cents` | `int` | Amount in fiat cents after fees |
| `exchange_rate` | `Decimal` | Conversion rate |
| `fee_cents` | `int` | Bridge fee in fiat cents |
| `expires_at` | `datetime` | Quote expiration (5 minutes) |

### OfframpTransaction

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | `str` | Bridge transfer identifier |
| `quote_id` | `str` | Associated quote ID |
| `provider` | `OfframpProvider` | `BRIDGE` |
| `status` | `OfframpStatus` | PENDING / PROCESSING / COMPLETED / FAILED / REFUNDED |
| `input_tx_hash` | `str` | On-chain transaction hash (when available) |
| `destination_account` | `str` | Bank account or card funding account |
| `provider_reference` | `str` | Bridge internal reference |

---

## 8. Error Handling

| Error | HTTP Status | Handling |
|-------|-------------|----------|
| Quote expired | -- | Client-side check via `quote.is_expired`; re-fetch quote |
| Insufficient balance | 400 | Surfaced to agent with balance check guidance |
| Invalid destination | 400 | Validation before execution |
| Rate limited | 429 | Exponential backoff with jitter |
| Bridge service error | 500+ | Circuit breaker; fail-closed, notify operator |
| Velocity limit exceeded | -- | `VelocityLimitExceeded` raised before API call |

---

## 9. Related Files

| File | Purpose |
|------|---------|
| `packages/sardis-cards/src/sardis_cards/offramp.py` | BridgeOfframpProvider, OfframpService, velocity limits |
| `packages/sardis-cards/src/sardis_cards/db_offramp.py` | Persistent offramp transaction storage |
| `packages/sardis-cards/src/sardis_cards/auto_conversion.py` | Automatic stablecoin-to-fiat conversion triggers |
| `packages/sardis-cards/src/sardis_cards/providers/stripe_issuing.py` | Card funding destination |
| `packages/sardis-ramp/src/sardis_ramp/router.py` | Ramp routing (onramp/offramp provider selection) |
