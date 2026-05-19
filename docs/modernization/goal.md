# Modernization Goal

## Product Understanding

Sardis appears to be an open-source financial authority layer for AI agents. The public repository combines a payment/control-plane API, policy-gated execution flows, wallets, agent mandates, approval and evidence records, protocol integrations, SDKs, docs, static public surfaces, and smart-contract or ZK-adjacent experiments. Hosted dashboard and product UI source belong in the private product repo.

The durable product behavior to preserve is:

- Agents can be represented, authorized, metered, limited, and audited.
- Payments and payment-like actions are evaluated before execution.
- Wallet, mandate, policy, approval, billing, webhook, idempotency, and evidence flows remain compatible.
- Public SDKs and API endpoints remain stable unless a migration explicitly versions them.
- Developer-facing docs and examples continue to explain Sardis as a payment authority/control plane, not just a wallet or crypto app.

## Current Architecture Summary

- Python public client facade at `src/sardis/`.
- FastAPI backend in `packages/api/src/sardis_server`, with a large `main.py` composition root, many routers, middleware, repositories, services, and lifecycle jobs.
- Python packages under `packages/sardis-*`, including core, API, chain, ledger, wallet, compliance, protocol, integrations, and agent-framework adapters.
- TypeScript packages for SDKs and integrations under `packages/sardis-sdk-js`, `packages/sardis-ai-sdk`, `packages/sardis-connect-js`, `packages/sardis-mcp-server`, and workflow adapters.
- Public apps in `apps/landing` and `apps/canvas-site`, plus a `docs-site`, generated static `canvases`, and serverless `api`/`api-proxy` folders.
- Solidity/Foundry contracts in `contracts/`.
- Noir policy circuit in `packages/sardis-zk-policy`.
- PostgreSQL schema history exists in both Alembic migrations and raw SQL migrations under `packages/api`.
- CI covers Python lint/tests, package tests, idempotency replay, JS builds/typechecks, CodeQL, gitleaks, scorecard, release dry-runs, and deploy workflows.

## Target Architecture Principles

- Keep the OSS repo as a boring, explicit monorepo: Python backend/domain packages, TypeScript SDK/integration packages, contracts, docs, examples.
- Make the API composition root declarative and domain-oriented instead of a multi-thousand-line bootstrap file.
- Treat payment, policy, signing, auth, idempotency, webhooks, billing, and evidence as safety-sensitive domains with explicit tests and fail-closed defaults.
- Prefer one package-manager story per ecosystem: root `uv.lock` for Python and root `pnpm-lock.yaml` for JavaScript unless a package is intentionally standalone.
- Generate artifacts outside source control unless they are release artifacts with a documented reason.
- Version public APIs and SDK contracts before changing behavior.
- Centralize duplicated API-client and shared domain type definitions through SDK/generated OpenAPI contracts where possible.
- Avoid speculative rewrites; migrate in slices that keep the repo runnable.

## Quality Bar

- A new contributor can identify the canonical backend, public apps, SDKs, migrations, and validation commands quickly.
- Critical payment and auth paths have focused regression tests.
- Generated files, local caches, package manager byproducts, and stale prototype folders are either ignored, archived, or intentionally documented.
- The default validation path is documented and runnable without private credentials.
- Duplicate logic is reduced where a stable shared abstraction is obvious.
- Public-facing docs match the current architecture and do not overstate unfinished capabilities.

## Preserve

- Public package names and import paths unless a versioned deprecation plan exists.
- Current `/api/v2` API contract and production auth/session semantics.
- Public API/session compatibility for product clients, without keeping hosted product UI source in the OSS repo.
- PostgreSQL migration compatibility and existing schema migration history.
- Security guards that require Redis/Postgres/JWKS in production-like environments.
- SDK examples and public docs that are still accurate.

## Rewrite Candidates

- Small internal composition modules inside `packages/api/src/sardis_server` may be extracted from `main.py`.
- Product/frontend API clients should converge on generated SDK/OpenAPI contracts outside the OSS protocol repo, with public SDK contracts kept stable.
- Prototype/demo integrations should be moved behind clearer examples or archived if not maintained.
- Raw SQL and Alembic migration duplication should be reconciled through a documented canonical path.

## Migration Success Criteria

- Audit reports exist with evidence and actionable remediation.
- Migration plan orders work by dependency and risk.
- The repo has a documented validation command set.
- Low-risk cleanup removes or quarantines obvious generated/local artifacts.
- No user work is overwritten.
- Each implementation step is isolated in a commit and validated.
