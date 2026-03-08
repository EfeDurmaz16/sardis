# Sardis Contract Audit Surface

> Last updated: 2026-03-08

## Executive Summary

**Sardis deploys 2 custom contracts totaling 292 SLOC. 1 is a 41-SLOC anchor contract; the other is a 251-SLOC fork of Circle's audited RefundProtocol (Apache 2.0). All wallet infrastructure (Safe, Zodiac Roles, Circle Paymaster) is pre-deployed, battle-tested, and NOT maintained by Sardis.**

Two additional source files exist (`SardisPolicyModule.sol`, `SardisVerifyingPaymaster.sol`) but are deprecated and will NOT be deployed.

---

## Contract Inventory

### Production Contracts (to be deployed by Sardis)

| Contract | File | Total LOC | SLOC | License | Status | Risk Profile |
|----------|------|-----------|------|---------|--------|--------------|
| SardisLedgerAnchor | `src/SardisLedgerAnchor.sol` | 84 | 41 | MIT | `pending_deploy` | **Low** -- write-only Merkle root storage, no funds held |
| RefundProtocol | `src/RefundProtocol.sol` | 412 | 251 | Apache-2.0 | `pending_deploy` | **Medium** -- holds USDC in escrow, arbiter-controlled refunds |

**Total auditable custom SLOC: 292**

### Deprecated Contracts (NOT deployed, kept for reference)

| Contract | File | Total LOC | SLOC | Reason for Deprecation |
|----------|------|-----------|------|------------------------|
| SardisPolicyModule | `src/SardisPolicyModule.sol` | 361 | 232 | Replaced by Zodiac Roles module (pre-deployed, audited, avoids custom audit) |
| SardisVerifyingPaymaster | `src/SardisVerifyingPaymaster.sol` | 159 | 112 | Replaced by Circle Paymaster (permissionless, no deployment needed) |

### Pre-Deployed Infrastructure (NOT maintained by Sardis)

| Component | Address | Audited By | TVL/Usage |
|-----------|---------|------------|-----------|
| Safe Proxy Factory | `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` | Multiple (Ackee, G0, OpenZeppelin) | $100B+ TVL |
| Safe Singleton v1.4.1 | `0x41675C099F32341bf84BFc5382aF534df5C7461a` | Multiple | $100B+ TVL |
| Safe 4337 Module | `0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226` | Safe team | Canonical |
| Zodiac Roles (Policy) | `0x9646fDAD06d3e24444381f44362a3B0eB343D337` | Gnosis Guild | Battle-tested |
| Circle Paymaster | `0x0578cFB241215b77442a541325d6A4E6dFE700Ec` | Circle | Production |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | Uniswap / Trail of Bits | Production |
| EntryPoint v0.7 | `0x0000000071727De22E5E9d8BAf0edAc6f37da032` | EF / Infinitism | ERC-4337 canonical |

---

## Detailed Contract Analysis

### 1. SardisLedgerAnchor (41 SLOC)

**Purpose:** Stores Merkle roots of audit log batches on-chain for tamper evidence. Provides immutable proof that a set of audit entries existed at a specific time.

**Risk profile: LOW**
- No funds held or transferred
- Write-only (owner-gated `anchor()` + public `verify()`)
- Single external dependency: OpenZeppelin `Ownable`
- Attack surface: only owner can write; worst case is owner key compromise leading to bogus anchors (no financial loss)

**External dependencies:**
- `@openzeppelin/contracts/access/Ownable.sol`

**Key functions:**
- `anchor(bytes32 root, string anchorId)` -- owner-only, stores Merkle root with timestamp
- `verify(bytes32 root)` -- public view, returns anchor timestamp
- `verifyProof(...)` -- public view, verifies Merkle inclusion proof

### 2. RefundProtocol (251 SLOC)

**Purpose:** Escrow contract for USDC payments with lockup periods, refund/chargeback support, and arbiter-mediated dispute resolution. Forked from Circle's open-source RefundProtocol (Apache 2.0).

**Risk profile: MEDIUM**
- Holds USDC in escrow between payment and withdrawal
- Arbiter (Sardis) can trigger refunds and early withdrawals
- EIP-712 signatures for early withdrawal authorization

**External dependencies:**
- `@openzeppelin/contracts/token/ERC20/IERC20.sol`
- `@openzeppelin/contracts/utils/cryptography/EIP712.sol`

**Key functions:**
- `pay(address to, uint256 amount, address refundTo)` -- creates escrowed payment
- `withdraw(uint256[] paymentIDs)` -- permissionless withdrawal after lockup
- `refundByRecipient(uint256 paymentID)` -- recipient-initiated refund
- `refundByArbiter(uint256 paymentID)` -- arbiter-initiated refund/chargeback
- `earlyWithdrawByArbiter(...)` -- EIP-712 signed early withdrawal

**Known considerations:**
- Original code is from Circle (audited), but Sardis deployment is a fresh instance
- Arbiter key is a single point of trust (Sardis platform address)
- No upgradeability (immutable deployment)

---

## What an Auditor Needs to Review

1. **SardisLedgerAnchor.sol** -- 41 SLOC, straightforward Merkle anchoring
2. **RefundProtocol.sol** -- 251 SLOC, Circle's escrow with EIP-712 signatures
3. **DeploySafeModules.s.sol** -- deployment script (constructor args, permissions)
4. **Integration points** -- how the backend calls these contracts (see `packages/sardis-chain/`)

**Total scope: ~292 SLOC of custom Solidity + 1 deploy script**

The remaining 2 source files (`SardisPolicyModule.sol`, `SardisVerifyingPaymaster.sol`) are deprecated and excluded from audit scope.

---

## Legacy / Deprecated Code

The `contracts/deprecated/` directory contains the original contract suite that was replaced by Safe Smart Accounts:
- `SardisWalletFactory.sol` -- replaced by Safe Proxy Factory
- `SardisAgentWallet.sol` -- replaced by Safe Smart Accounts
- `SardisEscrow.sol` -- replaced by RefundProtocol
- Associated tests and deploy scripts

These are retained for historical reference only and are NOT part of the audit surface.
