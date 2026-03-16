# Sardis Payment Tokens (SPT) — Architecture

> Virtual cards and stablecoins are a temporary solution. Payment tokens are the future.

> **Prerequisite:** This document builds on the [Spending Mandate Specification](./spending-mandate-spec.md). The spending mandate is the off-chain authorization primitive that payment tokens will encode on-chain.

## Relationship to Spending Mandates

Payment tokens are the **on-chain evolution** of spending mandates:

| Layer | Phase 1 (Now) | Phase 2 (6-12 months) | Phase 3 (12-18 months) |
|-------|--------------|----------------------|----------------------|
| Authorization | Off-chain spending mandate | Mandate → ERC-20 transfer hook | Native token mandate |
| Enforcement | Sardis API policy pipeline | Transfer hook validates mandate | Token self-enforces |
| Portability | API-scoped | Chain-scoped | Cross-chain |

The spending mandate defines WHAT is allowed. The payment token defines HOW it's enforced on-chain. Same semantics, different enforcement layer.

## What Payment Tokens Are

Sardis Payment Tokens (SPT) are **programmable digital value with embedded policy enforcement at the token level**. Unlike the current model — where policy is enforced at the API layer above static stablecoins — SPTs carry their spending rules on-chain. The token itself knows what it's allowed to buy, how much it can spend, and when it expires.

Think of SPTs as "USDC with a built-in spending mandate."

## Why They Matter

### Current Model (Phase 1)
```
Agent → Sardis API (policy check) → Chain Executor → USDC Transfer
```
Policy enforcement happens at the Sardis API layer. Once USDC leaves the wallet, there's no on-chain enforcement. An agent with a compromised API key could bypass Sardis and send USDC directly.

### Future Model (Phase 3)
```
Agent → SPT Contract (policy enforced on-transfer) → Recipient redeems → USDC
```
Policy enforcement is embedded in the token. Even if an agent bypasses Sardis's API, the token's transfer hook rejects policy-violating transactions on-chain. This is defense-in-depth: policy at the API layer AND the token layer.

## Technical Design

### Token Standard: ERC-20 + Transfer Hooks

SPTs are ERC-20 tokens with ERC-7579 / ERC-165 transfer hooks:

```solidity
contract SardisPaymentToken is ERC20, IERC7579TransferHook {
    // 1:1 backing by USDC in vault
    IERC20 public immutable USDC;
    address public immutable vault;

    // Per-token policy metadata
    struct TokenPolicy {
        uint256 perTxLimit;
        uint256 dailyLimit;
        uint256 expiresAt;
        bytes32 allowedCategoriesHash;
        address issuer;           // org that minted
    }

    mapping(address => TokenPolicy) public policies;

    function _beforeTokenTransfer(
        address from, address to, uint256 amount
    ) internal override {
        TokenPolicy memory p = policies[from];
        require(amount <= p.perTxLimit, "SPT: exceeds per-tx limit");
        require(block.timestamp < p.expiresAt, "SPT: token expired");
        // ... daily limit tracking, category check via oracle
    }
}
```

### Minting Flow

```
Org deposits 1000 USDC → Vault contract
  → Vault mints 1000 SPT to org's agent wallet
  → SPT carries the org's spending policy
  → Minting fee: X bps deducted (e.g., 0.25%)
```

### Redemption Flow

```
Merchant receives 500 SPT from agent
  → Merchant calls redeem(500 SPT) on vault
  → Vault burns 500 SPT, sends 500 USDC to merchant
  → Redemption fee: X bps deducted (e.g., 0.10%)
```

### Policy Metadata

Policy can be stored either:

1. **On-chain** (simpler, more gas): Full policy struct in contract storage
2. **EIP-712 signed attestation** (cheaper, more flexible): Policy hash on-chain, full policy resolved via attestation registry

For MVP, on-chain storage is preferred. For scale (1M+ agents), EIP-712 attestations with off-chain resolution.

## Relationship to Existing Infrastructure

| Existing Component | SPT Role |
|---|---|
| Safe Smart Accounts | Custody vault for USDC backing |
| Zodiac Roles | On-chain policy modules (precursor to SPT hooks) |
| ERC-8183 Job Manager | Job escrow using SPT instead of raw USDC |
| Platform Fee Engine | Minting/redemption fee calculation |
| KYA Trust Scoring | Trust tier determines SPT policy parameters |
| Audit Ledger | SPT mint/burn/transfer events anchored to ledger |

## Regulatory Considerations

SPTs will likely be classified as one of:
- **Prepaid instrument** (if denominated and redeemable in USD)
- **E-money** (EU/UK classification for stored value tokens)
- **Stablecoin derivative** (if treated as a synthetic asset)

Key regulatory paths:
- US: State money transmitter licenses (MSB registration already planned)
- EU: E-money institution license under EMD2/PSD2
- UK: FCA e-money authorization

Legal analysis needed before Phase 2 implementation. The vault's 1:1 USDC backing is designed to simplify regulatory classification — SPTs are not speculative tokens.

## Revenue Model

| Fee Type | Rate | When |
|---|---|---|
| Minting fee | 0.25% | Depositing USDC → SPT |
| Redemption fee | 0.10% | Burning SPT → USDC |
| Policy premium | $0.001/check | Advanced on-chain policy evaluation |
| Enterprise custom | Negotiable | Custom policy modules |

At $1M monthly token volume:
- Minting: $2,500/mo
- Redemption: $1,000/mo
- Combined with SaaS subscription: strong unit economics

## Implementation Roadmap

### Phase 1: Current (Stablecoins + Virtual Cards)
- Policy enforcement at Sardis API layer
- USDC transfers via Safe Smart Accounts
- Virtual cards via Stripe Issuing
- Platform fees collected off-chain via treasury address
- **Status: Production**

### Phase 2: Wrapped Policy Tokens (6-12 months)
- ERC-20 wrapper around USDC with transfer hooks
- Basic on-chain policy: per-tx limits, daily limits, expiration
- Vault contract for 1:1 backing
- Minting/redemption fee collection on-chain
- Merchant redemption portal
- **Prerequisites:** Legal analysis, audit, vault contract development

### Phase 3: Native Payment Tokens (12-18 months)
- Full policy enforcement on-chain (categories, approval chains)
- Cross-chain portability (Base → Polygon → Arbitrum)
- Inter-agent settlement (agent A pays agent B in SPT)
- Programmable escrow (SPT + ERC-8183 combined)
- On-chain trust scoring integration
- **Prerequisites:** Phase 2 proven, regulatory clarity, multi-chain contracts

## Open Questions

1. **Oracle design:** How do SPT transfer hooks resolve merchant categories on-chain? Chainlink? Custom oracle?
2. **Gas costs:** Transfer hooks add gas. Are paymaster-sponsored transactions sufficient for UX?
3. **Cross-chain:** How do SPTs maintain policy across bridges? Lock-and-mint? Burn-and-remint?
4. **Privacy:** Should transaction amounts be visible on-chain or use ZK proofs for privacy?
5. **Composability:** Can SPTs be used in DeFi protocols? Should they be? (Probably not for MVP — regulatory risk)

## Conclusion

Payment tokens transform Sardis from an API-level policy enforcer into a protocol-level trust primitive. The token itself becomes the unit of trust: programmable, auditable, and policy-enforcing by design. This is the path from "payment infrastructure" to "financial protocol."

The current stablecoin + virtual card model is the right Phase 1. It generates revenue and proves the market. SPTs are Phase 2-3: they deepen the moat, create protocol-level lock-in, and unlock new revenue streams (minting/redemption fees) that scale with transaction volume.
