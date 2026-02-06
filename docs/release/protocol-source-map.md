# Sardis Protocol Source Map (AP2 / TAP / UCP / x402)

Last reviewed: February 6, 2026

This document pins the external protocol sources Sardis uses as engineering references and maps them to current enforcement/tests.

## Canonical Sources

1. AP2 specification: https://ap2-protocol.org/specification/
2. AP2 + MCP/A2A context: https://ap2-protocol.net/en/topics/ap2-a2a-and-mcp
3. AP2 + x402 context: https://ap2-protocol.net/en/topics/ap2-and-x402
4. TAP (Visa Trusted Agent Protocol): https://developer.visa.com/capabilities/trusted-agent-protocol/trusted-agent-protocol-specifications
5. UCP spec overview: https://ucp.dev/latest/specification/overview/
6. UCP and AP2: https://ucp.dev/latest/documentation/ucp-and-ap2/
7. Coinbase MCP docs (x402 + Payments MCP): https://docs.cdp.coinbase.com/mcp
8. Coinbase x402 docs: https://docs.cdp.coinbase.com/x402

## Requirement Mapping

### AP2

- Mandate chain validation (intent/cart/payment type+purpose, amount bounds, subject continuity):
  - `packages/sardis-protocol/src/sardis_protocol/verifier.py`
  - `tests/test_protocol_conformance_basics.py`
- Merchant domain binding between cart and payment:
  - `packages/sardis-protocol/src/sardis_protocol/verifier.py`
  - `tests/test_protocol_domain_binding.py`
- Agent presence + modality signals on payment mandate:
  - `packages/sardis-core/src/sardis_v2_core/mandates.py`
  - `packages/sardis-protocol/src/sardis_protocol/verifier.py`
  - `tests/test_protocol_domain_binding.py`

### TAP

- Signature-Input/Signature parsing and required fields:
  - `packages/sardis-protocol/src/sardis_protocol/tap.py`
- Tag allowlist (`agent-browser-auth`, `agent-payer-auth`), timestamp window (max 8 min), nonce replay:
  - `packages/sardis-protocol/src/sardis_protocol/tap.py`
  - `tests/test_tap_signature_validation.py`
- Header algorithm allowlist and linked object structural checks:
  - `packages/sardis-protocol/src/sardis_protocol/tap.py`
  - `tests/test_tap_signature_validation.py`
- JWK-based signature verification helpers (Ed25519, PS256):
  - `packages/sardis-protocol/src/sardis_protocol/tap_keys.py`
  - `tests/test_tap_keys.py`

### x402

- Request schema and required fields:
  - `packages/sardis-protocol/src/sardis_protocol/schemas.py`
  - `tests/test_x402_schema_validation.py`
- Payment-method parsing and routing hints:
  - `packages/sardis-protocol/src/sardis_protocol/payment_methods.py`
  - `tests/test_protocol_conformance_basics.py`

### UCP

- Package-level UCP behavior:
  - `packages/sardis-ucp` tests (`PYTHONPATH=src pytest -q tests`)
- AP2/UCP compatibility remains integration-tested at package boundaries; full cross-implementation conformance remains a release gate item.

## Current Gaps (Engineering, Non-Operational)

1. TAP end-to-end verification is helper-level only; no production API middleware path enforcing TAP headers yet.
2. AP2 negative interoperability fixtures from external counterparties are not version-pinned in-repo.
3. UCP coverage is package-local; no external conformance harness against third-party UCP servers.
4. x402 coverage is schema + parsing level; no full 402 challenge/pay/retry integration harness in CI.

## Recommended Release Gate Additions

1. Add a CI job that runs protocol conformance smoke tests:
   - `tests/test_ap2_compliance_checks.py`
   - `tests/test_protocol_conformance_basics.py`
   - `tests/test_protocol_domain_binding.py`
   - `tests/test_tap_signature_validation.py`
   - `tests/test_tap_keys.py`
   - `tests/test_x402_schema_validation.py`
2. Introduce fixture snapshots from external AP2/TAP/UCP ecosystems and fail CI on schema drift.
3. Add TAP verification middleware in API for merchant-facing agent requests.
