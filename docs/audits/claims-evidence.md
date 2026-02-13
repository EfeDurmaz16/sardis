# Sardis Claims Evidence (Pre-Launch Snapshot)

Snapshot date: 2026-02-13

This document ties launch-facing claims to reproducible checks in-repo.

## Verified Claims

| Claim | Public Source | Evidence Command | Result |
| --- | --- | --- | --- |
| `52 MCP tools` | `README.md:30`, `README.md:225`, `landing/src/App.jsx:610` | `bash scripts/release/readiness_check.sh` | `MCP registry parity: 52 definitions = 52 handlers` |
| `150+ tests` | `README.md:252` | `pytest --collect-only -q` | `collected 823 items` (`761 selected`) |
| `19 packages on npm + PyPI` | `docs/marketing/product-hunt-launch.md:31`, `landing/src/App.jsx:1059` | `bash scripts/release/readiness_check.sh` | `package count: 19 (python=15, js=4)` |
| `5 chains` | `README.md:254`, `docs/marketing/product-hunt-launch.md:27` | `bash scripts/release/readiness_check.sh` | `mainnet chain count: 5` |
| `5 protocols (AP2, TAP, UCP, A2A, x402)` | `README.md:31`, `README.md:261` | file presence + exports | AP2 (`packages/sardis-protocol/src/sardis_protocol/schemas.py:12`), TAP (`packages/sardis-protocol/src/sardis_protocol/tap.py:23`), UCP (`packages/sardis-ucp/src/sardis_ucp/__init__.py:51`), A2A (`packages/sardis-a2a/src/sardis_a2a/__init__.py:1`), x402 (`packages/sardis-protocol/src/sardis_protocol/x402.py:1`) |

## Canonical Verification Command

```bash
bash scripts/release/readiness_check.sh
```

Current expected output:

```text
[readiness] starting checks
[readiness][pass] MCP registry parity: 52 definitions = 52 handlers
[readiness][pass] pytest collected items: 823 (selected: 761)
[readiness][pass] package count: 19 (python=15, js=4)
[readiness][pass] mainnet chain count: 5
[readiness] all checks passed
```

## Notes

- Mainnet chain support is explicitly constrained to Base, Polygon, Ethereum, Arbitrum, and Optimism; Solana is blocked as not yet implemented (`packages/sardis-chain/src/sardis_chain/executor.py:1558`).
- Keep this file in sync whenever public-facing claims change.
