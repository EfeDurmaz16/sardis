# 02 Code Quality Audit

## Findings

### High: App bootstrap contains too many responsibilities

- Evidence: `packages/api/src/sardis_api/main.py` configures telemetry, security middleware, rate limiting, TAP, x402, usage metering, repository construction, dozens of router overrides, checkout, merchant, billing, facility, sandbox, and health behavior.
- Impact: The file is hard to review and makes unrelated changes look dangerous.
- Recommended action: Extract pure registration helpers with small return types. Start with middleware and router groups because those are easiest to validate.
- Action type: Refactor.
- Estimated risk: Medium.
- Validation method: app startup smoke plus focused route tests.

### Medium: Broad lint ignores hide code quality drift

- Evidence: root `pyproject.toml` ignores broad classes such as `PLR0912`, `PLR0915`, `PLR0911`, `E722`, `F821`, and many naming rules.
- Impact: Real maintainability problems can remain invisible.
- Recommended action: Add stricter per-package profiles gradually; do not flip strict mode repo-wide yet.
- Action type: Migration.
- Estimated risk: Low.
- Validation method: `uv run ruff check` with narrowed include paths.

### Medium: Demos and examples are mixed with production packages

- Evidence: `demos/`, `examples/`, `api/`, `api-proxy/`, `canvases/`, and package code all live at top level.
- Impact: It is difficult to distinguish maintained product surface from prototype collateral.
- Recommended action: Add an inventory and status label for each top-level surface before deletion.
- Action type: Documentation plus later deletion/move.
- Estimated risk: Low.
- Validation method: README architecture map and CI path filters.

### Low: Some old compatibility comments are valuable but should move to docs

- Evidence: `apps/dashboard/lib/auth.ts` has detailed context for a prior cross-subdomain auth incident.
- Impact: Important safety context is embedded in implementation files.
- Recommended action: Preserve the guard comment but also document it in architecture/auth docs.
- Action type: Documentation.
- Estimated risk: Low.
- Validation method: Typecheck still catches `DynamicBaseURLConfig`.
