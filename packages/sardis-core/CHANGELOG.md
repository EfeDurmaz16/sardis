# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-02-11

### Added
- Velocity checks at policy layer: per-transaction, daily, weekly, monthly limits
- Gas fee estimation integrated into spending policy evaluation
- PostgreSQL persistence for spending policy state (replaces in-memory)
- MCC 4829 (Wire Transfers) added to data file as high-risk, default blocked

### Changed
- MCC codes 6051 (quasi-cash), 6540 (stored value), 5933 (pawn shops) now default blocked
- Unified sardis package as single SDK entry point (resolves dual-SDK confusion)

### Security
- Expanded disposable email domain detection from 6 to 40 providers
- Expanded OFAC/FATF high-risk country list from placeholder to 16 real codes

## [0.1.0] - 2025-01-27

### Added
- Initial release of sardis-core
- Comprehensive exception hierarchy with error codes
- Configuration management with environment variable loading
- Input validation utilities for wallets, agents, amounts, and addresses
- Retry mechanisms with exponential backoff and jitter
- Circuit breaker pattern for service resilience
- Structured logging with sensitive data masking
- Domain models:
  - Wallet and TokenBalance models
  - Transaction and TransactionStatus models
  - Hold and HoldResult models
  - Agent and AgentPolicy models
  - Mandate models (Intent, Cart, Payment)
  - VirtualCard models
- Natural language policy parser (optional, requires OpenAI)
- Redis-based spending tracker (optional)
- Cache service with in-memory and Redis backends
- Webhook event system
- Database utilities and schema

### Security
- Sensitive data masking in logs
- Secure key management utilities
- Input validation for all public APIs

[Unreleased]: https://github.com/sardis-io/sardis-core/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sardis-io/sardis-core/releases/tag/v0.1.0
