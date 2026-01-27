# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-27

### Added

- Initial release of the Sardis Fiat Ramp SDK
- `SardisFiatRamp` class for fiat on/off ramp operations
- Wallet funding from fiat sources:
  - Bank transfer (ACH) support
  - Wire transfer support
  - Card payment support
  - Crypto deposit support
- Bank withdrawal (off-ramp) functionality:
  - ACH payouts
  - Policy validation before withdrawal
- Merchant fiat payments:
  - Direct merchant payments in USD
  - Approval workflow for high-value transactions
  - Policy-based spending controls
- Transfer status tracking:
  - Funding status monitoring
  - Withdrawal status monitoring
- Full TypeScript support with exported types
- Error classes for precise error handling:
  - `RampError` base class
  - `PolicyViolation` for policy rejections
- Environment support (sandbox/production)
- Custom URL configuration for enterprise deployments

### Features

- ESM and CommonJS bundle support
- Full TypeScript type definitions
- Integration with Bridge.xyz for fiat rails
- Multi-chain support (Base, Polygon, Ethereum, Arbitrum, Optimism)
- USDC as primary stablecoin

[0.1.0]: https://github.com/sardis-network/sardis/releases/tag/ramp-v0.1.0
