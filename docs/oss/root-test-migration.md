# Root Test Migration Inventory

The repository-root `tests/` tree is a legacy migration backlog, not the default contributor test suite.
Maintained tests live under package-owned `tests/` directories such as `packages/server-api/tests/`, `packages/sardis-core/tests/`, `packages/sardis-ledger/tests/`, and `packages/sardis-chain/tests/`.

## Current Snapshot

- Root Python test files: `233`
- Files with stale API import/path references: `10`
- Default pytest path: `packages/server-api/tests` from root `pyproject.toml`
- Default npm test path: package-owned suites from `package.json`

## Owner Buckets

| Target owner | Root test files |
| --- | ---: |
| `needs owner review` | 95 |
| `package docs/tests or package-owned examples` | 3 |
| `package-owned integration test or archive-candidate` | 17 |
| `packages/sardis-chain/tests` | 19 |
| `packages/sardis-core/tests` | 19 |
| `packages/sardis-ledger/tests` | 8 |
| `packages/server-api/tests` | 72 |

## Migration Rules

1. Do not add new tests to root `tests/` unless the test genuinely spans multiple packages and has no clearer package owner.
2. When touching a root test, either move it to the owning package suite or mark it as archive-candidate in the PR.
3. API route tests should import `sardis_server.routes.<domain>` or test HTTP behavior through the maintained API app.
4. Compatibility imports such as `sardis_api` and `sardis.routers` must not be reintroduced.
5. Cross-package tests should document the packages they bind together and their required credentials or local services.

## Stale API Reference Backlog

| File | Suggested owner | Stale refs |
| --- | --- | ---: |
| `tests/integration/test_api_integration.py` | `packages/server-api/tests` | 2 |
| `tests/integration/test_delegated_payment_e2e.py` | `package-owned integration test or archive-candidate` | 2 |
| `tests/test_checkout_eip712.py` | `packages/server-api/tests` | 4 |
| `tests/test_checkout_onchain_verification.py` | `packages/server-api/tests` | 9 |
| `tests/test_coinbase_stack_integration.py` | `needs owner review` | 2 |
| `tests/test_e2e_full_flow.py` | `needs owner review` | 9 |
| `tests/test_emergency_freeze.py` | `needs owner review` | 11 |
| `tests/test_fake_routes_removed.py` | `needs owner review` | 10 |
| `tests/test_stripe_onramp.py` | `packages/server-api/tests` | 17 |
| `tests/test_zk_failclosed.py` | `needs owner review` | 3 |

Regenerate this inventory with:

```bash
python3 scripts/root_test_inventory.py --write
```
