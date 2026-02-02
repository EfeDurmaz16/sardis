# Lithic Production Onboarding Checklist

> Checklist for migrating Sardis virtual card infrastructure from Lithic sandbox to production.

---

## 1. Current State Assessment

### What is already integrated (sandbox)

The `sardis-cards` package (`packages/sardis-cards/`) contains a complete Lithic sandbox integration:

- **Provider:** `LithicProvider` in `packages/sardis-cards/src/sardis_cards/providers/lithic.py`
- **Base class:** `CardProvider` abstract interface in `providers/base.py`
- **Models:** `Card`, `CardTransaction`, `CardType`, `CardStatus`, `FundingSource`, `TransactionStatus` in `models.py`
- **Webhooks:** `CardWebhookHandler` and `AutoConversionWebhookHandler` in `webhooks.py`
- **API routes:** `/api/v2/cards/*` endpoints in `packages/sardis-api/src/sardis_api/routers/cards.py`

### Lithic SDK endpoints currently used

| Lithic API Call | Sardis Method | Purpose |
|---|---|---|
| `client.cards.create()` | `LithicProvider.create_card()` | Issue virtual cards (SINGLE_USE, UNLOCKED, MERCHANT_LOCKED) |
| `client.cards.retrieve()` | `LithicProvider.get_card()` | Fetch card details |
| `client.cards.update()` | `activate_card`, `freeze_card`, `unfreeze_card`, `cancel_card`, `update_limits`, `fund_card` | State and limit changes |
| `client.transactions.list()` | `LithicProvider.list_transactions()` | List card transactions |
| `client.transactions.retrieve()` | `LithicProvider.get_transaction()` | Get single transaction |
| `client.transactions.simulate_authorization()` | `LithicProvider.simulate_authorization()` | Sandbox-only test authorizations |
| `client.balance.list()` | `LithicProvider.get_account_balance()` | Account balance for reconciliation |

### Current card creation and transaction flow

1. API receives `POST /cards` with wallet_id, card_type, limits
2. `LithicProvider.create_card()` calls Lithic to issue a virtual card
3. Card is mapped from Lithic model to Sardis `Card` dataclass
4. Spending limits are set via `spend_limit` (cents) on the Lithic side
5. Webhooks (HMAC-SHA256 verified) handle transaction events
6. `AutoConversionWebhookHandler` triggers USDC-to-USD conversion on authorization events

### Known gaps

- **API routes use in-memory store** (`_cards_store` dict) instead of the Lithic provider -- the `cards.py` router sets `provider="internal"` with a TODO comment `# Use "lithic" when Lithic is integrated`
- **Webhook endpoint** (`POST /cards/webhooks`) is a stub -- no signature verification or event processing
- **Funding flow** (stablecoin off-ramp to Lithic funding account) is documented in `fund_card()` docstring but not fully wired
- **No database persistence** for card records

---

## 2. KYB (Know Your Business) Requirements

### Documents to prepare

- [ ] Certificate of Incorporation or equivalent
- [ ] EIN / Tax Identification Number
- [ ] Articles of Organization / Operating Agreement
- [ ] Proof of business address (utility bill or bank statement)
- [ ] Company website URL (sardis.sh)

### Beneficial ownership information

- [ ] Full legal name, date of birth, SSN/ITIN for each 25%+ owner
- [ ] Government-issued ID (passport or driver's license) for each owner
- [ ] Address for each beneficial owner
- [ ] Control person designation (CEO, CFO, or equivalent)

### Business information for Lithic application

- [ ] Estimated monthly transaction volume (number of transactions)
- [ ] Estimated monthly transaction dollar volume
- [ ] Average transaction size
- [ ] Maximum single transaction amount
- [ ] Use case description:
  > Sardis issues virtual cards to AI agent wallets. Agents use cards for programmatic purchases (SaaS subscriptions, cloud infrastructure, API services). Cards are funded from stablecoin off-ramps. All transactions are governed by natural language spending policies enforced before authorization.
- [ ] Target customer profile (businesses deploying AI agents)
- [ ] Geographic distribution of cardholders (US initially)

### Lithic program type

- [ ] Decide between **Issuing Program** (you are the program manager) vs. **Embedded Finance** (Lithic manages compliance)
- [ ] Confirm card network: Visa or Mastercard
- [ ] Confirm card product: Virtual only (no physical cards initially)

---

## 3. Technical Migration (Sandbox to Production)

### API key rotation

- [ ] Generate production API key from Lithic dashboard
- [ ] Store production key in secret manager (not `.env` files)
- [ ] Update `LITHIC_API_KEY` in production environment
- [ ] Set `LITHIC_ENVIRONMENT=production` (currently defaults to `"sandbox"`)
- [ ] Verify `LithicProvider.__init__()` reads the environment variable correctly
- [ ] Rotate and revoke old sandbox key after migration

### Webhook endpoint updates

- [ ] Register production webhook URL with Lithic (`https://api.sardis.sh/v2/cards/webhooks`)
- [ ] Obtain production webhook signing secret from Lithic
- [ ] Store signing secret in secret manager as `LITHIC_WEBHOOK_SECRET`
- [ ] **Wire up the webhook endpoint** -- current `POST /cards/webhooks` is a stub that does not verify signatures or process events
- [ ] Integrate `CardWebhookHandler.verify_and_parse()` into the webhook route
- [ ] Connect `AutoConversionWebhookHandler` for real-time stablecoin conversion triggers
- [ ] Implement idempotency (the handler has `_processed_events` in-memory; move to Redis/database for production)

### Base URL changes

- [ ] Lithic SDK handles this automatically via the `environment` parameter -- verify `lithic.Lithic(environment="production")` uses `https://api.lithic.com` instead of `https://sandbox.lithic.com`

### Card program configuration

- [ ] Set up card program in Lithic production dashboard
- [ ] Configure funding source / funding account
- [ ] Set program-level spending controls (max daily, max monthly)
- [ ] Configure allowed MCC codes if restricting merchant categories
- [ ] Set up authorization rules (real-time decisioning endpoint if needed)

### Spending controls configuration

- [ ] Map Sardis three-tier limits (`limit_per_tx`, `limit_daily`, `limit_monthly`) to Lithic's `spend_limit` and `spend_limit_duration`
- [ ] Current code only uses `TRANSACTION` duration for `spend_limit` -- add `MONTHLY` and `ANNUALLY` limits
- [ ] Implement Sardis-side enforcement for per-transaction limits (the `Card.can_authorize()` method exists but is not called from the provider)

### Database persistence

- [ ] Replace in-memory `_cards_store` dict in `cards.py` router with database-backed storage
- [ ] Add cards table to PostgreSQL (migration already partially exists in `003_ledger_compliance_tables.sql`)
- [ ] Store `provider_card_id` (Lithic token) for lookups
- [ ] Store card-to-wallet mapping for webhook processing

### Wire Lithic provider into API routes

- [ ] Replace `provider="internal"` in `cards.py` router with actual `LithicProvider` instantiation
- [ ] Route API calls through `LithicProvider` methods instead of creating cards in-memory
- [ ] Remove `simulate_authorization()` usage path from production code (sandbox only)

---

## 4. Compliance Requirements

### PCI DSS considerations

- [ ] Sardis never stores full card numbers (PANs) -- verify this remains true
- [ ] Card number last 4 digits only stored in `card_number_last4` field -- compliant
- [ ] Lithic handles PCI scope for card issuance and number storage
- [ ] If exposing card details to frontend: use Lithic's secure iframe / tokenized card display
- [ ] Document PCI responsibility matrix with Lithic
- [ ] Complete Lithic's PCI SAQ (Self-Assessment Questionnaire) if required

### Cardholder data handling

- [ ] No CVV/CVC storage anywhere in Sardis -- verify
- [ ] Card expiry stored (expiry_month, expiry_year) -- acceptable per PCI
- [ ] API responses never return full card numbers
- [ ] Logs do not contain card numbers or sensitive cardholder data
- [ ] Webhook payloads stored without sensitive card details

### Transaction monitoring

- [ ] Set up alerts for unusual transaction patterns
- [ ] Monitor for velocity anomalies (many transactions in short period)
- [ ] Flag transactions above configured thresholds
- [ ] Integrate with `sardis-ledger` for append-only audit trail
- [ ] Dashboard visibility into card transactions (current `Transactions.tsx` page)

### Chargeback procedures

- [ ] Define chargeback handling process with Lithic
- [ ] Set up chargeback webhook event handling (`dispute.created`, `dispute.updated`)
- [ ] Implement chargeback notification to wallet owner / agent operator
- [ ] Document evidence submission process
- [ ] Set aside chargeback reserve if required by Lithic

---

## 5. Testing Checklist (Pre-Production)

Run all tests against the production Lithic environment with low-value transactions before going live.

### Core operations

- [ ] Card creation works (SINGLE_USE type)
- [ ] Card creation works (UNLOCKED / MULTI_USE type)
- [ ] Card creation works (MERCHANT_LOCKED type)
- [ ] Card activation flow works (PENDING_ACTIVATION -> OPEN)
- [ ] Card retrieval returns correct details

### Transaction flow

- [ ] Authorization flow works (real card charge against test merchant)
- [ ] Transaction settlement works (authorization clears)
- [ ] Spending limits enforced (transaction above limit is declined)
- [ ] Per-transaction limit enforced
- [ ] Daily limit enforced
- [ ] Declined transaction returns proper error

### Card lifecycle

- [ ] Card freeze works (state changes to PAUSED)
- [ ] Frozen card declines transactions
- [ ] Card unfreeze works (state changes back to OPEN)
- [ ] Card cancellation works (state changes to CLOSED)
- [ ] Cancelled card cannot be reactivated

### Webhooks

- [ ] Webhook delivery works (events received at endpoint)
- [ ] Webhook signature verification passes with production secret
- [ ] `transaction.created` event parsed correctly
- [ ] `transaction.updated` event parsed correctly
- [ ] `transaction.voided` event parsed correctly
- [ ] `card.created` event parsed correctly
- [ ] Auto-conversion triggered on authorization webhook
- [ ] Duplicate webhook events are handled idempotently

### Funding and reconciliation

- [ ] Card funding updates spend limit correctly
- [ ] Account balance retrieval works
- [ ] Transaction amounts reconcile with Sardis ledger
- [ ] Off-ramp flow (USDC -> fiat -> Lithic funding account) works end-to-end

### Error handling

- [ ] Invalid card token returns proper error
- [ ] Expired card handled gracefully
- [ ] Network timeout handled with retry
- [ ] Lithic API rate limit handled (429 responses)
- [ ] Partial failure in batch operations handled

### E2E test suite

- [ ] `tests/e2e/test_cards_fiat_flow.py` passes against production
- [ ] All `TestVirtualCardOperations` tests pass
- [ ] All `TestCardFiatIntegration` tests pass

---

## 6. Go-Live Steps

### Pre-launch (T-3 days)

1. [ ] Complete KYB approval with Lithic (see section 2)
2. [ ] Receive production API keys and webhook secrets
3. [ ] Deploy database migration for cards table
4. [ ] Deploy updated `cards.py` router with `LithicProvider` integration
5. [ ] Deploy webhook endpoint with signature verification
6. [ ] Configure production environment variables in secret manager

### Staging validation (T-1 day)

7. [ ] Run full test suite against staging with production Lithic keys
8. [ ] Verify webhook delivery in staging
9. [ ] Issue a test card and make a small real transaction
10. [ ] Verify transaction appears in Sardis ledger
11. [ ] Verify auto-conversion webhook triggers correctly

### Production activation (T-0)

12. [ ] Enable production card issuance (feature flag or config toggle)
13. [ ] Issue first production card with low limits ($10 per-tx, $50 daily)
14. [ ] Verify card creation in Lithic dashboard
15. [ ] Make a small test transaction ($1-5)
16. [ ] Verify webhook received and processed
17. [ ] Verify ledger entry created
18. [ ] Gradually increase limits for production users

### Monitoring setup

19. [ ] Set up alerting for webhook delivery failures
20. [ ] Set up alerting for high decline rates
21. [ ] Set up alerting for Lithic API errors (5xx responses)
22. [ ] Monitor card creation success rate
23. [ ] Dashboard card analytics visible in `dashboard/`
24. [ ] Set up daily reconciliation job (Sardis ledger vs. Lithic transactions)

### Rollback plan

If critical issues are discovered after go-live:

1. **Freeze all active cards** via `LithicProvider.freeze_card()` for each issued card
2. **Disable card issuance** via feature flag / environment variable
3. **Switch API routes back** to internal/mock provider if needed
4. **Preserve webhook endpoint** to continue receiving events for already-issued cards
5. **Investigate and fix** before re-enabling
6. Cards can be unfrozen once the issue is resolved

---

## 7. Timeline Estimate

| Phase | Duration | Notes |
|---|---|---|
| KYB application submission | 1 day | Gather documents and submit |
| KYB review and approval | 1-4 weeks | Lithic reviews business, may request additional info |
| Production API key issuance | 1-2 days | After KYB approval |
| Technical migration | 3-5 days | Wire provider into routes, deploy webhook handler, database migration |
| Pre-production testing | 2-3 days | Full test suite against production Lithic |
| Staged rollout | 1 week | Start with internal/test users, gradually expand |
| **Total estimated timeline** | **3-7 weeks** | KYB approval is the primary blocker |

### Dependencies and blockers

| Dependency | Status | Blocker? |
|---|---|---|
| KYB approval from Lithic | Not started | Yes -- gates all production access |
| Database cards table migration | Migration file exists (`003_ledger_compliance_tables.sql`) | Partial -- needs verification |
| Wire `LithicProvider` into API routes | Not done -- routes use in-memory store | Yes -- required for production |
| Webhook endpoint implementation | Stub only | Yes -- required for transaction monitoring |
| Stablecoin off-ramp to Lithic funding | Documented in code but not wired | Yes -- required for card funding |
| PCI SAQ completion | Not started | Maybe -- depends on Lithic program type |
| Chargeback process documentation | Not started | No -- can be done post-launch with low volume |

---

## References

- Lithic API docs: https://docs.lithic.com
- Lithic dashboard: https://app.lithic.com
- Sardis cards package: `packages/sardis-cards/`
- Sardis cards API router: `packages/sardis-api/src/sardis_api/routers/cards.py`
- E2E card tests: `tests/e2e/test_cards_fiat_flow.py`
