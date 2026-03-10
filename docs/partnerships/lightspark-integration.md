# Lightspark Integration Spec

## Partner: Lightspark (Grid API, Instant Fiat Payouts, UMA)

**Status:** Production-ready
**Package:** `packages/sardis-lightspark/`
**Primary Classes:** `GridClient`, `GridTransferService`, `UMAService`

---

## 1. Overview

Lightspark provides Sardis with instant fiat payout infrastructure, cross-currency FX, and UMA (Universal Money Address) support through the Grid API. This integration enables AI agents to make instant fiat payouts via RTP/FedNow, convert between currencies at market rates, and receive payments via human-readable UMA addresses (e.g., `$agent@sardis.sh`). Lightspark Grid complements Bridge by providing instant settlement rails where Bridge provides standard ACH/SEPA.

### Key Capabilities

| Feature | Status | Details |
|---------|--------|---------|
| Instant USD payouts (RTP/FedNow) | Production | Sub-second settlement |
| ACH payouts | Production | Standard 1-2 day settlement |
| Same-day ACH | Production | Same business day |
| Wire transfers | Production | Same day |
| SEPA transfers | Production | 1 business day |
| FX conversion | Production | Market rate + spread |
| UMA addresses | Production | `$agent@sardis.sh` format |
| Plaid bank linking | Production | Secure bank account connection |
| Webhook events | Production | Real-time transfer notifications |
| Lightning Network | Available | Sub-second BTC payments |

---

## 2. Architecture

### 2.1 Package Structure

```
packages/sardis-lightspark/
  src/sardis_lightspark/
    __init__.py            # Public API exports
    client.py              # GridClient (authenticated HTTP)
    config.py              # LightsparkConfig dataclass
    exceptions.py          # Exception hierarchy
    models.py              # Data models (GridTransfer, UMAAddress, etc.)
    transfers.py           # GridTransferService (quote-execute-status)
    payouts.py             # Direct payout operations
    fx.py                  # FX conversion operations
    uma.py                 # UMA address management
    uma_registry.py        # UMA address registry
    plaid.py               # Plaid bank account linking
    webhooks.py            # Webhook event handling
  tests/
    ...
```

### 2.2 System Flow

```
AI Agent
    |
    +-- Instant payout (RTP/FedNow)
    |     |
    |     v
    |   GridTransferService.get_quote()
    |     |-- source: USD
    |     |-- target: USD
    |     |-- rail: RTP or FEDNOW
    |     v
    |   GridTransferService.execute_transfer()
    |     |-- funds delivered in seconds
    |     v
    |   Recipient bank account (instant)
    |
    +-- Cross-currency payment
    |     |
    |     v
    |   GridTransferService.get_quote()
    |     |-- source: USD
    |     |-- target: EUR (or GBP, BRL, etc.)
    |     |-- returns: exchange_rate, fee, target_amount
    |     v
    |   GridTransferService.execute_transfer()
    |     |-- FX conversion at quoted rate
    |     v
    |   Recipient in local currency
    |
    +-- UMA payment
          |
          v
        UMAService.send_payment("$recipient@domain.com", amount)
          |-- resolves UMA address
          |-- executes payment via Lightning or Grid
          v
        Payment delivered
```

---

## 3. Grid Transfer Service

### 3.1 Quote-Execute-Status Lifecycle

The `GridTransferService` implements a three-phase transfer flow:

**Phase 1: Quote**
```python
from sardis_lightspark import GridClient, LightsparkConfig, GridPaymentRail
from sardis_lightspark.transfers import GridTransferService

config = LightsparkConfig(api_key="...", api_secret="...", base_url="...")
client = GridClient(config)
transfer_service = GridTransferService(client)

# Get a quote for instant USD payout
quote = await transfer_service.get_quote(
    source_currency="USD",
    target_currency="USD",
    amount_cents=50000,       # $500.00
    rail=GridPaymentRail.RTP, # Real-Time Payments (instant)
)

# quote.quote_id: "grid_quote_..."
# quote.source_amount_cents: 50000
# quote.target_amount_cents: 49850
# quote.exchange_rate: Decimal("1.0")
# quote.fee_cents: 150  ($1.50)
# quote.expires_at: datetime (5 minutes)
```

**Phase 2: Execute**
```python
transfer = await transfer_service.execute_transfer(
    quote=quote,
    destination="bank_account_id",  # Plaid-linked bank account
    reference="Agent payout #1234",
)

# transfer.transfer_id: "grid_transfer_..."
# transfer.status: GridTransferStatus.PROCESSING
# transfer.rail: GridPaymentRail.RTP
```

**Phase 3: Status**
```python
transfer = await transfer_service.get_transfer_status("grid_transfer_...")

# transfer.status: GridTransferStatus.COMPLETED (instant for RTP/FedNow)
# transfer.completed_at: datetime
```

### 3.2 Quote Expiration

Quotes expire after 5 minutes. Attempting to execute an expired quote raises `GridQuoteExpiredError`:

```python
if quote.is_expired:
    # Re-fetch quote
    quote = await transfer_service.get_quote(...)

try:
    transfer = await transfer_service.execute_transfer(quote, ...)
except GridQuoteExpiredError:
    # Quote expired between check and execution
    pass
```

---

## 4. Payment Rails

### 4.1 Supported Rails

| Rail | Enum | Settlement | Availability | Fee Range |
|------|------|-----------|--------------|-----------|
| **RTP** | `GridPaymentRail.RTP` | Instant (< 10s) | 24/7/365 | $0.50-$2.00 |
| **FedNow** | `GridPaymentRail.FEDNOW` | Instant (< 10s) | 24/7/365 | $0.25-$1.00 |
| **ACH** | `GridPaymentRail.ACH` | 1-2 business days | Business days | $0.10-$0.50 |
| **ACH Same Day** | `GridPaymentRail.ACH_SAME_DAY` | Same business day | Business days | $0.50-$1.50 |
| **Wire** | `GridPaymentRail.WIRE` | Same day | Business days | $15-$30 |
| **SEPA** | `GridPaymentRail.SEPA` | 1 business day | Business days (EU) | EUR 0.20-0.50 |
| **Lightning** | `GridPaymentRail.LIGHTNING` | Instant (< 1s) | 24/7/365 | < $0.01 |

### 4.2 Sardis Priority Routing

Sardis selects Lightspark Grid as the preferred provider for instant USD payouts:

| Scenario | Primary Rail | Fallback |
|----------|-------------|----------|
| USD instant payout | Grid RTP | Grid FedNow -> Bridge wire |
| USD standard payout | Bridge ACH | Grid ACH |
| EUR payout | Striga SEPA | Grid SEPA |
| Micro-payment (< $1) | Grid Lightning | Grid RTP |

---

## 5. FX / Currency Conversion

### 5.1 Cross-Currency Quotes

```python
# USD to EUR conversion
quote = await transfer_service.get_quote(
    source_currency="USD",
    target_currency="EUR",
    amount_cents=100000,  # $1,000.00 USD
)

# quote.exchange_rate: Decimal("0.9234")
# quote.target_amount_cents: 91840  (EUR 918.40 after fees)
# quote.fee_cents: 500  ($5.00)
```

### 5.2 Supported Currency Pairs

| Source | Target | Notes |
|--------|--------|-------|
| USD | EUR | Most common for Sardis |
| USD | GBP | UK payouts |
| USD | BRL | Brazilian payouts |
| EUR | USD | European agent to US merchant |
| Any | Any | Grid supports 40+ currency pairs |

### 5.3 FX Rate Transparency

- Exchange rates are locked at quote time (5-minute validity)
- Fees are explicitly separated from the exchange rate
- No hidden spread -- the quoted rate is the executed rate

---

## 6. UMA (Universal Money Address)

### 6.1 Overview

UMA enables human-readable payment addresses for AI agents. Instead of sharing blockchain addresses, agents can receive payments at addresses like `$purchasing-agent@sardis.sh`.

### 6.2 UMA Address Management

```python
from sardis_lightspark.uma import UMAService

uma_service = UMAService(client)

# Create a UMA address for an agent
address = await uma_service.create_address(
    wallet_id="wal_abc123",
    local_part="purchasing-agent",  # $purchasing-agent@sardis.sh
    currency="USD",
)

# address.address: "$purchasing-agent@sardis.sh"
# address.uma_id: "uma_..."
# address.status: UMAAddressStatus.ACTIVE
```

### 6.3 UMA Data Model

| Field | Type | Description |
|-------|------|-------------|
| `uma_id` | `str` | Lightspark UMA identifier |
| `address` | `str` | Full UMA address (`$agent@sardis.sh`) |
| `wallet_id` | `str` | Associated Sardis wallet |
| `user_id` | `str` | Owner user ID (optional) |
| `currency` | `str` | Default currency (USD) |
| `status` | `UMAAddressStatus` | ACTIVE / SUSPENDED / DEACTIVATED |

### 6.4 UMA in Sardis A2A Payments

UMA addresses are integrated into Sardis's A2A (Agent-to-Agent) payment system. The `PaymentCapability` in `sardis-a2a` includes a `uma_address` field, enabling agents to advertise their payment address:

```python
# From sardis-a2a agent card
payment_capability = PaymentCapability(
    supported_tokens=["USDC", "EURC"],
    supported_chains=["base", "polygon"],
    uma_address="$agent@sardis.sh",  # UMA for receiving payments
)
```

### 6.5 Address Properties

```python
address = UMAAddress(address="$purchasing-agent@sardis.sh", ...)

address.local_part  # "purchasing-agent"
address.domain      # "sardis.sh"
```

---

## 7. Plaid Bank Account Linking

### 7.1 Overview

Lightspark Grid uses Plaid for secure bank account linking, enabling agents and their operators to connect bank accounts for payouts.

```python
from sardis_lightspark.plaid import create_link_token

# Generate a Plaid Link token for the frontend
link_token = await create_link_token(
    client,
    customer_id="grid_customer_123",
)

# link_token.link_token: "link-sandbox-..."
# link_token.expiration: datetime
```

### 7.2 Bank Account Flow

```
Frontend / Dashboard
    |
    v
Plaid Link (client-side widget)
    |-- User selects bank
    |-- User authenticates
    |-- Plaid returns public_token
    |
    v
Sardis API
    |-- Exchanges public_token for access_token
    |-- Links bank account to Grid customer
    |
    v
Bank account available for payouts
```

---

## 8. Webhook Events

### 8.1 Webhook Handler

```python
from sardis_lightspark import GridWebhookHandler, GridWebhookEventType

handler = GridWebhookHandler(webhook_secret="whsec_...")

@app.post("/webhooks/lightspark")
async def lightspark_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Grid-Signature", "")

    event = handler.verify_and_parse(payload, signature)

    if event.type == GridWebhookEventType.TRANSFER_COMPLETED:
        # Payout delivered
        pass
    elif event.type == GridWebhookEventType.TRANSFER_FAILED:
        # Payout failed -- retry or notify
        pass
```

### 8.2 Event Types

| Event Type | Description |
|------------|-------------|
| `TRANSFER_COMPLETED` | Payout delivered to recipient |
| `TRANSFER_FAILED` | Payout failed (insufficient funds, invalid destination) |
| `TRANSFER_REFUNDED` | Transfer reversed/refunded |
| `UMA_PAYMENT_RECEIVED` | Incoming UMA payment received |
| `CUSTOMER_VERIFIED` | Customer KYC/verification completed |
| `BANK_ACCOUNT_LINKED` | Plaid bank account successfully linked |

---

## 9. Error Handling

| Exception | Description |
|-----------|-------------|
| `GridAuthError` | Invalid API key or secret |
| `GridValidationError` | Invalid request parameters |
| `GridRateLimitError` | Rate limit exceeded |
| `GridQuoteExpiredError` | Quote expired before execution |
| `GridInsufficientFundsError` | Insufficient balance for transfer |
| `GridUMAResolutionError` | UMA address could not be resolved |
| `GridWebhookVerificationError` | Invalid webhook signature |
| `GridError` | General Grid API error |

---

## 10. Grid Customer Management

### 10.1 Customer Model

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | `str` | Grid customer identifier |
| `email` | `str` | Customer email |
| `status` | `GridCustomerStatus` | PENDING / ACTIVE / SUSPENDED / CLOSED |
| `plaid_access_token` | `str` | Plaid access token (encrypted) |
| `bank_account_id` | `str` | Linked bank account |

### 10.2 Transfer Status Lifecycle

```
QUOTED --> PENDING --> PROCESSING --> COMPLETED
                          |
                          +--> FAILED
                          |
                          +--> CANCELLED
                          |
                          +--> REFUNDED
```

---

## 11. Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LIGHTSPARK_API_KEY` | Yes | Grid API key |
| `LIGHTSPARK_API_SECRET` | Yes | Grid API secret |
| `LIGHTSPARK_BASE_URL` | No | API base URL |
| `LIGHTSPARK_WEBHOOK_SECRET` | Yes | Webhook verification secret |
| `LIGHTSPARK_UMA_DOMAIN` | No | UMA domain (default: sardis.sh) |

---

## 12. Related Files

| File | Purpose |
|------|---------|
| `packages/sardis-lightspark/src/sardis_lightspark/client.py` | GridClient HTTP client |
| `packages/sardis-lightspark/src/sardis_lightspark/transfers.py` | GridTransferService (quote-execute-status) |
| `packages/sardis-lightspark/src/sardis_lightspark/payouts.py` | Direct payout operations |
| `packages/sardis-lightspark/src/sardis_lightspark/fx.py` | FX conversion operations |
| `packages/sardis-lightspark/src/sardis_lightspark/uma.py` | UMA address management |
| `packages/sardis-lightspark/src/sardis_lightspark/uma_registry.py` | UMA address registry |
| `packages/sardis-lightspark/src/sardis_lightspark/plaid.py` | Plaid bank account linking |
| `packages/sardis-lightspark/src/sardis_lightspark/webhooks.py` | Webhook event handling |
| `packages/sardis-lightspark/src/sardis_lightspark/models.py` | All data models |
| `packages/sardis-a2a/src/sardis_a2a/agent_card.py` | A2A agent card with UMA address |
| `packages/sardis-ramp/src/sardis_ramp/router.py` | Priority routing (Grid vs Bridge vs Striga) |
