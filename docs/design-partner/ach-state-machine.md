# ACH Payment State Machine (Lithic Payments)

This state machine is the source of truth for Sardis treasury ACH orchestration.

## 1) Core status model

Internal payment statuses:

1. `PENDING`
2. `REVIEWED`
3. `PROCESSED`
4. `SETTLED`
5. `RELEASED`
6. `RETURN_INITIATED`
7. `RETURNED`
8. `DECLINED`
9. `VOIDED`
10. `REVERSED`
11. `EXPIRED`

## 2) Event to state mapping

| Lithic event | Internal status |
|---|---|
| `ACH_ORIGINATION_INITIATED` | `PENDING` |
| `ACH_ORIGINATION_REVIEWED` | `REVIEWED` |
| `ACH_ORIGINATION_PROCESSED` | `PROCESSED` |
| `ACH_ORIGINATION_SETTLED` | `SETTLED` |
| `ACH_ORIGINATION_RELEASED` | `RELEASED` |
| `ACH_RETURN_INITIATED` | `RETURN_INITIATED` |
| `ACH_RETURN_PROCESSED` | `RETURNED` |
| `ACH_RECEIPT_PROCESSED` | `PROCESSED` |
| `ACH_RECEIPT_SETTLED` | `SETTLED` |

Direct terminal states from payment object:

1. `DECLINED`
2. `VOIDED`
3. `REVERSED`
4. `EXPIRED`

## 3) Allowed transitions

1. `PENDING -> REVIEWED`
2. `REVIEWED -> PROCESSED`
3. `PROCESSED -> SETTLED`
4. `SETTLED -> RELEASED`
5. `PROCESSED -> RETURN_INITIATED`
6. `SETTLED -> RETURN_INITIATED`
7. `RETURN_INITIATED -> RETURNED`
8. Any non-terminal state can move to `DECLINED` when provider result is declined.

Rejected transitions are logged as policy violations and ignored.

## 4) Return reason handling

| Return reason | Action |
|---|---|
| `R01`, `R09` | eligible for bounded retry with policy checks |
| `R02`, `R03` | external account paused or closed, block retries |
| `R29` | external account paused, manual review required |

## 5) Replay and idempotency

1. Webhook dedupe key: `provider + event_id`.
2. Processing lock per event key.
3. Idempotency key on outward ACH create calls.
4. Event body hash mismatch on same event id is treated as suspicious.

## 6) Audit requirements

Every transition writes an immutable entry with:

1. `organization_id`
2. `payment_token`
3. `event_type`
4. `from_status`
5. `to_status`
6. `result`
7. `return_reason_code` when present
8. `provider_reference`
9. request and correlation ids

## 7) Reconciliation rules

1. Reconcile by payment token and settled amount in minor units.
2. Compare Lithic view vs Sardis ledger snapshot.
3. Track unresolved mismatches in exception queue with severity tiers.

