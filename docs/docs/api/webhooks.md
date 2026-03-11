# Webhooks

Real-time event notifications for wallet activity, payments, and policy violations.

## Overview

Sardis webhooks notify your application when events occur in your Sardis account. Use webhooks to:

- Monitor payment confirmations
- Detect policy violations
- Track wallet activity
- Respond to anomalies
- Trigger custom workflows

## Supported Events

### Wallet Events

- `wallet.created` - New wallet created
- `wallet.funded` - Wallet received funds
- `wallet.frozen` - Wallet frozen
- `wallet.unfrozen` - Wallet unfrozen
- `wallet.deleted` - Wallet deleted
- `wallet.policy.updated` - Spending policy changed

### Payment Events

- `wallet.payment.initiated` - Payment started
- `wallet.payment.success` - Payment confirmed on-chain
- `wallet.payment.failed` - Payment failed
- `wallet.payment.cancelled` - Payment cancelled

### Policy Events

- `wallet.policy.violated` - Transaction blocked by policy
- `wallet.policy.warning` - Transaction near policy limit

### Trust & KYA Events

- `wallet.trust.score_changed` - Trust score updated
- `wallet.trust.anomaly_detected` - Suspicious behavior
- `wallet.trust.threshold_crossed` - Score crossed threshold

### Compliance Events

- `wallet.compliance.check_passed` - Compliance check passed
- `wallet.compliance.check_failed` - Compliance check failed
- `wallet.compliance.sanctions_hit` - Sanctions screening alert

## Creating a Webhook

### Via API

```bash
curl https://api.sardis.sh/v2/webhooks \
  -H "Authorization: Bearer sk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/sardis-webhook",
    "events": ["wallet.payment.success", "wallet.payment.failed"],
    "secret": "whsec_example_placeholder_key"  # nosecret
  }'
```

### Via SDK

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")

webhook = client.webhooks.create(
    url="https://your-app.com/sardis-webhook",
    events=[
        "wallet.payment.success",
        "wallet.payment.failed",
        "wallet.policy.violated"
    ],
    secret="whsec_example_placeholder_key"  # nosecret
)

print(f"Webhook ID: {webhook.id}")
```

## Webhook Payload

All webhook events follow this format:

```json
{
  "id": "evt_abc123",
  "type": "wallet.payment.success",
  "created": 1708531200,
  "data": {
    "wallet_id": "wallet_abc123",
    "payment": {
      "id": "payment_xyz789",
      "amount": "50.00",
      "token": "USDC",
      "to": "0x1234...",
      "tx_hash": "0xabcd...",
      "status": "success",
      "created_at": "2026-02-21T10:30:00Z"
    }
  }
}
```

## Event Payloads

### wallet.payment.success

```json
{
  "id": "evt_abc123",
  "type": "wallet.payment.success",
  "created": 1708531200,
  "data": {
    "wallet_id": "wallet_abc123",
    "payment": {
      "id": "payment_xyz789",
      "amount": "50.00",
      "token": "USDC",
      "to": "0x1234567890abcdef1234567890abcdef12345678",
      "tx_hash": "0xabcd...",
      "block_number": 12345678,
      "gas_used": "0.0002",
      "purpose": "API credits",
      "created_at": "2026-02-21T10:30:00Z",
      "confirmed_at": "2026-02-21T10:30:15Z"
    }
  }
}
```

### wallet.payment.failed

```json
{
  "id": "evt_abc124",
  "type": "wallet.payment.failed",
  "created": 1708531300,
  "data": {
    "wallet_id": "wallet_abc123",
    "payment": {
      "id": "payment_xyz790",
      "amount": "50.00",
      "token": "USDC",
      "to": "0x1234...",
      "status": "failed",
      "error": "insufficient_balance",
      "error_message": "Wallet balance too low",
      "created_at": "2026-02-21T10:31:00Z"
    }
  }
}
```

### wallet.policy.violated

```json
{
  "id": "evt_abc125",
  "type": "wallet.policy.violated",
  "created": 1708531400,
  "data": {
    "wallet_id": "wallet_abc123",
    "violation": {
      "type": "daily_limit_exceeded",
      "policy": "Max $500/day",
      "attempted_amount": "5000.00",
      "limit": "500.00",
      "current_daily_spend": "450.00",
      "timestamp": "2026-02-21T10:32:00Z"
    }
  }
}
```

### wallet.trust.anomaly_detected

```json
{
  "id": "evt_abc126",
  "type": "wallet.trust.anomaly_detected",
  "created": 1708531500,
  "data": {
    "wallet_id": "wallet_abc123",
    "anomaly": {
      "type": "spending_spike",
      "severity": "high",
      "baseline": "75.00/day (30-day average)",
      "detected": "5000.00 single transaction",
      "action": "require_confirmation",
      "timestamp": "2026-02-21T10:33:00Z"
    }
  }
}
```

## Webhook Security

### Signature Verification

Sardis signs all webhook payloads with HMAC-SHA256. Verify signatures to ensure requests come from Sardis:

#### Python

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    """Verify Sardis webhook signature."""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)

# Flask example
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/sardis-webhook', methods=['POST'])
def handle_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Sardis-Signature')
    secret = "whsec_example_placeholder_key"  # nosecret

    if not verify_webhook_signature(payload, signature, secret):
        return jsonify({"error": "Invalid signature"}), 401

    event = request.get_json()

    if event['type'] == 'wallet.payment.success':
        handle_payment_success(event['data'])
    elif event['type'] == 'wallet.policy.violated':
        handle_policy_violation(event['data'])

    return jsonify({"status": "received"}), 200
```

#### TypeScript

```typescript
import crypto from 'crypto';
import express from 'express';

function verifyWebhookSignature(
  payload: string,
  signature: string,
  secret: string
): boolean {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

const app = express();

app.post('/sardis-webhook', express.raw({ type: 'application/json' }), (req, res) => {
  const payload = req.body.toString();
  const signature = req.headers['x-sardis-signature'] as string;
  const secret = 'whsec_example_placeholder_key'; // nosecret

  if (!verifyWebhookSignature(payload, signature, secret)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  const event = JSON.parse(payload);

  if (event.type === 'wallet.payment.success') {
    handlePaymentSuccess(event.data);
  }

  res.status(200).json({ status: 'received' });
});
```

### Best Practices

1. **Always verify signatures** - Never trust payload without verification
2. **Use HTTPS endpoints** - HTTP webhooks rejected
3. **Respond quickly** - Return 200 within 5 seconds
4. **Process async** - Queue events for background processing
5. **Handle idempotency** - Same event may be sent multiple times
6. **Rotate secrets** - Update webhook secrets periodically

## Handling Webhooks

### Express.js Example

```typescript
import express from 'express';
import { verifyWebhookSignature } from './utils';

const app = express();

app.post('/sardis-webhook',
  express.raw({ type: 'application/json' }),
  async (req, res) => {
    const payload = req.body.toString();
    const signature = req.headers['x-sardis-signature'] as string;

    if (!verifyWebhookSignature(payload, signature, process.env.WEBHOOK_SECRET!)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }

    const event = JSON.parse(payload);

    // Queue for background processing
    await queue.add('webhook', event);

    // Acknowledge receipt
    res.status(200).json({ received: true });
  }
);

// Background worker
queue.process('webhook', async (job) => {
  const event = job.data;

  switch (event.type) {
    case 'wallet.payment.success':
      await updateOrderStatus(event.data.payment.id, 'paid');
      await sendConfirmationEmail(event.data.payment);
      break;

    case 'wallet.payment.failed':
      await updateOrderStatus(event.data.payment.id, 'failed');
      await notifyCustomerSupport(event.data.payment);
      break;

    case 'wallet.policy.violated':
      await alertSecurityTeam(event.data.violation);
      break;
  }
});
```

### FastAPI Example

```python
from fastapi import FastAPI, Request, HTTPException
from sardis import verify_webhook_signature
import asyncio

app = FastAPI()

@app.post("/sardis-webhook")
async def handle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Sardis-Signature")
    secret = "whsec_example_placeholder_key"  # nosecret

    if not verify_webhook_signature(payload.decode(), signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = await request.json()

    # Queue for background processing
    await queue.enqueue("webhook", event)

    return {"received": True}

# Background worker
async def process_webhook(event):
    event_type = event["type"]
    data = event["data"]

    if event_type == "wallet.payment.success":
        await update_order_status(data["payment"]["id"], "paid")
        await send_confirmation_email(data["payment"])

    elif event_type == "wallet.policy.violated":
        await alert_security_team(data["violation"])
```

## Retry Logic

If your endpoint returns a non-200 status code, Sardis will retry:

- **Retry 1:** After 1 minute
- **Retry 2:** After 5 minutes
- **Retry 3:** After 15 minutes
- **Retry 4:** After 1 hour
- **Retry 5:** After 6 hours

After 5 failed attempts, the webhook is disabled and you're notified via email.

## Managing Webhooks

### List Webhooks

```python
webhooks = client.webhooks.list()

for webhook in webhooks:
    print(f"{webhook.id}: {webhook.url}")
```

### Update Webhook

```python
client.webhooks.update(
    webhook_id="webhook_abc123",
    events=["wallet.payment.success"]  # Updated event list
)
```

### Delete Webhook

```python
client.webhooks.delete("webhook_abc123")
```

### Test Webhook

Send a test event to verify your endpoint:

```python
client.webhooks.test(
    webhook_id="webhook_abc123",
    event_type="wallet.payment.success"
)
```

## Webhook Logs

View delivery history:

```python
logs = client.webhooks.logs(webhook_id="webhook_abc123")

for log in logs:
    print(f"{log.timestamp}: {log.status} - {log.response_code}")
```

## Event Filtering

Subscribe to specific events:

```python
# Only payment events
webhook = client.webhooks.create(
    url="https://your-app.com/payments",
    events=[
        "wallet.payment.success",
        "wallet.payment.failed"
    ]
)

# Only policy events
webhook = client.webhooks.create(
    url="https://your-app.com/policy-alerts",
    events=[
        "wallet.policy.violated",
        "wallet.policy.warning"
    ]
)

# All events
webhook = client.webhooks.create(
    url="https://your-app.com/all-events",
    events=["*"]
)
```

## Use Cases

### Order Fulfillment

```python
@app.post("/sardis-webhook")
async def handle_webhook(request: Request):
    event = await verify_and_parse(request)

    if event["type"] == "wallet.payment.success":
        payment = event["data"]["payment"]

        # Update order status
        order = await get_order_by_payment_id(payment["id"])
        order.status = "paid"
        await order.save()

        # Fulfill order
        await fulfill_order(order.id)

        # Send confirmation
        await send_email(order.customer_email, "Order confirmed!")

    return {"received": True}
```

### Anomaly Alerts

```python
@app.post("/sardis-webhook")
async def handle_webhook(request: Request):
    event = await verify_and_parse(request)

    if event["type"] == "wallet.trust.anomaly_detected":
        anomaly = event["data"]["anomaly"]

        # Alert security team
        await send_slack_alert(
            channel="#security",
            message=f"🚨 Anomaly detected: {anomaly['type']}\n"
                    f"Severity: {anomaly['severity']}\n"
                    f"Wallet: {event['data']['wallet_id']}"
        )

        # Freeze wallet if critical
        if anomaly["severity"] == "critical":
            await client.wallets.freeze(event["data"]["wallet_id"])

    return {"received": True}
```

### Accounting Integration

```python
@app.post("/sardis-webhook")
async def handle_webhook(request: Request):
    event = await verify_and_parse(request)

    if event["type"] == "wallet.payment.success":
        payment = event["data"]["payment"]

        # Create QuickBooks invoice
        await quickbooks.create_journal_entry(
            date=payment["created_at"],
            debit_account="Agent Wallet",
            credit_account="Vendor Payments",
            amount=payment["amount"],
            memo=payment["purpose"]
        )

    return {"received": True}
```

## Troubleshooting

### Webhook Not Receiving Events

1. Verify endpoint is reachable from internet
2. Check webhook logs in Sardis dashboard
3. Ensure endpoint returns 200 status
4. Verify signature verification is correct

### Duplicate Events

Sardis may send the same event multiple times. Make your handler idempotent:

```python
processed_events = set()

@app.post("/sardis-webhook")
async def handle_webhook(request: Request):
    event = await verify_and_parse(request)

    # Check if already processed
    if event["id"] in processed_events:
        return {"received": True, "duplicate": True}

    processed_events.add(event["id"])

    # Process event...

    return {"received": True}
```

### Timeout Issues

Background process long-running tasks:

```python
@app.post("/sardis-webhook")
async def handle_webhook(request: Request):
    event = await verify_and_parse(request)

    # Queue immediately
    await queue.enqueue("webhook", event)

    # Return quickly (< 5 seconds)
    return {"received": True}
```

## Next Steps

- [REST API Reference](rest.md) - Complete API docs
- [Python SDK](../sdks/python.md) - SDK reference
- [Spending Policies](../concepts/policies.md) - Policy documentation
