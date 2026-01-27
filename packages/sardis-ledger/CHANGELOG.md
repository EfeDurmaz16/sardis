# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-01-27

### Added
- Hybrid ledger combining PostgreSQL and immudb
- Blockchain anchoring for Merkle roots
- Balance snapshots for point-in-time queries
- Currency conversion utilities
- Reconciliation scheduler for automated checks

### Changed
- Improved batch transaction performance
- Enhanced lock manager with deadlock detection
- Better error messages for validation failures

## [0.2.0] - 2025-01-20

### Added
- Immutable audit trail with immudb integration
- Merkle proof generation and verification
- Verification status tracking
- Consistency checking utilities

### Fixed
- Lock timeout handling in high-concurrency scenarios
- Balance calculation edge cases

## [0.1.0] - 2025-01-15

### Added
- Initial release of sardis-ledger
- Append-only ledger store with Merkle tree receipts
- Row-level locking for concurrent transactions
- Batch transaction processing with atomic commits
- Ledger engine with lock management
- Blockchain reconciliation engine
- Chain provider abstraction
- Core models:
  - LedgerEntry with credit/debit types
  - BalanceSnapshot for historical queries
  - AuditLog for change tracking
  - ReconciliationRecord for chain state
  - BatchTransaction for grouped operations
- Currency rate management
- Lock record tracking

### Security
- Immutable append-only design
- Merkle tree verification
- Comprehensive audit logging

[Unreleased]: https://github.com/sardis-io/sardis-ledger/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/sardis-io/sardis-ledger/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/sardis-io/sardis-ledger/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sardis-io/sardis-ledger/releases/tag/v0.1.0
