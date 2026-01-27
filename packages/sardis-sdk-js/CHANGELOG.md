# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-27

### Added

- Full TypeScript SDK for Sardis stablecoin execution layer
- `SardisClient` class with comprehensive API coverage
- Payment execution with mandate support (AP2 bundles)
- Pre-authorization holds (create, capture, void, extend)
- Webhook management for real-time events
- Agent-to-Agent (A2A) marketplace integration
- Transaction gas estimation and status tracking
- Ledger queries and entry verification
- Agent management with spending policies
- Wallet management with MPC provider support
- Framework integrations:
  - LangChain.js toolkit
  - Vercel AI SDK tools
  - OpenAI function calling

### Features

- ESM, CommonJS, and browser bundle support
- Full TypeScript type definitions
- Typed error classes for precise error handling
- Retry logic with exponential backoff
- Request/response logging support
- Multi-chain support (Base, Polygon, Ethereum, Arbitrum, Optimism)
- Multi-token support (USDC, USDT, PYUSD, EURC)

## [0.1.0] - 2025-01-15

### Added

- Initial release
- Basic client implementation
- Payment execution support
- Wallet management

[0.2.0]: https://github.com/sardis-network/sardis-sdk-js/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sardis-network/sardis-sdk-js/releases/tag/v0.1.0
