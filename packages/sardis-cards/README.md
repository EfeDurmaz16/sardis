# sardis-cards

Virtual card integration for Sardis payment platform.

## Overview

This package provides virtual card issuance and management capabilities for AI agent wallets. It supports multiple card providers with Lithic as the primary integration.

## Supported Providers

- **Lithic** (recommended) - Developer-friendly API, used by Mercury, Brex, Ramp
- **Mock** - For testing and development

## Features

- Issue virtual cards linked to agent wallets
- Pre-load cards from stablecoin balances or bank transfers
- Per-transaction, daily, and monthly spending limits
- Merchant category controls
- Real-time transaction webhooks
- Card freeze/unfreeze operations

## Installation

```bash
pip install sardis-cards

# With Lithic provider
pip install sardis-cards[lithic]
```

## Quick Start

```python
from sardis_cards import CardService
from sardis_cards.providers.lithic import LithicProvider

# Initialize provider
provider = LithicProvider(api_key="your_lithic_api_key")
service = CardService(provider=provider)

# Issue a virtual card
card = await service.issue_card(
    wallet_id="wallet_123",
    card_type="virtual",
    limit_per_tx=500.00,
    limit_daily=2000.00,
)

# Fund the card
await service.fund_card(
    card_id=card.card_id,
    amount=100.00,
    source="stablecoin",
)

# Get card details
card = await service.get_card(card_id=card.card_id)
```

## Webhooks

Handle card transaction webhooks:

```python
from sardis_cards.webhooks import CardWebhookHandler

handler = CardWebhookHandler(secret="your_webhook_secret")

@app.post("/webhooks/cards")
async def handle_card_webhook(request: Request):
    event = handler.verify_and_parse(
        payload=await request.body(),
        signature=request.headers.get("X-Lithic-Signature"),
    )
    
    if event.type == "transaction.created":
        # Handle new transaction
        pass
```

## Configuration

Set environment variables:

```bash
LITHIC_API_KEY=your_api_key
LITHIC_ENVIRONMENT=sandbox  # or production
LITHIC_WEBHOOK_SECRET=your_webhook_secret
```

## License

MIT
