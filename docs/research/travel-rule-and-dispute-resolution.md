# Research: Travel Rule Compliance & On-Chain Dispute Resolution

**Date:** 2026-03-11
**Author:** Research for Sardis Payment OS

---

## Part 1: Travel Rule Compliance (FATF)

### Regulatory Context

The FATF Travel Rule (Recommendation 16) requires VASPs to share originator/beneficiary information for crypto transfers above certain thresholds:
- **US:** $3,000 (FinCEN) — $1,000 proposed
- **EU:** €0 (all transfers, TFR effective Dec 2024)
- **UK:** All transfers (effective Sep 2023)
- **FATF revision:** Agreed June 2025, taking effect by end of 2030

As of January 2026, **73% of countries** have made the Travel Rule law. 100% of surveyed VASPs plan to be compliant. VASPs blocking withdrawals until beneficiary info is confirmed jumped 431% YoY (2.9% → 15.4%).

**Sardis implication:** As a VASP handling USDC stablecoin transfers, Sardis must comply. The stablecoin leg triggers virtual asset Travel Rule requirements, while any fiat leg triggers ISO 20022 payment transparency requirements. Both require originator and beneficiary data.

---

### Solution A: TRISA (Travel Rule Information Sharing Architecture)

**What it does:** Open-source, decentralized P2P protocol for VASPs to exchange originator/beneficiary data (IVMS101 standard). Non-profit 501(c)(6) governance. Interoperable with TRP (OpenVASP successor) since November 2023.

**GitHub:**
- [`trisacrypto/trisa`](https://github.com/trisacrypto/trisa) — 47 stars, Go, MIT License
- [`trisacrypto/envoy`](https://github.com/trisacrypto/envoy) — 12 stars, Go, MIT License (self-hosted node)
- [`trisacrypto/directory`](https://github.com/trisacrypto/directory) — Global VASP Directory Service

**How it works:**
1. VASP registers with TRISA's Global Directory Service (GDS) and obtains mTLS certificates
2. Run an Envoy node (self-hosted or managed) that handles P2P encrypted data exchange
3. When a transfer triggers the threshold, originator VASP looks up beneficiary VASP in the directory
4. Secure IVMS101 data exchange happens peer-to-peer via mTLS
5. Both VASPs validate and store the compliance data

**Production-readiness:** Yes — production-ready with MainNet certificates available. Envoy node is the official deployment tool with Kubernetes and systemd deployment guides.

**Integration options:**
| Option | Timeline | Cost |
|--------|----------|------|
| Self-hosted (DIY) | 4-6 weeks | Free (MIT license) + infra costs |
| One-time integration service | 2-3 weeks | One-time fee (contact TRISA) |
| Managed service | 1-2 weeks | Ongoing fee (contact TRISA) |

**Sardis integration path:**
- Deploy an Envoy node alongside the Sardis API (Docker/Kubernetes)
- Integrate via Envoy's webhook API — when a transfer hits threshold, POST to Envoy with originator/beneficiary IVMS101 data
- Envoy handles counterparty lookup, data exchange, and compliance response
- Register Sardis as a VASP in the GDS
- ~4-6 weeks for self-hosted, Go codebase aligns with ops but webhooks mean Python integration is straightforward

**Verdict:** Best open-source option. Free, production-ready, interoperable with TRP. The Envoy node abstracts away protocol complexity.

---

### Solution B: TRP (Travel Rule Protocol) — OpenVASP Successor

**What it does:** Fully decentralized, permissionless peer-to-peer Travel Rule messaging protocol. Successor to the original OpenVASP protocol. Maintained by the OpenVASP Association.

**GitHub:**
- [`OpenVASP/openvasp-contracts`](https://github.com/OpenVASP/openvasp-contracts) — 5 stars, JavaScript, MIT License
- [`Notabene-id/openvasp-node-client`](https://github.com/Notabene-id/openvasp-node-client) — TypeScript client
- Original OpenVASP protocol is **discontinued**, replaced by TRP

**How it works:**
1. No centralized server — all data transfers happen P2P
2. Uses LNURL-like discovery mechanism for VASP endpoints
3. Supports IVMS101 and ISO 24165 (2,800+ digital assets)
4. No registration or membership fees required
5. Interoperable with TRISA since November 2023

**Production-readiness:** Yes, production-ready. Adopted by many VASPs via Notabene's platform.

**Cost:** Free protocol, but most VASPs access it through commercial platforms (Notabene, 21 Analytics) rather than raw protocol implementation.

**Sardis integration path:**
- Most practically accessed through Notabene or 21 Analytics (see commercial solutions below)
- Raw protocol implementation is possible but underdocumented compared to TRISA Envoy
- Since TRISA and TRP are interoperable, implementing TRISA gives you TRP reach too

**Verdict:** Good protocol, but better accessed through TRISA Envoy (interoperable) or a commercial provider like Notabene.

---

### Solution C: Notabene (Commercial — Market Leader)

**What it does:** End-to-end Travel Rule compliance SaaS platform. Trusted by 200+ companies including Copper, Luno, Crypto.com, Bitstamp. Partners with Chainalysis for KYT.

**How it works:**
1. REST and GraphQL APIs + JavaScript SDK
2. Automated counterparty VASP identification
3. Multi-protocol support (TRP, TRISA, TRUST, Sygna Bridge, etc.)
4. Built-in sanctions screening, risk scoring, and policy engine
5. Dashboard for compliance officers to manage data transfer requests

**Key features:**
- Counterparty VASP auto-identification
- Self-hosted wallet detection (critical for Sardis — agents may use self-hosted wallets)
- Automated threshold-based triggering
- Multi-jurisdictional rule configuration
- Real-time decision-making engine

**Production-readiness:** Yes — market-leading, most widely deployed.

**Pricing:**
- **Sunrise Plan (free):** Basic compliance, 10-minute setup, low volume
- **Paid tiers:** Usage-based, contact sales for pricing
- Estimated: $500-2,000/month for startup volumes (based on industry benchmarks)

**Sardis integration path:**
- Fastest integration: REST API call on every qualifying transfer
- When `sardis-chain` executor processes a USDC transfer above threshold:
  1. POST to Notabene API with originator data
  2. Notabene identifies counterparty VASP
  3. Notabene handles IVMS101 data exchange across protocols
  4. Receive compliance status via webhook
- Integration time: ~1-2 weeks
- Handles self-hosted wallet flows (important for agent wallets)

**Verdict:** Best commercial option. Fast integration, multi-protocol, handles edge cases. Worth the cost for production launch. Start with free Sunrise plan.

---

### Solution D: Sygna Bridge (Commercial — Asia Focus)

**What it does:** Travel Rule data exchange solution by CoolBitX, strong in Japan and Taiwan markets. Suite includes Bridge (protocol), Hub (AML platform), and Gate (browser-based AML).

**How it works:**
1. API-based proprietary protocol with IVMS101 support
2. Alliance network of trusted VASPs with signature-verified messages
3. PII shared through encrypted tunnels
4. Supports 3,000+ virtual assets

**Production-readiness:** Yes — widely deployed in Asia-Pacific.

**Pricing:** Commercial, contact sales. Integrated with Sumsub.

**Sardis integration path:**
- API integration similar to Notabene
- Most relevant if Sardis needs strong Asia-Pacific VASP coverage
- Can be accessed through Sumsub's unified Travel Rule solution

**Verdict:** Good for Asia-Pacific coverage, but Notabene has broader global reach. Consider as secondary protocol.

---

### Solution E: 21 Analytics (Commercial — Swiss)

**What it does:** Swiss-based Travel Rule compliance software. Flat-fee pricing, integrates with Chainalysis for risk scoring.

**Pricing:**
- **Flat fee** regardless of volume
- Zero onboarding fees
- Unlimited VASP-to-VASP and VASP-to-self-hosted wallet transactions
- Unlimited users
- Transparent, no hidden costs

**Production-readiness:** Yes — deployed, currently on version 7.3.

**Sardis integration path:** API integration, similar pattern to Notabene.

**Verdict:** Attractive flat-fee model for predictable costs. Good alternative to Notabene if volume-based pricing becomes expensive.

---

### Solution F: Sumsub Travel Rule (Commercial — Bundled with KYC)

**What it does:** Travel Rule solution bundled with Sumsub's KYC/AML platform. Connected to 1,800+ VASPs across GTR, TRP, CODE, Sygna, and Sumsub protocols.

**How it works:**
- Part of Transaction Monitoring solution
- Multi-level risk evaluation for counterparties
- Auto-detects VASP-to-VASP payments
- Sanctions, PEP, and adverse media screening included

**Sardis integration path:**
- Since Sardis already considered iDenfy for KYC, Sumsub would be a separate vendor
- However, if Sardis switches to Sumsub for KYC, the bundled Travel Rule is attractive
- Broadest protocol coverage among commercial providers

**Verdict:** Best if bundling with KYC. Otherwise, Notabene is more focused.

---

### Solution G: pacs.crypto (Emerging — ISO 20022 Bridge)

**What it does:** Open specification bridging ISO 20022 standards (pacs.008) to crypto asset payments. Built for FATF Travel Rule compliance with structured remittance information.

**GitHub:** [`tomalaerts-dev/pacs.crypto`](https://github.com/tomalaerts-dev/pacs.crypto) — 1 star, HTML, CC0-1.0 License

**Production-readiness:** No — very early stage, specification draft only.

**Verdict:** Interesting concept for bridging TradFi and crypto compliance, but too nascent for production use. Worth watching.

---

### Travel Rule Recommendation for Sardis

**Immediate (MVP launch):**
1. **Notabene Sunrise Plan (free)** — fastest integration, multi-protocol, handles self-hosted wallets
2. Implement threshold detection in `sardis-chain` executor (check transfer amount against jurisdiction thresholds)
3. Collect originator data from Sardis agent wallets (already have KYC via iDenfy)
4. ~1-2 weeks integration

**Medium-term (scale):**
1. Evaluate switching to **TRISA Envoy (self-hosted)** to reduce per-transaction costs
2. Or upgrade to **21 Analytics** for flat-fee predictability
3. Both give TRISA + TRP interoperability

**Key architectural decision:** Add a `TravelRuleProvider` abstract interface in `sardis-compliance` package, similar to existing provider abstractions. This allows swapping Notabene for TRISA Envoy later without touching business logic.

---

## Part 2: On-Chain Dispute Resolution

### Context

Sardis has Circle's RefundProtocol for basic refunds (Apache 2.0, audited). The question is whether full dispute resolution (chargebacks, service disputes, fraudulent transactions) needs an on-chain arbitration layer.

---

### Protocol A: Kleros (Decentralized Justice Platform)

**What it does:** Open-source decentralized arbitration protocol using blockchain, crowdsourced jurors, and game theory. The most widely used on-chain dispute resolution platform. First to be recognized by a national court (Mexico, 2025).

**GitHub:**
- [`kleros/kleros`](https://github.com/kleros/kleros) — 259 stars, Solidity, MIT License (v1)
- [`kleros/kleros-v2`](https://github.com/kleros/kleros-v2) — 80 stars, TypeScript, MIT License (v2, on Arbitrum)
- [`kleros/escrow-contracts`](https://github.com/kleros/escrow-contracts) — 10 stars, JavaScript, MIT License
- [`kleros/erc-792`](https://github.com/kleros/erc-792) — Arbitration Standard

**How it works:**
1. Funds locked in escrow smart contract (supports ETH + ERC20 tokens including USDC)
2. Either party can raise a dispute by paying an arbitration fee
3. Random jurors drawn from staked PNK token holders, weighted by stake
4. Jurors review evidence and vote (Schelling point mechanism — jurors incentivized to vote with majority)
5. Losing jurors get tokens slashed; winning jurors earn fees
6. Appeals possible (fee increases exponentially per round)
7. Smart contract enforces the ruling automatically

**Stablecoin (USDC) support:** Yes — ERC20 Escrow Dapp supports any ERC20 token with the ERC20 badge. USDC is supported. Deployed on Ethereum mainnet: `0xc25a0b9681abf6f090aed71a8c08fb564b41dab6`.

**V2 improvements:**
- Deployed on **Arbitrum** (lower gas costs)
- Supports stablecoin fee payments (not just native tokens)
- Cross-chain message relaying
- Currently in community testing on Arbitrum Sepolia

**Integration complexity:**
- Smart contract integration: implement `IArbitrable` interface (ERC-792)
- Your escrow contract calls `createDispute()` on Kleros Arbitrator
- Kleros calls `rule()` on your contract with the verdict
- ~2-4 weeks for contract integration + testing
- [Integration docs](https://docs.kleros.io/integrations/types-of-integrations/1.-dispute-resolution-integration-plan/smart-contract-integration)

**Production-proven:** Yes — operational since March 2019, hundreds of disputes resolved, recognized by Mexican court.

**Cost model:**
- Arbitration fee: variable by court/subcourt, typically 0.05-0.5 ETH equivalent
- Fee paid by dispute initiator, reimbursed to winner
- No platform subscription — purely per-dispute fees
- Appeals increase fee exponentially (discourages frivolous appeals)

**Sardis integration path:**
1. Modify `SardisEscrow.sol` to implement `IArbitrable` interface
2. When a payment dispute arises, either party calls `raiseDispute()` on the escrow
3. Escrow locks funds and creates dispute on Kleros Arbitrator (Arbitrum deployment)
4. Kleros jurors review evidence (transaction metadata, AP2 mandate chain, policy logs)
5. Ruling auto-executed: funds go to winner
6. Sardis Ledger records dispute outcome
7. Cross-chain: if escrow is on Base and Kleros on Arbitrum, use Kleros v2 cross-chain messaging

**Verdict:** Best option for Sardis. Production-proven, MIT licensed, supports USDC, ERC-792 standard is well-documented. V2 on Arbitrum keeps gas costs low.

---

### Protocol B: UMA Optimistic Oracle

**What it does:** Optimistic oracle that assumes data/assertions are true unless disputed. Used by Polymarket for prediction market resolution. Dispute resolution via Data Verification Mechanism (DVM) with UMA token holder voting.

**GitHub:**
- [`UMAprotocol/protocol`](https://github.com/UMAprotocol/protocol) — 458 stars, JavaScript, AGPL-3.0

**How it works:**
1. An assertion is made (e.g., "Merchant delivered the goods")
2. A bond is posted with the assertion
3. Challenge period (configurable, typically 2 hours to 7 days)
4. If no dispute: assertion accepted, bond returned
5. If disputed: escalates to DVM where UMA token holders vote (48-96 hour voting period)
6. Incorrect asserters/disputers lose their bonds

**Stablecoin support:** Yes — bonds can be in USDC or other ERC20 tokens. Deployed on multiple chains.

**Production-proven:** Yes — >98% of proposals go undisputed. Powers Polymarket (billions in volume). Operational since 2020.

**Integration complexity:**
- Integrate with Optimistic Oracle V3 contract
- Define assertion schema for payment disputes
- Configure challenge period and bond amount
- ~2-3 weeks for smart contract integration
- More complex than Kleros for payment disputes (designed for data assertions, not adversarial disputes)

**Cost model:**
- Bond amount: configurable (e.g., 1,000 USDC)
- No dispute = bond returned, gas costs only
- Dispute = loser forfeits bond + DVM voting gas
- No subscription fees

**Sardis integration path:**
1. On payment completion, merchant or agent can assert "service delivered satisfactorily"
2. If payer disagrees, they dispute during challenge period by posting counter-bond
3. If disputed, UMA DVM resolves via token holder vote
4. Escrow releases funds based on outcome

**Limitations for Sardis:**
- Designed for data assertions, not naturally suited for "who's right in this payment dispute"
- Dispute resolution relies on UMA token holders, not domain-specific jurors
- AGPL-3.0 license requires derivative works to be open-source
- Less intuitive for payment disputes compared to Kleros's escrow-native model

**Verdict:** Powerful but better suited for oracle/data disputes. The optimistic model works well if most transactions are honest (which they should be). Consider for high-value, low-dispute-rate scenarios. AGPL license is a concern.

---

### Protocol C: Aragon Court

**What it does:** Subjective dispute resolution protocol for DAOs, using guardian (juror) staking and voting.

**GitHub:**
- [`aragon/aragon-court`](https://github.com/aragon/aragon-court) — 110 stars, JavaScript, GPL-3.0

**How it works:**
1. Guardians stake ANT tokens to participate
2. Drafted randomly for disputes, weighted by stake
3. Vote on outcomes; minority voters get slashed
4. Appeals possible with increasing guardian count

**Production-proven:** V1 deployed and audited, but **Aragon as an organization has been in turmoil** (legal disputes with community, treasury controversies in 2023-2024). Current operational status is uncertain.

**Stablecoin support:** Primarily ETH/ANT denominated. ERC20 support not well documented for escrow.

**Integration complexity:** Medium — similar to Kleros but less documentation and ecosystem support.

**Verdict:** Not recommended. Organizational instability, less production usage than Kleros, GPL license. Kleros is strictly better for Sardis's use case.

---

### Protocol D: agent-court-rs (Emerging — Agent-Specific)

**What it does:** x402 reverse proxy with on-chain dispute resolution, designed specifically for AI agent API payments.

**GitHub:** [`karans4/agent-court-rs`](https://github.com/karans4/agent-court-rs) — 0 stars, Rust, No License

**Production-readiness:** No — brand new (March 2026), no stars, no license.

**Verdict:** Interesting concept directly aligned with Sardis's agent economy thesis, but too nascent. Worth watching and potentially contributing to.

---

### Protocol E: Simple Escrow Contracts (No Arbitration)

**Notable repo:** [`pcaversaccio/escrow-contract`](https://github.com/pcaversaccio/escrow-contract) — 43 stars, TypeScript, WTFPL License

**What it does:** Multilateral escrow for ETH and ERC-20 tokens with a single trusted governor (Cobie-style). No decentralized arbitration — relies on a trusted third party.

**Sardis relevance:** Sardis already has Circle's RefundProtocol which is more sophisticated. Not useful as a standalone solution, but the contract patterns are clean reference implementations.

**Verdict:** Not needed — Circle RefundProtocol covers this use case.

---

### Dispute Resolution Recommendation for Sardis

**Phase 1 — Current (MVP):**
- Continue using **Circle RefundProtocol** for simple refunds
- Most agent-to-merchant transactions won't need dispute resolution
- Sardis's spending policies and AP2 mandate chain verification prevent most disputes at the source

**Phase 2 — Post-Launch:**
1. Integrate **Kleros v2** (Arbitrum) for full dispute resolution:
   - Implement `IArbitrable` on `SardisEscrow.sol`
   - Define a Sardis-specific subcourt with appropriate juror requirements
   - USDC escrow with Kleros arbitration for disputed payments
   - ~2-4 weeks smart contract work
   - MIT license, production-proven, USDC-native

2. Consider **UMA Optimistic Oracle** as a secondary layer for:
   - High-value transfers where you want an optimistic "no news is good news" window
   - Automated dispute prevention (most honest transactions auto-settle)
   - Be mindful of AGPL-3.0 license implications

**Key architectural decision:** Add a `DisputeResolutionProvider` interface in `sardis-protocol` or `sardis-chain`:
```python
class DisputeResolutionProvider(ABC):
    async def create_dispute(self, escrow_id: str, evidence: dict) -> DisputeId
    async def get_dispute_status(self, dispute_id: DisputeId) -> DisputeStatus
    async def submit_evidence(self, dispute_id: DisputeId, evidence: dict) -> None
```

This allows starting with Circle RefundProtocol and upgrading to Kleros without business logic changes.

---

## Summary Comparison Tables

### Travel Rule Solutions

| Solution | Type | Cost | Integration Time | Protocol Coverage | Best For |
|----------|------|------|-----------------|-------------------|----------|
| **TRISA Envoy** | Open Source (MIT) | Free + infra | 4-6 weeks | TRISA + TRP | Cost-conscious, self-hosted |
| **TRP (OpenVASP)** | Open Protocol | Free | Complex | TRP | Via TRISA or commercial |
| **Notabene** | Commercial | Free tier → usage-based | 1-2 weeks | All major protocols | Fast launch, best coverage |
| **Sygna Bridge** | Commercial | Contact sales | 1-2 weeks | Sygna + partners | Asia-Pacific focus |
| **21 Analytics** | Commercial | Flat fee | 1-2 weeks | Multiple | Predictable costs |
| **Sumsub** | Commercial | Contact sales | 1-2 weeks | 5+ protocols | Bundled with KYC |

### Dispute Resolution Protocols

| Protocol | Stars | License | Chains | USDC Support | Dispute Cost | Maturity |
|----------|-------|---------|--------|--------------|--------------|----------|
| **Kleros v2** | 80 (v2) / 259 (v1) | MIT | Arbitrum (v2), Ethereum/Gnosis (v1) | Yes (ERC20) | ~0.05-0.5 ETH equiv | Production (since 2019) |
| **UMA Oracle** | 458 | AGPL-3.0 | Ethereum, Arbitrum, Polygon, others | Yes (bonds) | Bond-based | Production (since 2020) |
| **Aragon Court** | 110 | GPL-3.0 | Ethereum | Limited | ANT-based | Uncertain status |
| **Circle RefundProtocol** | N/A (audited) | Apache 2.0 | EVM chains | Yes (native) | Gas only | Production |

---

## Sources

### Travel Rule
- [TRISA Homepage](https://trisa.io/)
- [TRISA Developer Docs](https://trisa.dev/)
- [TRISA Envoy GitHub](https://github.com/trisacrypto/envoy)
- [OpenVASP Association](https://www.openvasp.org/)
- [Notabene Travel Rule Compliance](https://notabene.id/travel-rule-compliance)
- [Notabene Pricing](https://notabene.id/pricing)
- [Notabene Developer Portal](https://devx.notabene.id/)
- [Sygna Bridge](https://www.sygna.io/bridge/)
- [21 Analytics](https://www.21analytics.co/)
- [21 Analytics Pricing](https://www.21analytics.co/pricing/)
- [Sumsub Travel Rule](https://sumsub.com/travel-rule/)
- [Chainalysis + Notabene Partnership](https://www.chainalysis.com/blog/chainalysis-notabene-travel-rule-integration/)
- [Crypto Travel Rule Guide 2026](https://www.innreg.com/blog/crypto-travel-rule-guide)
- [FATF Crypto Guidance 2026](https://midlandsinbusiness.com/fatf-crypto-guidance-travel-rule-vasp-rules-and-aml-compliance-in)
- [Travel Rule Cross-Border Payments 2026 (Tazapay)](https://tazapay.com/blog/travel-rule-cross-border-payments-2026)
- [Stablecoin Regulation 2026 (BVNK)](https://bvnk.com/blog/global-stablecoin-regulations-2026)
- [Global Crypto Regulations 2026 (Sumsub)](https://sumsub.com/blog/global-crypto-regulations/)

### Dispute Resolution
- [Kleros Homepage](https://kleros.io/)
- [Kleros Escrow](https://kleros.io/escrow/)
- [Kleros Escrow Docs](https://docs.kleros.io/products/escrow)
- [Kleros v2 Integration Guide](https://blog.kleros.io/court-v2-integration-sneak-peek/)
- [Kleros Smart Contract Integration](https://docs.kleros.io/integrations/types-of-integrations/1.-dispute-resolution-integration-plan/smart-contract-integration)
- [Kleros ERC20 Escrow](https://blog.kleros.io/make-erc20-escrow-payments-with-kleros/)
- [UMA Documentation](https://docs.uma.xyz/)
- [UMA Optimistic Oracle](https://docs.uma.xyz/protocol-overview/how-does-umas-oracle-work)
- [UMA Quick Start](https://docs.uma.xyz/developers/optimistic-oracle/getting-started)
- [Aragon Court Docs](https://legacy-docs.aragon.org/products/aragon-court/aragon-court)
- [Decentralized Justice Comparison (Frontiers)](https://www.frontiersin.org/articles/10.3389/fbloc.2021.564551/full)
- [Blockchain Dispute Resolution (MDPI)](https://www.mdpi.com/2073-4336/14/3/34)
