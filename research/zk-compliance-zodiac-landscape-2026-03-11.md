# ZK Compliance & Zodiac Ecosystem Research

**Date:** 2026-03-11
**Purpose:** Map zero-knowledge proof compliance/policy systems and Zodiac-related tools for on-chain governance and policy enforcement relevant to Sardis.

---

## 1. ZODIAC ECOSYSTEM

### 1.1 Zodiac Core Library
- **Repo:** [gnosisguild/zodiac](https://github.com/gnosisguild/zodiac)
- **Stars:** 480 | **Language:** TypeScript | **License:** LGPL-3.0
- **What it does:** A composable library of standards and interfaces for building modules, modifiers, and guards that attach to Safe Smart Accounts (or any "avatar"). Defines the module/modifier/guard pattern that the entire ecosystem builds on.
- **Status:** Production. The standard interface for the entire Gnosis Safe module ecosystem.
- **Sardis relevance:** Sardis already builds on this standard. All Zodiac modules/modifiers/guards are composable with Sardis's Safe-based agent wallets.

### 1.2 Zodiac Roles Modifier (v2) -- CRITICAL FOR SARDIS
- **Repo:** [gnosisguild/zodiac-modifier-roles](https://github.com/gnosisguild/zodiac-modifier-roles)
- **Stars:** 131 | **Language:** TypeScript/Solidity | **License:** LGPL-3.0
- **Latest release:** `zodiac-roles-sdk-v3.4.6` (2026-03-10) -- actively maintained
- **What it does:** On-chain role-based access control for Safe Smart Accounts. Allows defining granular permissions: allowed target addresses, allowed function selectors, allowed parameter values/ranges, delegate call restrictions, ETH value limits, and rate/threshold limits on how frequently a permission can be used.
- **Key capability (v2):** "Permissions as Code" -- declarative permission definitions in TypeScript that compile to on-chain role configurations. This is a paradigm shift from manual UI configuration.
- **Production usage:** Gnosis Pay uses Roles for EVERY card transaction -- enforcing stablecoin selection, daily spending limits, and authorized settlement addresses. This is the exact same use case as Sardis agent wallets.
- **Status:** Production. Battle-tested at scale by Gnosis Pay (Visa card product).
- **Sardis relevance:** Sardis already uses this (pre-deployed at `0x9646fDAD...`). Key opportunities:
  - **Upgrade to v2 Permissions-as-Code:** Define Sardis spending policies as TypeScript code that compiles to on-chain Roles permissions
  - **Rate limiting:** v2 supports rate and threshold limits natively -- could replace or supplement Sardis's Redis-based rate limiting for on-chain enforcement
  - **Gnosis Pay pattern:** Sardis can replicate the exact architecture Gnosis Pay uses for card settlement (Roles enforces settlement address + daily limits + token restrictions)

### 1.3 Zodiac Guard: Scope
- **Repo:** [gnosisguild/zodiac-guard-scope](https://github.com/gnosisguild/zodiac-guard-scope)
- **Stars:** 44 | **Language:** TypeScript | **License:** LGPL-3.0
- **What it does:** A transaction guard that limits Safe signers to calling specific function signatures on specific contracts. Unlike Roles (which gates module-initiated txs), Scope guards owner-initiated transactions.
- **Status:** Production.
- **Sardis relevance:** Could be used to restrict what the Safe owners (human supervisors) can do, not just what the agent modules can do. Useful for "supervisor guardrails" -- e.g., preventing the human owner from removing the agent's policy module.

### 1.4 Zodiac Modifier: Delay
- **Repo:** [gnosisguild/zodiac-modifier-delay](https://github.com/gnosisguild/zodiac-modifier-delay)
- **Stars:** 25 | **Language:** TypeScript | **License:** LGPL-3.0
- **What it does:** Time-delayed transaction execution. Approved addresses can queue transactions, but they only execute after a configurable delay period. During the delay, the Safe owner can veto (mark as invalid).
- **Status:** Production. Used by Gnosis Pay alongside Roles.
- **Sardis relevance:** Highly relevant for high-value agent transactions. Pattern: Agent initiates tx -> Delay module queues it -> Human supervisor has N hours to veto -> Tx executes. This is the "human-in-the-loop" pattern Sardis needs for large payments.

### 1.5 Mech (Smart Account with Programmable Ownership)
- **Repo:** [gnosisguild/mech](https://github.com/gnosisguild/mech)
- **Stars:** 41 | **Language:** TypeScript | **License:** LGPL-3.0
- **What it does:** Smart accounts where ownership can be defined by arbitrary on-chain logic -- token holdings, NFT ownership, DAO votes, etc. Essentially: "who controls this wallet" is programmable.
- **Status:** Active development. Research-to-production stage.
- **Sardis relevance:** Could be the foundation for "agent-owned wallets" where the agent's identity (TAP attestation?) defines wallet ownership, rather than a traditional EOA.

### 1.6 Enclave (Encrypted Execution Environments)
- **Repo:** [gnosisguild/enclave](https://github.com/gnosisguild/enclave)
- **Stars:** 48 | **Language:** Rust | **License:** LGPL-3.0
- **What it does:** Protocol for Encrypted Execution Environments (E3). Enables private computation on encrypted data with on-chain verification.
- **Status:** Active development.
- **Sardis relevance:** Could enable private policy evaluation -- agent spending policies are evaluated in an encrypted environment, so neither the agent nor external observers can see the policy details, only the pass/fail result.

### 1.7 Zodiac Module: Reality
- **Repo:** [gnosisguild/zodiac-module-reality](https://github.com/gnosisguild/zodiac-module-reality)
- **Stars:** 104 | **Language:** TypeScript | **License:** LGPL-3.0
- **What it does:** Uses Reality.eth (prediction market oracle) to trigger Safe transactions. Enables optimistic governance: propose a tx, if nobody disputes it within a time window, it executes.
- **Status:** Production.
- **Sardis relevance:** Could be used for dispute resolution in merchant checkout -- "this refund should be processed" is proposed, merchant has time to dispute, otherwise it auto-executes.

### 1.8 Zodiac Safe App
- **Repo:** [gnosisguild/zodiac-safe-app](https://github.com/gnosisguild/zodiac-safe-app)
- **Stars:** 30 | **Language:** TypeScript | **License:** LGPL-3.0
- **What it does:** UI for managing Zodiac modules from within the Safe web app.
- **Status:** Production.
- **Sardis relevance:** Users can manage their Sardis agent wallet modules through the standard Safe UI.

### 1.9 karpatkey DeFi Kit
- **Repo:** [karpatkey/defi-kit](https://github.com/karpatkey/defi-kit)
- **Stars:** 31 | **Language:** TypeScript | **License:** MIT
- **What it does:** Pre-built Zodiac Roles permission sets for interacting with DeFi protocols (Aave V3, Compound V3, Uniswap, etc.). Provides a TypeScript SDK and REST API for generating permissions.
- **Status:** Production. Used by karpatkey to manage DAO treasuries.
- **Sardis relevance:** Template for how Sardis should build its own "payment kit" -- pre-built Roles permissions for USDC transfers, card settlements, merchant payments, etc. The pattern of "permissions as a library" is exactly what Sardis needs.

### 1.10 Permissions Starter Kit
- **Repo:** [gnosisguild/permissions-starter-kit](https://github.com/gnosisguild/permissions-starter-kit)
- **Stars:** 9 | **Language:** TypeScript | **License:** MIT
- **What it does:** Boilerplate for building Zodiac Roles permission sets.
- **Status:** Active.
- **Sardis relevance:** Starting point for building Sardis's permission library.

### 1.11 ThirdGuard Roles Policy Audits
- **Repo:** [ThirdGuard/roles-policy-audits](https://github.com/ThirdGuard/roles-policy-audits)
- **Stars:** 0 | **License:** None
- **What it does:** Auditing framework for policy changes on Zodiac Roles Modifier.
- **Status:** Early stage.
- **Sardis relevance:** Pattern for audit trail of policy changes -- when an agent's spending policy is modified, generate an audit record.

---

## 2. ZK IDENTITY / KYC

### 2.1 Privado ID (formerly Polygon ID) -- MOST MATURE
- **Repos:**
  - [0xPolygonID/issuer-node](https://github.com/0xPolygonID/issuer-node) -- 103 stars, Go, Apache-2.0
  - [0xPolygonID/contracts](https://github.com/0xPolygonID/contracts) -- 98 stars, TypeScript, GPL-3.0
  - [0xPolygonID/js-sdk](https://github.com/0xPolygonID/js-sdk) -- 71 stars, TypeScript, Apache-2.0
- **What it does:** Full-stack ZK identity infrastructure. Users receive Verifiable Credentials from issuers, store them in a self-custodial wallet, and generate ZK proofs to selectively disclose attributes. Built on iden3 protocol (same team that created circom).
- **Key features:**
  - W3C Verifiable Credentials standard
  - On-chain ZK proof verification (EVM compatible)
  - Self-hosted issuer node (Go)
  - Dynamic credentials (revocable, updatable)
  - Cross-chain support
  - **Billions Network:** New product for mobile-first, passport-based proof of personhood (no biometrics)
  - Merged with Disco.xyz for unified identity infrastructure
  - **Transak partnership:** Reusable KYC credentials -- complete KYC once, prove it anywhere via ZK
- **Status:** Production. Most mature ZK identity stack available. Rebranded from Polygon ID to independent company.
- **Sardis relevance:** **HIGH PRIORITY.** Sardis could:
  1. Issue KYC credentials via Privado ID after iDenfy verification
  2. Agents prove KYC status via ZK proof (no PII on-chain)
  3. Smart contracts verify the ZK proof before allowing transactions
  4. Reusable: agent KYC'd once can prove compliance to any merchant
  5. The Transak partnership pattern is exactly what Sardis needs for "KYC once, pay everywhere"

### 2.2 World ID (Worldcoin) -- PROOF OF PERSONHOOD
- **Repos:**
  - [worldcoin/idkit-js](https://github.com/worldcoin/idkit-js) -- 479 stars, TypeScript, MIT
  - [worldcoin/world-id-contracts](https://github.com/worldcoin/world-id-contracts) -- 193 stars, Solidity, MIT
  - [worldcoin/semaphore-rs](https://github.com/worldcoin/semaphore-rs) -- Rust Semaphore implementation
- **What it does:** Proof of personhood via iris scan (Orb). Uses Semaphore-based ZK proofs to verify uniqueness without revealing identity. IDKit SDK makes integration straightforward.
- **Key features:**
  - Proof of uniqueness (one person = one ID)
  - ZK-based (no personal data shared)
  - JavaScript SDK for web integration
  - On-chain verification contracts
  - 12-16 million registered users by 2025
  - Partnerships: Razer (gaming), Match Group (dating), Hakuhodo (ad fraud)
- **Status:** Production. Large user base but adoption limited outside Worldcoin ecosystem.
- **Sardis relevance:** MEDIUM. Could be used as a supplementary proof-of-personhood layer -- "this agent is controlled by a unique human" -- but not sufficient for KYC/AML compliance on its own. Useful for Sybil resistance (preventing one person from creating multiple agent wallets to circumvent spending limits).

### 2.3 Semaphore -- ZK GROUP MEMBERSHIP
- **Repo:** [semaphore-protocol/semaphore](https://github.com/semaphore-protocol/semaphore)
- **Stars:** 1,047 | **Language:** TypeScript | **License:** MIT
- **What it does:** Zero-knowledge protocol for anonymous group membership proofs. Users can prove they belong to a group and send signals (votes, endorsements) without revealing which member they are. Prevents double-signaling via nullifiers.
- **Key features (v4):**
  - EdDSA-based identities (replacing Poseidon)
  - Lean Incremental Merkle Tree (optimized)
  - On-chain and off-chain groups
  - JavaScript and Rust libraries
  - Used as foundation by Worldcoin
- **Status:** Production. v4 released. Maintained by PSE (Privacy & Scaling Explorations, an Ethereum Foundation initiative).
- **Sardis relevance:** MEDIUM-HIGH. Could enable:
  - "KYC'd group" -- agents prove they belong to the set of KYC-verified users without revealing which user
  - Anonymous compliance proofs -- "I am a member of the OFAC-clean group"
  - Threshold policies -- "at least 3 of 5 approved signers approved this, but you don't know which 3"

### 2.4 zkPassport -- PASSPORT-BASED ZK IDENTITY
- **Repos:**
  - [zkpassport/circuits](https://github.com/zkpassport/circuits) -- 82 stars, Solidity, Apache-2.0
  - [zkpassport/zkpassport-packages](https://github.com/zkpassport/zkpassport-packages) -- monorepo
- **What it does:** Generates ZK proofs from passport and national ID NFC chips. Users tap their passport on their phone, the app reads the chip, and generates a ZK proof of identity attributes (nationality, age, etc.) without revealing the actual document.
- **Status:** Active development. Pre-production.
- **Sardis relevance:** MEDIUM. Future integration path for passport-based KYC without requiring a third-party KYC provider. Could reduce Sardis's iDenfy costs by enabling direct passport verification.

### 2.5 zkPass -- WEB2 DATA ORACLE
- **Repos:**
  - [zkPassOfficial/Transgate-JS-SDK](https://github.com/zkPassOfficial/Transgate-JS-SDK) -- 40 stars, TypeScript
- **What it does:** A zkTLS oracle that converts private Web2 data (bank accounts, exchange accounts, government portals) into verifiable ZK proofs. Uses VOLE-based ZK proofs with 3-party TLS to prove data from any HTTPS source without revealing it.
- **Key features:**
  - Proves data from any HTTPS website (bank balance, KYC status, credit score)
  - Millisecond proof generation (VOLEitH technology)
  - JavaScript SDK for browser integration
  - No cooperation needed from the data source
- **Status:** Production. Has a live token (ZKP).
- **Sardis relevance:** HIGH. This is potentially transformative:
  - Prove bank account ownership without sharing credentials
  - Prove KYC status from an existing exchange (Coinbase, Binance) without re-doing KYC
  - Prove accredited investor status from brokerage accounts
  - "Portable compliance" -- prove you passed AML checks elsewhere

### 2.6 iden3 (Circom + snarkjs)
- **Repos:**
  - [iden3/circom](https://github.com/iden3/circom) -- 1,632 stars, WebAssembly, GPL-3.0
  - [iden3/snarkjs](https://github.com/iden3/snarkjs) -- 2,010 stars, JavaScript, GPL-3.0
  - [iden3/contracts](https://github.com/iden3/contracts) -- Solidity smart contracts
  - [iden3/circuits](https://github.com/iden3/circuits) -- circom circuits for iden3 protocol
- **What it does:** The foundational ZK tooling layer. Circom is the circuit compiler, snarkjs is the prover/verifier. Used by Polygon ID, Worldcoin, and many others.
- **Status:** Production. Industry standard for ZK circuit development.
- **Sardis relevance:** If Sardis builds custom ZK circuits (e.g., for policy verification), circom/snarkjs is the toolchain.

---

## 3. ZK COMPLIANCE

### 3.1 Galactica Network -- zkKYC PROTOCOL
- **Repos:**
  - [Galactica-corp/galactica-monorepo](https://github.com/Galactica-corp/galactica-monorepo) -- 13 stars, TypeScript, Apache-2.0
  - [Galactica-corp/galactica](https://github.com/Galactica-corp/galactica) -- 7 stars, Go, Apache-2.0
  - [Galactica-corp/zkKYC](https://github.com/Galactica-corp/zkKYC) -- archived, moved to monorepo
- **What it does:** A Layer 1 blockchain with native zkKYC. Users complete KYC through "Guardian Nodes" and receive a zero-knowledge KYC certificate (zkKYC) stored in their Metamask Snap. Smart contracts can require zkKYC proofs before transaction execution.
- **Key features:**
  - **Proactive compliance:** ZK proof required before on-chain tx
  - **Retroactive compliance:** Encrypted notes in ZKPs enable law enforcement investigation
  - **Guardian Nodes:** Decentralized KYC providers
  - **Selective disclosure:** Verifiers choose what proof is required (age, jurisdiction, sanction status, etc.)
  - **Metamask Snap:** User-side proof generation in browser
- **Status:** Testnet. Research-to-production. Small team, low GitHub stars.
- **Sardis relevance:** MEDIUM. The zkKYC concept is relevant but Galactica is its own L1, not easily portable. However, the design patterns (Guardian Nodes, selective disclosure, investigation module) are useful reference architecture for Sardis's own ZK compliance layer.

### 3.2 ERC-3643 / T-REX -- COMPLIANT TOKEN STANDARD
- **Repo:** [TokenySolutions/T-REX](https://github.com/TokenySolutions/T-REX) -- archived
- **Stars:** 265 | **Language:** Solidity | **License:** GPL-3.0
- **What it does:** ERC-3643 is the standard for regulated token transfers. Tokens can only be transferred if both sender and receiver pass on-chain identity checks via ONCHAINID contracts. Used for security tokens, real-world assets.
- **Status:** Production. Archived repo but standard is actively used. Over $28B in tokenized assets use ERC-3643.
- **Sardis relevance:** LOW-MEDIUM. Sardis doesn't issue tokens, but the compliance-gate pattern (check identity before transfer) is the same concept applied to USDC transfers.

### 3.3 zkOrigoPlus -- COMPLIANCE API
- **Website:** [zkorigoplus.com](https://zkorigoplus.com/)
- **What it does:** Enterprise compliance API bridging banking and blockchain. Real-time OFAC SDN screening, AML/KYC logic, ISO 20022 XML generation, multi-chain wallet verification.
- **Key features:**
  - OFAC SDN list screening
  - ISO 20022 (SWIFT) message generation
  - Stateless API (no PII storage)
  - 95% cheaper than Chainalysis
  - Powered by Claude 3 Haiku for advisory
- **Status:** Production API.
- **Sardis relevance:** MEDIUM. Could supplement or replace Elliptic for sanctions screening at lower cost. The ISO 20022 capability is interesting if Sardis ever bridges to traditional banking rails.

### 3.4 Treza Labs -- PRIVACY-PRESERVING COMPLIANCE INFRA
- **Repos:**
  - [treza-labs/treza-contracts](https://github.com/treza-labs/treza-contracts)
  - [treza-labs/treza-sdk](https://github.com/treza-labs/treza-sdk)
  - [treza-labs/treza-cli](https://github.com/treza-labs/treza-cli)
- **What it does:** Privacy-preserving infrastructure for crypto and finance using ZK compliance technology. Includes enclaves, KYC proofs, and smart contracts.
- **Status:** Early stage (Feb 2026). Very new.
- **Sardis relevance:** LOW. Watch as potential partner/competitor.

### 3.5 Chainlink Compliance Standard (OCP)
- **What it does:** Onchain Compliance Protocol (OCP) -- uses Chainlink DONs (Decentralized Oracle Networks) to store and verify compliance data on-chain. Integrates with existing identity systems (GLEIF vLEI, ERC-3643). Cross-Chain Identity (CCID) framework.
- **Status:** Production. Backed by Chainlink.
- **Sardis relevance:** MEDIUM. If Sardis wants oracle-verified compliance (e.g., "Chainlink confirms this wallet is OFAC-clean"), this is the standard to integrate.

### 3.6 Sismo -- ZK ATTESTATIONS
- **Repos:** [sismo-core/sismo-protocol](https://github.com/sismo-core/sismo-protocol)
- **What it does:** ZK attestation protocol enabling users to prove attributes from web2/web3 accounts. Evolved from ZK Badges to "Sismo Connect" -- a ZK proof gateway for apps.
- **Status:** **LIKELY DEFUNCT.** Last significant activity was 2023. Repos archived or stale. No 2025-2026 updates found.
- **Sardis relevance:** LOW. Interesting design patterns but project appears inactive. The concept has been superseded by zkPass and Privado ID.

---

## 4. ZK POLICY ENFORCEMENT

### 4.1 ZK Proof-of-Compliance Hook (Uniswap v4)
- **Repo:** [tmanas06/ZK-Proof-of-Compliance-Hook](https://github.com/tmanas06/ZK-Proof-of-Compliance-Hook)
- **What it does:** A Uniswap v4 hook that restricts swaps and LP actions to users who provide a ZK compliance proof. No personal data on-chain.
- **Status:** Hackathon project / proof of concept.
- **Sardis relevance:** MEDIUM. The pattern is directly applicable: "prove compliance before executing a payment" as a smart contract hook. This is the exact model Sardis could implement.

### 4.2 CompliGuard
- **Repo:** [Compliledger/CompliGuard](https://github.com/Compliledger/CompliGuard)
- **What it does:** Privacy-preserving compliance enforcement engine using Chainlink CRE. Operationalizes GENIUS Act, CLARITY Act, and sanctions-aligned controls.
- **Status:** Early stage (March 2026).
- **Sardis relevance:** LOW. Reference implementation for US regulatory compliance patterns.

---

## 5. STRATEGIC RECOMMENDATIONS FOR SARDIS

### Immediate (Already Using)
1. **Zodiac Roles Modifier v2** -- Sardis already uses this. Upgrade path:
   - Adopt "Permissions as Code" pattern from the SDK (v3.4.6)
   - Use karpatkey/defi-kit as template for building "Sardis Payment Kit"
   - Add rate/threshold limits natively in Roles (reduce Redis dependency for on-chain enforcement)
   - Replicate the Gnosis Pay architecture: Roles (spending policy) + Delay (human veto window)

### Short-term (3-6 months)
2. **Zodiac Delay Modifier** -- Add time-delayed execution for high-value agent transactions with human veto capability.
3. **Zodiac Scope Guard** -- Prevent human owners from removing agent safety modules.
4. **Privado ID integration** -- Issue ZK-verifiable KYC credentials after iDenfy verification. Agents can prove KYC status to merchants without sharing PII.
5. **zkPass TransGate** -- Enable "portable KYC" -- users who already passed KYC on Coinbase/Binance can prove it to Sardis without re-doing KYC.

### Medium-term (6-12 months)
6. **Semaphore groups** -- Create "OFAC-clean" groups where agents prove membership without revealing identity. On-chain sanctions compliance without PII.
7. **World ID** -- Sybil resistance layer to prevent one person from creating multiple agent wallets to circumvent aggregate spending limits.
8. **Custom ZK circuits (circom)** -- Build Sardis-specific circuits for:
   - "This agent's spending is within policy" (without revealing the policy)
   - "This agent passed KYC in jurisdiction X" (without revealing which jurisdiction)
   - "This transaction is below the agent's remaining daily limit" (without revealing the limit)

### Long-term (12+ months)
9. **Enclave (E3)** -- Private policy evaluation in encrypted execution environments.
10. **Mech** -- Agent-owned wallets with programmable ownership based on TAP attestations.
11. **Galactica-style investigation module** -- Encrypted notes in ZK proofs that enable law enforcement to investigate fraud while preserving normal user privacy.

---

## 6. KEY INSIGHT: THE GNOSIS PAY PRECEDENT

Gnosis Pay is the single most relevant reference implementation for Sardis. They use:
- **Safe Smart Account** as the wallet (same as Sardis)
- **Zodiac Roles Modifier** for spending policy enforcement (same as Sardis)
- **Zodiac Delay Modifier** for time-delayed execution with veto
- **Visa card** for fiat settlement (Sardis uses Stripe Issuing)

Every Gnosis Pay card transaction flows through Zodiac Roles. This proves the architecture works at scale for real payments. Sardis should study the Gnosis Pay implementation closely and replicate the pattern for agent payments.

**Key documentation:**
- [Gnosis Pay: How Delay and Roles Secure Your Card](https://help.gnosispay.com/hc/en-us/articles/39400440331668)
- [Gnosis Pay Accounts Documentation](https://docs.gnosispay.com/account)
- [Zodiac Roles Modifier Docs](https://docs.roles.gnosisguild.org/)
- [Evolving Smart Accounts with Onchain Permissions](https://gnosisguild.mirror.xyz/oQcy_c62huwNkFS0cMIxXwQzrfG0ESQax8EBc_tWwwk)
- [Permissions as Code (Engineering Blog)](https://engineering.gnosisguild.org/posts/permissions-as-code)

---

## Sources

### Zodiac Ecosystem
- [Zodiac Roles Modifier Docs](https://docs.roles.gnosisguild.org/)
- [Zodiac Wiki](https://www.zodiac.wiki/documentation)
- [Gnosis Guild Mirror Blog](https://gnosisguild.mirror.xyz/)
- [Gnosis Pay Help Center](https://help.gnosispay.com/)
- [DeFi Kit by karpatkey](https://kit.karpatkey.com/)
- [Lagoon: Safe & Zodiac Roles Setup](https://docs.lagoon.finance/curation-solutions/safe-and-zodiac-roles-modifier)

### ZK Identity/KYC
- [Privado ID](https://www.privado.id/)
- [Privado ID Blog: Moving Beyond Polygon](https://www.privado.id/blog/introducing-privado-id-moving-beyond-polygon-to-deliver-independent-privacy-preserving-identity-solutions)
- [Transak + Privado ID KYC Reusability](https://transak.com/blog/transak-and-privado-id-join-forces-to-pioneer-decentralized-kyc-reusability)
- [World ID Whitepaper](https://whitepaper.world.org/)
- [Semaphore Protocol](https://semaphore.pse.dev/)
- [Semaphore v4 Deep Dive](https://nkapolcs.dev/thoughts/20240728_zero_knowledge_with_semaphore_v4/)
- [zkPassport](https://github.com/zkpassport/circuits)
- [zkPass](https://zkpass.org/)
- [zkPass Technical Overview](https://docs.zkpass.org/overview/technical-overview)

### ZK Compliance
- [Galactica zkKYC Docs](https://docs.galactica.com/galactica-developer-documentation/galactica-concepts/zero-knowledge-kyc)
- [zkOrigoPlus](https://zkorigoplus.com/)
- [Chainlink Compliance Standard](https://docs.chain.link/oracle-platform/compliance-standard)
- [ZK Compliance Transforming RegTech (Security Boulevard)](https://securityboulevard.com/2026/01/zero-knowledge-compliance-how-privacy-preserving-verification-is-transforming-regulatory-technology/)
- [Nethermind: ZK Proofs in Blockchain Finance](https://www.nethermind.io/blog/zero-knowledge-proofs-in-blockchain-finance-opportunity-vs-reality)
- [Stellar: 5 Real-World ZK Use Cases](https://stellar.org/blog/developers/5-real-world-zero-knowledge-use-cases)
- [ERC-3643 / T-REX](https://github.com/TokenySolutions/T-REX)
- [ONCHAINID](https://docs.onchainid.com/docs/concepts/intro/)
- [Zyphe: ZK Proof in KYC Verification](https://www.zyphe.com/resources/blog/what-is-zero-knowledge-proof-in-kyc-verification)
