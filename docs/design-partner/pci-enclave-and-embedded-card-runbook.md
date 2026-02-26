# PCI Enclave + Embedded Card Runbook

Date: 2026-02-25
Owner: Sardis Core + Compliance

## 1. Target Model

Default production path:
- `tokenized_api` or `embedded_iframe` merchants only.
- PAN lane (`pan_entry`) is deny-by-default in production.
- PAN lane can be opened per merchant hostname allowlist for break-glass use.

Fallback path:
- Stablecoin-only execution (`x402` / on-chain USDC) when card integration or issuer funding is blocked.

## 2. Security Boundaries

Control plane (Sardis API):
- Stores intent, policy result, approval state, and redacted card metadata only.
- Never returns PAN/CVV in job/list/status payloads.
- Emits PAN-safe audit events.

Execution plane (PCI enclave worker):
- Consumes one-time `secret_ref` with short TTL.
- Token + attestation headers required for secret consume and completion callbacks.
- Replay protection on executor nonces.

Issuer plane (Stripe/Lithic/etc.):
- Embedded/iframe rendering for card reveal where possible.
- Real-time auth controls: merchant lock, velocity limits, spend limits, auto-freeze hooks.

## 3. New Runtime Controls (already wired in API)

- `SARDIS_CHECKOUT_REQUIRE_TOKENIZED_IN_PROD=1` (default behavior)
- `SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED=0` (default in production)
- `SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS=...` (break-glass allowlist)
- `SARDIS_CHECKOUT_EMBEDDED_IFRAME_MERCHANTS=...`
- `SARDIS_CHECKOUT_PAN_BOUNDARY_MODE=issuer_hosted_iframe_plus_enclave_break_glass`
- `SARDIS_CHECKOUT_PAN_PROVIDER=...` (optional explicit provider key)
- `SARDIS_CARDS_PRIMARY_PROVIDER=...` (fallback provider source)
- `SARDIS_CHECKOUT_PAN_PROVIDER_BOUNDARY_MATRIX_JSON=...` (approved overrides only)
- `SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION=1` (recommended)
- `SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_KEY=...`
- `SARDIS_CHECKOUT_EXECUTOR_TOKEN=...`

Security policy introspection:
- `GET /api/v2/checkout/secure/security-policy`
  - returns `pan_boundary_mode`, `pan_provider`, `pan_provider_boundary_mode`, `pan_boundary_mode_locked`, `pan_entry_break_glass_only`, and `pan_entry_allowlist`

Provider matrix policy:
- See `docs/design-partner/pan-boundary-provider-matrix.md` for default production mapping.
- In production, requested boundary mode cannot be looser than provider profile.

## 4. Compliance/Legal Workstream

Immediate:
- Confirm merchant vs service-provider role per flow.
- Map data flow where PAN/CVV can appear (including browser automation path).
- Document outsourcing boundaries and TPSP responsibilities.

Before production PAN lane:
- Complete PCI scope assessment for enclave architecture.
- Finalize evidence collection for access controls, logging, key management, and segmentation.
- Define annual/quarterly validation cadence with acquirer/brands.

## 5. Vendor Contact Checklist

Stripe Issuing:
- Ask for embedded card/iframe capabilities per region and product path.
- Ask for funding model constraints (Treasury, FBO, Connect, partner bank requirements).
- Ask for network token coverage by merchant category and fallback behavior.

Lithic:
- Confirm embedded reveal or equivalent hosted card UI options.
- Confirm auth controls for per-merchant/session locking and near-real-time freezing.
- Confirm spending limit granularity and webhook latency SLOs.

Rain / Bridge / stablecoin-native issuers:
- Confirm card funding path from stablecoin treasury.
- Confirm conversion model (instant swap vs prefund) and settlement windows.
- Confirm KYB/KYC responsibility split and compliance package.

## 6. Outreach Template (copy/paste)

Subject: Sardis card automation architecture review (embedded card + enclave + stablecoin fallback)

Body:
We are deploying autonomous purchasing agents and need a production-safe setup with:
1) embedded/iframe card path as default (no PAN exposure in our control plane),
2) isolated executor support for break-glass PAN entry,
3) strong real-time auth controls (merchant/session lock, velocity, auto-freeze),
4) clear funding model (fiat treasury and optional stablecoin rail).

Please confirm:
- supported architecture patterns,
- required account structure (per-customer account/FBO/sub-ledger),
- compliance responsibilities,
- sandbox-to-production migration steps and timeline.

## 7. Go/No-Go Rules

Go:
- Tokenized or embedded flow available for target merchants.
- Approval + deterministic policy + audit events enabled.
- Executor attestation and nonce replay protection enabled.

No-Go:
- PAN path required but enclave controls or compliance scope are not approved.
- Missing issuer auth controls or missing KYB/KYT governance for target segment.
