# Fiat-First Treasury Design Partner Runbook

Last updated: 2026-02-15

## Scope

This runbook covers the USD-first treasury launch path:

1. Sync financial accounts.
2. Link and verify external bank account.
3. Fund treasury with ACH collection.
4. Issue/use card from USD-backed treasury.
5. Withdraw with ACH payment.
6. Reconcile and verify audit trail.

Stablecoin conversion is optional and policy/feature-flag controlled.

## Prerequisites

1. API key with treasury permissions.
2. Org-scoped financial account mapping in `lithic_financial_accounts`.
3. `LITHIC_API_KEY` configured in API runtime.
4. Production only:
   - `LITHIC_WEBHOOK_SECRET` set.
   - webhook endpoint exposed at `POST /api/v2/webhooks/lithic/payments`.

## Environment Controls

1. `SARDIS_TREASURY_DEFAULT_ROUTE=fiat_first`
2. `SARDIS_TREASURY_MAX_PER_PAYMENT_MINOR`
3. `SARDIS_TREASURY_MAX_DAILY_ORG_MINOR`
4. `SARDIS_TREASURY_MAX_PAYMENTS_PER_HOUR`

## E2E Steps

### 1) Sync financial accounts

```bash
curl -X POST https://api.sardis.sh/api/v2/treasury/account-holders/sync \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"account_token":"acct_demo_123"}'
```

### 2) Link external bank account

```bash
curl -X POST https://api.sardis.sh/api/v2/treasury/external-bank-accounts \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "financial_account_token":"fa_issuing_123",
    "verification_method":"MICRO_DEPOSIT",
    "owner_type":"BUSINESS",
    "owner":"Design Partner LLC",
    "account_type":"CHECKING",
    "routing_number":"021000021",
    "account_number":"123456789",
    "currency":"USD",
    "country":"USA"
  }'
```

### 3) Verify micro-deposits

```bash
curl -X POST https://api.sardis.sh/api/v2/treasury/external-bank-accounts/eba_123/verify-micro-deposits \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"micro_deposits":["19","89"]}'
```

### 4) Fund treasury

```bash
curl -X POST https://api.sardis.sh/api/v2/treasury/fund \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "financial_account_token":"fa_issuing_123",
    "external_bank_account_token":"eba_123",
    "amount_minor":50000,
    "method":"ACH_NEXT_DAY",
    "sec_code":"CCD",
    "memo":"Design partner top-up"
  }'
```

### 5) Track status and balances

```bash
curl -H "X-API-Key: $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/treasury/payments/pay_123

curl -H "X-API-Key: $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/treasury/balances
```

### 6) Withdraw

```bash
curl -X POST https://api.sardis.sh/api/v2/treasury/withdraw \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "financial_account_token":"fa_issuing_123",
    "external_bank_account_token":"eba_123",
    "amount_minor":10000,
    "method":"ACH_NEXT_DAY",
    "sec_code":"CCD",
    "memo":"Vendor payout"
  }'
```

## Operational Checks

1. ACH event sequence matches `docs/design-partner/ach-state-machine.md`.
2. `treasury_balance_snapshots` updates after payment events.
3. Return codes are handled:
   - R01/R09 retry eligible.
   - R02/R03/R29 auto-pause external account.

## Rollback

1. Disable treasury route:
   - Set `SARDIS_TREASURY_DEFAULT_ROUTE=stablecoin_first` only if stablecoin route is fully configured.
2. Pause external accounts that show repeated returns.
3. Keep webhook ingestion enabled for reconciliation even during rollback.
