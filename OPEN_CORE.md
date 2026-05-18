# Sardis Open-Core Model

Sardis separates open financial-authority primitives from the hosted operations product.

## Open Source

The public repository contains the parts that should be inspectable, portable, and independently testable:

- mandate and authority semantics
- policy evaluation
- provider adapter contracts
- simulator providers
- SDKs and CLI
- MCP server and agent-framework integrations
- audit and evidence schemas
- protocol and API documentation
- examples, demos, and conformance tests

## Hosted / Commercial

The hosted Sardis product should live in a private repository or private deployment boundary:

- dashboard and approval inbox
- organization management, RBAC, and SSO
- billing and plan enforcement
- managed provider credentials
- production routing decisions
- compliance operations
- customer-specific workflows
- internal admin and support tools

## Rule

Public code may define the contract. Private code may operate the managed service.

If a feature is needed for interoperability, security review, SDK correctness, or conformance, it belongs in OSS. If it encodes customer operations, vendor strategy, sales process, credentials, billing, or hosted workflow details, it belongs private.
