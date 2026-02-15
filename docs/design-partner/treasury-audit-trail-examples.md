# Treasury Audit Trail Examples

Last updated: 2026-02-15

This document shows expected audit artifacts for ACH treasury operations.

## 1) ACH Fund Example

Request:

```json
{
  "financial_account_token": "fa_issuing_123",
  "external_bank_account_token": "eba_123",
  "amount_minor": 50000,
  "method": "ACH_NEXT_DAY",
  "sec_code": "CCD",
  "memo": "Top-up"
}
```

Expected records:

1. `ach_payments` row with `payment_token`.
2. `ach_payment_events` rows as events arrive.
3. `treasury_balance_snapshots` row after fund status update.
4. `treasury_webhook_events` row for each provider webhook (with replay-safe event id).

## 2) Event Chain Example

```text
ACH_ORIGINATION_INITIATED -> PENDING
ACH_ORIGINATION_REVIEWED  -> REVIEWED
ACH_ORIGINATION_PROCESSED -> PROCESSED
ACH_ORIGINATION_SETTLED   -> SETTLED
ACH_ORIGINATION_RELEASED  -> RELEASED
```

Reference: `docs/design-partner/ach-state-machine.md`

## 3) Return Code Branch Example

If return event contains `R03`:

1. `ach_payments.last_return_reason_code = R03`
2. `ach_payments.status = RETURNED` (or `RETURN_INITIATED` then `RETURNED`)
3. `external_bank_accounts.is_paused = true`
4. `external_bank_accounts.pause_reason` captures return context

## 4) Verification Query Examples

```sql
-- Payment + latest status
SELECT payment_token, status, result, last_return_reason_code, retry_count
FROM ach_payments
WHERE payment_token = 'pay_123';

-- Ordered event chain
SELECT event_type, result, return_reason_code, created_at
FROM ach_payment_events
WHERE payment_token = 'pay_123'
ORDER BY created_at ASC;

-- Latest balance snapshot
SELECT financial_account_token, available_amount_minor, pending_amount_minor, total_amount_minor, created_at
FROM treasury_balance_snapshots
WHERE organization_id = 'org_demo'
ORDER BY created_at DESC
LIMIT 1;
```

## 5) Evidence Bundle for Partner Review

1. API request/response pair for fund or withdraw.
2. `payment_token` and final status payload.
3. Webhook event sequence with replay-safe event ids.
4. Balance snapshot delta before/after settlement.
5. If failed: return code handling branch evidence.
