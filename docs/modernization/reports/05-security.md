# 05 Security Audit

## Findings

### Critical: Auth/session behavior differs across frontend surfaces

- Evidence: `apps/dashboard/lib/sardis-api.ts` intentionally uses a same-origin proxy because HttpOnly Better Auth cookies cannot be read in browser JS. `apps/landing/lib/sardis-api.ts` reads `localStorage` and non-HttpOnly cookies such as `better-auth.session_token`.
- Impact: Landing-side authenticated calls can encourage insecure token handling or fail in production where sessions are HttpOnly.
- Recommended action: Converge landing authenticated calls onto same-origin server proxy semantics or remove authenticated browser API calls from landing.
- Action type: Migration/refactor.
- Estimated risk: High.
- Validation method: browser auth smoke for dashboard and landing; no browser-readable session token requirement.

### High: Merchant checkout mandate validation can fail open

- Evidence: `packages/reference-api/server/routes/commerce/merchant_checkout.py` logs mandate lookup/validation errors and can continue to payment execution.
- Impact: payment policy enforcement can be bypassed during storage or parser failures.
- Recommended action: fail closed when `mandate_id` is present and mandate validation cannot complete.
- Action type: Code fix plus regression test.
- Estimated risk: High.
- Validation method: route test where validation raises and `execute_payment` is not called.

### High: KYC webhook handling can log/store raw sensitive payload data

- Evidence: `packages/reference-api/server/routes/compliance/kyc_onboarding.py` logs invalid raw bodies and stores payload-derived metadata.
- Impact: identity metadata can leak to logs, DB records, observability, or exports.
- Recommended action: redact logs, store normalized fields and payload hashes, and keep raw payloads only in protected encrypted storage if legally required.
- Action type: Code fix plus data-retention hardening.
- Estimated risk: High.
- Validation method: tests with fake PII assert logs/metadata do not contain raw payload fields.

### High: DB idempotency fallback does not bind payload hash

- Evidence: `packages/reference-api/server/idempotency.py` Redis path compares `request_hash`, but DB fallback records do not consistently read/write and compare that hash.
- Impact: reused idempotency keys with different payloads can return stale responses if Redis misses and DB hits.
- Recommended action: add `request_hash` to durable idempotency records and reject mismatch in DB fallback.
- Action type: Code plus migration plus tests.
- Estimated risk: High.
- Validation method: replay test forcing Redis miss and DB hit with changed payload.

### High: Payment/security middleware is feature-flag heavy

- Evidence: TAP enforcement is enabled by default only in production in `packages/reference-api/server/main.py`; x402 is feature-flagged; production guards live in `packages/reference-api/server/lifespan.py`.
- Impact: Dev/test behavior can differ substantially from production, making bypass regressions easy to miss.
- Recommended action: Add tests for production-like fail-closed startup and protected endpoint behavior.
- Action type: Tests.
- Estimated risk: Medium.
- Validation method: pytest with `SARDIS_ENVIRONMENT=production` and missing Redis/JWKS assertions.

### High: Public repo includes many private-surface ignore rules

- Evidence: `.gitignore` explicitly ignores `docs/marketing`, `docs/investor`, `docs/design-partner`, `docs/outreach`, `scripts/outreach`, pitch decks, internal checklists, and local exports.
- Impact: The repo has historically mixed public product code with private GTM/investor/customer artifacts.
- Recommended action: Keep modernization docs force-added intentionally; do not remove ignore guards without review.
- Action type: No action for guards; documentation.
- Estimated risk: Low.
- Validation method: `git ls-files` and secret scan.

### Medium: Webhook and signing code need contract-level tests

- Evidence: routers include many webhook paths: Stripe, Polar, CPN, Mastercard, Visa TAP, partner cards, provider facility webhooks.
- Impact: spoofing/replay bugs are high-cost in payment systems.
- Recommended action: Inventory webhook signature verification and replay protection tests by provider.
- Action type: Tests/refactor.
- Estimated risk: Medium.
- Validation method: provider-specific invalid signature, replay, timestamp, and body canonicalization tests.
