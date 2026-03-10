# Striga Integration Spec

## Partner: Striga (Full EEA Banking Infrastructure)

**Status:** Production-ready
**Package:** `packages/sardis-striga/`
**Primary Classes:** `StrigaClient`, `StrigaCardProvider`, `StrigaWebhookHandler`

---

## 1. Overview

Striga provides Sardis with full EEA (European Economic Area) banking infrastructure, enabling European AI agents and their operators to access virtual Visa card issuance, vIBAN accounts, SEPA transfers, KYC verification, standing orders, and crypto-to-fiat conversion. The `sardis-striga` package is a self-contained integration that wraps the Striga API with HMAC-SHA256 authentication, implements the Sardis `CardProvider` interface for card operations, and provides event-driven webhook handling.

### Key Capabilities

| Feature | Status | Details |
|---------|--------|---------|
| EUR virtual Visa cards | Production | KYC-linked, Apple Pay / Google Pay |
| vIBAN accounts | Production | Dedicated EUR IBANs for agents |
| SEPA transfers | Production | Inbound/outbound EUR transfers |
| KYC verification | Production | EU-compliant identity verification |
| Standing orders | Production | Recurring payment automation |
| Crypto-to-fiat swap | Production | USDC/EURC to EUR conversion |
| Webhook events | Production | Real-time event notifications |
| HMAC-SHA256 auth | Production | Signed API requests |

---

## 2. Architecture

### 2.1 Package Structure

```
packages/sardis-striga/
  src/sardis_striga/
    __init__.py           # Public API exports
    client.py             # StrigaClient (HMAC-authenticated HTTP)
    config.py             # StrigaConfig dataclass
    exceptions.py         # Exception hierarchy
    models.py             # Data models (StrigaCard, StrigaVIBAN, etc.)
    cards.py              # StrigaCardProvider (CardProvider implementation)
    viban.py              # vIBAN creation and management
    sepa.py               # SEPA transfer operations
    kyc.py                # KYC verification flow
    swap.py               # Crypto-fiat swap operations
    standing_orders.py    # Standing order management
    webhooks.py           # Webhook event handling
  tests/
    test_client.py
    test_cards.py
    test_viban.py
    test_sepa.py
    test_swap.py
    test_kyc.py
    test_webhooks.py
```

### 2.2 System Flow

```
AI Agent (EEA-based operator)
    |
    v
Sardis API
    |
    +-- KYC flow (Striga KYC) --> Identity verified
    |
    +-- vIBAN creation --> Dedicated EUR IBAN assigned
    |
    +-- SEPA inbound --> EUR received to vIBAN
    |
    +-- Crypto swap --> EURC/USDC converted to EUR
    |
    +-- Card issuance --> EUR virtual Visa card created
    |
    +-- Standing orders --> Recurring payments scheduled
    |
    +-- Webhooks --> Real-time event notifications
```

---

## 3. Core Client

### 3.1 StrigaClient

The `StrigaClient` is the foundation of all Striga API interactions. It implements HMAC-SHA256 request signing per Striga's authentication specification.

```python
from sardis_striga import StrigaClient, StrigaConfig

config = StrigaConfig(
    api_key="striga_api_key",
    api_secret="striga_api_secret",
    base_url="https://api.striga.com/v1",
)

async with StrigaClient(config) as client:
    result = await client.request("POST", "/wallets", {"userId": "user_123"})
```

**Authentication Flow:**
```
message = f"{timestamp}{method}{path}{body}"
signature = HMAC-SHA256(api_secret, message)

Headers:
    Content-Type: application/json
    Api-Key: <api_key>
    Api-Timestamp: <unix_timestamp>
    Api-Signature: <hmac_signature>
```

### 3.2 Error Handling

| Exception | HTTP Status | Description |
|-----------|-------------|-------------|
| `StrigaAuthError` | 401, 403 | Invalid API key or signature |
| `StrigaValidationError` | 400, 422 | Invalid request parameters |
| `StrigaRateLimitError` | 429 | Rate limit exceeded |
| `StrigaKYCRequiredError` | -- | Operation requires completed KYC |
| `StrigaInsufficientFundsError` | -- | Insufficient balance |
| `StrigaWebhookVerificationError` | -- | Invalid webhook signature |
| `StrigaError` | Other | General API error |

---

## 4. Card Issuance

### 4.1 StrigaCardProvider

`StrigaCardProvider` implements the Sardis `CardProvider` interface for EUR-denominated virtual Visa cards:

```python
from sardis_striga import StrigaClient, StrigaConfig
from sardis_striga.cards import StrigaCardProvider

config = StrigaConfig(api_key="...", api_secret="...", base_url="...")
client = StrigaClient(config)
card_provider = StrigaCardProvider(client, default_user_id="user_123")
```

### 4.2 Card Creation

```python
card = await card_provider.create_card(
    wallet_id="wal_eur_001",
    card_type=CardType.MULTI_USE,
    limit_per_tx=Decimal("500.00"),
    limit_daily=Decimal("2000.00"),
    limit_monthly=Decimal("10000.00"),
)
# card.provider == "striga"
# card.status == CardStatus.PENDING (requires activation)
```

### 4.3 Full Card Lifecycle

| Operation | Method | Notes |
|-----------|--------|-------|
| Create | `create_card()` | EUR-denominated, requires KYC-verified user |
| Activate | `activate_card()` | Transitions PENDING -> ACTIVE |
| Freeze | `freeze_card()` | Temporary suspension (unfreezing supported) |
| Unfreeze | `unfreeze_card()` | Restore frozen card to ACTIVE |
| Cancel | `cancel_card()` | Permanent deactivation |
| Update limits | `update_limits()` | Modify per-tx, daily, monthly limits |
| Fund | `fund_card()` | Add EUR balance from vIBAN or swap |
| List transactions | `list_transactions()` | Paginated transaction history |

### 4.4 Status Mapping

| Striga Status | Sardis CardStatus |
|---------------|-------------------|
| `created` | `PENDING` |
| `active` | `ACTIVE` |
| `frozen` | `FROZEN` |
| `cancelled` | `CANCELLED` |
| `expired` | `EXPIRED` |

### 4.5 Digital Wallet Provisioning

```python
# Apple Pay
apple_data = await card_provider.create_apple_pay_token("card_123")

# Google Pay
google_data = await card_provider.create_google_pay_token("card_123")
```

---

## 5. vIBAN Accounts

### 5.1 Overview

Striga vIBANs (virtual IBANs) provide each agent/wallet with a dedicated EUR bank account for receiving SEPA transfers.

```python
from sardis_striga.viban import create_viban, get_viban

viban = await create_viban(client, user_id="user_123", wallet_id="wal_eur_001")
# viban.iban: "DE89 3704 0044 0532 0130 00"
# viban.bic: "COBADEFFXXX"
# viban.status: StrigaVIBANStatus.ACTIVE
```

### 5.2 vIBAN Data Model

| Field | Type | Description |
|-------|------|-------------|
| `viban_id` | `str` | Striga vIBAN identifier |
| `iban` | `str` | Full IBAN number |
| `bic` | `str` | BIC/SWIFT code |
| `wallet_id` | `str` | Associated Sardis wallet |
| `user_id` | `str` | KYC-verified user |
| `status` | `StrigaVIBANStatus` | ACTIVE / SUSPENDED / CLOSED |
| `currency` | `str` | EUR |

---

## 6. SEPA Transfers

### 6.1 Outbound SEPA

```python
from sardis_striga.sepa import initiate_sepa_transfer

transfer = await initiate_sepa_transfer(
    client,
    user_id="user_123",
    source_wallet_id="wal_eur_001",
    destination_iban="DE89 3704 0044 0532 0130 00",
    destination_bic="COBADEFFXXX",
    amount_cents=10000,  # EUR 100.00
    reference="Invoice INV-2026-001",
)
```

### 6.2 Inbound SEPA

Inbound SEPA transfers arrive at the vIBAN address and are credited to the associated wallet. Sardis receives a webhook notification when funds arrive.

---

## 7. KYC Verification

### 7.1 KYC Flow

Striga provides EU-compliant KYC for card issuance and banking operations:

```python
from sardis_striga.kyc import initiate_kyc, check_kyc_status

# Start KYC process
kyc_session = await initiate_kyc(
    client,
    user_id="user_123",
    first_name="Alice",
    last_name="Smith",
    date_of_birth="1990-01-15",
    nationality="DE",
    document_type="passport",
)

# Check KYC status
status = await check_kyc_status(client, user_id="user_123")
# status: StrigaUserStatus.ACTIVE (verified) / PENDING / REJECTED
```

### 7.2 KYC Requirements by Operation

| Operation | KYC Required | Level |
|-----------|-------------|-------|
| vIBAN creation | Yes | Basic (name + DOB + document) |
| Card issuance | Yes | Enhanced (Basic + address verification) |
| SEPA outbound | Yes | Basic |
| SEPA inbound | Yes | Basic |
| Standing orders | Yes | Basic |
| Crypto swap | Yes | Enhanced |

---

## 8. Crypto-Fiat Swap

### 8.1 USDC/EURC to EUR Conversion

```python
from sardis_striga.swap import execute_swap

swap = await execute_swap(
    client,
    user_id="user_123",
    source_currency="EURC",
    target_currency="EUR",
    amount_minor=100_000_000,  # 100 EURC
)
# Funds credited to user's EUR wallet
```

### 8.2 Supported Swap Pairs

| Source | Target | Direction |
|--------|--------|-----------|
| USDC | EUR | Crypto -> Fiat |
| EURC | EUR | Crypto -> Fiat |
| EUR | USDC | Fiat -> Crypto |
| EUR | EURC | Fiat -> Crypto |

---

## 9. Standing Orders

### 9.1 Overview

Standing orders enable automated recurring payments from Striga wallets:

```python
from sardis_striga.standing_orders import create_standing_order

order = await create_standing_order(
    client,
    user_id="user_123",
    wallet_id="wal_eur_001",
    destination_iban="DE89...",
    amount_cents=5000,  # EUR 50.00
    frequency=StandingOrderFrequency.MONTHLY,
    reference="Subscription payment",
    start_date="2026-04-01",
)
```

### 9.2 Standing Order Frequencies

| Frequency | Enum Value |
|-----------|------------|
| Weekly | `StandingOrderFrequency.WEEKLY` |
| Biweekly | `StandingOrderFrequency.BIWEEKLY` |
| Monthly | `StandingOrderFrequency.MONTHLY` |
| Quarterly | `StandingOrderFrequency.QUARTERLY` |
| Annually | `StandingOrderFrequency.ANNUALLY` |

### 9.3 Standing Order Lifecycle

| Status | Description |
|--------|-------------|
| `ACTIVE` | Order is executing on schedule |
| `PAUSED` | Temporarily suspended |
| `CANCELLED` | Permanently stopped |
| `FAILED` | Last execution failed (insufficient funds, etc.) |

---

## 10. Webhook Events

### 10.1 Webhook Handler

```python
from sardis_striga import StrigaWebhookHandler, StrigaWebhookEventType

handler = StrigaWebhookHandler(webhook_secret="whsec_...")

@app.post("/webhooks/striga")
async def striga_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Striga-Signature", "")

    event = handler.verify_and_parse(payload, signature)

    if event.type == StrigaWebhookEventType.CARD_TRANSACTION:
        # Handle card transaction event
        pass
    elif event.type == StrigaWebhookEventType.SEPA_RECEIVED:
        # Handle inbound SEPA transfer
        pass
```

### 10.2 Event Types

| Event Type | Description |
|------------|-------------|
| `CARD_TRANSACTION` | Card authorization, settlement, or reversal |
| `CARD_STATUS_CHANGED` | Card activated, frozen, cancelled |
| `SEPA_RECEIVED` | Inbound SEPA transfer credited to vIBAN |
| `SEPA_SENT` | Outbound SEPA transfer completed |
| `KYC_STATUS_CHANGED` | KYC verification approved or rejected |
| `SWAP_COMPLETED` | Crypto-fiat swap completed |
| `STANDING_ORDER_EXECUTED` | Standing order payment processed |
| `STANDING_ORDER_FAILED` | Standing order payment failed |

---

## 11. Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STRIGA_API_KEY` | Yes | Striga API key |
| `STRIGA_API_SECRET` | Yes | Striga API secret for HMAC signing |
| `STRIGA_BASE_URL` | No | API base URL (default: `https://api.striga.com/v1`) |
| `STRIGA_WEBHOOK_SECRET` | Yes | Webhook verification secret |

---

## 12. Sardis Routing Integration

Sardis routes to Striga as the primary provider for EUR-denominated operations:

| Scenario | Provider | Reason |
|----------|----------|--------|
| EUR card issuance | Striga | Native EUR cards, EEA-licensed |
| EUR off-ramp | Striga (SEPA) | Priority routing for EUR |
| USD card issuance | Stripe Issuing | Native USD cards |
| USD off-ramp | Bridge (ACH) | Priority routing for USD |
| EUR standing orders | Striga | Native SEPA standing orders |

---

## 13. Related Files

| File | Purpose |
|------|---------|
| `packages/sardis-striga/src/sardis_striga/client.py` | HMAC-authenticated HTTP client |
| `packages/sardis-striga/src/sardis_striga/cards.py` | StrigaCardProvider (CardProvider impl) |
| `packages/sardis-striga/src/sardis_striga/viban.py` | vIBAN creation and management |
| `packages/sardis-striga/src/sardis_striga/sepa.py` | SEPA transfer operations |
| `packages/sardis-striga/src/sardis_striga/kyc.py` | KYC verification flow |
| `packages/sardis-striga/src/sardis_striga/swap.py` | Crypto-fiat swap operations |
| `packages/sardis-striga/src/sardis_striga/standing_orders.py` | Standing order management |
| `packages/sardis-striga/src/sardis_striga/webhooks.py` | Webhook event handling |
| `packages/sardis-striga/src/sardis_striga/models.py` | All data models |
| `packages/sardis-cards/src/sardis_cards/providers/router.py` | Multi-provider routing (Stripe vs Striga) |
