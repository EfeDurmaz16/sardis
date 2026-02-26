# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2026-02-26

### Added
- `FailoverKYCProvider` wrapper for primary/fallback KYC execution with deterministic inquiry routing.
- `FailoverSanctionsProvider` wrapper for primary/fallback sanctions screening with provider-error-aware failover.
- New failover test suite covering KYC and sanctions provider fallback behavior.

### Changed
- Provider exports now include canonical `IdenfyKYCProvider` alias in addition to legacy `IDenfyKYCProvider`.

## [0.3.0] - 2026-02-11

### Added
- Travel Rule (FATF R.16) compliance module for cross-border transfers >$3,000
- KYB (Know Your Business) verification via Persona for organizational onboarding
- PostgreSQL persistence for SAR (Suspicious Activity Report) storage
- PostgreSQL persistence for IdentityRegistry

### Security
- Travel Rule enforcement is fail-closed: transfers without complete data are blocked
- Originator and beneficiary identity required for cross-border transfers above threshold

## [0.2.0] - 2025-01-27

### Added
- Risk scoring engine with configurable thresholds
- PEP (Politically Exposed Persons) screening
- Adverse media monitoring integration
- Compliance dashboard with metrics
- Batch processing for bulk screening
- Audit log rotation with S3/GCS archival
- Retry logic with circuit breaker pattern
- Comprehensive compliance reporting (JSON, HTML, PDF, CSV)

### Changed
- Improved sanctions screening accuracy
- Enhanced KYC session management
- Better rate limiting for external API calls

## [0.1.0] - 2025-01-15

### Added
- Initial release of sardis-compliance
- Compliance engine with rule-based checking
- KYC verification with Persona integration
- Sanctions screening with Elliptic integration
- Audit trail for all compliance decisions
- Natural language policy provider
- Simple rule provider for custom policies

### Security
- Secure storage of compliance data
- Audit logging for all operations
- PII handling compliant with regulations

[Unreleased]: https://github.com/sardis-io/sardis-compliance/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/sardis-io/sardis-compliance/compare/v0.3.0...v0.4.1
[0.2.0]: https://github.com/sardis-io/sardis-compliance/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sardis-io/sardis-compliance/releases/tag/v0.1.0
