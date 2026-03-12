# Open-Source KYC / KYB / KYA / AML Landscape Research

**Date:** 2026-03-11
**Purpose:** Evaluate open-source alternatives to paid compliance services (Persona, iDenfy, Elliptic, Chainalysis) for Sardis

---

## Executive Summary

The open-source compliance tooling landscape has matured significantly. There are now credible, production-grade open-source options for **sanctions screening** (Moov Watchman, OpenSanctions), **transaction monitoring / AML** (Marble, Jube), and **KYC/KYB orchestration** (Ballerine). Document OCR is well-served by docTR and face recognition by InsightFace/DeepFace. The emerging **KYA (Know Your Agent)** category is nascent but relevant to Sardis's core thesis — AgentFacts and ERC-8004 are the leading open specifications. No single open-source project replaces a full-stack KYC vendor end-to-end, but a composable stack is viable.

---

## 1. KYC (Know Your Customer)

### Ballerine — **TOP PICK for KYC/KYB Orchestration**
| Field | Value |
|-------|-------|
| Repo | [ballerine-io/ballerine](https://github.com/ballerine-io/ballerine) |
| Stars | **2,359** |
| Language | TypeScript |
| License | Apache 2.0 (open core — some enterprise features proprietary) |
| YC Backed | Yes (W23) |

**What it does:** Open-source risk decisioning infrastructure — KYC, KYB, onboarding, transaction monitoring, and fraud prevention orchestration. NOT a verification provider itself, but an orchestrator that plugs into any provider (iDenfy, Veriff, AWS Rekognition, Google Vision, etc.).

**Key features:**
- Workflow engine (BPMN-like) for multi-step verification flows
- Back-office case management dashboard (manual review)
- Plugin system for 3rd-party vendor integration (vendor-agnostic)
- Rule engine for risk scoring
- LLM-based OCR plugin for document extraction
- White-label embeddable UI components
- Self-hosted or SaaS

**Could replace:** The orchestration layer that Persona or iDenfy provides (routing, workflow, case management). You still need underlying verification providers, but can use cheaper ones (AWS Rekognition at ~$1/1000 faces vs. Persona's $2+/verification).

**Build vs Buy:** **Use Ballerine as orchestration layer + cheap ML providers.** This is the best open-source approach to reducing per-verification cost below iDenfy's $0.55.

---

### OpenKYC (FaceOnLive)
| Field | Value |
|-------|-------|
| Repo | [FaceOnLive/ID-Verification-OpenKYC](https://github.com/FaceOnLive/ID-Verification-OpenKYC) |
| Stars | **424** |
| Language | JavaScript (UI) + Python (backend) |
| License | Unlicensed (community project, uses FaceOnLive APIs) |

**What it does:** End-to-end identity verification flow — face recognition, liveness detection (anti-spoofing), and ID document recognition. Claims 10,000+ ID types from 200+ countries.

**Key features:**
- Face liveness (depth detection, anti-spoofing)
- ID-to-selfie matching (99.9% accuracy claimed)
- Document OCR & authentication
- Open-source UI flow

**Caveat:** The UI is open source but it depends on FaceOnLive's proprietary API SDKs for the actual ML inference. Not truly self-hostable without their backend. More of a "freemium SDK demo" than a full open-source solution.

**Build vs Buy:** **Not viable as a standalone replacement.** Useful as UI inspiration but core ML is proprietary.

---

## 2. KYB (Know Your Business)

### Ballerine (same as above)
Ballerine is the only credible open-source option for KYB flows. It supports:
- Business registration document collection
- UBO (Ultimate Beneficial Owner) verification workflows
- Multi-step merchant onboarding
- Risk scoring with configurable rules
- Integration with business data providers (Companies House, OpenCorporates, etc.)

No other open-source project provides meaningful KYB capabilities. The KYB space is dominated by commercial vendors (Middesk, Persona for Business, Veriff).

---

## 3. KYA (Know Your Agent) — **Sardis-relevant emerging category**

### AgentFacts
| Field | Value |
|-------|-------|
| Repo | [agentfacts/agentfacts-py](https://github.com/agentfacts/agentfacts-py) |
| Stars | New (< 100) |
| Language | Python |
| License | Open source |

**What it does:** Universal KYA standard — a 10-category metadata framework for AI agent identity verification. Creates signed, verifiable JSON "agent cards" capturing identity, base model, tools, policy, and provenance.

**Key features:**
- Tamper-evident JSON identity cards
- Cryptographic multi-authority verification
- Works with OpenAI, Anthropic, LangChain, CrewAI, AutoGen
- Generator for standardized agent metadata

**Relevance to Sardis:** Directly aligned with Sardis's "Know Your Agent" concept. Could be integrated as the identity layer for agent wallets.

### ERC-8004: Trustless Agents (Ethereum Standard)
| Field | Value |
|-------|-------|
| Spec | [EIP-8004](https://eips.ethereum.org/EIPS/eip-8004) |
| Status | Deployed to mainnet |
| Implementations | [Phala TEE agent](https://github.com/Phala-Network/erc-8004-tee-agent), [0xgasless agent-sdk](https://github.com/0xgasless/agent-sdk) |

**What it does:** On-chain registries for AI agent identity, reputation, and validation. Extends A2A Protocol with a trust layer.

**Key features:**
- Identity Registry (ERC-721 based, on-chain handles)
- Reputation Registry (on-chain scoring)
- Validation Registry (proof of agent capabilities)
- Censorship-resistant agent identifiers

**Relevance to Sardis:** This is the on-chain KYA standard. Sardis could adopt ERC-8004 for agent wallet identity, giving agents verifiable on-chain identities that map to their spending policies.

### MCP-I (Model Context Protocol — Identity)
Built on Anthropic's open-source MCP. Establishes standards for agent identity and delegation. Directly compatible with Sardis's MCP server.

**Build vs Buy:** **Build on top of AgentFacts + ERC-8004.** This is Sardis's moat territory — no commercial vendor owns KYA yet. Being early here is strategic.

---

## 4. AML / Sanctions Screening

### Moov Watchman — **TOP PICK for Sanctions Screening**
| Field | Value |
|-------|-------|
| Repo | [moov-io/watchman](https://github.com/moov-io/watchman) |
| Stars | **439** |
| Language | Go |
| License | **Apache 2.0** (fully permissive) |
| Production Use | Yes, multiple companies |

**What it does:** HTTP API and Go library for searching against global sanctions and watchlists. Downloads, parses, normalizes, and indexes lists in-memory. No external database needed.

**Supported lists:**
- US OFAC (SDN, SSI, etc.)
- US Consolidated Screening List (BIS, DPL, etc.)
- UN Consolidated Sanctions List
- EU Consolidated Sanctions List
- UK Sanctions List
- OpenSanctions datasets (320+ sources, PEPs)

**Key features:**
- Jaro-Winkler distance scoring (matches OFAC's own methodology)
- In-memory indexing, concurrent searches
- Auto-refresh of government lists
- Docker images (moov/watchman on Docker Hub)
- No external dependencies (no DB, no Elasticsearch)
- REST API on :8084 with zero config

**Could replace:** Elliptic's sanctions screening for named entities. Does NOT do blockchain address/transaction screening (that's a different problem).

**Build vs Buy:** **Deploy Watchman immediately.** Apache 2.0, production-proven, zero cost, trivial Docker deployment. This directly replaces the sanctions-list-screening portion of Elliptic.

---

### OpenSanctions + Yente API
| Field | Value |
|-------|-------|
| Repo | [opensanctions/opensanctions](https://github.com/opensanctions/opensanctions) |
| Stars | **688** |
| Language | Python |
| License | MIT (code), **commercial license required for data in commercial use** |
| API Repo | [opensanctions/yente](https://github.com/opensanctions/yente) — 125 stars |

**What it does:** The most comprehensive open database of international sanctions data, PEPs, and persons of interest. 320+ data sources, 330+ global sources integrated.

**Key features:**
- Yente: self-hosted screening API (Docker, ElasticSearch backend)
- Bulk matching and entity search
- Reconciliation API spec compatible
- FollowTheMoney data model (used by investigative journalists)
- PEP (Politically Exposed Persons) database
- Fuzzy name matching

**Pricing:**
- **Non-commercial:** Free
- **Commercial self-hosted:** Free software, paid data license required (contact for pricing)
- **Hosted SaaS API:** EUR 0.10/call, volume discounts above 20K req/mo

**Could replace:** Elliptic's PEP/sanctions screening. Better data coverage than Watchman alone (OpenSanctions integrates into Watchman as a data source).

**Build vs Buy:** **Use as a data source feeding into Watchman, or deploy Yente separately.** The data license cost is the main consideration for commercial use. Watchman already has native OpenSanctions integration.

---

## 5. Transaction Monitoring / Fraud Detection

### Marble (CheckMarble) — **TOP PICK for Transaction Monitoring**
| Field | Value |
|-------|-------|
| Repo | [checkmarble/marble](https://github.com/checkmarble/marble) |
| Stars | **475** |
| Language | Go (backend), React (frontend) |
| License | Open core (core is open source, enterprise features licensed) |
| Positioning | "Open-source alternative to Feedzai, SEON, SumSub" |

**What it does:** Real-time decision engine for fraud and AML. Transaction monitoring, AML screening, and case investigation.

**Key features:**
- Real-time or post-trade transaction monitoring
- Custom data model (mirrors your data warehouse)
- Customer & company screening against sanctions/PEP/adverse media lists
- Unified case manager for alert investigation
- AI automation for rule building and investigation
- Embedded analytics / BI
- Audit trail (searchable, unalterable)
- RBAC, SSO (OIDC), IP whitelisting
- SOC 2 Type II (cloud version)
- Self-hosted or SaaS deployment

**Pricing:**
- **Self-hosted (open source core):** Free
- **Licensed (advanced features):** Contact for pricing
- **Cloud SaaS:** "Surprisingly cheaper than market leaders" per their site

**Could replace:** The transaction monitoring component of Elliptic/Chainalysis (for fiat-side monitoring). Combined with Watchman for sanctions, this covers most AML needs.

**Build vs Buy:** **Strong candidate for production use.** The Go backend is fast, the data model is flexible, and it integrates with any core banking/payment system. Self-host the open-source core, upgrade to licensed if you need advanced features.

---

### Jube
| Field | Value |
|-------|-------|
| Repo | [jube-home/aml-fraud-transaction-monitoring](https://github.com/jube-home/aml-fraud-transaction-monitoring) |
| Stars | **58** |
| Language | C# (.NET) |
| License | **AGPL-3.0** |

**What it does:** Full AML and fraud detection platform with ML for real-time transaction monitoring.

**Key features:**
- Real-time transaction monitoring engine
- Adaptive ML (supervised + unsupervised, neural network topology search)
- Rule engine (thresholds, velocity, aggregation, sanctions screening)
- Case management with escalation and audit trails
- Behavioral feature abstraction (volume, velocity, geolocation)
- Docker/Kubernetes deployment, multi-tenancy

**Caveat:** AGPL license means any modifications must be open-sourced. C# stack is a poor fit for Sardis's Python/Go ecosystem. Lower community adoption (58 stars).

**Build vs Buy:** **Skip for Sardis.** Marble is a better fit (Go, more stars, better ecosystem fit, more permissive license).

---

### IBM AMLSim
| Field | Value |
|-------|-------|
| Repo | [IBM/AMLSim](https://github.com/IBM/AMLSim) |
| Stars | **348** |
| Language | Python |
| License | Apache 2.0 |

**What it does:** Synthetic banking transaction data generator with known money laundering patterns. NOT a detection system — a simulator for testing ML models.

**Useful for:** Training and testing your own AML models, generating test data. Not a production monitoring tool.

---

## 6. Document Verification / OCR

### docTR (Mindee) — **TOP PICK for Document OCR**
| Field | Value |
|-------|-------|
| Repo | [mindee/doctr](https://github.com/mindee/doctr) |
| Stars | **5,951** |
| Language | Python |
| License | **Apache 2.0** |

**What it does:** High-performance OCR library using deep learning. Two-stage pipeline: text detection (localizing words) then text recognition (identifying characters).

**Key features:**
- End-to-end document OCR
- QR code, barcode, ID picture, logo recognition
- PyTorch and TensorFlow backends
- Fast inference with GPU acceleration
- OnnxTR wrapper available (no PyTorch/TF dependency, lighter)
- Active maintenance (v0.9.0+)

**Could replace:** The document OCR component of Persona/iDenfy. Combined with a face matching model, covers most ID document verification.

**Build vs Buy:** **Excellent building block.** Use docTR for document text extraction, combine with InsightFace for face matching, and Ballerine for orchestration. Total cost: infrastructure only.

---

### InsightFace — **TOP PICK for Face Recognition**
| Field | Value |
|-------|-------|
| Repo | [deepinsight/insightface](https://github.com/deepinsight/insightface) |
| Stars | **28,054** |
| Language | Python |
| License | MIT (partially — check model-specific licenses) |

**What it does:** State-of-the-art 2D and 3D face analysis — detection (RetinaFace), recognition (ArcFace), alignment, and verification.

**Key features:**
- RetinaFace detection + ArcFace recognition (industry standard)
- 2D and 3D face analysis
- GPU-optimized, production-grade throughput
- Face anti-spoofing capabilities
- PyTorch and MXNet backends

**Could replace:** The face matching/liveness component of Persona/iDenfy.

---

### DeepFace
| Field | Value |
|-------|-------|
| Repo | [serengil/deepface](https://github.com/serengil/deepface) |
| Stars | **22,358** |
| Language | Python |
| License | **MIT** |

**What it does:** Lightweight face recognition and analysis library wrapping multiple backends (VGG-Face, FaceNet, OpenFace, DeepID, ArcFace, Dlib, SFace).

**Key features:**
- Face verification, recognition, analysis (age, gender, race, emotion)
- Multiple model backends
- Easy API (one-line calls)
- Lower throughput than InsightFace for production

**Build vs Buy:** **Use InsightFace for production, DeepFace for prototyping.** InsightFace has better GPU parallelism and throughput.

---

## 7. Recommended Stack for Sardis

### Replace iDenfy ($0.55/verification) with:

| Layer | Tool | License | Cost |
|-------|------|---------|------|
| Orchestration | **Ballerine** | Apache 2.0 | Free (self-hosted) |
| Document OCR | **docTR** | Apache 2.0 | Infra only |
| Face Recognition | **InsightFace** | MIT | Infra only |
| Liveness Detection | InsightFace anti-spoofing + custom | MIT | Infra only |
| Fallback/Complex Cases | iDenfy API | Commercial | $0.55/case |

**Estimated cost:** ~$0.01-0.05/verification (compute) vs. $0.55 with iDenfy. Use iDenfy as fallback for edge cases or regulatory-required certified verification.

### Replace Elliptic (sanctions/AML) with:

| Layer | Tool | License | Cost |
|-------|------|---------|------|
| Sanctions Screening | **Moov Watchman** | Apache 2.0 | Free |
| Data Enrichment | **OpenSanctions** | MIT + data license | Data license fee |
| Transaction Monitoring | **Marble** | Open core | Free (self-hosted core) |
| Blockchain Address Screening | **Keep Elliptic** | Commercial | Per-query pricing |

**Note:** Watchman + OpenSanctions covers named-entity sanctions screening. For **blockchain address screening** (wallet risk scoring, taint analysis), there is NO viable open-source alternative to Elliptic/Chainalysis. This remains a "buy" decision.

### KYA (new — build as moat):

| Layer | Tool | License | Cost |
|-------|------|---------|------|
| Agent Identity Standard | **AgentFacts** | Open source | Free |
| On-chain Agent Registry | **ERC-8004** | Open standard | Gas costs |
| MCP Integration | **MCP-I** | Open source | Free |

---

## 8. Summary Matrix

| Category | Best OSS Option | Stars | License | Can Replace Paid? | Effort |
|----------|----------------|-------|---------|-------------------|--------|
| **KYC Orchestration** | Ballerine | 2,359 | Apache 2.0 | Partially (still need ML providers) | Medium |
| **KYB** | Ballerine | 2,359 | Apache 2.0 | Partially | Medium |
| **KYA** | AgentFacts + ERC-8004 | New | Open | N/A (no commercial yet) | Low-Medium |
| **Sanctions Screening** | Moov Watchman | 439 | Apache 2.0 | **Yes** (replaces named-entity screening) | **Low** |
| **Sanctions Data** | OpenSanctions | 688 | MIT + data license | Partially (data license for commercial) | Low |
| **Transaction Monitoring** | Marble | 475 | Open core | **Yes** (fiat-side AML) | Medium |
| **Document OCR** | docTR | 5,951 | Apache 2.0 | **Yes** | Low |
| **Face Recognition** | InsightFace | 28,054 | MIT | **Yes** | Low-Medium |
| **Face Liveness** | InsightFace | 28,054 | MIT | Partially | Medium |
| **Blockchain Address Risk** | None | — | — | **No** (keep Elliptic) | N/A |

---

## Sources

- [Ballerine GitHub](https://github.com/ballerine-io/ballerine)
- [Moov Watchman GitHub](https://github.com/moov-io/watchman)
- [OpenSanctions](https://www.opensanctions.org/)
- [OpenSanctions Yente API](https://github.com/opensanctions/yente)
- [Marble / CheckMarble GitHub](https://github.com/checkmarble/marble)
- [Jube GitHub](https://github.com/jube-home/aml-fraud-transaction-monitoring)
- [docTR GitHub](https://github.com/mindee/doctr)
- [InsightFace GitHub](https://github.com/deepinsight/insightface)
- [DeepFace GitHub](https://github.com/serengil/deepface)
- [AgentFacts](https://agentfacts.org/)
- [AgentFacts Python SDK](https://github.com/agentfacts/agentfacts-py)
- [ERC-8004 Spec](https://eips.ethereum.org/EIPS/eip-8004)
- [FaceOnLive OpenKYC](https://github.com/FaceOnLive/ID-Verification-OpenKYC)
- [IBM AMLSim](https://github.com/IBM/AMLSim)
- [Marble Pricing](https://www.checkmarble.com/pricing)
- [OpenSanctions Licensing](https://www.opensanctions.org/licensing/)
- [Jube Website](https://jube.io/)
