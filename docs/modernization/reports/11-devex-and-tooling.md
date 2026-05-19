# 11 DevEx And Tooling Audit

## Findings

### High: Repo discovery is noisy without generated-folder pruning

- Evidence: simple file traversal reported many files from `.venv`, `.next`, `node_modules`, caches, and build outputs.
- Impact: Audits, search, and contributor orientation become misleading.
- Recommended action: Add a maintained inventory script and document it.
- Action type: Tooling.
- Estimated risk: Low.
- Validation method: `python3 scripts/repo_inventory.py`.

### Medium: `.gitignore` intentionally blocks most docs paths

- Evidence: `.gitignore` ignores `/docs/*` except selected public docs folders.
- Impact: New modernization docs must be force-added intentionally.
- Recommended action: Add `!/docs/modernization/` and `!/docs/modernization/**` so future updates do not need `git add -f`.
- Action type: Cleanup.
- Estimated risk: Low.
- Validation method: `git check-ignore docs/modernization/goal.md` returns non-ignored after change.

### Medium: Validation scripts exist but are fragmented

- Evidence: root package scripts include release readiness, JS builds, SDK tests, live chain checks, and PR maintenance; CI has many workflows.
- Impact: Local contributors need a simple first validation command.
- Recommended action: Add a modernization validation script that runs cheap, credential-free checks and points to heavier gates.
- Action type: Tooling.
- Estimated risk: Low.
- Validation method: script exits 0 locally.

### High: Public quickstarts reference a non-existent Python `Sardis` class

- Evidence: root README and docs-site quickstarts reference `from server import Sardis`, while `src/sardis/__init__.py` exports `SardisClient` and `AsyncSardisClient`.
- Impact: first-run developer experience breaks at import time.
- Recommended action: update docs to the existing client names or add a tested facade. Prefer docs fix first.
- Action type: Documentation/API naming fix.
- Estimated risk: Low.
- Validation method: `python -c "from sardis import SardisClient"`.

### High: Manual deploy workflow contains stale app paths

- Evidence: `.github/workflows/deploy.yml` references old `landing`/`dashboard` paths while actual apps live under `apps/landing` and `apps/dashboard`.
- Impact: manual deploy dispatch can fail or give false confidence.
- Recommended action: remove stale jobs or update them to canonical app paths and pnpm filters.
- Action type: CI/deploy cleanup.
- Estimated risk: Medium.
- Validation method: `actionlint` plus workflow dry run.
