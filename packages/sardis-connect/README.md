# sardis-connect

Make any API agent-ready in 3 lines. Zero-crypto merchant integration for Sardis.

## Quick Start

```python
from fastapi import FastAPI
from sardis_connect import SardisConnect

app = FastAPI()

# 1. Initialize with your merchant credentials
sardis = SardisConnect(
    api_key="mch_live_xxx",
    merchant_id="merch_xxx",
    service_name="My AI API",
)

# 2. Define your priced endpoints
sardis.price("/api/generate", amount="0.05", description="Generate text")
sardis.price("/api/analyze", amount="0.10", description="Analyze data")

# 3. Mount the router
app.include_router(sardis.router)
```

This adds three endpoints to your API:

| Endpoint | Purpose |
|----------|---------|
| `GET /.well-known/sardis.json` | Agent discovery — what your API offers and costs |
| `POST /sardis/pay` | Create payment session before accessing priced endpoint |
| `POST /sardis/verify` | Verify payment was completed |

## How Agents Use It

```python
import httpx

# 1. Discover the API
manifest = httpx.get("https://your-api.com/.well-known/sardis.json").json()

# 2. Pay for the endpoint
payment = httpx.post("https://your-api.com/sardis/pay", json={
    "endpoint": "/api/generate",
    "payer_wallet_id": "wal_xxx",
}).json()

# 3. Complete payment (via Sardis SDK)
sardis_client.pay(session_id=payment["session_id"])

# 4. Use the API with proof of payment
result = httpx.post("https://your-api.com/api/generate",
    headers={"X-Sardis-Session": payment["session_id"]},
    json={"prompt": "Hello world"}
)
```

## Settlement

You receive USD in your Stripe account. The agent pays in stablecoins.
Sardis handles the conversion. You never touch crypto.

## Environment Variables

```bash
SARDIS_MERCHANT_API_KEY=mch_live_xxx
SARDIS_MERCHANT_ID=merch_xxx
SARDIS_CONNECT_BASE_URL=https://your-api.com
SARDIS_WEBHOOK_SECRET=your_webhook_secret_here  # optional
```
