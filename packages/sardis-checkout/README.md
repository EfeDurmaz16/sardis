# Sardis Checkout Surface

**Agentic Checkout** - PSP routing and orchestration layer for Sardis.

This package provides the checkout surface that routes agent payments to existing PSPs (Stripe, PayPal, Coinbase, Circle) while leveraging the core Agent Wallet OS for policy enforcement and mandate verification.

---

## Architecture

```
Agent Checkout Request
         │
         ▼
┌─────────────────────────────────────┐
│   Agent Wallet OS (Core)            │
│   - Policy Check                    │
│   - Mandate Verification            │
│   - Agent Identity                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Checkout Orchestrator             │
│   - PSP Selection                   │
│   - Session Management              │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
┌──────────┐   ┌──────────┐
│ Stripe   │   │ PayPal   │
│ Connector│   │ Connector│
└──────────┘   └──────────┘
```

---

## Features

- **Multi-PSP Support:** Route to Stripe, PayPal, Coinbase, Circle
- **Policy-Based Routing:** Uses core policy engine for approval
- **Checkout Sessions:** Create and manage checkout sessions
- **Webhook Handling:** Process PSP webhooks
- **Merchant Dashboard:** Analytics and configuration

---

## Installation

```bash
pip install sardis-checkout
```

---

## Usage

### Basic Checkout Flow

```python
from sardis_checkout import CheckoutOrchestrator
from sardis_checkout.connectors import StripeConnector

# Initialize orchestrator
orchestrator = CheckoutOrchestrator(
    stripe_connector=StripeConnector(api_key="sk_..."),
)

# Create checkout session
session = await orchestrator.create_checkout_session(
    agent_id="agent_123",
    merchant_id="merchant_456",
    amount=Decimal("100.00"),
    currency="USD",
    metadata={"order_id": "order_789"},
)

# Get checkout URL
print(session.checkout_url)  # https://checkout.stripe.com/...
```

### PSP Selection

```python
# Orchestrator automatically selects PSP based on:
# 1. Merchant preference
# 2. Agent policy constraints
# 3. PSP availability

psp = await orchestrator.select_psp(
    merchant_id="merchant_456",
    agent_id="agent_123",
    amount=Decimal("100.00"),
)
```

### Webhook Handling

```python
from sardis_checkout.webhooks import handle_stripe_webhook

# Handle Stripe webhook
event = await handle_stripe_webhook(
    payload=request.body,
    signature=request.headers["stripe-signature"],
    secret=stripe_webhook_secret,
)

if event.type == "checkout.session.completed":
    # Update ledger, emit webhook, etc.
    await process_payment_completion(event.data)
```

---

## Connectors

### Stripe

```python
from sardis_checkout.connectors.stripe import StripeConnector

connector = StripeConnector(
    api_key="sk_test_...",
    webhook_secret="whsec_...",
)

session = await connector.create_checkout_session(
    amount=Decimal("100.00"),
    currency="USD",
    agent_id="agent_123",
    metadata={},
)
```

### PayPal (Coming Soon)

```python
from sardis_checkout.connectors.paypal import PayPalConnector

connector = PayPalConnector(
    client_id="...",
    client_secret="...",
)
```

### Coinbase Commerce (Coming Soon)

```python
from sardis_checkout.connectors.coinbase import CoinbaseConnector

connector = CoinbaseConnector(
    api_key="...",
)
```

---

## API Integration

### FastAPI Router

```python
from sardis_checkout.api import create_checkout_router

app.include_router(
    create_checkout_router(orchestrator),
    prefix="/api/v2/checkout",
    tags=["checkout"],
)
```

### Endpoints

- `POST /checkout/create` - Create checkout session
- `GET /checkout/{id}` - Get checkout status
- `POST /checkout/{id}/complete` - Complete checkout
- `POST /checkout/webhooks/{psp}` - PSP webhook handler

---

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type check
mypy src/

# Lint
ruff check src/
```

---

## License

Proprietary - All rights reserved.
