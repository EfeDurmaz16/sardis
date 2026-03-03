# Circle Gateway Nanopayments Integration Research (Sardis)

Research date: 2026-03-03
Project: Sardis
Scope: Where and how to integrate Circle Gateway Nanopayments in this repo, with concrete feasibility analysis.

## TL;DR

Circle Nanopayments is a strong fit for Sardis, but only if integrated as an off-chain x402 batching rail, not as a direct replacement for existing on-chain `dispatch_payment` settlement.

Best first integration point:
- `packages/sardis-api/src/sardis_api/routers/wallets.py` x402 endpoints (`/{wallet_id}/x402/challenge|verify|settle`)

Best product surface after that:
- Marketplace per-request services (`price_type="per_request"`) so agents can charge/pay per API call with minimal on-chain overhead.

Important current blocker:
- Current Sardis x402 endpoint flow is incomplete/misaligned for production batching (details in "Current Sardis Gap Analysis").

Implementation status update (2026-03-03):
- Phase 1 hardening work started and partially completed in code:
  - `355a1f64`: fixed x402 challenge/verify/settle wiring
  - `44fbd6a6`: persisted x402 challenges to database
  - `8be1bc0c`: added x402 wallet flow tests
  - `312f148c`: added x402 challenge migration
  - `02e72e8d`: normalized x402 header handling in JS SDK
  - `2e958af2`: added optional Circle Gateway x402 settlement rail scaffold in API

---

## 1. What Circle Nanopayments Adds

From Circle Gateway docs, Nanopayments provides:
- x402-compatible paywalls for HTTP/API access.
- Off-chain signed micropayment proofs per request.
- Deferred batch settlement via a facilitator/payment-intent flow.
- Gateway wallet abstraction with `deposit`, `pay`, `getBalance`, `withdraw`.

Core model:
1. User deposits once to Gateway balance.
2. Each API call carries signed payment proof (no on-chain tx per call).
3. Seller verifies proof and serves content immediately.
4. Facilitator batches and settles on-chain later.

Practical implications for Sardis:
- Better economics for high-frequency low-value agent interactions.
- Better UX than requiring one on-chain transfer per micro-call.
- Requires stateful facilitator + settlement queue lifecycle.

References:
- https://developers.circle.com/gateway/nanopayments
- https://developers.circle.com/gateway/nanopayments/quickstarts/buyer
- https://developers.circle.com/gateway/nanopayments/quickstarts/seller
- https://developers.circle.com/gateway/nanopayments/sdk-reference
- https://docs.x402.org/batched-settlement-mechanism

---

## 2. Current Circle Gateway Facts (as of 2026-03-03)

### 2.1 API shape

Gateway Nanopayments API reference shows payment-intent endpoints:
- `POST /v1/payment-intents`
- `PUT /v1/payment-intents/{paymentIntentId}` (attach signatures)
- `POST /v1/payment-intents/{paymentIntentId}/settle`

Reference:
- https://developers.circle.com/gateway/nanopayments/api-reference

### 2.2 Supported chains and ecosystem direction

Gateway supported blockchains include:
- Base
- Arbitrum
- Polygon
- Ethereum
- Avalanche
- Solana
- Aptos
- Sui
- Unichain
- World Chain
- Sonic
- Linea
- Arc Testnet

Reference:
- https://developers.circle.com/gateway/supported-blockchains

### 2.3 Pricing and limits

Circle Gateway fees page states:
- Early access free until end of Q1 2026.
- Planned fee after: 0.5 bps per transfer.
- During beta, withdrawal max noted as 25,000 USDC.

Reference:
- https://www.circle.com/gateway

---

## 3. Current Sardis Gap Analysis (Updated 2026-03-03)

This section maps your current implementation against a proper x402 + batching lifecycle.

### 3.1 x402 challenge endpoint object-shape mismatch

Status: Resolved (2026-03-03).

Resolution:
- Router now correctly dereferences `challenge_response.challenge` before reading fields.

### 3.2 verify -> settle persistence flow

Status: Resolved (2026-03-03).

Resolution:
- `/x402/verify` now persists settlement status via `DatabaseSettlementStore`.
- `/x402/settle` reads the persisted row and continues lifecycle.

### 3.3 challenge store deployment safety

Status: Resolved (2026-03-03).

Resolution:
- Challenges are now persisted in `x402_challenges` with TTL cleanup, removing process-local fragility.

### 3.4 header/protocol drift across clients

Current test/client surfaces represent mixed x402 header styles:
- JS SDK test uses `x-payment-challenge`.
- Python SDK test uses `WWW-Authenticate: x402 ...`.
- Protocol module includes `PaymentRequired` / `PAYMENT-SIGNATURE` / `PAYMENT-RESPONSE`.

Evidence:
- JS test [protocol-e2e.test.ts](/Users/efebarandurmaz/sardis/packages/sardis-sdk-js/src/__tests__/protocol-e2e.test.ts:390)
- Python test [test_protocol_e2e.py](/Users/efebarandurmaz/sardis/packages/sardis-sdk-python/tests/test_protocol_e2e.py:254)
- Header constants in [x402.py](/Users/efebarandurmaz/sardis/packages/sardis-protocol/src/sardis_protocol/x402.py:16)

Impact:
- Integration friction when wiring Circle Nanopayments middleware, which assumes standardized x402 flow.

Progress:
- JS SDK now normalizes `PaymentRequired`, `x-payment-challenge`, and `WWW-Authenticate: x402 ...` into a consistent challenge header surface (`02e72e8d`).
- Python SDK still needs equivalent normalization helper for parity.

### 3.5 Existing `X402Client` is transfer-hash style, not batching style

`sardis-coinbase` client responds to 402 by sending immediate on-chain USDC transfer and header `X-Payment: txHash=...`.

Evidence:
- [x402_client.py](/Users/efebarandurmaz/sardis/packages/sardis-coinbase/src/sardis_coinbase/x402_client.py:35)

Impact:
- Not compatible with Circle Gateway Nanopayment model (signed proofs + batched settlement).

---

## 4. Where Integration Fits Best in This Repo

## Option A (Recommended first): Replace current x402 payee flow in wallets router

Target:
- [wallets.py](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/wallets.py:1446)

Why:
- Existing x402 surface already exposed.
- Minimal API contract disruption.
- Lets Sardis keep policy/compliance checks while switching settlement rail.

What changes:
- Keep challenge/verify semantics but switch verify output into facilitator queue.
- Back settlement with payment-intent lifecycle and async batch worker.
- Move challenge storage to Redis/Postgres.

## Option B: Add Nanopayment PSP connector in checkout

Targets:
- [checkout router](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/checkout.py:31)
- [orchestrator](/Users/efebarandurmaz/sardis/packages/sardis-checkout/src/sardis_checkout/orchestrator.py:1)

Why:
- Checkout already models PSP routing.
- Good fit for "pay-per-request API checkout" products.

Tradeoff:
- Checkout package currently effectively Stripe-first; adding x402 rail requires deeper connector design changes.

## Option C (High strategic): Marketplace per-request pricing

Targets:
- [marketplace model](/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/marketplace.py:67)
- [marketplace router](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/marketplace.py:1)

Why:
- You already model `price_type = per_request`.
- Nanopayments naturally matches machine-to-machine service calls.

Outcome:
- Agent service economy monetization with low settlement overhead.

## Option D: MCP tool metering

Targets:
- [MCP payments tool](/Users/efebarandurmaz/sardis/packages/sardis-mcp-server/src/tools/payments.ts:1)
- [MCP API client](/Users/efebarandurmaz/sardis/packages/sardis-mcp-server/src/api.ts:1)

Why:
- MCP server is already agent-facing and payment-oriented.

Tradeoff:
- Tool transport is stdio MCP; adding HTTP 402 gating needs explicit bridging architecture.

---

## 5. Implementation Blueprint (Recommended)

Phase 1: Fix and harden current x402 foundation (1-2 weeks)
- [Done] Fix challenge object mismatch.
- [Done] Persist verify results to `x402_settlements` (or new normalized table).
- [Done] Replace in-memory challenge cache with Redis/Postgres + TTL.
- [In progress] Normalize headers and challenge format across SDKs (JS done, Python pending).

Phase 2: Add Circle Gateway facilitator adapter (2-3 weeks)
- Introduce `NanopaymentFacilitator` interface:
  - `create_payment_intent(...)`
  - `attach_signature(...)`
  - `settle_intent(...)`
  - `fetch_summary(...)`
- [Started] Implement Circle adapter calling Gateway payment-intent API.
- Keep policy/compliance checks before final settlement enqueue.

Phase 3: Integrate product surface (2-4 weeks)
- Start with wallet x402 endpoints (drop-in rail switch).
- Add marketplace per-request monetization and reporting.
- Optional checkout connector afterward.

Phase 4: Operability and risk controls (ongoing)
- Settlement lag SLO metrics.
- Retry and dead-letter for failed batches.
- Reconciliation jobs against `payment-intents` summaries.
- Alerting on stuck states (`verified` too long, repeated `failed` settles).

---

## 6. Data Model Additions Suggested

Current `x402_settlements` table is too thin for production facilitator operations.

Suggested new fields/tables:
- `x402_challenges`:
  - `payment_id`, `wallet_id`, `resource_uri`, `amount`, `currency`, `nonce`, `expires_at`, `status`
- `x402_payments`:
  - `payment_id`, `wallet_id`, `payer`, `payee`, `amount_minor`, `network`, `signature_hash`, `verified_at`
- `x402_batches`:
  - `batch_id`, `provider`, `status`, `payment_intent_id`, `created_at`, `settled_at`, `error`
- `x402_batch_items`:
  - `batch_id`, `payment_id`, `status`, `tx_hash`, `error`

Reason:
- Enables reliable facilitator lifecycle, reconciliation, and auditability.

---

## 7. Language/SDK Practicality

Observation:
- Sardis backend is Python-first.
- Circle Nanopayment quickstarts are Node-centric.

Pragmatic path:
- Use direct Gateway REST API from Python service layer for core facilitator logic.
- Optionally run a Node sidecar only if Circle releases a stable public batching SDK package.

Why:
- Avoid introducing a new mandatory runtime boundary prematurely.
- Keep your policy/compliance pipeline where it is today (Python/FastAPI).

Note:
- Circle quickstart text references `@circle-fin/x402-batching`, but this package was not discoverable in public npm registry lookups on 2026-03-03. Validate package availability before designing around it.

Registry checks used:
- `npm view @circlefin/x402-batching` -> not found
- npm search API results for `x402-batching` and `circle-fin x402` did not list a Circle batching package

---

## 8. Risk Register

Technical risks:
- Protocol/header drift causing buyer/seller incompatibility.
- Multi-instance consistency issues if challenge state is not centralized.
- Settlement trust assumptions if verify/settle responsibilities are split without strict controls.

Operational risks:
- Batch settlement delays can impact merchant trust if not surfaced in status APIs.
- Reconciliation complexity across Sardis ledger and provider intent states.

Product risks:
- Using on-chain-per-call path for true micropayments is economically non-viable at scale.

---

## 9. Recommended Decision

Decision:
1. Integrate Circle Nanopayments into existing wallet x402 endpoints first.
2. Treat it as a new settlement rail (off-chain signed + batched), not as direct transfer replacement.
3. Productize next in marketplace per-request services.

Avoid initially:
- Forcing Nanopayments into current checkout connector layer first.
- Shipping on top of in-memory challenge state.

---

## Sources

Circle:
- https://developers.circle.com/gateway/nanopayments
- https://developers.circle.com/gateway/nanopayments/quickstarts/buyer
- https://developers.circle.com/gateway/nanopayments/quickstarts/seller
- https://developers.circle.com/gateway/nanopayments/sdk-reference
- https://developers.circle.com/gateway/nanopayments/api-reference
- https://developers.circle.com/gateway/supported-blockchains
- https://www.circle.com/gateway

x402:
- https://docs.x402.org/batched-settlement-mechanism
- https://github.com/coinbase/x402

Local Sardis references:
- [wallet x402 routes](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/wallets.py:1446)
- [x402 protocol generator](/Users/efebarandurmaz/sardis/packages/sardis-protocol/src/sardis_protocol/x402.py:76)
- [x402 settlement store](/Users/efebarandurmaz/sardis/packages/sardis-protocol/src/sardis_protocol/x402_settlement.py:1)
- [x402 settlements schema](/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/database.py:1014)
- [checkout entrypoint](/Users/efebarandurmaz/sardis/packages/sardis-api/src/sardis_api/routers/checkout.py:31)
- [marketplace per_request pricing model](/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/marketplace.py:67)
- [legacy x402 client transfer flow](/Users/efebarandurmaz/sardis/packages/sardis-coinbase/src/sardis_coinbase/x402_client.py:35)
