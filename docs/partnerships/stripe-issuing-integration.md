# Stripe Issuing Integration Spec

## Partner: Stripe (Virtual Card Issuance)

**Status:** Production-ready
**Package:** `packages/sardis-cards/src/sardis_cards/providers/stripe_issuing.py`
**Provider Class:** `StripeIssuingProvider` (implements `CardProvider` interface)

---

## 1. Overview

Sardis uses Stripe Issuing as the primary virtual card provider for USD-denominated markets. The `StripeIssuingProvider` implements the `CardProvider` abstract interface, enabling Sardis to issue, manage, and monitor virtual Visa cards for AI agents. Each card is policy-controlled through Sardis's natural language spending policy engine, with real-time authorization decisions made via Stripe's webhook system.

### Key Capabilities

| Feature | Status | Details |
|---------|--------|---------|
| Virtual card creation | Production | $0.10 per card |
| Real-time authorization webhooks | Production | < 3 second response window |
| Granular spending controls | Production | Per-transaction, daily, monthly limits |
| Merchant category restrictions | Production | MCC-based blocking via policy engine |
| Merchant-locked cards | Production | Single-merchant cards for subscriptions |
| Card funding via Treasury | Production | Issuing balance management |
| Apple Pay provisioning | Production | Ephemeral key + push provisioning |
| Google Pay provisioning | Production | Ephemeral key + push provisioning |
| Simulation mode | Sandbox | Full test authorization flow |

---

## 2. Architecture

```
AI Agent
  |
  v
Sardis SDK (sardis.cards.create / sardis.cards.pay)
  |
  v
Sardis API (FastAPI)
  |
  v
CardService --> StripeIssuingProvider (CardProvider interface)
  |                    |
  |                    v
  |              Stripe Issuing API
  |                    |
  v                    v
SpendingPolicyEngine   Stripe Authorization Webhook
  |                    |
  v                    v
Policy Decision ----> Approve / Decline (< 3s)
```

### Provider Interface

`StripeIssuingProvider` implements the `CardProvider` abstract base class defined in `packages/sardis-cards/src/sardis_cards/providers/base.py`:

```python
class CardProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def create_card(self, wallet_id, card_type, limit_per_tx, limit_daily, limit_monthly, ...) -> Card: ...

    @abstractmethod
    async def get_card(self, provider_card_id) -> Card | None: ...

    @abstractmethod
    async def activate_card(self, provider_card_id) -> Card: ...

    @abstractmethod
    async def freeze_card(self, provider_card_id) -> Card: ...

    @abstractmethod
    async def cancel_card(self, provider_card_id) -> Card: ...

    @abstractmethod
    async def update_limits(self, provider_card_id, ...) -> Card: ...

    @abstractmethod
    async def fund_card(self, provider_card_id, amount) -> Card: ...

    @abstractmethod
    async def list_transactions(self, provider_card_id, ...) -> list[CardTransaction]: ...

    @abstractmethod
    async def get_transaction(self, provider_tx_id) -> CardTransaction | None: ...
```

---

## 3. Card Lifecycle

### 3.1 Card Creation

```python
provider = StripeIssuingProvider(
    api_key="sk_live_...",
    webhook_secret="whsec_...",
    policy_evaluator=spending_policy.evaluate,  # Sardis policy engine
)

card = await provider.create_card(
    wallet_id="wal_abc123",
    card_type=CardType.MULTI_USE,
    limit_per_tx=Decimal("500.00"),
    limit_daily=Decimal("2000.00"),
    limit_monthly=Decimal("10000.00"),
    cardholder_name="Acme Corp",
    cardholder_email="finance@acme.com",
)
```

**Flow:**
1. Create Stripe Issuing Cardholder (individual type, billing address required)
2. Create virtual card with `status="inactive"` and spending controls
3. Auto-activate card and return `Card` model with Sardis-internal `card_id`

**Cardholder Reuse:** Pass `reuse_cardholder_id` to avoid creating duplicate cardholders for the same organization.

### 3.2 Card Activation

```python
card = await provider.activate_card("ic_xxx")
```

Sets Stripe card status to `"active"`. Card is immediately usable.

### 3.3 Card Freeze (Temporary Suspension)

```python
card = await provider.freeze_card("ic_xxx")
```

Stripe does not have a native "freeze" state. Sardis implements freeze by cancelling the card with `cancellation_reason="lost"`, which is distinguishable from permanent cancellation (`"design_changed"`). The `_map_card_status` method maps this back to `CardStatus.FROZEN`.

**Limitation:** Stripe does not support unfreezing cancelled cards. `unfreeze_card()` raises `NotImplementedError` with guidance to create a replacement card.

### 3.4 Card Cancellation (Permanent)

```python
card = await provider.cancel_card("ic_xxx")
```

Cancels with `cancellation_reason="design_changed"` for permanent deactivation.

### 3.5 Spending Limit Updates

```python
card = await provider.update_limits(
    "ic_xxx",
    limit_per_tx=Decimal("1000.00"),
    limit_daily=Decimal("5000.00"),
)
```

Updates Stripe spending controls in-place. Preserves existing limits for any parameter not specified.

---

## 4. Authorization Webhook Handling

### 4.1 Real-Time Authorization Flow

When a card is used at a merchant, Stripe sends an `issuing_authorization.request` webhook event. Sardis must respond within **3 seconds** with an approve or decline decision.

```
Merchant POS --> Card Network --> Stripe --> Sardis Webhook Endpoint
                                               |
                                               v
                                          1. Verify HMAC signature
                                          2. Extract: card_id, amount, MCC, merchant
                                          3. Evaluate spending policy (async)
                                          4. Check card authorization rules
                                               |
                                               v
                                          {"approved": true/false}
```

### 4.2 Policy Evaluation Pipeline

The `handle_authorization_webhook` method implements a two-stage authorization:

**Stage 1: Spending Policy Engine** (if `policy_evaluator` is configured)
- Evaluates natural language spending policies against the transaction
- Inputs: `wallet_id`, `amount`, `mcc_code`, `merchant_name`
- Returns: `(bool, str)` -- allowed/denied with reason

**Stage 2: Card-Level Rules**
- `card.can_authorize(amount, merchant_id)` checks:
  - Card status is ACTIVE
  - Amount within per-transaction limit
  - Daily/monthly cumulative limits not exceeded
  - Merchant-lock enforcement (if applicable)

Policy denials are surfaced before card-level checks, so the decline reason accurately reflects the policy rule that blocked the transaction.

### 4.3 Webhook Implementation

```python
@app.post("/webhooks/stripe-issuing")
async def stripe_issuing_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    result = await provider.handle_authorization_webhook(payload, signature)
    return JSONResponse(result)
```

### 4.4 Webhook Security

- **Signature verification:** HMAC-SHA256 via `stripe.Webhook.construct_event()`
- **Environment variable:** `STRIPE_WEBHOOK_SECRET` (whsec_...)
- **Replay protection:** Stripe includes timestamp in signature; SDK rejects events older than 5 minutes

---

## 5. Treasury Funding Flow

### 5.1 Stablecoin-to-Card Funding Pipeline

```
Agent USDC Wallet (on-chain)
    |
    v (1) Off-ramp via Bridge/Zero Hash
Fiat USD
    |
    v (2) Transfer to Stripe Treasury
Stripe Issuing Balance
    |
    v (3) Card spending limits updated
Card ready for use
```

### 5.2 fund_card Implementation

The `fund_card()` method adjusts the card's daily spending limit to reflect new available funds. In production, balance tracking is handled separately via authorization webhooks.

```python
card = await provider.fund_card("ic_xxx", amount=Decimal("500.00"))
# card.funded_amount reflects cumulative funding
```

### 5.3 Balance Monitoring

```python
balance = await provider.get_issuing_balance()
# Returns total available USD in Stripe Issuing balance
```

---

## 6. Digital Wallet Provisioning

### 6.1 Apple Pay

```python
provisioning_data = await provider.provision_apple_pay("ic_xxx")
# Returns ephemeral key for client-side push provisioning
```

### 6.2 Google Pay

```python
provisioning_data = await provider.provision_google_pay("ic_xxx")
# Returns ephemeral key for client-side push provisioning
```

Both methods create a Stripe Ephemeral Key scoped to the Issuing card, using API version `2024-12-18.acacia`.

---

## 7. Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STRIPE_API_KEY` | Yes | Stripe secret key (`sk_test_...` or `sk_live_...`) |
| `STRIPE_WEBHOOK_SECRET` | Yes | Webhook signing secret (`whsec_...`) |

### Test Mode Detection

The provider auto-detects test mode via the API key prefix:
- `sk_test_...` -- Sandbox mode (simulations enabled)
- `sk_live_...` -- Production mode (simulations disabled)

### Simulation (Test Mode Only)

```python
tx = await provider.simulate_authorization(
    provider_card_id="ic_xxx",
    amount=Decimal("49.99"),
    merchant_name="TEST MERCHANT",
    merchant_category="5812",  # Restaurant MCC
)
```

---

## 8. Data Model Mapping

### Stripe to Sardis Status Mapping

| Stripe Card Status | Sardis CardStatus | Notes |
|--------------------|-------------------|-------|
| `inactive` | `PENDING` | Card created, not yet activated |
| `active` | `ACTIVE` | Card is usable |
| `canceled` (reason: `lost`) | `FROZEN` | Temporary suspension |
| `canceled` (reason: `design_changed`) | `CANCELLED` | Permanent cancellation |

### Stripe to Sardis Transaction Status

| Stripe Auth Status | Sardis TransactionStatus | Notes |
|--------------------|--------------------------|-------|
| `approved=true`, `status=pending` | `APPROVED` | Authorization held |
| `approved=true`, `status=closed` | `SETTLED` | Transaction settled |
| `approved=false` | `DECLINED` | Authorization denied |
| `status=reversed` | `REVERSED` | Authorization reversed |

### ID Mapping

- Stripe card IDs: `ic_...` (mapped to `card_...` in Sardis)
- Stripe authorization IDs: `iauth_...` (mapped to `ctx_...` in Sardis)
- Sardis maintains `provider_card_id` / `provider_tx_id` for reverse lookups

---

## 9. Security Considerations

| Concern | Mitigation |
|---------|------------|
| PAN exposure | `reveal_card_details()` intentionally raises `NotImplementedError`. PAN access is restricted to client-side Stripe Issuing Elements (PCI-controlled). |
| Webhook authenticity | HMAC-SHA256 signature verification on every webhook event |
| API key storage | Environment variables only; never logged or stored in database |
| Policy bypass | Policy engine runs before card-level checks; fail-closed by default |
| Rate limiting | Stripe's built-in rate limits + Sardis API-level rate limiting via Redis |

---

## 10. Related Files

| File | Purpose |
|------|---------|
| `packages/sardis-cards/src/sardis_cards/providers/stripe_issuing.py` | StripeIssuingProvider implementation |
| `packages/sardis-cards/src/sardis_cards/providers/base.py` | CardProvider abstract interface |
| `packages/sardis-cards/src/sardis_cards/models.py` | Card, CardTransaction, CardStatus models |
| `packages/sardis-cards/src/sardis_cards/service.py` | CardService orchestration |
| `packages/sardis-cards/src/sardis_cards/webhooks.py` | Webhook routing and handling |
| `packages/sardis-cards/src/sardis_cards/card_lifecycle.py` | Card lifecycle state machine |
| `packages/sardis-cards/src/sardis_cards/card_routing.py` | Multi-provider card routing |
| `packages/sardis-core/src/sardis_v2_core/spending_policy.py` | Natural language spending policy engine |
