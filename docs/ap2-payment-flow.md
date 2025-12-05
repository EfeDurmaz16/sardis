# AP2 Payment Flow (Sardis V2)

This guide describes how an AP2-compatible agent can execute a stablecoin payment through Sardis V2.

## 1. Construct Mandates
1. **Intent Mandate** – User authorizes spending scope and TTL.
2. **Cart Mandate** – Agent produces cart details bound to the Intent.
3. **Payment Mandate** – Final authorization referencing cart hash, chain, token, and destination.

All three mandates are W3C VC objects signed with the agent’s TAP-compatible key. See `tests/ap2_helpers.py` for a programmatic example (`build_signed_bundle`).

## 2. Submit to Sardis
Send the bundle to `/api/v2/ap2/payments/execute` with the following JSON shape:
```json
{
  "intent": { ... },
  "cart": { ... },
  "payment": { ... }
}
```
Sardis verifies:
- VC signatures + proof metadata
- Mandate linkage (same subject, merchant, purpose)
- Replay protection via durable cache
- Domain allowlist

## 3. Policy + Compliance
The PaymentOrchestrator invokes:
- Wallet policies (`sardis-wallet`) for limits/whitelists
- Compliance provider (rule engine today, external vendor later)
- Results include `compliance_provider` and `compliance_rule` IDs for audit trails.

## 4. Execution
- `sardis-chain` dispatches the simulated stablecoin transfer (Turnkey/Fireblocks adapters drop in later).
- `sardis-ledger` writes immutable entries with chain receipts and `audit_anchor` values.
- `sardis-protocol` archives mandate chains for non-repudiation.

## 5. Response
Example response body:
```json
{
  "mandate_id": "payment-...",
  "ledger_tx_id": "tx_...",
  "chain_tx_hash": "0xabc...",
  "chain": "base",
  "audit_anchor": "merkle::...",
  "status": "submitted",
  "compliance_provider": "rules",
  "compliance_rule": "baseline"
}
```
Use `ledger_tx_id` to fetch recent settlements via future ledger endpoints, and `chain_tx_hash` to trace on-chain receipts once MPC execution lands.

## 6. SDK Usage
- **Python**: `await SardisClient.execute_ap2_payment(bundle_dict)`.
- **TypeScript**: `await sardisClient.executeAp2Payment(bundle)`.

Both SDKs mirror the HTTP response structure so developers can log compliance metadata and audit anchors easily.
