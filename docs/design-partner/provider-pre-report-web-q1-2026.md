# Provider Pre-Report (Web Research)

Date: February 26, 2026  
Scope: Stripe, Lithic, Rain, Bridge for Sardis card + funding stack (pre-call brief)

## TL;DR

- **Best near-term control plane fit:** Stripe + Lithic (mature auth controls, webhook surfaces, known issuing patterns).
- **Best stablecoin-native direction:** Rain + Bridge appear strongest on public positioning, but exact API/compliance boundary must be validated in partner calls.
- **PAN/PCI minimization path:** prioritize issuer-hosted reveal / embedded flows; keep Sardis PAN lane as break-glass only.

## Provider Snapshot

| Provider | PAN / Reveal posture | Funding posture | KYC/KYB / compliance posture | Notes |
| --- | --- | --- | --- | --- |
| Stripe | Issuing Elements exists (hosted UI path) | Issuing balance top-up / treasury-linked routes documented | Strong platform compliance model; exact split by program/account setup | Strong default rail for enterprise control + hosted UX |
| Lithic | Virtual cards + auth rules/webhooks | Card/funding ops available; exact treasury model partner-dependent | Issuer-led controls and program model | Strong auth-time enforcement surface |
| Rain | Publicly positions stablecoin cards + money-in/out/accounts | Stablecoin-first positioning (on/off + accounts) | Publicly states compliance-first posture; legal pages emphasize partner institutions | Strong candidate for stablecoin-native lane if API scope matches |
| Bridge | Public docs expose cards + dedicated virtual cards + sandbox | Money-in/out and card products documented | Enterprise/API model; detailed compliance split needs call confirmation | Strong candidate for stablecoin funding adapters |

## Key Findings (with sources)

### Stripe
- Stripe documents adding funds to balance using top-ups and idempotency behavior via API headers.  
  Source: https://docs.stripe.com/topups  
- Stripe Issuing Elements provides hosted/embedded card detail UX (helps PCI scope minimization vs raw PAN handling).  
  Source: https://docs.stripe.com/issuing/elements  

### Lithic
- Lithic supports issuing cards and authorization-rule controls in public docs.  
  Source: https://docs.lithic.com/docs/issuing-cards  
  Source: https://docs.lithic.com/docs/building-card-programs-with-auth-rules

### Rain
- Rain public site positions cards + money-in + money-out + accounts and stablecoin settlement model.  
  Source: https://www.rain.xyz/cards  
  Source: https://www.rain.xyz/money-in  
  Source: https://www.rain.xyz/money-out  
  Source: https://www.rain.xyz/accounts  
- Rain legal/public messaging states it is a fintech company and payment products are provided with licensed partners.  
  Source: https://www.rain.xyz/

### Bridge
- Bridge public docs expose cards overview, dedicated virtual cards, and sandbox setup.  
  Source: https://apidocs.bridge.xyz/get-started/cards  
  Source: https://apidocs.bridge.xyz/cards/dedicated-virtual-cards  
  Source: https://apidocs.bridge.xyz/get-started/sandbox

## Open Items For 15-Min Calls

1. PAN model: hosted/embedded reveal options, ephemeral reveal TTL, and whether raw PAN access is avoidable for our target merchants.
2. Funding mechanics: per-tenant account model, prefund windows/cutoffs, fallback rails, and webhook SLA.
3. Compliance split: KYB/KYC/KYT RACI, sanctions monitoring ownership, incident reporting obligations.
4. Auth-time controls: merchant lock, MCC lock, velocity controls, and hard response timeout guarantees.
5. Stablecoin path: direct stablecoin-backed issuing vs conversion layer; failure behavior during conversion delays.

## Current Recommendation

- Keep Sardis architecture as:
  - deterministic off-chain policy + approval + audit trail,
  - issuer-hosted/embedded reveal default,
  - PAN lane only as break-glass enclave path,
  - stablecoin fallback lane (x402/on-chain) for merchants that cannot support secure embedded card UX.

- **Inference note:** Rain and Bridge public docs/website provide high-level product signals; exact production fit (especially compliance boundary and auth-time SLA) remains **unconfirmed until partner calls**.
