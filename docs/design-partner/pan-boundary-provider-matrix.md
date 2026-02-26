# PAN Boundary Provider Matrix

Date: 2026-02-26  
Owner: Sardis Core + Compliance

## Purpose

Define deterministic PAN boundary defaults per issuer/provider so production cannot accidentally run a looser PAN lane than the provider profile allows.

## Default Provider Profiles

| Provider key | Default boundary mode | Rationale |
| --- | --- | --- |
| `stripe_issuing`, `stripe` | `issuer_hosted_iframe_only` | Keep PAN in issuer-hosted UI by default. |
| `lithic` | `issuer_hosted_iframe_plus_enclave_break_glass` | Allow controlled break-glass PAN lane for merchants without embedded flow. |
| `rain` | `issuer_hosted_iframe_plus_enclave_break_glass` | Same break-glass posture while partner capabilities are finalized. |
| `bridge` | `issuer_hosted_iframe_only` | Default to hosted-only until card reveal model is certified. |
| `coinbase_cdp` | `issuer_hosted_iframe_only` | On-chain-first; PAN lane should remain constrained. |

## Runtime Rules

In production:
1. Provider is resolved from:
   - `SARDIS_CHECKOUT_PAN_PROVIDER`, else
   - `SARDIS_CARDS_PRIMARY_PROVIDER`.
2. If provider has a profile, requested `SARDIS_CHECKOUT_PAN_BOUNDARY_MODE` cannot be looser than provider profile.
3. If requested mode is looser, API locks to provider profile and emits lock metadata.

Security policy endpoint (`GET /api/v2/checkout/secure/security-policy`) returns:
- `pan_provider`
- `pan_provider_boundary_mode`
- `pan_boundary_mode`
- `pan_boundary_mode_locked`

## Config Override (Controlled)

Use `SARDIS_CHECKOUT_PAN_PROVIDER_BOUNDARY_MATRIX_JSON` only for approved partner overrides.

Example:

```json
{
  "rain": "issuer_hosted_iframe_only",
  "bridge": "issuer_hosted_iframe_only"
}
```

Only supported modes are accepted:
- `issuer_hosted_iframe_only`
- `enclave_break_glass_only`
- `issuer_hosted_iframe_plus_enclave_break_glass`

## Go/No-Go

Go when:
- provider profile exists and is enforced in production,
- policy endpoint reflects lock state,
- PAN lane remains allowlist + attestation gated.

No-Go when:
- provider profile unknown and PAN lane is opened without explicit compliance approval.
