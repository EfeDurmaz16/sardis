# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-01-27

### Added
- MEV protection with Flashbots integration
- Private mempool support for sensitive transactions
- Deposit monitoring with real-time callbacks
- Enhanced confirmation tracking with reorg detection
- Transaction simulation before execution
- Logging utilities with chain context

### Changed
- Improved gas estimation accuracy
- Better RPC failover handling
- Enhanced nonce recovery mechanisms

## [0.1.0] - 2025-01-15

### Added
- Initial release of sardis-chain
- Multi-chain executor supporting Ethereum, Base, Polygon, Arbitrum
- MPC custody integration with Turnkey
- Transaction execution with automatic gas estimation
- Nonce management with conflict resolution
- Confirmation tracking with configurable thresholds
- RPC client with connection pooling and failover
- Chain configuration management
- Wallet manager for MPC operations

### Security
- Secure key handling through MPC providers
- No private keys stored in memory
- Transaction signing via custody providers

[Unreleased]: https://github.com/sardis-io/sardis-chain/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sardis-io/sardis-chain/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sardis-io/sardis-chain/releases/tag/v0.1.0
