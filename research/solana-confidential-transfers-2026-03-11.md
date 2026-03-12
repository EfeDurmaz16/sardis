# Solana Confidential Transfers: Deep Technical Research

**Date:** 2026-03-11
**Status:** Active research -- ZK ElGamal program disabled on mainnet since June 2025

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technical Architecture](#technical-architecture)
3. [Cryptographic Primitives](#cryptographic-primitives)
4. [The Auditor / Compliance Model](#the-auditor--compliance-model)
5. [Performance & Limitations](#performance--limitations)
6. [USDC Integration Status](#usdc-integration-status)
7. [Arcium CSPL (Next-Gen Alternative)](#arcium-cspl-next-gen-alternative)
8. [EVM Equivalents & Comparisons](#evm-equivalents--comparisons)
9. [Relevance to Sardis](#relevance-to-sardis)
10. [Recommendation](#recommendation)

---

## Executive Summary

Solana's **Confidential Balances** system is a set of three Token-2022 extensions that encrypt token balances and transfer amounts using **Twisted ElGamal encryption**, **Pedersen commitments**, and **Sigma protocol zero-knowledge proofs**. It was announced as live on mainnet on April 8, 2025, but was **disabled on June 19, 2025** after a critical vulnerability in the ZK ElGamal Proof Program allowed forging of arbitrary valid proofs. As of March 2026, **the feature remains disabled** pending completion of a security audit.

**Key properties:**
- **What's confidential:** Token balances and transfer amounts only. Account addresses, sender/receiver identities, and transaction timestamps remain fully public.
- **What's NOT confidential:** Counterparty identities, token type, timing -- this is not Tornado Cash-style anonymity.
- **Compliance built-in:** Optional auditor ElGamal key at the mint level can decrypt all transfer amounts for that token.
- **USDC does NOT use it:** USDC on Solana still uses the original SPL Token Program, not Token-2022. Circle is pursuing privacy via a separate project (USDCx on Aleo).

---

## Technical Architecture

### The Three Extensions

| Extension | Purpose | Status |
|-----------|---------|--------|
| **Confidential Transfer** | Encrypts balances & transfer amounts between accounts | Disabled (audit) |
| **Confidential Transfer Fee** | Confidential fee handling using same crypto | Disabled (audit) |
| **Confidential MintBurn** | Private minting/burning with hidden total supply | Disabled (audit) |

### How a Confidential Transfer Works (Step-by-Step)

```
1. MINT CREATION (one-time)
   - Create Token-2022 mint with ConfidentialTransferMint extension
   - Set authority, auto_approve_new_accounts, optional auditor_elgamal_pubkey
   - NOTE: Cannot add confidential transfer capability retroactively

2. ACCOUNT CONFIGURATION (per user)
   - Create associated token account
   - Reallocate space for ConfidentialTransferAccount extension
   - Generate ElGamal keypair + AES key (client-side, from owner's ed25519 key)
   - Call ConfigureAccount with ElGamal pubkey + proof of pubkey validity
   - Initialize encrypted zero balances

3. DEPOSIT (public -> confidential)
   - Move tokens from public balance into encrypted pending balance
   - Amount is encrypted using account's ElGamal pubkey
   - Public balance decreases by exact amount (deposit amount is visible)

4. APPLY PENDING BALANCE (owner-only)
   - Move tokens from pending -> available (both encrypted)
   - Only the account owner can perform this
   - Prevents front-running attacks on ZK proof generation

5. CONFIDENTIAL TRANSFER (the core operation)
   - Client generates THREE zero-knowledge proofs:
     a) Equality Proof: new_balance = current_balance - transfer_amount
     b) Ciphertext Validity Proof: amount properly encrypted for sender, receiver, auditor
     c) Range Proof: balance >= 0 and amount >= 0 (non-negative, within 48-bit range)
   - Submit proofs to ZK ElGamal Proof Program -> creates context state accounts
   - Execute Transfer instruction referencing proof context accounts
   - Close proof accounts to recover SOL rent
   - Recipient's pending balance increases (encrypted)

6. RECIPIENT APPLIES PENDING BALANCE
   - Same as step 4, but for recipient

7. WITHDRAW (confidential -> public, optional)
   - Generate equality + range proofs
   - Converts confidential balance back to public
```

### Account State Structure

Each confidential token account maintains:

```
ConfidentialTransferAccount {
    approved: bool,                          // Whether account is approved for confidential transfers
    elgamal_pubkey: ElGamalPubkey,          // Account's encryption public key
    pending_balance_lo: ElGamalCiphertext,   // Encrypted incoming (low 16 bits)
    pending_balance_hi: ElGamalCiphertext,   // Encrypted incoming (high 32 bits)
    available_balance: ElGamalCiphertext,     // Encrypted spendable balance
    decryptable_available_balance: AesCiphertext, // AES-encrypted for owner fast decryption
    pending_balance_credit_counter: u64,     // Number of pending credits
    maximum_pending_balance_credit_counter: u64,
    expected_pending_balance_credit_counter: u64,
    actual_pending_balance_credit_counter: u64,
}
```

### CLI Commands (Reference)

```bash
# Create mint with confidential transfers (auto-approve)
spl-token --program-id TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb \
  create-token --enable-confidential-transfers auto

# Configure account for confidential transfers
spl-token configure-confidential-transfer-account --address <ACCOUNT_PUBKEY>

# Deposit tokens to confidential balance
spl-token deposit-confidential-tokens <MINT_PUBKEY> <AMOUNT> --address <ACCOUNT_PUBKEY>

# Apply pending balance
spl-token apply-pending-balance --address <ACCOUNT_PUBKEY>

# Confidential transfer
spl-token transfer <MINT_PUBKEY> <AMOUNT> --confidential <DESTINATION_PUBKEY>

# Withdraw from confidential to public
spl-token withdraw-confidential-tokens <MINT_PUBKEY> <AMOUNT> --address <ACCOUNT_PUBKEY>
```

### Rust Code: Mint Initialization with Auditor

```rust
use spl_token_2022::extension::ExtensionInitializationParams;

let extension_initialization_params =
    vec![ExtensionInitializationParams::ConfidentialTransferMint {
        authority: Some(payer.pubkey()),
        auto_approve_new_accounts: true,
        // Set to Some(auditor_elgamal_pubkey) for compliance
        auditor_elgamal_pubkey: None,
    }];
```

### Rust Code: Transfer with Proofs

```rust
// The transfer requires three separate proof generation + verification steps:

// 1. Equality Proof (CiphertextCommitmentEqualityProofData)
//    Proves: new_balance = current_balance - transfer_amount

// 2. Ciphertext Validity Proof (BatchedGroupedCiphertext3HandlesValidityProofData)
//    Proves: amount encrypted correctly for sender, receiver, and auditor keys

// 3. Range Proof (BatchedRangeProofU128Data)
//    Proves: 0 <= transfer_amount <= 2^48 AND 0 <= remaining_balance

// Each proof is submitted to the ZK ElGamal Proof Program which creates
// context state accounts, then the Transfer instruction references them.
```

---

## Cryptographic Primitives

### Twisted ElGamal Encryption (over Curve25519)

Standard ElGamal on an elliptic curve encrypts a message `m` as `(r*G, m*G + r*PK)` where `r` is random, `G` is the generator, and `PK` is the public key. Decryption recovers `m*G` then solves the discrete log.

**Twisted ElGamal** splits the ciphertext into two components:
1. **Pedersen Commitment**: `C = m*G + r*H` (message-binding, key-independent)
2. **Decryption Handle**: `D = r*PK` (key-specific, message-independent)

This split enables:
- **Homomorphic addition**: `Enc(a) + Enc(b) = Enc(a+b)` -- arithmetic on ciphertexts without decryption
- **Multi-recipient encryption**: Same commitment, different handles per recipient (sender, receiver, auditor)
- **Smaller ciphertext size**: Shared commitment across recipients

### Pedersen Commitments

```
C = m*G + r*H

Where:
  m = the secret value (balance or transfer amount)
  r = randomness (blinding factor)
  G, H = independent generators on Curve25519
```

Properties:
- **Hiding**: Given `C`, cannot determine `m` (information-theoretically secure)
- **Binding**: Cannot find different `(m', r')` that produces the same `C` (computationally secure)
- **Homomorphic**: `C(m1) + C(m2) = C(m1 + m2)` (with combined randomness)

### Sigma Protocols (Zero-Knowledge Proofs)

Sigma protocols are three-round (commit-challenge-response) interactive proofs made non-interactive via the **Fiat-Shamir heuristic** (hash-based challenge generation).

| Proof Type | What It Proves | Used In |
|-----------|---------------|---------|
| **Public-Key Validity** | ElGamal pubkey is well-formed | ConfigureAccount |
| **Zero-Balance** | Ciphertext encrypts zero | EmptyAccount (close) |
| **Ciphertext-Commitment Equality** | Ciphertext and Pedersen commitment encode same value | Transfer, Withdraw |
| **Ciphertext-Ciphertext Equality** | Two ciphertexts encrypt same value | Transfer, WithheldFee |
| **Ciphertext Validity** | Ciphertext is properly formed | Transfer, Withdraw |
| **Fee Sigma** | Transfer fee computed correctly | TransferWithFee |

### Bulletproofs (Range Proofs)

Range proofs verify `0 <= x < 2^n` without revealing `x`. The system uses **Bulletproofs** (Bunz et al. 2017) which:
- Require no trusted setup
- Have logarithmic proof size: `O(log n)` instead of `O(n)`
- Support **aggregation**: Multiple range proofs batched into one

Transfer amounts are restricted to **48-bit numbers** (max ~281 trillion), split into:
- `amount_lo`: 16-bit range proof
- `amount_hi`: 32-bit range proof

The Solana ZK ElGamal Proof Program lives at address: `ZkE1Gama1Proof11111111111111111111111111111`

---

## The Auditor / Compliance Model

### How It Works

1. **At Mint Creation**: The token issuer (e.g., Circle for USDC, or Sardis for a wrapped token) sets an optional `auditor_elgamal_pubkey` on the mint.

2. **During Every Transfer**: The transfer amount is encrypted **three ways**:
   - Under the **sender's** ElGamal public key
   - Under the **receiver's** ElGamal public key
   - Under the **auditor's** ElGamal public key (if configured)

3. **Compliance Decryption**: Any entity holding the auditor's ElGamal **private key** can decrypt the transfer amount from any transaction for that mint. They see:
   - The exact transfer amount
   - Which accounts were involved (these are always public)
   - The transaction timestamp

4. **Limitation**: Only a **single** auditor ElGamal public key can be set per mint. There is no built-in key-sharing or multi-auditor mechanism (would need a custom MPC/threshold decryption layer).

### Compliance Properties

| Property | Supported? | Notes |
|----------|-----------|-------|
| Auditor can see transfer amounts | Yes | Via auditor ElGamal key decryption |
| Auditor can see account balances | Partially | Can reconstruct from transaction history |
| Public cannot see amounts | Yes | Only encrypted ciphertexts visible on-chain |
| Sender/receiver addresses visible | Yes | Account addresses are always public |
| Token type visible | Yes | Mint address is always public |
| Freeze authority works | Yes | Standard Token-2022 freeze still works |
| AML screening possible | Yes | With auditor key + public addresses |
| Real-time monitoring | Yes | Auditor can decrypt as transactions land |

### Sardis as Auditor (Hypothetical)

If Sardis issued or wrapped a token on Solana using Token-2022 with confidential transfers:
- Sardis would hold the auditor ElGamal private key
- Sardis could decrypt all transfer amounts for compliance/AML
- The public (competitors, MEV bots, chain analysts) would see only encrypted amounts
- Agent spending patterns would be hidden from competitors
- Sardis's compliance layer (Elliptic AML screening) could still function

**Key risk**: Single-key auditor is a single point of compromise. If the auditor private key leaks, all historical and future transfer amounts for that mint are decryptable.

---

## Performance & Limitations

### Transaction Size

- Solana transactions are limited to **1,232 bytes** (current) or **4,096 bytes** (v1 format, SIMD-0296)
- A confidential transfer requires **3 separate proof context accounts** (equality, validity, range)
- Each proof must be verified in a separate instruction
- Result: A single confidential transfer requires **multiple sequential transactions** (typically 3-5)
- Workaround: Jito Bundles can atomically sequence these transactions

### Compute Units

- Default per-instruction limit: 200,000 CUs (can be raised to 1.4M per transaction)
- ZK proof verification is compute-heavy (~100k CUs per proof verification)
- A full confidential transfer consumes significantly more CUs than a standard SPL transfer (~3,000 CUs)
- Estimated total: **300,000-500,000 CUs** across the multi-transaction flow

### Throughput

- Token-2022 Confidential Transfers: **~20-30 confidential transfers per second** (limited by proof verification)
- For comparison, standard SPL transfers: thousands per second
- Arcium CSPL claims: "tens of thousands to millions" encrypted operations/sec (MPC-based, not yet live)

### Latency

- Standard Solana transfer: ~400ms (single slot)
- Confidential transfer: **several seconds** (multiple sequential transactions + proof generation)
- Client-side proof generation: Rust is fast (~100ms), JavaScript libraries not yet available

### Other Limitations

| Limitation | Impact |
|-----------|--------|
| ZK ElGamal Program disabled on mainnet | **Cannot use confidential transfers at all until audit completes** |
| Transfer amounts capped at 48 bits | Max ~281 trillion units (sufficient for most tokens) |
| Only Rust SDK available | No JavaScript/TypeScript client-side proof generation yet |
| Single auditor key per mint | No multi-party auditor without custom threshold crypto |
| Cannot add confidential transfer to existing mint | Must be configured at mint creation |
| Deposit/withdraw amounts are public | Only confidential-to-confidential transfers are private |
| Lost encryption keys = lost funds | No recovery mechanism for ElGamal private keys |
| Pattern analysis still possible | Timing, frequency, and counterparty patterns visible |

---

## USDC Integration Status

### Current State (March 2026)

**USDC on Solana does NOT use Token-2022 or confidential transfers.**

- USDC mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (original SPL Token Program)
- Circle has not migrated USDC to Token-2022
- Circle has not announced plans to enable confidential transfers for USDC on Solana

### Circle's Privacy Strategy: USDCx on Aleo

Instead of using Solana's native confidential transfers, Circle is building **USDCx** -- a privacy-preserving wrapped USDC on **Aleo** (a zkSNARK-based L1):

- **USDCx** = privacy-preserving USDC with "banking-level privacy"
- Built on Aleo's native ZK architecture (not Solana Token-2022)
- Wallet addresses AND transaction details hidden on-chain
- Circle retains ability to provide compliance records to regulators
- Partnership with Aleo announced; pilot ongoing

### Other Stablecoins Using Confidential Transfers

- **Agora Dollar ($AUSD)**: Enabled confidential transfers on Solana mainnet (before the June 2025 disable)
- **Paxos USDP**: Launched on Solana using Token Extensions (unclear if confidential specifically)

### Implications for Sardis

Since USDC on Solana doesn't use Token-2022, Sardis cannot do confidential USDC transfers on Solana using the native extension. Options:
1. **Wait for Circle** to migrate or wrap USDC on Token-2022 (no timeline)
2. **Issue a Sardis-wrapped token** on Token-2022 with confidential transfers (adds trust assumption)
3. **Use Arcium CSPL** when it launches (works with any existing SPL token, including USDC)
4. **Use EVM-side solutions** (see below)

---

## Arcium CSPL (Next-Gen Alternative)

### What Is It?

**CSPL (Confidential SPL)** is a next-generation confidential token standard from Arcium, announced at Solana Breakpoint 2025, targeting Q1 2026 launch.

### Key Differences from Token-2022 Confidential Transfers

| Feature | Token-2022 Confidential Transfer | Arcium CSPL |
|---------|--------------------------------|-------------|
| Approach | Client-side ZK proofs + on-chain verification | Multi-Party Computation (MPC) via Arx nodes |
| Throughput | ~20-30 TPS | "tens of thousands to millions" ops/sec (claimed) |
| Token compatibility | Only Token-2022 mints (must be created with extension) | Any existing SPL token (including USDC) |
| Smart contract support | No (only token transfers) | Yes (confidential smart token accounts) |
| Proof generation | Client-side (heavy, Rust-only currently) | Off-chain MPC clusters |
| Trust model | Trustless (on-chain ZK verification) | Trust in MPC cluster (Byzantine fault-tolerant) |
| Status | Disabled on mainnet (security audit) | Mainnet Alpha (Feb 2026); full mainnet Q1 2026 |

### Architecture

- **Arx Nodes**: Computational nodes forming MPC clusters
- **MXEs (Multi-Party eXecution Environments)**: Configurable VMs for Byzantine fault-tolerant MPC execution
- **Encrypted Shared State**: Unlike isolated encryption per user, allows computation across encrypted data from multiple parties
- **Confidential Smart Token Accounts**: Smart contracts that hold and transfer tokens privately -- no single entity (human or computer) knows the balance

### Implications

CSPL could be the more practical path for Sardis on Solana because:
- Works with existing USDC (no need for Token-2022 migration)
- Much higher throughput
- But: adds trust assumption in MPC cluster operators
- But: brand new, unaudited in production

---

## EVM Equivalents & Comparisons

### Overview of EVM Privacy Solutions

| Solution | Approach | Status (March 2026) | Compliance | Sardis-Relevant? |
|----------|----------|---------------------|------------|------------------|
| **Tornado Cash** | Mixer (zk-SNARKs) | **OFAC sanctioned** | None | **NO -- sanctioned** |
| **RAILGUN** | Shielded system (zk-SNARKs) | Live, ~$100M TVL | Proof-of-Innocence | Maybe (regulatory risk) |
| **Aztec Network** | ZK rollup L2 | In development | Configurable | Future option |
| **Zama fhEVM** | Fully Homomorphic Encryption | Live (Sepolia), 500-1000 TPS target by EOY 2026 | Configurable decryption | Most promising for EVM |
| **Paladin** (Kaleido/LF) | Modular privacy framework | Live, Apache 2.0 | Designed for institutional compliance | Strong candidate |
| **Oasis Sapphire** | Confidential EVM (TEE-based) | Live | TEE-based access control | Moderate |
| **Stealth Addresses** (Umbra) | Receiver privacy only | Live, 77K+ addresses | Limited | Partial solution |
| **Encrypt** | ZK privacy layer | Live (Feb 2026), $14M+ volume | TBD | Early stage |

### Detailed Comparisons

#### RAILGUN
- Uses zk-SNARKs to shield balances and transfers inside a smart contract "shielded pool"
- Deployed on Ethereum, Polygon, BSC; Solana on roadmap
- **Proof of Innocence**: Users can prove their funds don't originate from sanctioned addresses (without revealing full history)
- Risk: Regulatory gray area; similar architecture to Tornado Cash
- TVL: ~$100M (WETH, USDT, USDC)

#### Zama fhEVM (Most Comparable to Solana CT)
- Encrypted smart contracts using Fully Homomorphic Encryption
- User sends encrypted data -> FHE coprocessors compute on ciphertext -> encrypted result back on-chain -> user decrypts
- **Confidential ERC-20**: Replace integer operations with FHE equivalents
- Token issuer can configure who can decrypt (similar to Solana's auditor key)
- Performance: Currently slow (~10 TPS), targeting 500-1000 TPS by end of 2026 with GPU acceleration
- OpenZeppelin integration for building secure confidential smart contracts

#### Paladin (Most Enterprise-Ready)
- Linux Foundation Decentralized Trust project
- Works on any unmodified EVM chain (Ethereum, Base, Polygon)
- Combines ZKP tokens, issuer-backed tokens, and private smart contracts
- Designed from the ground up for institutional/regulated use
- Trusted notaries co-sign transactions (hybrid trust model)
- Apache 2.0 licensed, open governance
- **Best fit for regulated entities like Sardis** that need compliance-friendly privacy on EVM

### Comparison: Solana CT vs EVM Solutions

| Property | Solana CT | Zama fhEVM | Paladin | RAILGUN |
|----------|-----------|-----------|---------|---------|
| Privacy scope | Amounts only | Full state | Configurable | Full (mixer-like) |
| Compliance | Auditor key | Configurable decrypt | Notary co-signing | Proof of Innocence |
| Trust model | Trustless (ZK) | Trust coprocessors | Trust notaries | Trustless (ZK) |
| Performance | 20-30 TPS | ~10 TPS (2026 GPU: 500+) | Depends on base chain | Depends on base chain |
| Regulatory risk | Low | Low | Lowest | Medium-High |
| Maturity | Disabled (audit) | Early production | Production | Production |

---

## Relevance to Sardis

### Use Cases for Confidential Transfers in Sardis

1. **Protecting Agent Spending Patterns**
   - Without privacy: Competitors can observe on-chain how much an AI agent spends, on what, and when
   - With confidential transfers: Transfer amounts are hidden; only Sardis (as auditor) can see them
   - Value: Significant for enterprise clients who don't want spending intelligence leaking

2. **Policy Enforcement with Encrypted Amounts**
   - **Challenge**: Sardis's spending policy engine needs to evaluate amounts (daily limits, per-tx limits, category budgets)
   - **With Solana CT**: Sardis holds the auditor key, so the policy engine can decrypt amounts server-side before approving
   - **With Arcium CSPL**: MPC computation could evaluate policies on encrypted data (future)
   - **On EVM (Paladin/Zama)**: Similar auditor/decrypt model

3. **Compliance Layer Integration**
   - Sardis's Elliptic AML screening needs transaction amounts
   - Auditor key decryption provides this while keeping amounts private from the public chain
   - Regulatory bodies can be given selective decryption access

4. **Competitive Moat**
   - "Privacy-preserving agent payments with compliance" is a strong differentiator
   - No other agent payment infrastructure offers this

### Challenges for Sardis

| Challenge | Severity | Mitigation |
|-----------|----------|------------|
| Solana CT disabled on mainnet | **Critical** | Wait for re-enablement (months?) or use CSPL/EVM alternatives |
| USDC not on Token-2022 | **High** | Cannot do confidential USDC on Solana natively; need wrapper or CSPL |
| No JS/TS proof libraries | **Medium** | Server-side Rust proof generation (fits Sardis's WaaS model) |
| Single auditor key risk | **Medium** | HSM storage; threshold decryption wrapper |
| Multi-chain complexity | **Medium** | Sardis is primarily EVM; Solana adds another chain to support |
| Regulatory uncertainty | **Medium** | Auditor key + compliance records mitigate; Paladin safest on EVM |

---

## Recommendation

### Short-Term (Now - Q3 2026): Do NOT prioritize Solana confidential transfers

**Reasons:**
1. The ZK ElGamal program is **disabled on mainnet** with no firm re-enablement date
2. USDC on Solana **does not use Token-2022** -- confidential USDC is not possible
3. No JavaScript/TypeScript proof generation libraries -- only Rust (adds integration complexity)
4. Sardis's core chains are EVM (Base, Ethereum, Polygon) where the user base already exists

### Medium-Term (Q3 2026 - Q1 2027): Monitor two tracks

**Track A: Solana (watch)**
- Monitor ZK ElGamal program audit completion and re-enablement
- Watch Circle's USDC Token-2022 migration plans
- Evaluate Arcium CSPL when it reaches production maturity
- If CSPL delivers on "any existing SPL token" promise with USDC support, it becomes the preferred Solana path

**Track B: EVM (invest)**
- **Evaluate Paladin** (Kaleido/LF Decentralized Trust) for Base/Ethereum/Polygon
  - Apache 2.0, institutional-grade, works on unmodified EVM
  - Compliance-native design with notary co-signing
  - Best regulatory posture of any EVM privacy solution
- **Monitor Zama fhEVM** for confidential ERC-20 on Base
  - True encrypted computation (not just transfers)
  - Waiting for GPU acceleration to hit 500+ TPS
- **Avoid RAILGUN** for now (regulatory risk similar to Tornado Cash associations)

### Long-Term (2027+): Build "Confidential Agent Payments" as a feature

When the infrastructure matures, Sardis should offer:
1. **Confidential transfers** where agent spending amounts are encrypted on-chain
2. **Auditor key** held by Sardis for compliance/AML decryption
3. **Policy enforcement** via server-side decryption before signing
4. **Selective disclosure** allowing agents/owners to prove specific amounts to counterparties

This becomes a significant moat: "Your AI agent's spending is private from competitors but compliant with regulators."

### Decision Matrix

| Path | Readiness | USDC Support | Compliance | Effort | Recommendation |
|------|-----------|-------------|------------|--------|---------------|
| Solana CT (Token-2022) | Blocked (disabled) | No (USDC not on T22) | Auditor key | High | **Wait** |
| Arcium CSPL | Alpha (Q1 2026) | Yes (any SPL token) | TBD | Medium | **Monitor** |
| Paladin (EVM) | Production | Yes (any ERC-20) | Notary model | Medium | **Evaluate now** |
| Zama fhEVM | Early production | Yes (wrap any ERC-20) | Configurable | High | **Monitor** |
| Circle USDCx (Aleo) | Pilot | Native USDC | Circle-managed | Low (use their API) | **Watch** |

---

## Sources

### Official Documentation
- [Solana Confidential Transfer Extension](https://solana.com/docs/tokens/extensions/confidential-transfer)
- [Solana Confidential Balances Protocol Overview](https://www.solana-program.com/docs/confidential-balances/overview)
- [Solana ZK Proofs Documentation](https://www.solana-program.com/docs/confidential-balances/zkps)
- [Solana Transfer Tokens (Confidential)](https://solana.com/docs/tokens/extensions/confidential-transfer/transfer-tokens)
- [Solana Create Mint (Confidential)](https://solana.com/docs/tokens/extensions/confidential-transfer/create-mint)
- [Solana Token Extensions Overview](https://solana.com/solutions/token-extensions)

### Security Incidents
- [Post Mortem: ZK ElGamal Proof Program Bug (June 2025)](https://solana.com/news/post-mortem-june-25-2025)
- [Post Mortem: ZK ElGamal Proof Program Bug (May 2025)](https://solana.com/news/post-mortem-may-2-2025)

### Technical Guides
- [QuickNode: Confidential Transfers Developer Guide](https://www.quicknode.com/guides/solana-development/spl-tokens/token-2022/confidential)
- [QuickNode: Confidential Balances Now Live](https://blog.quicknode.com/confidential-balance-token-extensions-on-solana/)
- [Helius: Confidential Balances Deep Dive](https://www.helius.dev/blog/confidential-balances)
- [Solana Developers: Confidential Balances Sample (GitHub)](https://github.com/solana-developers/Confidential-Balances-Sample/blob/main/docs/product_guide.md)
- [Twisted ElGamal Encryption Whitepaper (PDF)](https://spl.solana.com/assets/files/twisted_elgamal-2115c6b1e6c62a2bb4516891b8ae9ee0.pdf)

### Arcium CSPL
- [Arcium CSPL Keynote (Breakpoint 2025)](https://solanacompass.com/learn/breakpoint-25/keynote-arcium-yannik-schrade)
- [Arcium Mainnet Alpha](https://blockeden.xyz/blog/2026/02/12/arcium-mainnet-alpha-encrypted-supercomputer-solana/)
- [Helius: Arcium Privacy 2.0 for Solana](https://www.helius.dev/blog/solana-privacy)

### Circle / USDC
- [Circle USDC on Solana](https://www.circle.com/multi-chain-usdc/solana)
- [Circle USDCx on Aleo (The Block)](https://www.theblock.co/post/381934/circle-tests-privacy-preserving-wrapped-version-usdc-aleo)
- [PaymentsJournal: Circle Privacy-Focused Stablecoin](https://www.paymentsjournal.com/circle-to-launch-privacy-focused-stablecoin-iteration/)

### EVM Privacy Solutions
- [Paladin: Programmable Privacy for EVM](https://www.paladinprivacy.org/)
- [Paladin GitHub (Kaleido)](https://github.com/kaleido-io/paladin)
- [Kaleido: Blockchain Privacy for EVM Landscape](https://www.kaleido.io/blockchain-blog/blockchain-privacy-for-evm)
- [Zama fhEVM GitHub](https://github.com/zama-ai/fhevm)
- [Zama: Confidential ERC-20 Tokens](https://www.zama.org/post/confidential-erc-20-tokens-using-homomorphic-encryption)
- [RAILGUN Documentation](https://docs.railgun.org/wiki)

### News & Analysis
- [The Block: Solana Confidential Balances Launch](https://www.theblock.co/post/350076/solana-developers-launch-new-confidential-balances-token-extensions-to-improve-onchain-privacy)
- [CryptoSlate: Solana ZK-Based Confidential Balances](https://cryptoslate.com/solana-launches-zero-knowledge-based-confidential-balances-to-merge-privacy-with-compliance/)
- [BeInCrypto: Confidential Balances Drive Institutional Adoption](https://beincrypto.com/solana-confidential-balances-bridge-privacy-and-compliance/)
- [Solana Breakpoint 2025 Summary](https://solana.com/news/solana-breakpoint-2025)
