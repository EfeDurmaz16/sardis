# Issuer Funding Decision Matrix (2026-02-24)

## Scope

This note answers three questions for Sardis:

1. What does "Stripe-compatible funding" actually mean?
2. Do we need Stripe Treasury now, or can we ship without it?
3. Should we prioritize a stablecoin-native issuer (Rain/Bridge) for cleaner dual-rail design?

Date context: validated against provider docs/public pages on **February 24, 2026**.

## What "Stripe-compatible funding" means

For Stripe Issuing, cards spend from an **Issuing balance**. Funding options today:

1. **Push funding**: Stripe gives bank account/routing details for your Issuing balance; you send ACH/wire from your bank.
2. **Pull funding (US-only)**: initiate pull from a verified external US bank account into Stripe balance.

This means "Stripe-compatible funding" = getting USD into the Issuing balance in a compliant way, not sending stablecoins directly to a card ledger.

## Do we need Treasury right now?

Short answer: **No, not for initial Issuing go-live**.

You can start with Issuing balance top-ups (push/pull funding) and ship cards.

Treasury becomes important when you need:

1. Programmatic money movement with Financial Accounts.
2. Per-customer account architecture (connected account + treasury + issuing capabilities).
3. Bank-like operations and deeper account-level controls.

## "Per customer account" model in Stripe (what it really implies)

If each enterprise customer should have isolated card funding and controls:

1. Create a **Connect account** per customer entity.
2. Request capabilities (`transfers`, `card_issuing`, and when needed `treasury`).
3. Create financial account/cardholder/cards under that connected account.

This is valid, but integration/compliance complexity is materially higher than pooled funding.

## Can we do: fiat -> Coinbase on-ramp -> Stripe card?

Possible in architecture terms, but not as a native direct stablecoin funding lane for Issuing in general availability:

1. Stripe card rails still need Issuing/Stripe balance funding.
2. Stripe stablecoin products today are mostly:
   - stablecoin **payments** settling into USD,
   - stablecoin **payouts** (Connect private preview),
   - stablecoin-backed cards in Financial Accounts (private preview).

So the pragmatic version is:

1. Keep Stripe card balance funded in USD.
2. Use Coinbase/CDP side for on-chain spend + optional treasury conversion workflows.
3. Move to native stablecoin-backed card model only if your Stripe account is approved for preview programs.

## Stablecoin-native issuer alternatives

### Bridge

Bridge appears most explicit technically for cards right now:

1. Cards API documents **three funding strategies**: Bridge Wallet, Non-Custodial direct pull, Card Wallet.
2. Supports stablecoin card spend with custodial or non-custodial wallet models.
3. Good fit for Sardis dual-rail goals if access is approved.

### Rain

Rain positioning is strong for stablecoin card programs, but public docs are less API-granular than Bridge docs:

1. Public materials emphasize stablecoin-native issuing and Visa acceptance.
2. Claims support for multiple chains/assets and configurable flow of funds.
3. Program launch and economics are partner/onboarding-driven.

## Recommended path for Sardis

1. **Now (ship path)**: Keep Stripe Issuing as USD-funded secondary issuer and complete provider routing.
2. **Now+ (parallel)**: Continue Rain/Bridge onboarding; prepare adapter contracts and readiness checks.
3. **Decision gate**: If Bridge or Rain production access lands first with acceptable terms, promote stablecoin-native issuer for eligible corridors while retaining Stripe/Lithic fallback.
4. **Treasury timing**: Add full Treasury/connected-account model only when customer-level isolation and bank-like workflows justify the added complexity.

## Decision matrix (high level)

| Option | Time to ship | Complexity | Stablecoin nativeness | Funding clarity |
|---|---:|---:|---:|---:|
| Stripe Issuing (USD funded, no Treasury) | Fast | Low-Med | Low | High |
| Stripe Issuing + Connect + Treasury | Medium-Slow | High | Low-Med (preview dependent) | High |
| Bridge Cards | Medium (access dependent) | Med | High | High |
| Rain Cards | Medium (access dependent) | Med | High | Medium |

## Sources

- Stripe Issuing balance funding: https://docs.stripe.com/issuing/funding/balance
- Stripe Financial Accounts overview (funding methods/timelines): https://docs.stripe.com/financial-accounts
- Stripe Treasury inbound transfers: https://docs.stripe.com/treasury/moving-money/financial-accounts/into/inbound-transfers
- Stripe Issuing + Connect setup: https://docs.stripe.com/issuing/connect
- Stripe Treasury connected accounts: https://docs.stripe.com/treasury/account-management/connected-accounts
- Stripe stablecoin payments: https://docs.stripe.com/payments/stablecoin-payments
- Stripe stablecoin payouts (private preview): https://docs.stripe.com/crypto/stablecoin-payouts
- Stripe stablecoins in Financial Accounts (private preview card support): https://docs.stripe.com/financial-accounts/stablecoins
- Bridge Cards product page: https://www.bridge.xyz/product/cards
- Bridge Cards API funding strategies: https://apidocs.bridge.xyz/platform/cards/overview/funding-strategies
- Bridge non-custodial card funding: https://apidocs.bridge.xyz/platform/cards/overview/noncustodial
- Rain cards page (flow/funding claims): https://www.rain.xyz/cards
- Rain money-in page: https://www.rain.xyz/money-in
- Rain legal/service posture: https://www.rain.xyz/get-started
