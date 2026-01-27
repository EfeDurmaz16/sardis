# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/sardis-io/sardis-api/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sardis-io/sardis-api/releases/tag/v0.1.0
