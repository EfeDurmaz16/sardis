# Funding Architecture Decision (2026-02-26)

Owner: Sardis Core  
Status: Accepted (Phase 1 rollout)

## Decision

Adopt a strategy-driven funding control plane for issuer top-ups with explicit feature flags:

- `fiat_first` (default): Stripe Treasury top-up path is primary.
- `stablecoin_first`: blocked unless stablecoin prefund flag is enabled.
- `hybrid`: allows mixed rails (as adapters are wired).

This is exposed via runtime config and API introspection endpoint:
- `GET /api/v2/stripe/funding/issuing/topups/strategy`

## Why

1. Avoid silent rail drift as we onboard Stripe/Lithic/Rain/Bridge in parallel.
2. Keep deterministic behavior under changing partner capabilities.
3. Make ops posture auditable and visible to enterprise customers.

## Implemented Flags

Environment prefix: `SARDIS_FUNDING_`

- `SARDIS_FUNDING_STRATEGY=fiat_first|stablecoin_first|hybrid`
- `SARDIS_FUNDING_PRIMARY_ADAPTER=stripe|coinbase_cdp|rain|bridge`
- `SARDIS_FUNDING_FALLBACK_ADAPTER=stripe|coinbase_cdp|rain|bridge`
- `SARDIS_FUNDING_STABLECOIN_PREFUND_ENABLED=true|false`
- `SARDIS_FUNDING_REQUIRE_CONNECTED_ACCOUNT=true|false`

## Current Adapter Wiring (Phase 1)

- Wired:
  - `stripe` (Stripe Treasury top-up adapter)
  - `rain` (HTTP top-up adapter)
  - `bridge` (HTTP top-up adapter)
  - `coinbase_cdp` (HTTP top-up adapter; requires dedicated topup API key)
- Runtime still defaults to `fiat_first` unless strategy flag is changed.

### New config/environment surface

- `COINBASE_CDP_TOPUP_API_KEY`
- `COINBASE_CDP_TOPUP_BASE_URL` (or `SARDIS_FUNDING` strategy defaults)
- `COINBASE_CDP_TOPUP_PATH`
- `RAIN_FUNDING_TOPUP_PATH`
- `BRIDGE_FUNDING_TOPUP_PATH`

## Runtime Guardrails

1. `stablecoin_first` without prefund enabled -> `503 stablecoin_prefund_disabled`
2. connected-account policy enabled with unresolved account -> `400 connected_account_required_by_policy`
3. no available funding adapters -> `503 stripe_treasury_not_configured`

## Next

1. Wire `coinbase_cdp` adapter for stablecoin prefund.
2. Add Rain/Bridge funding adapters where commercial/API access is confirmed.
3. Extend funding failover tests to include cross-rail simulation (`fiat -> stablecoin` and reverse).
