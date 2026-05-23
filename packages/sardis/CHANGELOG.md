# Changelog

All notable changes to the `sardis` umbrella package will be documented here.

## [2.0.0a0] — 2026-05-23

First alpha of the unified `sardis` package, consolidating 34 fragmented
`sardis-*` PyPI packages into a single install with framework adapters as
optional extras.

### Added
- Top-level `sardis.Sardis` and `sardis.AsyncSardis` clients (renamed from
  `sardis_sdk.SardisClient` / `AsyncSardisClient`).
- Consolidated submodules:
  - `sardis.core` (from `sardis-core`)
  - `sardis.protocol` (from `sardis-protocol`)
  - `sardis.compliance` (from `sardis-compliance`)
  - `sardis.guardrails` (from `sardis-guardrails`)
  - `sardis.ledger` (from `sardis-ledger`)
  - `sardis.chain` (from `sardis-chain`)
  - `sardis.cards` (from `sardis-cards`)
  - `sardis.wallet` (from `sardis-wallet`)
  - `sardis.ramp` (from `sardis-ramp`)
  - `sardis.checkout` (from `sardis-checkout`)
  - `sardis.ucp` (from `sardis-ucp`)
  - `sardis.cli` (from `sardis-cli`)
- Framework integration extras:
  - `sardis[langchain]` (from `sardis-langchain`)
  - `sardis[crewai]` (from `sardis-crewai`)
  - `sardis[openai-agents]` (from `sardis-openai-agents`)
  - `sardis[autogpt]` (from `sardis-autogpt`)
  - `sardis[browser-use]` (from `sardis-browser-use`)
  - `sardis[composio]` (from `sardis-composio`)
  - `sardis[adk]` (from `sardis-adk`)
  - `sardis[a2a]` (from `sardis-a2a`)
  - `sardis[anthropic]` (from `sardis-agent-sdk` — package name renamed)
- Single `sardis` CLI binary (entry point `sardis.cli.main:cli`).

### Changed
- Legacy `sardis_*` packages republished as deprecation shims at version
  `0.99.0`. They re-export from the umbrella with a `DeprecationWarning`.
  Legacy submodule imports (e.g., `from sardis_chain.executor import
  CHAIN_CONFIGS`) keep working via `__path__` rebinding.

### Removed
- 8 zero-download dead packages deleted in Phase 2A: `sardis-agentkit`,
  `sardis-connect`, `sardis-e2b`, `sardis-lightspark`, `sardis-mpp`,
  `sardis-striga`, `sardis-zk-policy`, `sardis-zkp`.

### Deprecation
- All legacy `sardis-*` packages will be removed on **2026-11-23** (6-month
  sunset window). Migrate to `from sardis.<submodule> import ...` and
  `from sardis import Sardis, AsyncSardis` before that date.

### Deferred to v2.0.0b0
See `MIGRATION_NOTES.md` for the full list. Notable items:
- Public-API curation (drop ~291 incidental re-exports down to < 100).
- Root `src/sardis/` shadow cleanup.
- Test fixture rebuild.

## [Unreleased]

(Future b0 work will land here.)
