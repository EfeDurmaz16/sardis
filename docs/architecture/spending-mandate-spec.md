# Spending Mandate Specification

**Version:** 1.0
**Date:** March 2026
**Status:** Implemented (MVP)

## Abstract

A spending mandate is a machine-readable payment authorization primitive that defines the scoped, time-limited, revocable authority an AI agent has to spend money. It replaces raw credential delegation with structured, auditable, cross-rail permission objects.

## Motivation

Early agent payment approaches assumed broad access to payment credentials. This model fails because:

1. **Over-broad authority.** LLMs are non-deterministic and can retry, drift, or mishandle edge cases.
2. **Security risk.** Payment secrets should not be delegated to agent runtime layers.
3. **Enterprise requirements.** Enterprises need bounded, reviewable, revocable authority.
4. **Conflated problems.** Access to a payment rail is not the same as authority to use it safely.

The spending mandate separates these concerns.

## Schema

### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (`mandate_xxx`) |
| `org_id` | string | Yes | Organization that owns this mandate |
| `principal_id` | string | Yes | User/entity who authorized the mandate |
| `issuer_id` | string | Yes | Who created the mandate |
| `agent_id` | string | No | Which agent is authorized |
| `wallet_id` | string | No | Which wallet is bound |

### Scope Fields

| Field | Type | Description |
|-------|------|-------------|
| `merchant_scope` | object | `{allowed: [...], blocked: [...], mcc_codes: [...]}` |
| `purpose_scope` | string | Natural language description of allowed purposes |

### Amount Controls

| Field | Type | Description |
|-------|------|-------------|
| `amount_per_tx` | decimal | Maximum per single transaction |
| `amount_daily` | decimal | Maximum daily aggregate |
| `amount_weekly` | decimal | Maximum weekly aggregate |
| `amount_monthly` | decimal | Maximum monthly aggregate |
| `amount_total` | decimal | Lifetime budget for this mandate |
| `currency` | string | Currency code (default: USDC) |
| `spent_total` | decimal | Running total of spent amount |

### Rail Permissions

| Field | Type | Description |
|-------|------|-------------|
| `allowed_rails` | string[] | Permitted rails: card, usdc, bank |
| `allowed_chains` | string[] | Permitted blockchains: base, polygon, etc. |
| `allowed_tokens` | string[] | Permitted tokens: USDC, USDT, EURC |

### Time Controls

| Field | Type | Description |
|-------|------|-------------|
| `valid_from` | timestamp | When the mandate becomes active |
| `expires_at` | timestamp | When the mandate automatically expires |

### Approval Controls

| Field | Type | Description |
|-------|------|-------------|
| `approval_threshold` | decimal | Amount above which human approval is required |
| `approval_mode` | enum | `auto`, `threshold`, `always_human` |

### Lifecycle

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `draft`, `active`, `suspended`, `revoked`, `expired`, `consumed` |
| `version` | integer | Incremented on each update |
| `policy_hash` | string | SHA-256 of mandate rules for integrity |
| `revoked_at` | timestamp | When mandate was revoked |
| `revoked_by` | string | Who revoked |
| `revocation_reason` | string | Why revoked |

## Lifecycle State Machine

```
    ┌─────────┐
    │  DRAFT  │
    └────┬────┘
         │ activate
         ▼
    ┌─────────┐     suspend     ┌───────────┐
    │ ACTIVE  │ ──────────────► │ SUSPENDED │
    └────┬────┘ ◄────────────── └─────┬─────┘
         │         resume             │
         │                            │ revoke
         ├── revoke ──► REVOKED ◄─────┘
         │
         ├── expire ──► EXPIRED
         │
         └── consume ─► CONSUMED
```

### Transition Rules

| From | To | Trigger |
|------|----|---------|
| DRAFT | ACTIVE | Manual activation by issuer |
| ACTIVE | SUSPENDED | Manual suspension (e.g., investigation) |
| SUSPENDED | ACTIVE | Manual resume after investigation |
| ACTIVE | REVOKED | Permanent invalidation (irreversible) |
| SUSPENDED | REVOKED | Permanent invalidation from suspended state |
| ACTIVE | EXPIRED | Automatic when `expires_at` is reached |
| ACTIVE | CONSUMED | Automatic when `spent_total >= amount_total` |

Every transition produces a `MandateStateTransition` audit record.

## Enforcement Model

Payment authorization follows a layered model:

```
1. Identity at the edge
   └─ Is this a legitimate agent? Who is it acting for?

2. Mandate validation
   └─ Does an active mandate exist for this agent/wallet?
   └─ Is the payment within mandate scope?
   └─ Is the amount within remaining limits?
   └─ Is the rail permitted?
   └─ Does it require human approval?

3. Policy enforcement
   └─ Does the payment pass the spending policy checks?
   └─ Velocity checks, anomaly detection, compliance gates

4. Execution
   └─ Route to appropriate rail (card, USDC, bank)
   └─ MPC signing via Turnkey
   └─ On-chain settlement or card authorization

5. Audit
   └─ Record mandate_id on transaction
   └─ Append to immutable ledger
   └─ Anchor Merkle root on-chain
```

## Revocation Model

Three levels of revocation:

### Pre-Spend Revocation
Invalidate the mandate before any payment begins. The `revoke` transition immediately sets status to REVOKED. Any subsequent `check_payment()` call returns `approved=false`.

### Pre-Settlement Halt
After mandate check passes but before on-chain settlement, the kill switch can halt execution. This is enforced at the orchestrator level.

### Post-Settlement Remediation
After settlement, remediation depends on the rail:
- **Card:** Chargeback/refund through Stripe
- **USDC:** Escrow release reversal (if using RefundProtocol) or manual recovery
- **Bank:** ACH reversal within regulatory windows

## Cross-Rail Authorization

The mandate is **rail-agnostic** by design. The same mandate can authorize payments on:
- Virtual cards (via Stripe Issuing)
- USDC on-chain (via MPC wallets on Base, Polygon, etc.)
- Bank transfers (via ACH/wire)

The `allowed_rails` field controls which rails are permitted. The mandate semantics (amount limits, merchant scope, approval thresholds) apply identically regardless of rail.

## Industry Comparison

| Feature | Sardis Mandate | Stripe SPT | Visa TAP | Mastercard Agent Pay | Google AP2 |
|---------|---------------|------------|----------|---------------------|------------|
| Merchant scope | Yes | Seller-scoped | Merchant trust | Tokenized acceptance | Protocol-level |
| Amount limits | Per-tx + aggregate | Amount-bounded | N/A | N/A | Intent-level |
| Cross-rail | Card + USDC + bank | Card-only | Card-only | Card-only | Multi-rail |
| Approval workflows | Auto/threshold/human | N/A | N/A | N/A | N/A |
| Revocation | Instant + audit | Deactivation | N/A | N/A | N/A |
| Agent identity | Agent_id + principal | N/A | TAP identity | Agent registration | Agent context |
| Policy language | Natural language | N/A | N/A | N/A | N/A |
| Kill switch | Yes (multi-scope) | N/A | N/A | N/A | N/A |
| Audit trail | Merkle-anchored | Events | N/A | N/A | N/A |

## Examples

### API Spend Mandate
```python
mandate = SpendingMandate(
    principal_id="usr_abc",
    agent_id="agent_research_01",
    purpose_scope="AI API usage for research",
    amount_per_tx=Decimal("50"),
    amount_daily=Decimal("200"),
    amount_monthly=Decimal("2000"),
    merchant_scope={"allowed": ["openai.com", "anthropic.com", "google.com"]},
    allowed_rails=["card", "usdc"],
    approval_mode=ApprovalMode.AUTO,
)
```

### Procurement Mandate
```python
mandate = SpendingMandate(
    principal_id="usr_cfo",
    agent_id="agent_procurement",
    purpose_scope="Office supplies and cloud infrastructure",
    amount_per_tx=Decimal("5000"),
    amount_monthly=Decimal("50000"),
    merchant_scope={"allowed": ["aws.amazon.com", "staples.com"], "mcc_codes": ["5045", "5943"]},
    approval_threshold=Decimal("1000"),
    approval_mode=ApprovalMode.THRESHOLD,
    allowed_rails=["card", "bank"],
)
```

### Travel Booking Mandate
```python
mandate = SpendingMandate(
    principal_id="usr_travel_manager",
    agent_id="agent_travel",
    purpose_scope="Corporate travel: flights, hotels, ground transport",
    amount_per_tx=Decimal("2000"),
    amount_total=Decimal("25000"),
    merchant_scope={"allowed": ["*airline*", "*hotel*", "*marriott*", "*hilton*"]},
    approval_threshold=Decimal("500"),
    approval_mode=ApprovalMode.THRESHOLD,
    allowed_rails=["card"],
    expires_at=datetime(2026, 12, 31, tzinfo=UTC),
)
```

## Future: On-Chain Mandate Tokens

The spending mandate is designed to move on-chain as the technology matures:

**Phase 1 (Current):** Off-chain enforcement via Sardis API
**Phase 2:** Mandate rules encoded as ERC-20 transfer hooks
**Phase 3:** Native payment tokens with embedded mandate semantics

The data model is intentionally structured so that every field maps cleanly to a smart contract parameter or on-chain attestation. No rewrite needed.
