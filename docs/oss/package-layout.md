# Package Layout Policy

Sardis keeps public package paths optimized for contributor navigation. A path
should answer three questions quickly:

1. What package am I changing?
2. Is this a deployable app, a published library, a protocol primitive, or an
   integration adapter?
3. Which validation command proves my change?

## Rules

Deployable applications use role-based source roots. The reference API source
root is:

```text
packages/reference-api/server
```

Do not use repeated application layouts such as:

```text
packages/sardis-api/src/sardis_api
packages/reference-api/src/sardis_api
packages/reference-api/server/routers
```

The package directory already says this is the reference API. The import root
therefore stays `server`, not `sardis_api`, and route files live under
`server/routes/<domain>/<module>.py`.

Python libraries may keep `src/<import_package>` when that protects packaging
correctness and editable installs. Examples:

```text
packages/sardis-protocol/src/sardis_protocol
packages/sardis-sdk-python/src/sardis_sdk
packages/sardis-wallet/src/sardis_wallet
```

Do not flatten published libraries only to shorten paths. A library flattening
must prove that editable installs, tests, published import names, and downstream
imports continue to work.

TypeScript packages may keep a top-level `src/` when the package exports are
controlled by `package.json`.

## Current Package Families

| Family | Current paths | Layout stance |
| --- | --- | --- |
| Reference service | `packages/reference-api/` | Keep `server/` as the app source root. No `src/sardis_api`. |
| Core protocols | `packages/sardis-core/`, `packages/sardis-protocol/`, `packages/sardis-mpp/`, `packages/sardis-ledger/` | Keep published library import roots stable; migrate stale-looking import names only with compatibility shims. |
| SDKs | `packages/sardis-sdk-python/`, `packages/sardis-sdk-js/`, `packages/sardis-ai-sdk/`, `packages/sardis-agent-sdk/` | Keep public package names stable; use `docs/architecture/sdk-packages.md` before changing official SDK versus framework-integration ownership. |
| Agent integrations | `packages/sardis-mcp-server/`, `packages/sardis-openai/`, `packages/sardis-openai-agents/`, `packages/sardis-langchain/`, `packages/sardis-crewai/`, `packages/sardis-adk/`, `packages/sardis-agentkit/` | Keep package-specific validation; use `docs/architecture/openai-packages.md` before changing OpenAI package ownership. |
| Provider adapters | `packages/sardis-cards/`, `packages/sardis-ramp/`, `packages/sardis-coinbase/`, `packages/sardis-lightspark/`, `packages/sardis-striga/` | Keep sandbox-safe adapter packages until provider status is rechecked. |
| Connect packages | `packages/sardis-connect/`, `packages/sardis-connect-js/` | Keep the boundary in `docs/architecture/connect-packages.md`: Python FastAPI middleware versus TypeScript Node/Express middleware. |

## Rename Candidates

These are the package names most likely to confuse contributors. They should be
renamed only through focused migration commits, not as a broad mechanical sweep.

| Candidate | Why it is confusing | Preferred next action |
| --- | --- | --- |
| oversized protocol route modules | `packages/reference-api/server/routes/protocol/mpp.py` currently mixes HTTP handlers, request models, persistence fallback, policy checks, and provider execution in one route module. | Keep x402 and MPP HTTP adapters under `routes/protocol/`, but extract reusable MPP logic into focused domain/service/repository modules before adding new behavior. Preserve public HTTP paths. |
| route files named after their parent folder | Old names like `routes/billing/billing.py`, `routes/compliance/compliance.py`, `routes/evidence/evidence.py`, and `routes/wallets/wallets.py` made navigation feel duplicated even when the domain folder was correct. | Keep route modules named by role, for example `accounts.py`, `screening.py`, `records.py`, `lifecycle.py`, or `webhooks.py`. Preserve public HTTP paths and route registration behavior. |
| `packages/sardis-connect/` and `packages/sardis-connect-js/` | Same product word with language split hidden at the suffix. | Boundary is documented in `docs/architecture/connect-packages.md`. Rename only after preserving published package names, local filters, README commands, validation, and imports. |
| `packages/sardis-openai/` and `packages/sardis-openai-agents/` | The boundary between generic OpenAI API helpers and Agents SDK integration is not obvious. | Boundary is documented in `docs/architecture/openai-packages.md`. Keep both unless a migration preserves install commands, imports, optional dependencies, examples, and validation. |
| `packages/sardis-agent-sdk/` and `packages/sardis-sdk-python/` | Both sound like the primary Python SDK. | Boundary is documented in `docs/architecture/sdk-packages.md`. Keep official API client behavior in `packages/sardis-sdk-python/` and Anthropic runtime glue in `packages/sardis-agent-sdk/` unless a migration preserves install commands, imports, examples, and validation. |
| `packages/sardis-core/src/sardis_v2_core/` | The `v2` import name looks stale and prototype-like even though the package is core. | `sardis_core` is now the preferred import shim. Keep `sardis_v2_core` working while internal imports migrate in focused commits. |
| legacy Python packages without `src/` | `packages/sardis-autogpt/`, `packages/sardis-browser-use/`, `packages/sardis-composio/`, `packages/sardis-crewai/`, and `packages/sardis-openai-agents/` do not match the newer Python package layout. | Migrate one package at a time after its package-owned tests pass. Do not move files without proving editable install behavior. |
| `packages/sardis-zkp/` | The package contains both Noir circuits and a Python helper wrapper, so contributors can confuse circuit validation with runtime proof safety. | Keep the Python wrapper under `src/sardis_zkp/`, keep Noir circuit checks explicit, and do not treat mock proof tests as production cryptographic verification. |
| tracked-empty or local-only package shells | Names such as CLI variants, proxies, widgets, or bots can look like maintained public surfaces if they appear in docs without tracked source. | Keep untracked local shells out of public contribution docs. If a shell becomes tracked, add README, status, and validation immediately or archive it. |
| provider packages with stale upstreams | Provider status may have changed and packages may duplicate newer adapters. | Add provider-not-configured tests, then archive stale packages before renaming active ones. |

## Validation

Run this before layout, package naming, or contribution-path changes:

```bash
pnpm repo:package-layout
pnpm repo:package-validation
pnpm run check:contributor
```

The package layout check blocks known bad API shapes and requires the package
layout policy to stay linked from contributor-facing docs.
