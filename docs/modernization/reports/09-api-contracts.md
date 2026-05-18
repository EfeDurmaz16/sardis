# 09 API Contracts Audit

## Findings

### High: Public API surface is very broad

- Evidence: `packages/server-api/src/sardis/routers/` contains well over 100 router modules, and `main.py` registers many under `/api/v2`.
- Impact: Any cleanup can accidentally change public routes.
- Recommended action: Generate and commit an OpenAPI snapshot for contract diffing before route refactors.
- Action type: Tests/tooling.
- Estimated risk: Medium.
- Validation method: OpenAPI snapshot diff in CI.

### High: Payment execution semantics are duplicated across entrypoints

- Evidence: wallet transfer, mandates, on-chain payments, secure checkout, and pay routes each wire execution-related logic.
- Impact: policy, compliance, idempotency, attestation, and ledger behavior can drift between payment paths.
- Recommended action: introduce one execution application service with route-specific adapters after parity tests.
- Action type: Refactor.
- Estimated risk: High.
- Validation method: golden-path and denial-path parity tests across payment entrypoints.

### Medium: Dashboard client expects collection response normalization

- Evidence: `apps/dashboard/lib/sardis-api.ts` imports `extractListOrThrow` while `apps/landing/lib/sardis-api.ts` expects arrays directly.
- Impact: API response envelope expectations can diverge across apps.
- Recommended action: Centralize collection response handling in SDK/client layer.
- Action type: Refactor.
- Estimated risk: Medium.
- Validation method: frontend unit tests around agent/wallet list parsing.

### Medium: OpenAPI artifacts exist but canonical generation is unclear

- Evidence: `packages/server-api/openapi/` contains ChatGPT action and README artifacts; API app has `openapi_schema.py`.
- Impact: Docs/SDK generation may drift from runtime routes.
- Recommended action: Add a documented command to regenerate and verify OpenAPI artifacts.
- Action type: Tooling.
- Estimated risk: Low.
- Validation method: run generation and compare clean git diff.
