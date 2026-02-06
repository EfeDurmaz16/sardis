# Sardis v0.8.1: Protocol Conformance Hardening

Date: February 6, 2026

## Summary

This release hardens protocol-level correctness for AP2 and TAP while improving traceability against canonical AP2/TAP/UCP/x402 sources.

The focus is engineering safety in staging/testnet environments ahead of broader design partner usage.

## Shipped

1. AP2 PaymentMandate semantics:
   - Added and enforced explicit `ai_agent_presence`
   - Added and enforced explicit `transaction_modality` (`human_present`, `human_not_present`)
2. TAP validation hardening:
   - Header algorithm allowlist for message signatures
   - Linked object algorithm checks for `agenticConsumer` and `agenticPaymentContainer`
   - Canonical linked-object signature-base helper (excluding `signature` field)
3. Test coverage expansion:
   - TAP negative tests for invalid algorithms and signature failures
   - AP2 negative tests for missing agent presence and invalid modality
4. Conformance governance:
   - Added protocol source map: `docs/release/protocol-source-map.md`
   - Wired source mapping into start-to-end flow docs

## Why This Matters

1. Reduces protocol interpretation drift before mainnet commitments
2. Improves interoperability confidence with AP2/TAP ecosystem participants
3. Improves auditability: every major protocol assertion now maps to code + tests

## Known Remaining Engineering Gaps

1. TAP verification is helper-level; merchant-facing API middleware enforcement remains pending.
2. External conformance fixtures (third-party AP2/TAP/UCP payload sets) are not yet pinned in-repo.
3. x402 full 402 challenge/pay/retry integration harness is not yet in CI.

## References

1. AP2 spec: https://ap2-protocol.org/specification/
2. TAP spec (Visa): https://developer.visa.com/capabilities/trusted-agent-protocol/trusted-agent-protocol-specifications
3. UCP overview: https://ucp.dev/latest/specification/overview/
4. Coinbase MCP docs: https://docs.cdp.coinbase.com/mcp
5. Protocol source map: `docs/release/protocol-source-map.md`
