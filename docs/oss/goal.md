# Sardis OSS Goal

Sardis should be a contribution-ready open-source protocol and developer-platform repository for agent financial authority.

The public repository should make it easy for an external contributor to understand, run, test, and improve the common Sardis primitives without needing access to hosted-product secrets, private dashboards, sales material, investor material, customer context, or managed-provider operations.

## Product Boundary

Sardis open source is the shared authority layer:

- mandate semantics
- policy evaluation
- provider adapter interfaces
- simulator and sandbox adapters
- audit and evidence schemas
- idempotency and replay-safety patterns
- OpenAPI and API contract documentation
- SDKs and framework integrations
- MCP tooling
- conformance tests
- examples and demos that run without private credentials

Sardis Cloud / product code is the hosted operations layer:

- dashboard and approval inbox
- organization management
- billing and plan enforcement
- production credential vaulting
- managed provider routing
- compliance operations
- customer-specific workflows
- internal admin tools
- GTM, sales, investor, hiring, and partner-development material

## Quality Bar

The public repository must satisfy these standards before it is treated as mature OSS:

- Fresh clone can run documented setup and checks.
- Public CI does not require private secrets or product-only services.
- Every supported package has a README with purpose, install, usage, tests, stability, and contribution notes.
- Public/private boundary is documented and reflected in CI.
- Security-sensitive flows fail closed and have regression tests.
- Examples use current SDK APIs.
- Generated or private artifacts are not tracked as source.
- Package maturity is explicit: core, supported, experimental, demo, private-candidate, or archive-candidate.

## Success Criteria

- Contributors can open useful PRs against SDKs, protocol packages, policy/evidence primitives, MCP tooling, docs, and examples.
- Hosted product code can later move to a private repository without changing OSS API semantics.
- CI gives fast, deterministic feedback for OSS changes.
- The repository no longer exposes private commercial planning material as tracked public files.
- The architecture reads as a modern financial authority layer for agents, not as a mixed prototype/product dump.
