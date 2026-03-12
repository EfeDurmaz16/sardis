# Fraud Detection & Compliance-as-a-Service Landscape Research

**Date:** 2026-03-11
**Purpose:** Understand how modern fraud/compliance companies work, extract techniques and architectural patterns relevant to Sardis.

---

## Table of Contents

1. [Company Profiles](#company-profiles)
   - Tier 1: Sardine, Flagright, Unit21, Alloy
   - Tier 2: Sift, Featurespace, Sumsub, Plaid Identity
   - Tier 3: Notabene (crypto-native)
2. [Common Patterns Across All Companies](#common-patterns)
3. [Merchant Risk Scoring Techniques](#merchant-risk-scoring)
4. [Open-Source Components Worth Knowing](#open-source)
5. [Agent Economy Fraud — The Frontier](#agent-economy-fraud)
6. [Sardis-Specific Recommendations](#sardis-recommendations)

---

## Company Profiles

---

### 1. Sardine.ai — AI-Native Fraud Prevention

**Founded by:** Soups Ranjan (ex-Coinbase Head of Risk) + team from PayPal, Uber
**Funding:** $145M total ($70M Series C, Feb 2025). Led by Activant, a16z, GV, Moody's, Experian.
**Customers:** 300+ enterprises in 70+ countries (FIS, Deel, GoDaddy, X).

#### Core Approach
Sardine uniquely combines **device intelligence + behavioral biometrics** into a single lightweight SDK. Most competitors separate these into two different vendor integrations. This is their primary moat.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Device Intelligence** | 4 persistent identifiers (Device ID, Device Fingerprint, Mobile User ID, Account Device ID). Survives factory resets and app reinstalls. Apple DeviceCheck integration. Detects jailbroken/rooted devices. |
| **Behavioral Biometrics** | Typing speed, mouse movements, scrolling/swiping patterns, context switching, hesitation/distraction events. "Same User Score" validates if returning user is the same person. |
| **Feature Engineering** | 4,000+ expert-engineered fraud features evaluated in real-time. |
| **ML Models** | Trained on billions of sessions. Sub-100ms latency. Identity fraud, payment fraud, counterparty risk, money laundering models. |
| **Network Graph** | Visual exploration of suspicious connections between users and devices. |
| **Sonar Consortium** | Formerly SardineX. 20+ members (Visa, Blockchain.com, Alloy Labs). Universal identifier (UID) for every entity — shares anonymized risk scores, device fingerprints, behavioral biometrics, blocklists. Operates under GLBA and PATRIOT Act 314(b). |
| **AI Agents** | Finley (ops copilot), Max (chargeback disputes), Marley (merchant risk), Ruby (SAR filing), Customer Support Agent. |
| **RDP/Emulator Detection** | Only device+behavior platform that detects all remote screen-sharing applications. |

#### Pricing
- Enterprise custom pricing. Median buyer pays ~$140K/year (range $17K-$258K).
- Minimum monthly commit model (platform access + consumption rates).
- Component-level: ID doc verification ~$0.10-$1.50/check, biometric liveness ~$0.25-$2.00/session.

#### Open-Source Components
None. Fully proprietary. The 2.2B+ profiled device network is the moat.

#### What Sardis Can Learn
- **The SDK-first approach is key.** Sardine's single SDK captures device + behavior signals before any transaction occurs. Sardis should consider a lightweight JavaScript/mobile SDK for checkout that captures device signals.
- **Consortium data is a massive moat.** Even a small consortium of Sardis merchants sharing anonymized fraud signals would dramatically improve detection.
- **4,000 features is achievable iteratively.** Start with the top ~50 device/behavior features, expand over time.
- **AI agents for compliance ops** (SAR filing, chargeback disputes) are a product differentiator.

---

### 2. Flagright — API-First AML Compliance

**Stage:** Seed ($4.3M). Early but ambitious.
**Positioning:** "The AI operating system for financial crime compliance." Developer-friendly, API-first.

#### Core Approach
Flagright is the most developer-friendly AML platform. 6 API endpoints cover the entire compliance stack. They position as the modern alternative to legacy systems costing $50K-$250K+ annually.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Triple Risk Scoring** | KYC Risk Score (KRS), Transaction Risk Score (TRS), dynamic Customer Risk Assessment (CRA) combining both. Each factor has weighted contributions (e.g., geo mismatch = 0.2, cross-border pattern = 0.7). |
| **No-Code Rule Engine** | Compliance teams build/test custom rules without engineering. Rule simulation, shadow rules, intelligent threshold suggestions. |
| **AI Forensics (AIF)** | AI agents for automated compliance investigations. |
| **Real-Time Webhooks** | Risk level changes pushed to connected systems in real-time. |
| **Simulator** | Test threshold/weight changes against historical data before production deployment. |

#### Pricing
- Usage-based pricing (not publicly disclosed per-transaction rates).
- **Startup Program:** Free first year (up to 600K transactions), Year 2 up to 1.2M transactions.
- Enterprise: $25K-$100K/year for smaller deployments, $500K-$2M+ for large.

#### Open-Source Components
- Official SDK clients: [flagright-node](https://github.com/flagright/flagright-node), [flagright-python](https://github.com/flagright/flagright-python), [flagright-java](https://github.com/flagright/flagright-java), [flagright-go](https://github.com/flagright/flagright-go).
- API documentation at docs.flagright.com.
- No open-source core.

#### What Sardis Can Learn
- **6 API endpoints for full AML** is an elegant design constraint. Sardis should aim for similar simplicity in our compliance API surface.
- **Weighted risk scoring** is straightforward to implement. A simple weighted formula with configurable weights per risk factor is both powerful and explainable.
- **Shadow rules + simulators** before production are essential. Sardis should build backtesting into any rule engine from day one.
- **Free tier for startups** is a great GTM motion for a compliance product.

---

### 3. Unit21 — Agentic AI for Fraud & AML Operations

**Funding:** Substantial (exact undisclosed). Relaunched March 2026 as "Leader in AI Risk Infrastructure."
**Customers:** 100+ in production, including Intuit. Processes 500K+ alerts/month.

#### Core Approach
Unit21 rebuilt its platform from the ground up around **agentic AI** in 2025. AI agents run the full financial crime lifecycle: detect risk, execute investigations end-to-end, produce regulator-ready outcomes with complete audit trails.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Graph-Based Rules** | Visual rule builder. Example: alert when 4+ users share geolocation, IP, or client fingerprint. |
| **Dynamic Rules** | Complex rule engine for custom detection logic. Launch in minutes, production or shadow mode. |
| **AI Rule Recommendations** | ML analyzes alert patterns, outcomes, and context to suggest optimized rule logic. Up to 93% fewer false positives. |
| **Agentic AI Lifecycle** | Detection → Investigation → Decisioning in one system. Up to 80% faster investigation handle times. |
| **No-Code Interface** | Create, test, backtest rules without vendor assistance. |

#### Pricing
- Custom enterprise pricing (not publicly disclosed).
- Estimated to be competitive with Flagright/Sardine for mid-market.

#### Open-Source Components
None.

#### What Sardis Can Learn
- **Graph-based rules are powerful and intuitive.** "Alert when N entities share attribute X" is a pattern Sardis can implement for detecting coordinated agent fraud or mule networks.
- **AI-suggested rule optimization** is the future. Start with a manual rule engine, then layer ML to suggest improvements based on alert outcomes.
- **93% fewer false positives** is the metric that matters. False positives destroy user experience. Every rule should be measured by its false positive rate.

---

### 4. Alloy — Identity Decisioning Orchestration

**Funding:** Significant (valued at $1.55B as of 2021).
**Customers:** Major banks, credit unions, fintechs.

#### Core Approach
Alloy is not a fraud detection company — it is an **orchestration layer** that sits between your application and 200+ identity/fraud data sources. You build visual workflows that route decisions through multiple providers based on your risk tolerance.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **200+ Data Source Integrations** | KYC, KYB, watchlist monitoring, traditional + alternative credit, fraud scoring, risk scoring. Global coverage across 195 markets. |
| **Visual Workflow Builder** | No-code decisioning workflows. Route identity checks through providers in any order/configuration. |
| **Perpetual KYB/CRA** | Automatically re-run checks when business ownership/risk profile changes. Not point-in-time. |
| **Unified Identity Graph** | Single source of truth for customer identity across onboarding, login, account changes, transactions. |

#### Pricing
- Annual contracts: $120K-$500K (per-transaction + platform subscription).
- Significant contract size reflects enterprise positioning.

#### What Sardis Can Learn
- **Orchestration is the meta-pattern.** Sardis already abstracts wallet providers — the same pattern applies to compliance. Build a compliance orchestrator that can swap data sources (iDenfy, Sumsub, Elliptic, etc.) without changing application code.
- **Visual workflow builders** for compliance teams are high-value. Non-technical compliance officers need to adjust policies without engineering support.
- **Perpetual monitoring** (not just point-in-time verification) is becoming table stakes. Sardis should design KYC/KYB as continuous, not one-shot.

---

### 5. Sift — Digital Trust & Safety at Scale

**Scale:** 1T+ events/year in global data network. 70B+ monthly events.
**Customers:** Major e-commerce and fintech companies globally.

#### Core Approach
Sift's moat is the **sheer scale of its data network**. With over 1 trillion events per year, when a fraudster attacks any Sift customer, those signals automatically improve models for all customers.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Global Data Network** | 1T+ events/year. Cross-customer signal sharing. When fraud hits one customer, all benefit. |
| **ThreatClusters** | Industry-specific consortium models. Clusters companies with similar fraud patterns into cohorts. Up to 20% better detection accuracy. |
| **LSTM Neural Networks** | Deep learning with masking layers for variable-length sequences. RMSprop optimizer. Training via Airflow + PySpark. |
| **Triple Model Architecture** | Custom models (per-customer) + Global models (broad trends) + ThreatClusters (industry-specific). Combined for final score. |
| **Score API** | Returns fraud risk score (0-100) + top 20 risk signals explaining the score. |
| **Backtesting** | Built on BigQuery for workflow backtesting at scale. |

#### Pricing
- Custom enterprise quotes based on volume and modules.
- Not cost-efficient for small merchants with limited volume.

#### What Sardis Can Learn
- **Consortium/network effects are everything.** Sift's 1T events/year makes their models nearly unbeatable. Sardis should plan for network effects from the start — even with 10 merchants, shared signals help.
- **Explainable scores** (top 20 risk signals) are critical for merchant trust and regulatory compliance.
- **Industry-specific model clustering (ThreatClusters)** is brilliant. Different merchant verticals have different fraud patterns. Sardis could cluster by use case (AI agent payments vs. human checkout vs. subscription).
- **BigQuery for backtesting** is pragmatic. Use existing data infrastructure rather than building custom backtesting.

---

### 6. Featurespace — Adaptive Behavioral Analytics (ARIC)

**Acquired by Visa (2024).** Enterprise-focused. Used by major banks.

#### Core Approach
Featurespace invented **Adaptive Behavioral Analytics** — the system models what *good* behavior looks like per customer, then detects anomalies. This is fundamentally different from most fraud systems that look for known bad patterns.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Individual Behavioral Profiles** | Builds unique behavior model per customer. Detects anomalies against their personal baseline. |
| **Self-Learning Models** | Automatically update with new behavioral data. No model degradation over time. |
| **Sub-30ms Latency** | Determines anomalies in even slight behavior changes within 30 milliseconds. |
| **Link Analysis** | Detects subtle differences suggesting an account is part of a wider fraud ring. |
| **Automated Deep Behavioral Networks** | RNN-based architecture that automates feature discovery. |
| **Anomaly vs. Pattern Matching** | Models good behavior, not bad. Can detect entirely new/unknown fraud types. |

#### Pricing
- Enterprise custom. Lower setup cost than some competitors.
- Now part of Visa's product suite.

#### What Sardis Can Learn
- **Model good behavior, detect deviations.** This is the gold standard for fraud detection. For Sardis: model each agent's normal spending pattern, flag deviations.
- **Per-entity behavioral profiles** are feasible even at small scale. Each agent wallet gets a behavioral model: typical transaction amounts, timing, destination types, gas usage patterns.
- **Self-updating models** prevent drift. Critical for agent payments where behavior patterns evolve rapidly.
- **Sub-30ms latency** is the target for inline fraud checks. Sardis's pre-execution pipeline should aim for similar.

---

### 7. Sumsub — Full-Cycle Verification

**Scale:** 4,000+ clients (Bitpanda, Wirex, Bybit, Vodafone, Duolingo). 140K+ verifications/day.

#### Core Approach
Sumsub is the **all-in-one verification platform** — KYC, KYB, AML screening, fraud prevention, and transaction monitoring in a single dashboard. Optimized for conversion rate (91-98% depending on region).

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Full-Stack Verification** | ID verification, database validation, biometric authentication, address verification, non-doc verification, AML screening — all in one. |
| **KYB (6-in-1)** | Only six-in-one KYB solution. Access to 500M+ commercial records. |
| **Liveness Detection** | Anti-spoofing biometric checks. |
| **14,000+ Document Types** | Covers 220+ countries. |
| **Sub-50-Second Verification** | Average verification time under 50 seconds. |
| **Transaction Monitoring** | KYT (Know Your Transaction) modules and continuous AML monitoring. |

#### Pricing
- Starts at **$1.35/verification** with $299/month minimum.
- 14-day free trial with 50 free checks.
- Charged only for successful verifications.
- Competitive with Onfido, Jumio, Veriff.

#### What Sardis Can Learn
- **$1.35/verification is the price benchmark.** Sardis's current iDenfy choice at $0.55/verification is well-positioned.
- **Conversion rate is a key metric.** 91-98% means minimal friction. Sardis should track KYC conversion rates obsessively.
- **"Full-cycle" positioning** (onboarding + ongoing monitoring in one vendor) simplifies compliance architecture. Consider whether iDenfy can cover ongoing AML monitoring too, or if a separate vendor (Elliptic) remains necessary.

---

### 8. Plaid Identity — Bank-Verified Identity

#### Core Approach
Plaid verifies identity by **accessing information already on file at the user's bank** — name, email, phone, address. No document scanning needed. Identity proven through bank account ownership.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Bank-Derived Identity** | Pulls verified identity data from 12,000+ financial institutions. |
| **Match Scores** | Shows match scores for name, email, phone, address against bank records. |
| **7-Second Account Linking** | Minimal friction. |
| **23% Conversion Increase** | Instant verification boosts approval rates. |
| **Document Upload Fallback** | Bank statement upload with ownership verification. |

#### Pricing
- Per-API-call model (custom pricing, not publicly disclosed).

#### What Sardis Can Learn
- **Bank-verified identity is the highest-trust signal.** If a user links their bank account and the name matches, that's stronger than any ID document.
- **For fiat on-ramp flows,** Plaid identity verification could replace or augment KYC. If a user connects their bank via Coinbase Onramp, we implicitly get identity signals.
- **Match scores** (not binary pass/fail) enable risk-based decisioning.

---

### 9. Notabene — Travel Rule Compliance (Crypto-Native)

#### Core Approach
Notabene is the dominant **Travel Rule compliance** solution for VASPs. Enables VASPs to send required originator/beneficiary information alongside crypto transfers, automatically adapting to each jurisdiction's requirements.

#### Key Techniques
| Technique | Details |
|-----------|---------|
| **Jurisdiction-Aware Rules** | Automatically recognizes originator/beneficiary info requirements per jurisdiction. |
| **Counterparty VASP Management** | Identifies counterparty VASPs, manages risk profiles. |
| **Automated Risk-Based Rules** | Auto-approve/flag transactions based on VASP, jurisdiction, KYT risk score, sanction screen matches. |
| **Non-Custodial Wallet Handling** | Ownership proofs for self-hosted wallets where required. |
| **Protocol Interoperability** | Works with multiple Travel Rule messaging protocols (TRUST, OpenVASP, etc.). |

#### Pricing
- Not publicly disclosed. TRUST protocol costs ~$50K/year for VASPs.
- Custom enterprise pricing for Notabene's full solution.

#### What Sardis Can Learn
- **Travel Rule compliance is increasingly mandatory** for crypto businesses. As Sardis processes cross-border stablecoin payments, Travel Rule will apply.
- **Jurisdiction-aware automation** is essential. Rules that auto-adapt to the sending/receiving country reduce compliance burden.
- **Notabene is a potential integration partner,** not something to build. Travel Rule protocol interoperability is complex and evolving.

---

## Common Patterns Across All Companies

### 1. Multi-Layer Defense Architecture
Every company implements a layered approach:
```
Layer 1: Device Intelligence (fingerprints, emulator detection, jailbreak detection)
Layer 2: Behavioral Biometrics (typing, mouse, scroll, hesitation patterns)
Layer 3: Rule Engine (configurable, no-code, with shadow mode and backtesting)
Layer 4: ML Models (supervised + unsupervised, ensemble methods)
Layer 5: Graph/Network Analysis (link analysis, fraud ring detection)
Layer 6: Consortium/Network Data (shared signals across customers)
Layer 7: Case Management (investigation workflows, AI-assisted)
```

### 2. Real-Time is Non-Negotiable
- Sardine: <100ms
- Featurespace: <30ms
- Flagright: Sub-second
- All modern systems score transactions in real-time, not batch.

### 3. No-Code Rule Engines Are Table Stakes
Every platform offers non-technical compliance teams the ability to create, test, and deploy rules without engineering help. Features include:
- Shadow mode (run rules without acting on results)
- Backtesting against historical data
- Simulation of threshold changes
- Rule versioning and audit trails

### 4. Consortium Data Is the Ultimate Moat
- Sardine: Sonar consortium (20+ members, anonymized fraud signals)
- Sift: 1T+ events/year global network
- Alloy: 200+ data source integrations
- The companies with the largest data networks have the best models. Period.

### 5. Explainable AI Is Required
- Sift: Top 20 risk signals with every score
- Flagright: Weighted risk factors with configurable contributions
- Regulators require explainability. Black-box ML alone is insufficient.

### 6. Agentic AI Is the New Frontier
- Unit21: Rebuilt entirely around agentic AI (2025-2026)
- Sardine: 5 AI agents for different compliance tasks
- Flagright: AI Forensics agents
- Pattern: AI agents handle repetitive compliance tasks (SAR filing, chargeback disputes, merchant risk assessment).

### 7. Continuous Monitoring Replaces Point-in-Time
- Alloy: Perpetual KYB/CRA (re-run checks on business changes)
- Sumsub: Continuous AML monitoring
- One-time KYC at onboarding is no longer sufficient. Ongoing behavioral monitoring is the standard.

---

## Merchant Risk Scoring Techniques

### Risk Score Composition
Modern merchant risk scoring combines:

| Factor | Weight (typical) | Description |
|--------|-------------------|-------------|
| **Industry/MCC Code** | High | Some industries (gambling, crypto, adult) are inherently higher risk. |
| **Chargeback Ratio** | Very High | Primary indicator. >1% is a red flag. |
| **Transaction Velocity** | High | Sudden spikes in volume or value. |
| **Geographic Risk** | Medium | Transactions from/to high-risk jurisdictions. |
| **Business Age** | Medium | New merchants have less history to evaluate. |
| **PCI DSS Compliance** | Medium | Non-compliance increases breach risk. |
| **Historical Fraud Incidents** | Very High | Past behavior predicts future behavior. |
| **Credit History** | Medium | Financial stability of the merchant. |

### Velocity Metrics Tracked
- Transaction count per time window (per customer, per card, per device)
- Payment instrument velocity (same card across different merchants)
- Declined transaction velocity (multiple declines = card testing)
- Device velocity (same device, multiple accounts)
- Billing address velocity (same address, different identities)
- Email velocity (similar email patterns)
- IP address velocity (same IP, multiple transactions)

### Scoring Architecture
```
Input Signals → Feature Engineering → Ensemble Model → Risk Score (0-99)
                                          ↓
                                    [Gradient Boosting]
                                    [Neural Networks]
                                    [Anomaly Detection (Autoencoders)]
                                          ↓
                                    Weighted Average → Final Score
                                          ↓
                              Threshold Logic → Approve / Review / Block
```

### Three Attack Vectors to Score Against
1. **Identity Layer** — Stolen, synthetic, or spoofed identities.
2. **Transaction Layer** — Tampered amounts, frequencies, merchant IDs. Card testing via bots.
3. **Backend Logic Layer** — Exploiting technical/procedural weaknesses in payment logic.

---

## Open-Source Components Worth Knowing

### Production-Grade
| Project | Stars | Description | Relevance to Sardis |
|---------|-------|-------------|---------------------|
| [**Marble**](https://github.com/checkmarble/marble) | Active | Real-time decision engine for fraud/AML. Used by 100+ fintechs. Self-hosted option. Go backend. SOC 2 Type II. | **HIGH** — Could serve as Sardis's rule engine. Open-source core with enterprise licensing. |
| [**FingerprintJS**](https://github.com/fingerprintjs/fingerprintjs) | 22k+ | Browser fingerprinting library. 40-60% accuracy (client-side only). | **MEDIUM** — Free device fingerprinting for checkout SDK. Combine with server-side signals for better accuracy. |
| [**Fingerprint Pro**](https://fingerprint.com) | N/A | Commercial. 99.5% accuracy with server-side processing. $0-99/mo for low volume. | **MEDIUM** — Consider for checkout device identification. $99/mo for 20K identifications is reasonable. |

### Research & Learning
| Project | Description |
|---------|-------------|
| [**graph-fraud-detection-papers**](https://github.com/safe-graph/graph-fraud-detection-papers) | Curated list of graph/transformer-based fraud detection papers. |
| [**DGFraud**](https://github.com/safe-graph/DGFraud) | Deep graph-based toolbox for fraud detection. |
| [**fraud-detection-handbook**](https://github.com/Fraud-Detection-Handbook/fraud-detection-handbook) | Reproducible ML for credit card fraud detection — practical handbook. |
| [**jube-home/aml-fraud-transaction-monitoring**](https://github.com/jube-home/aml-fraud-transaction-monitoring) | Open-source AML + fraud detection for real-time transaction monitoring. |

### SDK Clients (for potential vendor integrations)
- Flagright: [Node](https://github.com/flagright/flagright-node), [Python](https://github.com/flagright/flagright-python), [Java](https://github.com/flagright/flagright-java), [Go](https://github.com/flagright/flagright-go)
- Sumsub: [iOS SDK](https://github.com/SumSubstance/IdensicMobileSDK-iOS-Release)

---

## Agent Economy Fraud — The Frontier

This is where Sardis has **first-mover advantage**. No existing fraud company is purpose-built for agent-to-agent or agent-to-merchant payments.

### New Threat Model for Agent Payments

| Threat | Description | Current Defenses |
|--------|-------------|------------------|
| **Prompt Injection → Payment** | Malicious prompt causes agent to make unauthorized payment. | Sardis spending policies, mandate chain verification. |
| **Agent Identity Spoofing** | Fraudulent agent impersonates legitimate one. | TAP protocol, Ed25519 attestation. |
| **Coordinated Agent Fraud** | Multiple compromised agents coordinate to fragment/launder payments. | Graph analysis, velocity limits (gap). |
| **Model Manipulation** | Agent's ML model manipulated to approve fraudulent transactions. | Policy engine (external to agent's model). |
| **Autonomous Money Laundering** | Agent automates layering stage: fragmentation, asset conversion, cross-chain routing in seconds. | Pre-execution pipeline, chain monitoring (gap). |
| **Replay Attacks** | Replay valid transaction mandates. | Mandate cache, idempotency keys. |

### "Know Your Agent" (KYA) Framework

TRM Labs and others are developing KYA alongside traditional KYC:
- **Who/what is the agent?** — Cryptographic identity, deployer attestation.
- **What is it permitted to do?** — Spending policies, allowed merchants, amount limits.
- **Who is accountable?** — Clear human principal chain.
- **Continuous behavioral monitoring** — Per-agent behavioral baselines.

**Sardis is already building most of this** through spending policies + TAP/AP2 protocol verification + AGIT (fail-closed).

### Visa TAP (Trusted Agent Protocol)

TAP is now in production pilot (hundreds of real transactions in 2025):
- Cryptographically signed HTTP messages carry agent identity + user identity + payment details.
- Every request is locked to specific merchant website + page.
- Timestamps + session IDs prevent replay.
- Payment Account References (PARs) for card-on-file transactions.
- **Sardis already implements TAP verification** — this is a competitive advantage.

---

## Sardis-Specific Recommendations

### Immediate (Next 30 Days) — Build vs. Buy Assessment

| Capability | Build vs. Buy | Recommendation |
|------------|---------------|----------------|
| **Device Fingerprinting** | Buy (free tier) | Integrate FingerprintJS open-source in checkout SDK. Upgrade to Fingerprint Pro ($99/mo) if accuracy insufficient. |
| **Behavioral Biometrics** | Build (basic) | Capture typing speed, mouse patterns, hesitation events in checkout SDK. 5-10 basic signals. Not Sardine-level, but useful. |
| **Rule Engine** | Build (simple) or Adopt (Marble) | Evaluate Marble (open-source) for self-hosted rule engine. Alternatively, build a simple weighted-score engine in Python. |
| **Transaction Risk Scoring** | Build | Weighted risk score: velocity + amount + geo + device + behavioral signals. Start with 10-20 features. |
| **KYC/KYB** | Buy (iDenfy) | Already decided. $0.55/verification is well below market ($1.35 Sumsub). |
| **AML Screening** | Buy (Elliptic) | Already integrated. Add continuous monitoring (not just point-in-time). |
| **Travel Rule** | Buy (Notabene) | Integrate when cross-border volume warrants it. Complex protocol, not worth building. |
| **Consortium Data** | Build (long-term) | Start collecting anonymized fraud signals across merchants. Even 10 merchants sharing data is valuable. Design the schema now. |
| **Graph Analysis** | Build (later) | Not needed until scale warrants it. When you see coordinated fraud, add graph-based rules. |
| **AI Compliance Agents** | Build (later) | SAR filing automation, merchant risk assessment agents. Leverage existing LLM infrastructure. |

### Architecture Recommendations

#### 1. Pre-Execution Fraud Pipeline (Enhance Existing)
Sardis already has `PreExecutionPipeline` with AGIT/KYA/FIDES hooks. Extend it:
```
Transaction Request
    → Device Signal Check (FingerprintJS visitor ID + basic behavioral signals)
    → Velocity Check (Redis-backed: per-agent, per-wallet, per-merchant windows)
    → Amount Anomaly Check (is this within 2σ of agent's normal pattern?)
    → Geo/IP Check (is the request origin consistent with agent's profile?)
    → Rule Engine Evaluation (configurable rules, shadow mode support)
    → ML Score (start simple: logistic regression on top features)
    → Spending Policy Check (existing)
    → Mandate Chain Verification (existing AP2)
    → APPROVE / REVIEW / BLOCK
```

#### 2. Merchant Risk Score for Checkout
For "Pay with Sardis" checkout, implement a merchant risk score:
```python
merchant_risk_score = (
    0.30 * chargeback_ratio_score +     # Historical chargeback rate
    0.20 * velocity_anomaly_score +      # Transaction volume spikes
    0.15 * business_age_score +          # Time since merchant onboarding
    0.15 * geographic_risk_score +       # High-risk jurisdiction flag
    0.10 * integration_quality_score +   # API error rates, webhook reliability
    0.10 * dispute_ratio_score           # Historical dispute rate
)
```
Action thresholds: 0-30 = auto-approve, 30-70 = enhanced monitoring, 70+ = manual review.

#### 3. Agent Behavioral Profiling
Implement Featurespace-inspired per-agent behavioral baselines:
- Track each agent's normal: transaction amounts, timing patterns, merchant categories, gas usage, chain preferences.
- Flag deviations beyond 2-3 standard deviations.
- Self-updating profiles (exponential moving averages).
- This is Sardis's unique differentiator — no one else profiles AI agent behavior.

#### 4. Fraud Signal Schema (For Future Consortium)
Design the anonymized fraud signal schema now, even if consortium sharing comes later:
```json
{
  "signal_id": "uuid",
  "timestamp": "iso8601",
  "entity_type": "agent|wallet|merchant|device",
  "entity_hash": "sha256_of_identifier",
  "signal_type": "fraud_confirmed|fraud_suspected|chargeback|dispute",
  "risk_score": 0-100,
  "device_fingerprint_hash": "sha256",
  "behavioral_anomaly_score": 0-100,
  "velocity_flags": ["high_frequency", "unusual_amount"],
  "outcome": "blocked|approved_fraud|approved_legitimate"
}
```

#### 5. Checkout SDK Device Signals
Add to the existing checkout embed SDK:
```javascript
// Minimum viable device intelligence for checkout
const deviceSignals = {
  // Device identification
  visitorId: fingerprintJS.getVisitorId(),

  // Basic behavioral signals
  timeToFirstInteraction: ms,
  formFillSpeed: charsPerSecond,
  mouseMovementEntropy: float,
  copyPasteDetected: boolean,

  // Environment signals
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  language: navigator.language,
  screenResolution: `${screen.width}x${screen.height}`,

  // Bot indicators
  webdriverDetected: navigator.webdriver,
  headlessIndicators: checkHeadlessBrowser(),
}
```

### Priority Ranking

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Velocity checks in PreExecutionPipeline (Redis) | 2-3 days | High — blocks most basic fraud |
| **P0** | Merchant risk score for checkout | 3-5 days | High — protects checkout product |
| **P1** | Basic device fingerprinting in checkout SDK | 1-2 days | Medium — adds a fraud signal layer |
| **P1** | Per-agent behavioral baselines | 1 week | High — unique differentiator |
| **P1** | Transaction risk scoring (weighted formula) | 3-5 days | High — unified risk score |
| **P2** | Rule engine (evaluate Marble vs. build) | 1-2 weeks | Medium — needed for compliance teams |
| **P2** | Fraud signal schema design | 2-3 days | Medium — foundation for future consortium |
| **P2** | Basic behavioral biometrics in checkout SDK | 1 week | Medium — typing/mouse patterns |
| **P3** | AI compliance agents (SAR, disputes) | 2-4 weeks | Medium — operational efficiency |
| **P3** | Graph-based fraud rules | 2-3 weeks | Low (until scale) |
| **P3** | Consortium data sharing | Ongoing | High (long-term moat) |

---

## Key Takeaways

1. **Sardis's spending policy + mandate chain verification is already ahead of most.** The pre-execution pipeline with AGIT/KYA/FIDES is a strong foundation. Extend it with device, velocity, and behavioral signals.

2. **The agent economy creates a new fraud surface that no existing vendor covers.** Sardine, Sift, and Unit21 are all designed for human users. Agent behavioral profiling is a greenfield opportunity.

3. **Start simple, iterate fast.** Flagright covers full AML with 6 API endpoints. A weighted risk score with 10-20 features beats no risk score. Marble (open-source) can bootstrap a rule engine.

4. **Consortium data is the long-term moat.** Every merchant on "Pay with Sardis" should contribute anonymized fraud signals. Design the schema now, even if sharing comes later.

5. **Buy compliance (KYC, AML screening, Travel Rule), build detection (velocity, behavioral, agent profiling).** The detection layer is where Sardis's domain expertise in agent payments creates unique value.

---

## Sources

### Sardine.ai
- [Sardine Platform](https://www.sardine.ai/platform)
- [Sardine Device Intelligence & Behavior Biometrics](https://www.sardine.ai/device-and-behavior)
- [Sonar (SardineX) Fraud Consortium](https://www.sardine.ai/blog/sardinex-fraud-data-consortium)
- [Sardine Series C Announcement](https://www.sardine.ai/blog/series-c-announcement)
- [Contrary Research: Sardine Business Breakdown](https://research.contrary.com/company/sardine)
- [Geodesic: Sardine's Unified Data Fabric](https://geodesiccap.com/insight/sardine-a-new-era-in-fraud-prevention-and-compliance/)

### Flagright
- [Flagright Homepage](https://www.flagright.com/)
- [Flagright Real-Time Risk Scoring](https://www.flagright.com/post/real-time-risk-scoring-in-aml-compliance-flagrights-approach)
- [Flagright Startup Program](https://www.flagright.com/startups)
- [Flagright Seed Funding](https://www.flagright.com/post/flagright-raises-4-3-million-in-seed-funding-to-advance-ai-native-aml-compliance-and-risk-management-solutions)

### Unit21
- [Unit21 Homepage](https://www.unit21.ai/)
- [Unit21 AI Rule Recommendations](https://www.businesswire.com/news/home/20251027904277/en/Unit21-Unveils-AI-Rule-Recommendations)
- [Unit21 Relaunch as AI Risk Infrastructure](https://www.businesswire.com/news/home/20260310768649/en/Unit21-Relaunches-as-the-Leader-in-AI-Risk-Infrastructure)

### Alloy
- [Alloy Homepage](https://www.alloy.com/)
- [Alloy Solutions](https://www.alloy.com/solutions)
- [Alloy on AWS](https://aws.amazon.com/startups/learn/alloys-global-identity-decisioning-platform-built-on-aws)
- [How to Build an Alloy-like Platform](https://ideausher.com/blog/build-alloy-like-identity-decisioning-risk-platform/)

### Sift
- [Sift Platform](https://sift.com/platform/)
- [Sift Score API](https://sift.com/solutions/sift-score-api/)
- [Sift ThreatClusters](https://www.globenewswire.com/news-release/2024/08/22/2934411/0/en/Sift-Unveils-ThreatClusters)
- [Sift Deep Learning](https://engineering.sift.com/deep-learning-fraud-detection/)
- [Sift on BigQuery](https://cloud.google.com/blog/products/data-analytics/how-sift-delivers-fraud-detection-workflow-backtesting-at-scale)

### Featurespace
- [ARIC Risk Hub](https://www.featurespace.com/aric-risk-hub)
- [Automated Deep Behavioral Networks](https://www.featurespace.com/automated-deep-behavioral-networks)
- [Featurespace on NVIDIA](https://blogs.nvidia.com/blog/featurespace-blocks-financial-fraud/)

### Sumsub
- [Sumsub Pricing](https://sumsub.com/pricing/)
- [Sumsub Full-Cycle Platform](https://sumsub.com/newsroom/sumsub-introduces-a-full-cycle-verification-platform-stirring-the-borders-of-kyc-kyb-aml-and-anti-fraud/)
- [Sumsub KYB](https://sumsub.com/blog/kyb-guide/)

### Plaid
- [Plaid Identity API](https://plaid.com/products/identity/)
- [Plaid Auth](https://plaid.com/products/auth/)
- [Plaid Identity Docs](https://plaid.com/docs/identity/)

### Notabene
- [Notabene Travel Rule Compliance](https://notabene.id/travel-rule-compliance)
- [Notabene Regulations Map](https://notabene.id/regulations)
- [State of Crypto Travel Rule 2025](https://notabene.id/state-of-crypto-travel-rule-compliance-report)

### Open Source
- [Marble — Real-time decision engine](https://github.com/checkmarble/marble)
- [FingerprintJS](https://github.com/fingerprintjs/fingerprintjs)
- [Fingerprint Pro](https://fingerprint.com/pricing/)
- [Graph Fraud Detection Papers](https://github.com/safe-graph/graph-fraud-detection-papers)
- [Fraud Detection Handbook](https://github.com/Fraud-Detection-Handbook/fraud-detection-handbook)

### Industry & Standards
- [TRM Labs: Autonomous AI Agents and Financial Crime](https://www.trmlabs.com/resources/blog/autonomous-ai-agents-and-financial-crime-risk-responsibility-and-accountability)
- [Visa Trusted Agent Protocol](https://developer.visa.com/capabilities/trusted-agent-protocol)
- [Visa TAP on GitHub](https://github.com/visa/trusted-agent-protocol)
- [DataVisor: Top 10 Fraud Platforms 2026](https://www.datavisor.com/blog/top-10-fraud-platforms-plus-evaluation-criteria-challenges-and-trends)
- [Fintech Global: Fraud Detection Rules 2026](https://fintech.global/2026/01/02/how-fraud-detection-rules-are-evolving-in-2026/)
- [McKinsey: Payments Fraud Prevention](https://www.mckinsey.com/industries/financial-services/our-insights/guardrails-for-growth-building-a-resilient-payments-system)
- [FraudNet: Merchant Risk Scoring](https://www.fraud.net/services/payment-processor-merchant-risk-scoring)
- [Visa: Future of Fraud Detection](https://corporate.visa.com/en/solutions/visa-protect/insights/fraud-detection.html)
