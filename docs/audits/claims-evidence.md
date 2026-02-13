# Sardis Claims Evidence (Pre-Launch Snapshot)

Snapshot date: 2026-02-13

This document ties launch-facing claims to reproducible checks in-repo.

## Verified Claims

| Claim | Public Source | Evidence Command | Result |
| --- | --- | --- | --- |
| `52 MCP tools` | `README.md:30`, `README.md:225`, `landing/src/App.jsx:610` | `bash scripts/release/readiness_check.sh` | `MCP registry parity: 52 definitions = 52 handlers` |
| `150+ tests` | `README.md:252` | `pytest --collect-only -q` | `collected 840 items` (`778 selected`) |
| `19 packages on npm + PyPI` | `docs/marketing/product-hunt-launch.md:31`, `landing/src/App.jsx:1059` | `bash scripts/release/readiness_check.sh` | `package count: 19 (python=15, js=4)` |
| `5 chains` | `README.md:254`, `docs/marketing/product-hunt-launch.md:27` | `bash scripts/release/readiness_check.sh` | `mainnet chain count: 5` |
| `5 protocols (AP2, TAP, UCP, A2A, x402)` | `README.md:31`, `README.md:261` | file presence + exports | AP2 (`packages/sardis-protocol/src/sardis_protocol/schemas.py:12`), TAP (`packages/sardis-protocol/src/sardis_protocol/tap.py:23`), UCP (`packages/sardis-ucp/src/sardis_ucp/__init__.py:51`), A2A (`packages/sardis-a2a/src/sardis_a2a/__init__.py:1`), x402 (`packages/sardis-protocol/src/sardis_protocol/x402.py:1`) |
| `Env docs match runtime usage` | `.env.example` | `bash scripts/release/env_doc_check.sh` | `documented all runtime env vars (runtime=74, documented=97)` |
| `SDK versions are metadata-consistent` | `packages/sardis-sdk-python/pyproject.toml`, `packages/sardis-sdk-js/package.json` | `bash scripts/release/version_consistency_check.sh` | `root=0.3.1`, `python-sdk=0.3.3`, `ts-sdk=0.3.4` all matched constants |
| `Root sardis exports match documented API` | `sardis/__init__.py`, `README.md`, `examples/*.py` | `pytest -q tests/docs/test_sardis_root_exports.py` | verifies documented root symbols and conditional SDK re-exports |
| `Dependency CVE checks enforced in CI` | `.github/workflows/ci.yml` | `bash scripts/release/dependency_audit.sh` | CI `security` job runs `pip-audit` + `pnpm audit --audit-level high --prod` |
| `Publishable package metadata is complete` | `packages/*/pyproject.toml`, `packages/*/package.json` | `bash scripts/release/package_metadata_check.sh` | pyproject/package.json required fields and per-package `LICENSE` files all validated |
| `Critical path coverage exists for payment/policy/wallet lifecycle` | `tests/test_protocol_stack_integration.py`, `tests/test_cross_tenant_isolation.py`, `tests/integration/test_full_scenario.py` | `bash scripts/release/critical_path_check.sh` | Targeted smoke suite passes and is wired into CI |
| `Smart contract tests pass post-remediation` | `contracts/test/*.t.sol` | `FOUNDRY_OFFLINE=true forge test --root contracts` | `91 passed, 0 failed, 0 skipped` |
| `Launch copy uses verified metrics` | `docs/marketing/product-hunt-launch.md`, `docs/marketing/social-launch-kit.md` | manual review against this file | hard metrics (19 packages, 52 tools, 5 chains/protocols) now explicitly tied to `claims-evidence.md` |
| `Clone-and-run first-run flow is scripted` | `scripts/release/clone_and_run_smoke.sh` | `bash scripts/release/clone_and_run_smoke.sh --no-install` | Runs facade smoke flow + readiness + critical-path checks from a single entry point |
| `Residual risks are documented` | `docs/audits/final-remediation-report.md` | file review | report includes completed controls, proof commands, and remaining risk items |

## Canonical Verification Command

```bash
bash scripts/release/readiness_check.sh
```

Current expected output:

```text
[readiness] starting checks
[readiness] validating env documentation parity
[env-doc][pass] documented all runtime env vars (runtime=74, documented=97)
[readiness] validating SDK/package version consistency
[version][pass] root sardis version: 0.3.1
[version][pass] Python SDK version: 0.3.3
[version][pass] TypeScript SDK version: 0.3.4
[readiness][pass] MCP registry parity: 52 definitions = 52 handlers
[readiness][pass] pytest collected items: 840 (selected: 778)
[readiness][pass] package count: 19 (python=15, js=4)
[readiness][pass] mainnet chain count: 5
[readiness] all checks passed
```

## Notes

- Mainnet chain support is explicitly constrained to Base, Polygon, Ethereum, Arbitrum, and Optimism; Solana is blocked as not yet implemented (`packages/sardis-chain/src/sardis_chain/executor.py:1558`).
- Keep this file in sync whenever public-facing claims change.
