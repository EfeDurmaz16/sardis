# 07 Testing Audit

## Findings

### High: Root file traversal can include local environment artifacts

- Evidence: local traversal found `apps/api/.venv`, `.pytest_cache`, `.ruff_cache`, `.next`, and other build folders. They are ignored, but scripts using plain `find` can still traverse them.
- Impact: Audits and ad hoc scripts report dependency tests or generated files as project code.
- Recommended action: Add a repo inventory/validation script that prunes ignored/generated folders.
- Action type: Tooling.
- Estimated risk: Low.
- Validation method: script output excludes `.venv`, `.next`, `node_modules`, caches, and Foundry build outputs.

### High: Production safety paths need explicit fail-closed tests

- Evidence: production guards in `lifespan.py` require Redis and TAP JWKS in production-like modes; main app registers payment/signature middleware behind env flags.
- Impact: Refactors can weaken safety silently.
- Recommended action: Add tests for missing critical env, middleware registration, and no insecure fallback in production.
- Action type: Tests.
- Estimated risk: Medium.
- Validation method: targeted pytest.

### High: Money-moving routes need replay coverage

- Evidence: `/api/v2/pay` and batch payment flows can execute lower-level transfer operations directly.
- Impact: retry after client timeout can double-submit unless lower layers catch every path.
- Recommended action: require and test idempotency for all money-moving mutation routes.
- Action type: Tests plus code.
- Estimated risk: High.
- Validation method: same-key same-payload replay, same-key different-payload rejection, and concurrent request tests.

### Medium: CI type and coverage gates are weak for payment/security code

- Evidence: root CI enforces only 40 percent coverage for API/core and does not run strict mypy despite package configs.
- Impact: typed contracts can drift and critical paths may remain unexercised.
- Recommended action: add mypy as non-blocking first, then blocking; raise coverage per domain rather than globally.
- Action type: CI migration.
- Estimated risk: Low.
- Validation method: CI passes with typecheck job and coverage report split by domain.

### Medium: Coverage threshold is modest for a payment control plane

- Evidence: CI root Python test has `--cov-fail-under=40`.
- Impact: Critical routes may be untested even if CI is green.
- Recommended action: Raise coverage per critical package over time rather than globally at once.
- Action type: Tests.
- Estimated risk: Low.
- Validation method: critical-domain coverage reports.

### Medium: JS validation is package-specific

- Evidence: root scripts include landing/dashboard typecheck/build and SDK tests, but not a single documented modernization validation command.
- Impact: Contributors may run incomplete checks.
- Recommended action: Add or document a stable `check:modernization` command.
- Action type: Tooling.
- Estimated risk: Low.
- Validation method: command runs read-only checks successfully.
