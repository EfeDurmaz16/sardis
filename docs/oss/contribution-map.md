# Sardis Contribution Map

This map turns the package maturity matrix into practical contribution paths.
Use it to pick the right package, scope the PR, and choose the validation
command before making changes.

Start with:

```bash
pnpm run check:contributor
```

That gate is intentionally credential-free. It checks the OSS/private boundary,
stale API paths, source-layout invariants, package documentation coverage,
root-test migration inventory, and a small mixed package/root pytest smoke
suite.

## Contribution Principles

- Keep one logical change per PR.
- Prefer package-owned tests over root `tests/`.
- Do not add hosted-product, customer, sales, investor, or production-provider
  material to the public repo.
- Provider integrations must be sandbox-safe by default and explicit about
  credential requirements.
- Security-sensitive work must include fail-closed tests or a clear validation
  command.
- Keep source placement aligned with `docs/oss/source-layout.md`. The reference
  API source tree is `packages/reference-api/server`; do not reintroduce the old
  repeated API package names, extra API `src` layer, or legacy flat router
  bucket.
- Keep package layout aligned with `docs/oss/package-layout.md`. Package names
  should describe the contribution surface clearly, and deployable apps should
  use short role-based source roots rather than repeated product names.

## Core Contribution Paths

These packages are the stable OSS center of gravity. They should receive the
highest review rigor and the best tests.

| Area | Packages | Good contributions | Validation |
| --- | --- | --- | --- |
| Public SDK facade | `src/sardis/`, `packages/sardis-sdk-python/`, `packages/sardis-sdk-js/` | API drift fixes, typed examples, error handling, idempotency helpers | `uv run pytest packages/sardis-sdk-python/tests -q`; `pnpm --filter @sardis/sdk test`; `pnpm --filter @sardis/sdk typecheck` |
| Authority primitives | `packages/sardis-core/`, `packages/sardis-protocol/` | Mandate semantics, AP2/TAP fixtures, policy evaluation, replay safety | `uv run pytest packages/sardis-core/tests -q`; `PYTHONPATH=packages/sardis-protocol/src uv run pytest packages/sardis-protocol/tests -q` |
| Paid HTTP protocols | `packages/sardis-protocol/`, `packages/sardis-mpp/`, `packages/reference-api/` | x402 challenge/settlement fixes, MPP session negotiation, policy-before-payment conformance, receipt/evidence recording | `PYTHONPATH=packages/sardis-protocol/src uv run pytest packages/sardis-protocol/tests -q`; `PYTHONPATH=packages/sardis-mpp/src uv run --with pympp pytest packages/sardis-mpp/tests -q`; `PYTHONPATH=packages/reference-api uv run pytest tests/test_x402_middleware.py tests/test_mpp_router.py -q` |
| Evidence and ledger | `packages/sardis-ledger/` | Audit packet fixtures, tamper-evidence tests, reconciliation examples | `uv run pytest packages/sardis-ledger/tests -q` |
| Reference API | `packages/reference-api/` | Route tests, OpenAPI alignment, middleware safety, domain routing cleanup | `uv run pytest packages/reference-api/tests -q`; `pnpm run check:contributor` |
| Agent tooling | `packages/sardis-mcp-server/` | MCP schema improvements, examples, simulated-response labeling | `pnpm --filter @sardis/mcp-server build`; `pnpm --filter @sardis/mcp-server test` |

## Supported Package Paths

Supported packages are intended for outside users but may have narrower scope
than the core packages.

| Area | Packages | Good contributions | Validation |
| --- | --- | --- | --- |
| Local tooling | `packages/sardis-cli/` | CLI smoke commands, clearer errors, local demo setup | package README command plus `pnpm run check:contributor` |
| Chain and wallet adapters | `packages/sardis-chain/`, `packages/sardis-wallet/` | Simulator/live boundary tests, non-custodial docs, chain routing fixes | `uv run pytest packages/sardis-chain/tests -q`; `uv run pytest packages/sardis-wallet/tests -q` |
| Compliance and checkout | `packages/sardis-compliance/`, `packages/sardis-checkout/` | Sandbox provider docs, fail-closed KYC/KYT tests, checkout mandate validation | package-owned pytest suite |
| Framework integrations | `packages/sardis-ai-sdk/`, `packages/sardis-langchain/`, `packages/sardis-crewai/`, `packages/sardis-agent-sdk/`, `packages/sardis-openai-agents/` | Current framework examples, import compatibility, smoke tests | package README command plus integration CI when present |
| Protocol integrations | `packages/sardis-a2a/`, `packages/sardis-ucp/` | Conformance fixtures, schema examples, interoperability docs | package-owned pytest suite |

## Experimental Package Paths

Experimental packages can accept contributions, but PRs must be explicit about
API instability and provider caveats.

| Area | Packages | Good contributions | Validation |
| --- | --- | --- | --- |
| Provider adapters | `packages/sardis-cards/`, `packages/sardis-ramp/`, `packages/sardis-coinbase/`, `packages/sardis-lightspark/`, `packages/sardis-striga/` | Sandbox-only examples, capability declarations, provider-not-configured tests | package-owned pytest suite or focused route test |
| Payment protocols | `packages/sardis-mpp/`, `packages/sardis-connect/`, `packages/sardis-connect-js/` | Policy-before-payment tests, receipt recording, API boundary docs | package README command plus `pnpm run check:contributor` |
| ZK experiments | `packages/sardis-zk-policy/`, `packages/sardis-zkp/` | Reproducible dev setup, fail-closed verifier tests, fixture docs | package README command and relevant root migration test if not yet moved |
| Agent ecosystem experiments | `packages/sardis-adk/`, `packages/sardis-agentkit/`, `packages/sardis-browser-use/`, `packages/sardis-composio/`, `packages/sardis-autogpt/`, `packages/sardis-openai/`, `packages/sardis-openclaw/`, `packages/sardis-gpt/`, `packages/sardis-e2b/`, `packages/sardis-guardrails/` | Refresh against current upstream APIs, add minimal smoke tests, archive stale packages when justified | package README command or a new package-owned smoke test |
| Workflow integrations | `packages/n8n-nodes-sardis/`, `packages/sardis-activepieces/` | Build gates, credential-safe examples, node/action metadata cleanup | package build/test command |

## What Not To Put In Public PRs

Do not add:

- hosted dashboard or approval inbox code
- production deployment secrets or customer runbooks
- sales, GTM, investor, hiring, or partner-development material
- real provider credentials, webhook secrets, API keys, private keys, or raw
  customer payloads
- generated artifacts unless the source and regeneration command are clear

Use `docs/oss/public-private-boundary.md` and
`docs/oss/private-repo-migration-manifest.md` when a file looks borderline.

## Choosing A Test Location

| Change | Put tests in |
| --- | --- |
| API route, middleware, auth, webhooks | `packages/reference-api/tests/` |
| Policy, mandate, authority, orchestration | `packages/sardis-core/tests/` or `packages/sardis-protocol/tests/` |
| Ledger, audit packet, reconciliation | `packages/sardis-ledger/tests/` |
| Chain, wallet, provider execution | owning package tests |
| SDK behavior | owning SDK package tests |
| Cross-package migration backlog | root `tests/` only while migrating, documented in `docs/oss/root-test-migration.md` |

Root tests are a migration backlog, not the default contribution path. If a
root test becomes important for a new PR, move it to the owning package first
unless it genuinely spans multiple packages.

## x402 And MPP Contributions

x402 and MPP are separate protocol surfaces, not duplicate packages:

- x402 primitives live in `packages/sardis-protocol/`; API facilitator routes
  and middleware live in `packages/reference-api/`.
- MPP client/session primitives live in `packages/sardis-mpp/`; API session
  routes and middleware live in `packages/reference-api/`.
- Shared Sardis behavior belongs in policy, execution, receipt, and evidence
  code, not in a new `x402_mpp` bucket.

Use `docs/architecture/x402-and-mpp.md` before changing either surface. Run the
validation targets separately; package-local and root pytest suites currently
load different `tests.conftest` modules and should not be combined into one
pytest invocation.

```bash
PYTHONPATH=packages/sardis-protocol/src uv run pytest packages/sardis-protocol/tests -q
PYTHONPATH=packages/sardis-mpp/src uv run --with pympp pytest packages/sardis-mpp/tests -q
PYTHONPATH=packages/reference-api uv run pytest tests/test_x402_middleware.py tests/test_mpp_router.py -q
```
