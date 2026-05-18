# 06 Performance Audit

## Findings

### Medium: App startup has too many optional integrations in one path

- Evidence: `packages/api/src/sardis_api/main.py` constructs many repositories/providers and imports optional modules inside `create_app`.
- Impact: Cold start and test startup become slower and less deterministic.
- Recommended action: Group optional integrations behind lazy registrars and only initialize enabled domains.
- Action type: Refactor.
- Estimated risk: Medium.
- Validation method: measure `create_app()` import/startup time before and after.

### Medium: In-memory fallbacks are safe for dev but can hide scale issues

- Evidence: production guards in `packages/api/src/sardis_api/lifespan.py` reject missing Redis/JWKS in production-like modes, but many repositories still fall back to `memory://` in app setup.
- Impact: Tests may pass while distributed runtime behavior differs.
- Recommended action: Add a Postgres/Redis integration profile for critical flows.
- Action type: Tests.
- Estimated risk: Medium.
- Validation method: docker-compose-backed idempotency, cap, webhook replay, and kill-switch tests.

### Low: Frontend bundles should be checked after dependency cleanup

- Evidence: landing/dashboard builds are separate Next apps; prior repo memory indicates wins from lazy-loading heavy libraries.
- Impact: Dependency changes can reintroduce bundle size drift.
- Recommended action: Add size/build artifact checks after cleanup.
- Action type: Tooling.
- Estimated risk: Low.
- Validation method: Next build output comparison.
