# Sardis API Reference

## Overview

The Sardis API is organized around REST. It accepts JSON-encoded request bodies, returns JSON-encoded responses, and uses standard HTTP response codes.

**Base URL:** `http://localhost:8000/api/v1`

**OpenAPI Docs:** `http://localhost:8000/docs`

---

## Authentication

The current MVP uses open access. In production, authenticate using API keys:

```http
Authorization: Bearer sk_live_xxxxxxxxxxxxx
```

---

## Agents

### Create Agent

Creates a new AI agent with an associated wallet.

```http
POST /agents
```

**Request Body:**

```json
{
  "name": "shopping_agent_1",
  "owner_id": "developer_123",
  "description": "Agent for e-commerce purchases",
  "initial_balance": "100.00",
  "limit_per_tx": "20.00",
  "limit_total": "100.00"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Agent name (3-50 chars) |
| owner_id | string | Yes | Developer/owner identifier |
| description | string | No | Agent description |
| initial_balance | decimal | No | Starting balance (default: 0) |
| limit_per_tx | decimal | No | Max amount per transaction |
| limit_total | decimal | No | Max total spending |

**Response:** `201 Created`

```json
{
  "agent": {
    "agent_id": "agent_a1b2c3d4e5f6g7h8",
    "name": "shopping_agent_1",
    "owner_id": "developer_123",
    "description": "Agent for e-commerce purchases",
    "wallet_id": "wallet_x1y2z3w4v5u6t7s8",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  },
  "wallet": {
    "wallet_id": "wallet_x1y2z3w4v5u6t7s8",
    "agent_id": "agent_a1b2c3d4e5f6g7h8",
    "balance": "100.00",
    "currency": "USDC",
    "limit_per_tx": "20.00",
    "limit_total": "100.00",
    "spent_total": "0.00",
    "remaining_limit": "100.00",
    "virtual_card": {
      "card_id": "vc_1234567890abcdef",
      "masked_number": "**** **** **** 5678",
      "is_active": true
    },
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Agent Wallet

Retrieves wallet information for an agent.

```http
GET /agents/{agent_id}/wallet
```

**Response:** `200 OK`

```json
{
  "wallet_id": "wallet_x1y2z3w4v5u6t7s8",
  "agent_id": "agent_a1b2c3d4e5f6g7h8",
  "balance": "85.00",
  "currency": "USDC",
  "limit_per_tx": "20.00",
  "limit_total": "100.00",
  "spent_total": "15.00",
  "remaining_limit": "85.00",
  "virtual_card": {
    "card_id": "vc_1234567890abcdef",
    "masked_number": "**** **** **** 5678",
    "is_active": true
  },
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List Agent Transactions

Gets transaction history for an agent.

```http
GET /agents/{agent_id}/transactions?limit=10&offset=0
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max transactions to return |
| offset | int | 0 | Pagination offset |

**Response:** `200 OK`

```json
[
  {
    "tx_id": "tx_abc123def456ghi789",
    "from_wallet": "wallet_x1y2z3w4v5u6t7s8",
    "to_wallet": "wallet_merchant_abc",
    "amount": "15.00",
    "fee": "0.10",
    "total_cost": "15.10",
    "currency": "USDC",
    "purpose": "Product purchase",
    "status": "completed",
    "created_at": "2024-01-15T10:35:00Z",
    "completed_at": "2024-01-15T10:35:01Z"
  }
]
```

---

## Payments

### Create Payment

Executes a payment from an agent to a merchant or wallet.

```http
POST /payments
```

**Request Body:**

```json
{
  "agent_id": "agent_a1b2c3d4e5f6g7h8",
  "merchant_id": "merchant_electronics_1",
  "amount": "15.99",
  "currency": "USDC",
  "purpose": "Product purchase: Wireless Headphones"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| agent_id | string | Yes | Agent making payment |
| merchant_id | string | * | Merchant receiving payment |
| recipient_wallet_id | string | * | Direct wallet payment |
| amount | decimal | Yes | Amount to pay |
| currency | string | No | Token (default: USDC) |
| purpose | string | No | Payment description |

*Either `merchant_id` or `recipient_wallet_id` is required.

**Response:** `200 OK`

```json
{
  "success": true,
  "transaction": {
    "tx_id": "tx_abc123def456ghi789",
    "from_wallet": "wallet_x1y2z3w4v5u6t7s8",
    "to_wallet": "wallet_merchant_abc",
    "amount": "15.99",
    "fee": "0.10",
    "total_cost": "16.09",
    "currency": "USDC",
    "purpose": "Product purchase: Wireless Headphones",
    "status": "completed",
    "created_at": "2024-01-15T10:35:00Z",
    "completed_at": "2024-01-15T10:35:01Z"
  },
  "error": null
}
```

**Error Response:** `400 Bad Request`

```json
{
  "success": false,
  "transaction": null,
  "error": "Insufficient balance: have 10.00, need 16.09"
}
```

### Create Payment Request

Creates an invoice that another agent can pay.

```http
POST /payments/request
```

**Request Body:**

```json
{
  "requester_agent_id": "agent_service_provider",
  "payer_agent_id": "agent_client",
  "amount": "25.00",
  "currency": "USDC",
  "description": "API usage fee for January",
  "expires_in_hours": 24
}
```

**Response:** `201 Created`

```json
{
  "request_id": "preq_abc123def456",
  "requester_agent_id": "agent_service_provider",
  "payer_agent_id": "agent_client",
  "amount": "25.00",
  "currency": "USDC",
  "description": "API usage fee for January",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-16T10:30:00Z"
}
```

### Pay Payment Request

Pays a pending payment request.

```http
POST /payments/request/{request_id}/pay
```

**Response:** `200 OK`

Same as Create Payment response.

### Estimate Payment

Calculates total cost including fees.

```http
GET /payments/estimate?amount=15.99&currency=USDC
```

**Response:** `200 OK`

```json
{
  "amount": "15.99",
  "fee": "0.10",
  "total": "16.09",
  "currency": "USDC"
}
```

### Get Transaction

Retrieves a specific transaction.

```http
GET /payments/{tx_id}
```

**Response:** `200 OK`

```json
{
  "tx_id": "tx_abc123def456ghi789",
  "from_wallet": "wallet_x1y2z3w4v5u6t7s8",
  "to_wallet": "wallet_merchant_abc",
  "amount": "15.99",
  "fee": "0.10",
  "total_cost": "16.09",
  "currency": "USDC",
  "purpose": "Product purchase",
  "status": "completed",
  "error_message": null,
  "created_at": "2024-01-15T10:35:00Z",
  "completed_at": "2024-01-15T10:35:01Z"
}
```

---

## Merchants

### Create Merchant

Registers a new merchant to receive payments.

```http
POST /merchants
```

**Request Body:**

```json
{
  "name": "TechStore Electronics",
  "description": "Electronics and gadgets retailer",
  "category": "electronics"
}
```

**Response:** `201 Created`

```json
{
  "merchant_id": "merchant_abc123def456",
  "name": "TechStore Electronics",
  "wallet_id": "wallet_m1n2o3p4q5r6s7t8",
  "description": "Electronics and gadgets retailer",
  "category": "electronics",
  "is_active": true,
  "created_at": "2024-01-15T10:00:00Z"
}
```

### List Merchants

Gets all registered merchants.

```http
GET /merchants
```

**Response:** `200 OK`

```json
[
  {
    "merchant_id": "merchant_abc123def456",
    "name": "TechStore Electronics",
    "wallet_id": "wallet_m1n2o3p4q5r6s7t8",
    "category": "electronics",
    "is_active": true
  }
]
```

---

## Product Catalog

### List Products

Browse the product catalog.

```http
GET /catalog/products?category=electronics&max_price=50&in_stock_only=true
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| category | string | null | Filter by category |
| max_price | decimal | null | Maximum price |
| in_stock_only | bool | true | Only in-stock items |

**Response:** `200 OK`

```json
[
  {
    "product_id": "prod_001",
    "name": "Wireless Bluetooth Headphones",
    "description": "High-quality wireless headphones with noise cancellation",
    "price": "49.99",
    "currency": "USDC",
    "category": "electronics",
    "in_stock": true,
    "merchant_id": "merchant_abc123"
  }
]
```

### Get Product

Get a specific product.

```http
GET /catalog/products/{product_id}
```

**Response:** `200 OK`

```json
{
  "product_id": "prod_001",
  "name": "Wireless Bluetooth Headphones",
  "description": "High-quality wireless headphones with noise cancellation",
  "price": "49.99",
  "currency": "USDC",
  "category": "electronics",
  "in_stock": true,
  "merchant_id": "merchant_abc123"
}
```

---

## Webhooks

### Create Webhook

Subscribe to events.

```http
POST /webhooks
```

**Request Body:**

```json
{
  "url": "https://your-app.com/webhooks/sardis",
  "events": ["payment.completed", "payment.failed", "limit.exceeded"]
}
```

**Available Events:**

| Event | Description |
|-------|-------------|
| payment.initiated | Payment started |
| payment.completed | Payment successful |
| payment.failed | Payment failed |
| wallet.created | New wallet created |
| wallet.funded | Funds added to wallet |
| limit.exceeded | Spending limit hit |
| limit.warning | Approaching limit (80%) |
| risk.alert | High risk detected |

**Response:** `201 Created`

```json
{
  "subscription_id": "whsub_abc123def456",
  "url": "https://your-app.com/webhooks/sardis",
  "events": ["payment.completed", "payment.failed", "limit.exceeded"],
  "secret": "whsec_xxxxxxxxxxxxxxxxxxxxxxxxx",
  "is_active": true,
  "total_deliveries": 0,
  "successful_deliveries": 0,
  "failed_deliveries": 0
}
```

**Webhook Payload:**

```json
{
  "id": "evt_abc123def456ghi789",
  "type": "payment.completed",
  "data": {
    "transaction": {
      "id": "tx_xyz789",
      "from_wallet": "wallet_agent_1",
      "to_wallet": "wallet_merchant_1",
      "amount": "15.99",
      "fee": "0.10",
      "total": "16.09",
      "currency": "USDC",
      "status": "completed"
    }
  },
  "created_at": "2024-01-15T10:35:00Z",
  "api_version": "2024-01"
}
```

**Verifying Signatures:**

```python
import hmac
import hashlib

def verify_webhook(payload: str, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# In your webhook handler:
signature = request.headers.get("X-Sardis-Signature")
if not verify_webhook(request.body, signature, webhook_secret):
    return Response(status=401)
```

### List Webhooks

```http
GET /webhooks
```

### Get Webhook

```http
GET /webhooks/{subscription_id}
```

### Update Webhook

```http
PATCH /webhooks/{subscription_id}
```

### Delete Webhook

```http
DELETE /webhooks/{subscription_id}
```

### Test Webhook

```http
POST /webhooks/{subscription_id}/test
```

---

## Risk & Authorization

### Get Risk Score

Get risk assessment for an agent.

```http
GET /risk/agents/{agent_id}/score
```

**Response:** `200 OK`

```json
{
  "score": 15.0,
  "level": "low",
  "factors": [],
  "details": {},
  "is_acceptable": true
}
```

### Get Risk Profile

Get detailed risk profile.

```http
GET /risk/agents/{agent_id}/profile
```

**Response:** `200 OK`

```json
{
  "agent_id": "agent_a1b2c3d4e5f6g7h8",
  "current_score": 15.0,
  "current_level": "low",
  "total_transactions": 42,
  "failed_transactions": 2,
  "total_volume": "1250.00",
  "is_flagged": false,
  "flag_reason": null,
  "authorized_services": ["merchant_abc123", "merchant_xyz789"]
}
```

### Authorize Service

Whitelist a merchant/service for reduced risk scoring.

```http
POST /risk/agents/{agent_id}/authorize
```

**Request Body:**

```json
{
  "service_id": "merchant_abc123"
}
```

**Response:** `200 OK`

```json
{
  "agent_id": "agent_a1b2c3d4e5f6g7h8",
  "services": ["merchant_abc123"]
}
```

### Revoke Authorization

```http
DELETE /risk/agents/{agent_id}/authorize/{service_id}
```

### Flag Agent

Flag an agent for review (blocks transactions).

```http
POST /risk/agents/{agent_id}/flag
```

**Request Body:**

```json
{
  "reason": "Suspicious transaction pattern detected"
}
```

### Unflag Agent

```http
DELETE /risk/agents/{agent_id}/flag
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid/missing API key |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable - Validation error |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Error - Server error |

**Error Response Format:**

```json
{
  "detail": "Agent agent_xyz not found"
}
```

---

## Rate Limits

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 60 | 1,000 |
| Standard | 300 | 10,000 |
| Enterprise | 1,000 | Unlimited |

Rate limit headers:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642248600
```

---

## SDK Examples

### Python

```python
from sardis_sdk import SardisClient
from decimal import Decimal

client = SardisClient(base_url="http://localhost:8000")

# Create agent
agent = client.register_agent(
    name="my_agent",
    owner_id="dev_123",
    initial_balance=Decimal("100.00"),
    limit_per_tx=Decimal("20.00")
)

# Check if can afford
if client.can_afford(agent.agent.agent_id, Decimal("15.99")):
    result = client.pay(
        agent_id=agent.agent.agent_id,
        amount=Decimal("15.99"),
        merchant_id="merchant_123"
    )
```

### cURL

```bash
# Create agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"name":"test","owner_id":"dev","initial_balance":"100"}'

# Make payment
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"agent_xxx","merchant_id":"merchant_yyy","amount":"10"}'
```

### TypeScript

```typescript
const response = await fetch('http://localhost:8000/api/v1/agents', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'my_agent',
    owner_id: 'dev_123',
    initial_balance: '100.00',
    limit_per_tx: '20.00'
  })
});

const { agent, wallet } = await response.json();
```

---

## Changelog

### v0.3.0 (Current)
- **PostgreSQL Ledger**: Persistent, ACID-compliant transaction storage
- **Async Architecture**: High-performance asynchronous service layer
- **Database Migrations**: Alembic integration for schema management
- Improved test coverage and reliability

### v0.2.0
- Multi-chain support (Base, Ethereum, Polygon, Solana)
- Multi-token support (USDC, USDT, PYUSD, EURC)
- Webhook system
- Risk scoring and service authorization
- Payment requests (invoices)

### v0.1.0
- Initial MVP release
- Agent wallets with spending limits
- Basic payment processing
- Shopping agent demo

