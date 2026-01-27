# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-27

### Added

- Initial release of `@sardis/ai-sdk`
- **Tool Functions**
  - `createSardisTools()` - Full tool set (7 tools)
  - `createMinimalSardisTools()` - Pay + balance only
  - `createReadOnlySardisTools()` - Analytics only (no payments)
- **Tools**
  - `sardis_pay` - Execute payments
  - `sardis_create_hold` - Create pre-authorizations
  - `sardis_capture_hold` - Capture holds
  - `sardis_void_hold` - Cancel holds
  - `sardis_check_policy` - Policy verification
  - `sardis_get_balance` - Wallet balance
  - `sardis_get_spending` - Spending analytics
- **SardisProvider Class**
  - High-level provider for Vercel AI SDK integration
  - Built-in system prompt with payment guidelines
  - Transaction logging and callbacks
  - Direct payment methods (without AI)
- **Policy Enforcement**
  - Local pre-checks before API calls
  - Maximum payment amount limits
  - Blocked category filtering
  - Allowed merchant whitelist mode
- **TypeScript Support**
  - Full type definitions
  - Zod schemas for validation
  - Exported types for all parameters and results

### Dependencies

- Requires `ai` >= 3.0.0 (Vercel AI SDK)
- Uses `@sardis/sdk` for API communication
- Uses `zod` for schema validation
