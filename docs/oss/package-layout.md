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
`server/routes/<domain>.py`.

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
| SDKs | `packages/sardis-sdk-python/`, `packages/sardis-sdk-js/`, `packages/sardis-ai-sdk/` | Keep public package names stable; improve docs and tests first. |
| Agent integrations | `packages/sardis-mcp-server/`, `packages/sardis-openai-agents/`, `packages/sardis-langchain/`, `packages/sardis-crewai/`, `packages/sardis-adk/`, `packages/sardis-agentkit/` | Keep package-specific validation; archive stale integrations before broad renames. |
| Provider adapters | `packages/sardis-cards/`, `packages/sardis-ramp/`, `packages/sardis-coinbase/`, `packages/sardis-lightspark/`, `packages/sardis-striga/` | Keep sandbox-safe adapter packages until provider status is rechecked. |
| Connect packages | `packages/sardis-connect/`, `packages/sardis-connect-js/` | Clarify Python middleware versus JS embed/SDK boundary before renaming either side. |

## Rename Candidates

These are the package names most likely to confuse contributors. They should be
renamed only through focused migration commits, not as a broad mechanical sweep.

| Candidate | Why it is confusing | Preferred next action |
| --- | --- | --- |
| `packages/sardis-connect/` and `packages/sardis-connect-js/` | Same product word with language split hidden at the suffix. | Decide whether Python is server middleware and JS is browser/client embed. Then rename docs and package paths in one package at a time if needed. |
| `packages/sardis-openai/` and `packages/sardis-openai-agents/` | The boundary between generic OpenAI API helpers and Agents SDK integration is not obvious. | Keep both until package-owned tests prove current upstream compatibility; archive or merge the weaker one. |
| `packages/sardis-agent-sdk/` and `packages/sardis-sdk-python/` | Both sound like the primary Python SDK. | Document the public SDK facade versus agent-runtime helper boundary, then rename or archive after compatibility checks. |
| `packages/sardis-core/src/sardis_v2_core/` | The `v2` import name looks stale and prototype-like even though the package is core. | `sardis_core` is now the preferred import shim. Keep `sardis_v2_core` working while internal imports migrate in focused commits. |
| legacy Python packages without `src/` | `packages/sardis-autogpt/`, `packages/sardis-browser-use/`, `packages/sardis-composio/`, `packages/sardis-crewai/`, and `packages/sardis-openai-agents/` do not match the newer Python package layout. | Migrate one package at a time after its package-owned tests pass. Do not move files without proving editable install behavior. |
| `packages/sardis-zkp/src/lib.py` | The package mixes Noir circuit layout with a generic Python-looking `src/lib.py`, so contributors cannot tell whether it is a circuit package or Python library. | Decide whether the package is circuit-only or needs a real Python wrapper, then document the validation command before moving files. |
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
