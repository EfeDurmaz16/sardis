# Sardis v2 Migration Notes — Items Deferred to b0

This document lists work that is intentionally **not** part of the v2.0.0a0
mechanical consolidation. These items will land in the v2.0.0b0 cycle.

## Deferred

### 1. Root project layout (`src/sardis/` at repo root)
The workspace root still ships a leftover `src/sardis/` directory from before
the umbrella package existed. It is currently shadowed by the umbrella at
`packages/sardis/src/sardis/`, but should be folded into the umbrella or
deleted outright in b0 to remove the confusion. Tracked: Phase 2F follow-up.

### 2. `sardis-agent-sdk` package rename
The legacy package `sardis-agent-sdk` has been consolidated into
`sardis.integrations.anthropic` (the rename was unavoidable to honor the SDK
redesign target). For backwards compatibility, the legacy PyPI name
`sardis-agent-sdk` is preserved as a deprecation shim. b0 will deprecate the
shim entirely and rename downstream consumers.

### 3. Public API curation
`sardis.core.__init__` currently re-exports ~150 names verbatim from the
legacy `sardis_v2_core` package. The redesign target trims this to a curated
~50-name surface (see `project-directions/sardis-python-sdk-redesign.md`
section "sardis.core"). b0 will land the curation behind a deprecation cycle
for the dropped names.

Similarly: `sardis.protocol`, `sardis.compliance`, `sardis.guardrails`,
`sardis.ledger`, `sardis.chain`, `sardis.cards`, `sardis.wallet`,
`sardis.ramp`, `sardis.checkout`, `sardis.ucp` all still re-export everything
the legacy package exposed. Per-submodule curation is a b0 task.

### 4. 291-name cull
Per the SDK redesign doc, the consolidated package currently re-exports 291
top-level names across submodules. Target is < 100 for the v2.0.0 GA release.
b0 will mark removed names with deprecation warnings; v2.1.0 will delete
them.

### 5. Test reorganization
Tests have been mechanically moved alongside their consolidated modules
(`packages/sardis/tests/<submodule>/`). Coverage gaps and cross-submodule
test fixtures (`conftest.py`) have NOT been audited. b0 will rebuild the
fixture pyramid and add umbrella-level smoke tests.

### 6. Legacy root pyproject extras
`pyproject.toml` (now `sardis-workspace`) still declares
`[project.optional-dependencies]` groups like `[chain]`, `[compliance]`,
`[wallet]`, etc. These produce uv warnings because the umbrella package
defines different extras. They are workspace dev-time conveniences and will
be reorganized in b0.

### 7. Dead optional providers
`sardis.core.minter` and `sardis.cards.providers` still contain guarded
conditional imports for `sardis_zkp` and `sardis_striga` — packages killed
in Phase 2A. The guard blocks runtime failure, but the code paths are dead.
b0 will strip them.

## Sunset Timeline

| Milestone | Date | Action |
|---|---|---|
| v2.0.0a0 | 2026-05-23 | Mechanical consolidation lands. All legacy shims published @ 0.99.0. |
| v2.0.0b0 | TBD | Public-API curation, b0-grade renames, test fixture rebuild. |
| v2.0.0 GA | TBD | 291-name cull behind deprecation. |
| 2026-11-23 | hard deadline | Legacy `sardis_*` shims removed entirely. |
