# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- A2A trust peer discovery endpoint: `GET /api/v2/a2a/trust/peers`
- A2A trust security posture endpoint: `GET /api/v2/a2a/trust/security-policy`
- A2A trust mutation audit feed endpoint: `GET /api/v2/a2a/trust/audit/recent`
- Deterministic trust-table hashing and compliance proof paths in trust API responses

### Changed
- Trust relation mutations now support approval quorum (`approval_id` + `approval_ids`) with distinct reviewer checks
- On-chain payment endpoint now evaluates goal-drift thresholds with review/block flow controls
- Production mode now fails closed when A2A trust table migration is missing

### Security
- 4-eyes approval enforcement added for trust relation mutations with strict org/action/metadata binding
- Goal-drift fail-closed deny path for high-risk autonomous on-chain payment requests
- Expanded payment hardening release gate coverage for trust, quorum, and goal-drift controls

## [0.2.0] - 2026-02-11

### Added
- Per-organization rate limiting with configurable tier overrides via `org_overrides`
- Extracted lifespan management into dedicated `lifespan.py` module
- Extracted OpenAPI schema customization into `openapi_schema.py`
- Extracted health check endpoints into `health.py` with factory pattern
- Extracted `CardProviderCompatAdapter` into `card_adapter.py`

### Changed
- Refactored main.py from 1392 to 683 lines (51% reduction) via module extraction
- Rate limiter now keys by `org:{org_id}` when organization context is available
- Both Redis and in-memory rate limiters support per-org configuration

### Security
- Rate limiting respects organization-specific quotas for enterprise customers

## [0.1.0] - 2025-01-27

### Added
- Initial release of sardis-api
- FastAPI application with OpenAPI documentation
- REST endpoints for:
  - Wallet management (create, get, balance)
  - Transaction processing (initiate, status, list)
  - Agent management (register, policy updates)
  - Mandate processing (intent, cart, payment)
  - Hold operations (create, capture, void)
  - Ledger queries
  - Compliance status
- Middleware stack:
  - Authentication (API key, JWT)
  - Rate limiting per client
  - Request/response logging
  - Security headers (CORS, CSP)
  - Exception handling
- Idempotency support for transaction endpoints
- Concurrency handling for payment operations

### Security
- API key validation
- JWT authentication support
- Rate limiting protection
- Input validation on all endpoints
- Secure header configuration

[Unreleased]: https://github.com/sardis-io/sardis-api/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sardis-io/sardis-api/releases/tag/v0.2.0
[0.1.0]: https://github.com/sardis-io/sardis-api/releases/tag/v0.1.0
