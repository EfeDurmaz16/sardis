# ACH Return Support Playbook

Last updated: 2026-02-15

## Purpose

Standardize response for ACH failures in USD-first treasury flows.

## Severity Model

1. `SEV-1`: replay/signature failures on webhook ingestion.
2. `SEV-2`: payment stuck or repeated returns for a single org.
3. `SEV-3`: isolated return code with successful retry path.

## Return Code Actions

| Return Code | Meaning | System Action | Support Action |
| --- | --- | --- | --- |
| R01 | Insufficient funds | Increment retry counter | Ask customer to re-fund source account and retry |
| R09 | Uncollected funds | Increment retry counter | Delay retry window and notify customer |
| R02 | Account closed | Auto-pause external account | Request new bank account link |
| R03 | No account/unable to locate | Auto-pause external account | Validate routing/account details and re-link |
| R29 | Corporate not authorized | Auto-pause external account | Collect authorization evidence before re-enable |

## Support Workflow

1. Identify payment:
   - `GET /api/v2/treasury/payments/{payment_token}`
2. Inspect latest events:
   - `ach_payment_events` by `payment_token`
3. Confirm external account status:
   - `external_bank_accounts.is_paused`
4. Apply branch:
   - Retry branch: R01/R09
   - Pause branch: R02/R03/R29
5. Record incident in audit log with:
   - `payment_token`
   - `event_type`
   - `return_reason_code`
   - support decision

## Retry Policy

1. Retry is capped (`max_retry_count=2` by default).
2. Only codes R01/R09 are auto-retry eligible.
3. Retry orchestration is handled by scheduled job `treasury_retry_returns`.

## Customer Communication Templates

### Retry required (R01/R09)

`We could not settle your ACH payment due to temporary source-account balance conditions (code: <RETURN_CODE>). Please ensure available funds and retry.`

### Re-link required (R02/R03/R29)

`Your linked bank account was paused for safety after ACH return code <RETURN_CODE>. Please re-link or update the account details to continue.`

## Escalation

Escalate to engineering when:

1. Same `payment_token` receives duplicate conflicting events.
2. Webhook signature validation fails unexpectedly in production.
3. Account remains paused after successful verification replay.
