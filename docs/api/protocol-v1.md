# Sardis Protocol v1.0 -- API Reference

> Base URL: `https://api.sardis.sh/api/v2`
>
> All endpoints require a Bearer token via the `Authorization` header
> unless noted otherwise.

---

## Table of Contents

1. [Payment Objects](#payment-objects)
2. [Funding](#funding)
3. [Mandate Delegation](#mandate-delegation)
4. [FX (Foreign Exchange)](#fx-foreign-exchange)
5. [Bridge Transfers](#bridge-transfers)
6. [Escrow](#escrow)
7. [Disputes](#disputes)
8. [Batch Payments](#batch-payments)
9. [Streaming Payments](#streaming-payments)
10. [Usage Metering](#usage-metering)

---

## Payment Objects

Payment objects are signed, one-time, merchant-bound payment tokens.
They are the core settlement primitive in the Sardis protocol.

### POST /payment-objects/mint

Create a signed, one-time payment token from a spending mandate.

**Request Body**

```json
{
  "mandate_id": "mandate_abc123",
  "merchant_id": "merch_xyz789",
  "amount": "25.00",
  "currency": "USDC",
  "privacy_tier": "transparent",
  "memo": "Invoice #1042",
  "expires_in_seconds": 3600,
  "metadata": { "order_id": "ord_001" }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mandate_id` | string | yes | Spending mandate to mint from |
| `merchant_id` | string | yes | Merchant this payment is for |
| `amount` | decimal | yes | Exact payment amount (> 0) |
| `currency` | string | no | Default `"USDC"` |
| `privacy_tier` | string | no | `transparent`, `hybrid`, or `full_zk`. Default `"transparent"` |
| `memo` | string | no | Optional memo (max 256 chars) |
| `expires_in_seconds` | int | no | TTL 60-86400. Default `3600` |
| `metadata` | object | no | Arbitrary key-value pairs |

**Response** `201 Created`

```json
{
  "object_id": "po_a1b2c3d4e5f6",
  "mandate_id": "mandate_abc123",
  "merchant_id": "merch_xyz789",
  "exact_amount": "25.00",
  "currency": "USDC",
  "status": "minted",
  "privacy_tier": "transparent",
  "session_hash": "sha256:...",
  "cell_ids": ["cell_aaa111", "cell_bbb222"],
  "signature_chain": ["sig_0x..."],
  "object_hash": "sha256:...",
  "expires_at": "2026-03-23T13:00:00+00:00",
  "created_at": "2026-03-23T12:00:00+00:00",
  "metadata": { "order_id": "ord_001" }
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Payment object minted |
| 404 | Mandate not found |
| 409 | Mandate is not active |
| 422 | Amount exceeds per-tx or total limit |

---

### POST /payment-objects/{id}/present

Transition a payment object from `minted` to `presented`.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Payment object ID (`po_...`) |

**Request Body**

```json
{
  "merchant_id": "merch_xyz789",
  "merchant_signature": "0xabc..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `merchant_id` | string | yes | Merchant presenting to |
| `merchant_signature` | string | no | Merchant's verification signature |

**Response** `200 OK` -- Same shape as `PaymentObjectResponse`.

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Transitioned to presented |
| 403 | Merchant ID mismatch |
| 404 | Payment object not found |
| 409 | Object is not in `minted` state |
| 410 | Payment object has expired |

---

### POST /payment-objects/{id}/verify

Transition a payment object from `presented` to `verified` (merchant-side).

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Payment object ID (`po_...`) |

**Request Body**

```json
{
  "merchant_id": "merch_xyz789",
  "merchant_signature": "0xdef..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `merchant_id` | string | yes | Verifying merchant |
| `merchant_signature` | string | yes | Merchant signature over the object hash |

**Response** `200 OK` -- Same shape as `PaymentObjectResponse`.

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Transitioned to verified |
| 403 | Merchant ID mismatch |
| 404 | Payment object not found |
| 409 | Object is not in `presented` state |

---

### GET /payment-objects/{id}

Retrieve a single payment object by ID.

**Response** `200 OK` -- `PaymentObjectResponse`

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Payment object not found |

---

### GET /payment-objects

List payment objects with optional filters.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| `mandate_id` | string | Filter by mandate |
| `merchant_id` | string | Filter by merchant |
| `status` | string | Filter by status (`minted`, `presented`, `verified`, `settled`, `expired`) |
| `offset` | int | Pagination offset (default 0) |
| `limit` | int | Page size 1-200 (default 50) |

**Response** `200 OK`

```json
{
  "objects": [ /* PaymentObjectResponse[] */ ],
  "total": 142,
  "offset": 0,
  "limit": 50
}
```

---

## Funding

UTXO-style funding commitments and cells. Funding cells are discrete,
reserve-backed units that back payment objects.

### POST /funding/commit

Create a funding commitment and mint initial funding cells.

**Request Body**

```json
{
  "vault_ref": "0x1234...abcd",
  "total_value": "1000.00",
  "currency": "USDC",
  "cell_strategy": "fixed",
  "cell_denomination": "100.00",
  "settlement_preferences": { "chain": "tempo" },
  "expires_in_seconds": 604800,
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vault_ref` | string | yes | On-chain vault or wallet reference |
| `total_value` | decimal | yes | Total value to commit (> 0) |
| `currency` | string | no | Default `"USDC"` |
| `cell_strategy` | string | no | `fixed` or `proportional`. Default `"fixed"` |
| `cell_denomination` | decimal | cond. | Required when `cell_strategy` is `"fixed"` |
| `settlement_preferences` | object | no | Chain/routing preferences |
| `expires_in_seconds` | int | no | TTL in seconds (min 3600) |
| `metadata` | object | no | Arbitrary key-value pairs |

**Response** `201 Created`

```json
{
  "commitment_id": "fcom_a1b2c3d4e5f6",
  "org_id": "org_abc",
  "vault_ref": "0x1234...abcd",
  "total_value": "1000.00",
  "remaining_value": "1000.00",
  "currency": "USDC",
  "cell_strategy": "fixed",
  "cell_denomination": "100.00",
  "cell_count": 10,
  "status": "active",
  "expires_at": "2026-03-30T12:00:00+00:00",
  "created_at": "2026-03-23T12:00:00+00:00",
  "metadata": {}
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Commitment created with cells |
| 422 | Missing `cell_denomination` for fixed strategy |

---

### GET /funding/commitments

List funding commitments for the authenticated organization.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status (`active`, `depleted`, `expired`) |

**Response** `200 OK` -- `CommitmentResponse[]`

---

### GET /funding/cells

List funding cells with optional filters.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| `commitment_id` | string | Filter by commitment |
| `status` | string | `available`, `claimed`, `spent`, `merged` |
| `currency` | string | Filter by currency |
| `offset` | int | Default 0 |
| `limit` | int | 1-200, default 50 |

**Response** `200 OK`

```json
{
  "cells": [
    {
      "cell_id": "cell_aaa111",
      "commitment_id": "fcom_a1b2c3d4e5f6",
      "value": "100.00",
      "currency": "USDC",
      "status": "available",
      "owner_mandate_id": null,
      "payment_object_id": null,
      "claimed_at": null,
      "spent_at": null,
      "created_at": "2026-03-23T12:00:00+00:00"
    }
  ],
  "total": 10,
  "offset": 0,
  "limit": 50
}
```

---

### POST /funding/cells/{id}/split

Split a single funding cell into smaller cells.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Cell ID (`cell_...`) |

**Request Body**

```json
{
  "amounts": ["60.00", "40.00"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amounts` | decimal[] | yes | At least 2 values that sum to the cell's value |

**Response** `200 OK` -- `CellResponse[]` (the new cells)

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Cell split successfully |
| 404 | Cell not found |
| 409 | Cell is not `available` |
| 422 | Split amounts do not sum to cell value |

---

### POST /funding/cells/merge

Merge multiple funding cells into a single cell.

**Request Body**

```json
{
  "cell_ids": ["cell_aaa111", "cell_bbb222", "cell_ccc333"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cell_ids` | string[] | yes | At least 2 cell IDs to merge |

**Response** `200 OK` -- `CellResponse` (the merged cell)

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Cells merged successfully |
| 404 | One or more cells not found |
| 409 | Not all cells are `available` |
| 422 | Cells have different currencies or belong to different commitments |

---

## Mandate Delegation

Hierarchical mandate trees. A parent mandate delegates to children
with inherited, narrowing bounds.

### POST /mandates/{id}/delegate

Create a child mandate via delegation with narrowed bounds.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Parent mandate ID |

**Request Body**

```json
{
  "agent_id": "agent_research_01",
  "purpose_scope": "API hosting expenses",
  "amount_per_tx": "50.00",
  "amount_daily": "200.00",
  "amount_weekly": null,
  "amount_monthly": "2000.00",
  "amount_total": "5000.00",
  "merchant_scope": { "categories": ["cloud_infrastructure"] },
  "allowed_rails": ["usdc"],
  "allowed_chains": ["tempo", "base"],
  "allowed_tokens": ["USDC"],
  "expires_at": "2026-06-23T00:00:00+00:00",
  "approval_mode": "auto",
  "approval_threshold": null,
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | no | Agent to delegate to |
| `purpose_scope` | string | no | Narrowed purpose (must be subset of parent) |
| `amount_per_tx` | decimal | no | Per-transaction limit (must be <= parent) |
| `amount_daily` | decimal | no | Daily limit |
| `amount_weekly` | decimal | no | Weekly limit |
| `amount_monthly` | decimal | no | Monthly limit |
| `amount_total` | decimal | no | Lifetime total |
| `merchant_scope` | object | no | Allowed merchant categories/IDs |
| `allowed_rails` | string[] | no | Payment rails subset |
| `allowed_chains` | string[] | no | Allowed blockchain networks |
| `allowed_tokens` | string[] | no | Allowed token types |
| `expires_at` | ISO 8601 | no | Must be before parent's expiry |
| `approval_mode` | string | no | `auto`, `threshold`, or `always_human`. Default `"auto"` |
| `approval_threshold` | decimal | no | Amount above which human approval is required |
| `metadata` | object | no | Arbitrary key-value pairs |

**Response** `201 Created`

```json
{
  "child_mandate_id": "mandate_newchild01",
  "parent_mandate_id": "mandate_abc123",
  "delegation_depth": 1,
  "status": "active",
  "created_at": "2026-03-23T12:00:00+00:00"
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Child mandate created |
| 404 | Parent mandate not found |
| 422 | Delegation violates narrowing rules (details in response body) |

---

### GET /mandates/{id}/tree

Get the full delegation tree rooted at a mandate.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Root mandate ID |

**Response** `200 OK`

```json
{
  "id": "mandate_abc123",
  "parent_mandate_id": null,
  "agent_id": null,
  "principal_id": "usr_owner",
  "purpose_scope": "Operations",
  "amount_per_tx": "500.00",
  "amount_total": "50000.00",
  "spent_total": "1200.00",
  "status": "active",
  "delegation_depth": 0,
  "children": [
    {
      "id": "mandate_child01",
      "parent_mandate_id": "mandate_abc123",
      "agent_id": "agent_research_01",
      "principal_id": "usr_owner",
      "purpose_scope": "API hosting expenses",
      "amount_per_tx": "50.00",
      "amount_total": "5000.00",
      "spent_total": "320.00",
      "status": "active",
      "delegation_depth": 1,
      "children": [],
      "created_at": "2026-03-22T09:00:00+00:00"
    }
  ],
  "created_at": "2026-03-20T08:00:00+00:00"
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Tree returned |
| 404 | Mandate not found |

---

## FX (Foreign Exchange)

Cross-currency stablecoin swaps. On Tempo the provider is `tempo_dex`;
on other chains the swap routes through Uniswap V3.

### POST /fx/quote

Request an FX quote for a stablecoin swap.

**Request Body**

```json
{
  "from_currency": "USDC",
  "to_currency": "EURC",
  "from_amount": "1000.00",
  "chain": "tempo",
  "slippage_bps": 50
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_currency` | string | yes | Source currency |
| `to_currency` | string | yes | Target currency |
| `from_amount` | decimal | yes | Amount to swap (> 0) |
| `chain` | string | no | Default `"tempo"` |
| `slippage_bps` | int | no | Slippage tolerance in basis points 1-1000. Default `50` |

**Response** `201 Created`

```json
{
  "quote_id": "fxq_a1b2c3d4e5f6",
  "from_currency": "USDC",
  "to_currency": "EURC",
  "from_amount": "1000.00",
  "to_amount": "921.50",
  "rate": "0.9215",
  "effective_rate": "0.9215",
  "slippage_bps": 50,
  "provider": "tempo_dex",
  "chain": "tempo",
  "status": "quoted",
  "expires_at": "2026-03-23T12:00:30+00:00",
  "created_at": "2026-03-23T12:00:00+00:00"
}
```

Quotes expire in 30 seconds.

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Quote created |

---

### POST /fx/execute

Execute an FX swap from a previously obtained quote.

**Request Body**

```json
{
  "quote_id": "fxq_a1b2c3d4e5f6"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `quote_id` | string | yes | Quote ID to execute |

**Response** `200 OK` -- Same shape as `FXQuoteResponse` with `status: "completed"`.

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Swap executed |
| 404 | Quote not found |
| 409 | Quote already executed or cancelled |
| 410 | Quote has expired |

---

### GET /fx/rates

Get current indicative FX rates for all supported pairs.

**Response** `200 OK`

```json
{
  "rates": [
    { "from": "USDC", "to": "EURC", "rate": "0.9215", "provider": "tempo_dex" },
    { "from": "EURC", "to": "USDC", "rate": "1.0852", "provider": "tempo_dex" },
    { "from": "USDC", "to": "USDT", "rate": "1.0000", "provider": "tempo_dex" },
    { "from": "USDT", "to": "USDC", "rate": "1.0000", "provider": "tempo_dex" }
  ],
  "updated_at": "2026-03-23T12:00:00+00:00"
}
```

---

## Bridge Transfers

Cross-chain bridge transfers for stablecoins.

### POST /bridge/transfer

Initiate a cross-chain bridge transfer.

**Request Body**

```json
{
  "from_chain": "base",
  "to_chain": "tempo",
  "token": "USDC",
  "amount": "500.00",
  "bridge_provider": "relay"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_chain` | string | yes | Source chain |
| `to_chain` | string | yes | Destination chain (must differ from source) |
| `token` | string | no | Default `"USDC"` |
| `amount` | decimal | yes | Amount to bridge (> 0) |
| `bridge_provider` | string | no | `relay`, `across`, `squid`, `bungee`, `layerzero`. Default `"relay"` |

**Response** `201 Created`

```json
{
  "transfer_id": "brt_a1b2c3d4e5f6",
  "from_chain": "base",
  "to_chain": "tempo",
  "token": "USDC",
  "amount": "500.00",
  "bridge_provider": "relay",
  "bridge_fee": "0.025000",
  "status": "pending",
  "estimated_seconds": 30,
  "created_at": "2026-03-23T12:00:00+00:00"
}
```

**Bridge Fee Estimates (bps)**

| Provider | Fee (bps) | Estimated Time |
|----------|-----------|----------------|
| relay | 5 | ~30s |
| across | 8 | ~60s |
| squid | 10 | ~120s |
| bungee | 12 | ~90s |
| layerzero | 15 | ~180s |

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Transfer initiated |
| 422 | Source and destination chains are the same |

---

## Escrow

Time-locked escrow holds for conditional payments.

Lifecycle: `held` -> `confirming` -> `released` (or `disputing`)

### POST /escrow

Create an escrow hold.

**Request Body**

```json
{
  "payment_object_id": "po_a1b2c3d4e5f6",
  "merchant_id": "merch_xyz789",
  "amount": "250.00",
  "currency": "USDC",
  "timelock_hours": 72,
  "chain": "tempo",
  "metadata": { "order_id": "ord_555" }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payment_object_id` | string | yes | Payment object backing this escrow |
| `merchant_id` | string | yes | Merchant receiving funds on release |
| `amount` | decimal | yes | Amount to hold (> 0) |
| `currency` | string | no | Default `"USDC"` |
| `timelock_hours` | int | no | 1-720 hours. Default `72` |
| `chain` | string | no | Default `"tempo"` |
| `metadata` | object | no | Arbitrary key-value pairs |

**Response** `201 Created`

```json
{
  "hold_id": "esc_a1b2c3d4e5f6",
  "payment_object_id": "po_a1b2c3d4e5f6",
  "payer_id": "usr_payer",
  "merchant_id": "merch_xyz789",
  "amount": "250.00",
  "currency": "USDC",
  "chain": "tempo",
  "status": "held",
  "timelock_expires_at": "2026-03-26T12:00:00+00:00",
  "released_at": null,
  "delivery_confirmed_at": null,
  "created_at": "2026-03-23T12:00:00+00:00"
}
```

---

### POST /escrow/{id}/confirm-delivery

Confirm delivery and release escrowed funds to the merchant.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Escrow hold ID (`esc_...`) |

**Request Body**

```json
{
  "evidence": { "tracking_number": "1Z999AA10123456784" }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `evidence` | object | no | Optional delivery evidence |

**Response** `200 OK` -- `EscrowResponse` with `status: "released"`

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Delivery confirmed, funds released |
| 409 | Invalid escrow state for confirmation |

---

### POST /escrow/{id}/dispute

File a dispute on an escrow hold. Freezes funds pending resolution.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Escrow hold ID (`esc_...`) |

**Request Body**

```json
{
  "reason": "not_delivered",
  "description": "Item was not delivered within the agreed timeframe."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | no | One of: `not_delivered`, `not_as_described`, `unauthorized`, `duplicate`, `service_quality`, `overcharge`, `other`. Default `"other"` |
| `description` | string | no | Freeform explanation |

**Response** `201 Created` -- `DisputeResponse`

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Dispute filed |
| 409 | Invalid escrow state for dispute |

---

## Disputes

Dispute lifecycle: `filed` -> `evidence_collection` -> `under_review` -> `resolved_*`

### POST /disputes/{id}/evidence

Submit evidence for a dispute (either party).

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Dispute ID (`disp_...`) |

**Request Body**

```json
{
  "party": "payer",
  "evidence_type": "screenshot",
  "content": { "url": "https://example.com/screenshot.png" },
  "description": "Screenshot of order status showing not shipped"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `party` | string | yes | `payer` or `merchant` |
| `evidence_type` | string | yes | `screenshot`, `receipt`, `log`, `communication`, `other` |
| `content` | object | no | Evidence payload (URLs, hashes, structured data) |
| `description` | string | no | Human-readable description |

**Response** `201 Created`

```json
{
  "evidence_id": "evd_a1b2c3d4e5f6",
  "dispute_id": "disp_xyz789",
  "submitted_by": "usr_payer",
  "party": "payer",
  "evidence_type": "screenshot",
  "description": "Screenshot of order status showing not shipped",
  "created_at": "2026-03-23T14:00:00+00:00"
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Evidence submitted |
| 409 | Dispute is not in an evidence-accepting state |

---

### POST /disputes/{id}/resolve

Resolve a dispute with an outcome.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Dispute ID (`disp_...`) |

**Request Body**

```json
{
  "outcome": "resolved_refund",
  "payer_amount": "250.00",
  "merchant_amount": "0.00",
  "reasoning": "Merchant failed to provide shipping evidence within the deadline."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `outcome` | string | yes | `resolved_refund`, `resolved_release`, or `resolved_split` |
| `payer_amount` | decimal | no | Amount returned to payer. Default `0` |
| `merchant_amount` | decimal | no | Amount released to merchant. Default `0` |
| `reasoning` | string | no | Explanation for the decision |

**Response** `200 OK`

```json
{
  "resolution_id": "res_a1b2c3d4e5f6",
  "dispute_id": "disp_xyz789",
  "outcome": "resolved_refund",
  "resolved_by": "usr_admin",
  "payer_amount": "250.00",
  "merchant_amount": "0.00",
  "reasoning": "Merchant failed to provide shipping evidence within the deadline.",
  "created_at": "2026-03-24T10:00:00+00:00"
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Dispute resolved |
| 409 | Dispute is not in a resolvable state |

---

### GET /disputes/{id}

Get a dispute by ID.

**Response** `200 OK`

```json
{
  "dispute_id": "disp_xyz789",
  "escrow_hold_id": "esc_a1b2c3d4e5f6",
  "payment_object_id": "po_a1b2c3d4e5f6",
  "payer_id": "usr_payer",
  "merchant_id": "merch_xyz789",
  "reason": "not_delivered",
  "description": "Item was not delivered within the agreed timeframe.",
  "amount": "250.00",
  "currency": "USDC",
  "status": "evidence_collection",
  "evidence_count": 2,
  "evidence_deadline": "2026-03-30T12:00:00+00:00",
  "resolved_at": null,
  "created_at": "2026-03-23T13:00:00+00:00"
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Dispute not found |

---

## Batch Payments

Atomic multi-transfer via Tempo type 0x76. All transfers succeed or all
fail -- no partial settlement.

### POST /payments/batch

Execute an atomic batch payment on Tempo.

**Request Body**

```json
{
  "transfers": [
    { "to": "0xAlice...", "amount": "100.00", "token": "USDC", "memo": "Payment 1" },
    { "to": "0xBob...", "amount": "50.00", "token": "USDC", "memo": "Payment 2" },
    { "to": "0xCarol...", "amount": "75.00", "token": "USDC" }
  ],
  "chain": "tempo",
  "mandate_id": "mandate_abc123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transfers` | TransferItem[] | yes | 1-50 transfers |
| `transfers[].to` | string | yes | Recipient address |
| `transfers[].amount` | decimal | yes | Amount (> 0) |
| `transfers[].token` | string | no | Default `"USDC"` |
| `transfers[].memo` | string | no | 32-byte memo (hex or UTF-8, max 64 chars) |
| `chain` | string | no | Must be `"tempo"`. Default `"tempo"` |
| `mandate_id` | string | no | Optional spending mandate for validation |

**Response** `201 Created`

```json
{
  "tx_hash": "0xabc123...",
  "chain": "tempo",
  "transfer_count": 3,
  "total_amount": "225.00",
  "status": "confirmed",
  "transfers": [
    { "index": 0, "to": "0xAlice...", "amount": "100.00", "token": "USDC", "status": "included" },
    { "index": 1, "to": "0xBob...", "amount": "50.00", "token": "USDC", "status": "included" },
    { "index": 2, "to": "0xCarol...", "amount": "75.00", "token": "USDC", "status": "included" }
  ]
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Batch confirmed |
| 404 | Active mandate not found (when `mandate_id` is provided) |
| 422 | Chain is not `tempo`, or total exceeds mandate limit, or token unavailable |

---

## Streaming Payments

SSE-based pay-per-use payments backed by TempoStreamChannel. Opens a
payment channel, consumes work units as they are produced, and settles
on-chain when done.

### POST /payments/stream/open

Open a streaming payment channel.

**Request Body**

```json
{
  "service_address": "0xServiceProvider...",
  "deposit_amount": "50.00",
  "token": "USDC",
  "unit_price": "0.001",
  "max_units": 50000,
  "duration_hours": 24
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service_address` | string | yes | Service provider address |
| `deposit_amount` | decimal | yes | Initial deposit (> 0) |
| `token` | string | no | Default `"USDC"` |
| `unit_price` | decimal | yes | Price per work unit (> 0) |
| `max_units` | int | no | Max units (null = unlimited up to deposit) |
| `duration_hours` | int | no | Channel duration 1-168 hours. Default `24` |

**Response** `201 Created`

```json
{
  "stream_id": "stream_a1b2c3d4e5f6",
  "channel_id": "ch_xyz789",
  "deposit_amount": "50.00",
  "unit_price": "0.001",
  "units_consumed": 0,
  "amount_consumed": "0",
  "remaining": "50.00",
  "status": "open",
  "sse_url": "/api/v2/payments/stream/stream_a1b2c3d4e5f6/events"
}
```

---

### POST /payments/stream/{id}/consume

Consume work units and issue a payment voucher.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Stream ID (`stream_...`) |

**Request Body**

```json
{
  "stream_id": "stream_a1b2c3d4e5f6",
  "units": 100,
  "metadata": { "request_id": "req_001" }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stream_id` | string | yes | Stream ID |
| `units` | int | no | Units to consume, 1-1000. Default `1` |
| `metadata` | object | no | Optional context |

**Response** `200 OK`

```json
{
  "stream_id": "stream_a1b2c3d4e5f6",
  "units_consumed": 100,
  "total_units": 100,
  "amount_this_batch": "0.100000",
  "total_amount": "0.100000",
  "remaining": "49.900000",
  "voucher_sequence": 1
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Units consumed, voucher issued |
| 404 | Stream not found |
| 409 | Stream is not open |
| 422 | Would exceed deposit or max units |

---

### GET /payments/stream/{id}/events

Server-Sent Events (SSE) stream for real-time payment updates.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Stream ID (`stream_...`) |

**Response** `200 OK` with `Content-Type: text/event-stream`

**Event Types**

| Type | Description |
|------|-------------|
| `connected` | Initial connection event |
| `payment` | A consumption event with amount, units, and voucher sequence |
| `closed` | Stream has been settled and closed |

**Example SSE Data**

```
data: {"type":"connected","stream_id":"stream_a1b2c3d4e5f6"}

data: {"type":"payment","units":100,"amount":"0.100000","total_units":100,"total_amount":"0.100000","voucher_sequence":1,"timestamp":"2026-03-23T12:01:00+00:00"}

: keepalive 2026-03-23T12:01:30+00:00

data: {"type":"closed","stream_id":"stream_a1b2c3d4e5f6"}
```

---

### POST /payments/stream/{id}/settle

Settle all accumulated vouchers on-chain and close the stream.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Stream ID (`stream_...`) |

**Response** `200 OK` -- `StreamResponse` with `status: "settled"`

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Stream settled |
| 404 | Stream not found |

---

## Usage Metering

Metered billing: report usage deltas, query meter state, and list meters
for a subscription.

### POST /usage/report

Report a usage delta for a metered billing meter.

**Request Body**

```json
{
  "meter_id": "meter_api_calls",
  "usage_delta": "150",
  "countersignature": "a3f8b2...",
  "idempotency_key": "report_2026-03-23_batch_01"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `meter_id` | string | yes | Meter to report usage against |
| `usage_delta` | decimal | yes | Incremental usage units (> 0) |
| `countersignature` | string | cond. | HMAC-SHA256 hex digest over `"<meter_id>:<usage_delta>"`. Required when the meter has `requires_countersignature=true` |
| `idempotency_key` | string | no | Client-supplied key to prevent duplicate reports (max 128 chars) |

**Response** `201 Created`

```json
{
  "report_id": "urpt_a1b2c3d4e5f6",
  "meter_id": "meter_api_calls",
  "usage_delta": "150",
  "cumulative_usage": "12350",
  "billable_amount": "12.350000",
  "recorded_at": "2026-03-23T12:00:00+00:00"
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 201 | Usage recorded |
| 403 | Invalid countersignature |
| 404 | Meter not found |
| 422 | Meter requires countersignature but none provided |

---

### GET /usage/meters/{id}

Get meter details and current billable amount.

**Path Parameters**

| Param | Description |
|-------|-------------|
| `id` | Meter ID |

**Response** `200 OK`

```json
{
  "meter_id": "meter_api_calls",
  "subscription_id": "sub_abc123",
  "name": "API Calls",
  "unit": "call",
  "unit_price": "0.001000",
  "cumulative_usage": "12350",
  "billable_amount": "12.350000",
  "requires_countersignature": true,
  "created_at": "2026-03-01T00:00:00+00:00",
  "updated_at": "2026-03-23T12:00:00+00:00"
}
```

**Status Codes**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Meter not found |

---

### GET /usage/meters

List meters for a subscription.

**Query Parameters**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `subscription_id` | string | yes | Subscription to list meters for |
| `limit` | int | no | 1-200. Default `50` |
| `offset` | int | no | Default `0` |

**Response** `200 OK`

```json
{
  "meters": [ /* MeterResponse[] */ ],
  "total": 3
}
```

---

## Common Error Format

All error responses follow a consistent structure:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422), the `detail` field may contain a structured
object with `message`, `error_code`, and `violations` keys.

## Authentication

All endpoints require a valid Bearer token:

```
Authorization: Bearer sk_live_...
```

Tokens are obtained via the `/auth/login` endpoint or issued as API keys
through the dashboard.

## Rate Limits

Default rate limits apply per API key:

| Tier | Requests/min | Burst |
|------|-------------|-------|
| Free | 60 | 10 |
| Pro | 600 | 50 |
| Enterprise | 6000 | 200 |

Rate limit headers are included in every response:
`X-RateLimit-Remaining`, `X-RateLimit-Reset`.
