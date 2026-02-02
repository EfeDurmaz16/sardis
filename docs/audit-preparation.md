# Sardis Smart Contract Audit Preparation

**Prepared:** 2026-02-02
**Version:** 1.0
**Contact:** Sardis Engineering Team

---

## 1. Audit Scope

### Contracts in Scope

| Contract | File | Total Lines | Estimated SLOC |
|----------|------|-------------|----------------|
| SardisAgentWallet | `contracts/src/SardisAgentWallet.sol` | 612 | ~350 |
| SardisWalletFactory | `contracts/src/SardisWalletFactory.sol` | 308 | ~180 |
| SardisEscrow | `contracts/src/SardisEscrow.sol` | 596 | ~340 |
| **Total** | **3 contracts** | **1,516** | **~870** |

### Compiler & Dependencies

- **Solidity version:** `^0.8.20`
- **Framework:** Foundry (forge)
- **Dependencies:**
  - OpenZeppelin Contracts (v5.x):
    - `IERC20`, `SafeERC20` (token interaction)
    - `ReentrancyGuard` (reentrancy protection)
    - `Pausable` (circuit breaker)
    - `Ownable` (access control for factory & escrow)
    - `Address` (safe ETH transfers via `sendValue`)

### Out of Scope

- OpenZeppelin library internals
- Off-chain backend (Python API, MPC signing via Turnkey)
- Frontend dashboard and landing page

---

## 2. Architecture Overview

### Contract Interaction Diagram

```
                    +-----------------------+
                    | SardisWalletFactory   |
                    | (Ownable, Pausable)   |
                    +-----------+-----------+
                                |
                     deploys via CREATE / CREATE2
                                |
                                v
                    +-----------------------+
                    | SardisAgentWallet     |
                    | (ReentrancyGuard,     |
                    |  Pausable)            |
                    +-----------------------+
                       |              |
                  pay / payWithCoSign  createHold / captureHold
                       |              |
                       v              v
                   ERC20 tokens    Merchants

                    +-----------------------+
                    | SardisEscrow          |
                    | (ReentrancyGuard,     |
                    |  Ownable)             |
                    +-----------------------+
                       |         |        |
                    buyer     seller    arbiter
```

### Wallet Factory Pattern

- `SardisWalletFactory` is owned by the Sardis platform (deployer).
- It deploys `SardisAgentWallet` instances via `new` (CREATE) or inline assembly (CREATE2 for deterministic addresses).
- The factory sets itself as the initial `sardis` role on each wallet (the co-signer).
- The factory collects optional deployment fees in native ETH and tracks all wallets via `isValidWallet` mapping.

### Agent Wallet Roles

| Role | Address | Capabilities |
|------|---------|-------------|
| **agent** | AI agent's address | `pay`, `createHold`, `captureHold`, `voidHold`, merchant management, `pause` |
| **sardis** | Platform co-signer | All agent capabilities + `setLimits`, `setAllowlistMode`, `unpause`, `setRecoveryAddress`, `transferSardis`, `payWithCoSign` |
| **recoveryAddress** | Emergency backup | `emergencyWithdraw` only |

### Escrow Flow

1. **Created** -- buyer calls `createEscrow` or `createEscrowWithMilestones`
2. **Funded** -- buyer calls `fundEscrow`, transferring `amount + fee` into the contract
3. **Released** -- after both `sellerConfirmed` and `buyerApproved`, or via `releaseWithCondition`
4. **Disputed** -- either buyer or seller calls `raiseDispute`
5. **Resolved** -- arbiter calls `resolveDispute(escrowId, buyerPercent)`, splitting funds
6. **Refunded** -- buyer calls `refund` after deadline passes (if seller has not confirmed)
7. **Expired** -- buyer cancels an unfunded escrow via `cancelEscrow`

---

## 3. Threat Model

### 3.1 Assets at Risk

- **ERC20 tokens held in agent wallets** (USDC, EURC, USDT, PYUSD) -- direct theft or unauthorized transfers
- **ERC20 tokens locked in escrow** -- `amount + fee` per active escrow
- **ETH deployment fees** held in factory contract
- **Hold reservations** -- over-commitment could make wallet insolvent relative to obligations

### 3.2 Trust Boundaries

| Boundary | Trust Assumption |
|----------|-----------------|
| Agent <-> Sardis platform | Sardis is a privileged co-signer; can set limits, unpause, transfer its own role. Agent trusts Sardis not to be malicious. |
| Agent <-> Merchant | Merchant addresses are validated via allowlist/denylist. No on-chain identity verification of merchants. |
| Buyer <-> Seller (Escrow) | Neither is trusted; escrow enforces conditional release. |
| Buyer/Seller <-> Arbiter | Arbiter is a single trusted party for dispute resolution. Complete discretion over fund split (0-100%). |
| Factory owner <-> Wallet users | Factory owner controls default recovery address, deployment fees, and pause state. |

### 3.3 Attack Vectors

| Vector | Relevance | Mitigation in Code |
|--------|-----------|-------------------|
| **Reentrancy** | High -- ERC20 transfers in `pay`, `captureHold`, escrow `_release` | `ReentrancyGuard` on all transfer functions; `SafeERC20` used throughout |
| **Signature replay** | High -- `payWithCoSign` uses agent signatures | `usedSignatures` mapping tracks message hashes; `chainid` included in hash; deadline enforced |
| **Signature malleability** | Medium -- malleable `s` values could bypass replay check | EIP-2 low-s check enforced in `_splitSignature`; `v` validated to 27/28 |
| **Front-running** | Medium -- `payWithCoSign` transactions visible in mempool | Mitigated by nonce + deadline; co-sign requires Sardis as `msg.sender` |
| **Access control bypass** | High -- privileged functions gated by role | Modifiers `onlyAgent`, `onlySardis`, `onlyAgentOrSardis`, `onlyRecovery`; escrow uses `onlyBuyer`, `onlySeller`, `onlyArbiter` |
| **Gas griefing** | Low -- no unbounded loops in wallet; milestone array capped at 20 | Milestone cap of 20; hold iteration is not required (mapping-based) |
| **ERC20 return value issues** | Medium -- some tokens don't return bool | `SafeERC20` wraps all transfer/transferFrom calls |
| **Integer overflow** | Low -- Solidity 0.8.x has built-in overflow checks | Compiler-level protection |
| **Denial of service via pause** | Medium -- Sardis or agent can pause wallet | `unpause` restricted to Sardis only; factory pause restricted to owner |

---

## 4. Key Invariants

These invariants must hold at all times and should be verified by the auditor:

### SardisAgentWallet

1. **Hold accounting:** `totalHeldAmount[token] <= IERC20(token).balanceOf(address(wallet))` at all times (no over-commitment)
2. **Daily limit:** `spentToday <= dailyLimit` within any single day period (after reset)
3. **Hold lifecycle:** A hold can only be captured once (`hold.captured` set to `true` exactly once) and cannot be captured after being voided
4. **Hold lifecycle (void):** A hold can only be voided once and cannot be voided after being captured
5. **Signature uniqueness:** Each `messageHash` in `payWithCoSign` can only be used once (`usedSignatures[hash] == true` after first use)
6. **Nonce monotonicity:** `nonce` only increments, never decrements
7. **Role separation:** Only `recoveryAddress` can call `emergencyWithdraw`; only `sardis` can call `setLimits`, `unpause`, `transferSardis`

### SardisEscrow

8. **Escrow funding:** When funded, the contract holds exactly `amount + fee` for that escrow (transferred via `safeTransferFrom`)
9. **State machine:** Escrow states transition only along valid paths: Created -> Funded -> {Released, Disputed, Refunded} and Disputed -> Resolved and Created -> Expired
10. **Dispute resolution:** `buyerAmount + sellerAmount == escrow.amount` (the fee is always sent to owner separately)
11. **Milestone accounting:** Sum of all milestone amounts equals `escrow.amount` (enforced at creation)
12. **Milestone release:** Each milestone can only be released once (`m.released` set true once)
13. **Refund condition:** Refund only possible when `!sellerConfirmed && block.timestamp > deadline`

### SardisWalletFactory

14. **Wallet tracking:** Every deployed wallet is recorded in `isValidWallet`, `allWallets`, `agentWallets`, and `walletToAgent`
15. **Fee collection:** `msg.value >= deploymentFee` enforced; excess refunded via `sendValue`

---

## 5. Known Issues / Accepted Risks

| Issue | Severity | Status |
|-------|----------|--------|
| **Single arbiter for escrow disputes** | Medium (centralization) | Accepted. The arbiter is a Sardis-controlled address. A malicious or compromised arbiter can arbitrarily split disputed funds. Future improvement: multi-sig arbiter or decentralized arbitration. |
| **No timelock on owner/Sardis operations** | Medium | Accepted. `transferSardis`, `setLimits`, `setRecoveryAddress`, `setArbiter` take effect immediately. No delay for wallet users to react. |
| **Factory owner controls default recovery address** | Low | Accepted. New wallets inherit `defaultRecoveryAddress` from factory. Owner can change it at any time, affecting only future deployments. |
| **emergencyWithdraw ignores holds** | Medium | Accepted. Recovery address can withdraw the full token balance, including tokens reserved by active holds. This is by design for emergency scenarios. |
| **payWithCoSign bypasses spending limits** | Medium | Accepted. Co-signed transactions intentionally skip `_checkLimits` and `_updateSpentAmount` to allow higher-value transactions when Sardis co-signs. Note: `_updateSpentAmount` is not called for co-signed payments, so they do not count against daily limits. |
| **No expiry cleanup for holds** | Low | Accepted. Expired holds remain in storage; `totalHeldAmount` is not automatically decremented when holds expire. Funds become inaccessible until `voidHold` is called on expired holds (voiding does not check expiry). |
| **Wallet receives ETH** | Low | Accepted. Both `SardisAgentWallet` and `SardisWalletFactory` have `receive() payable` but no mechanism to withdraw ETH from the wallet (only ERC20 via `emergencyWithdraw`). ETH sent to the wallet is permanently locked. |

---

## 6. Recent Changes

The following changes were made in preparation for this audit:

1. **EIP-2 low-s signature check** -- Added to `_splitSignature` in `SardisAgentWallet` to prevent signature malleability. Enforces `s <= secp256k1n/2` and validates `v` is 27 or 28.

2. **`capturedAmount` field added to Hold struct** -- Tracks the actual amount captured (which may be less than the hold amount for partial captures).

3. **Zero-amount guards** -- Added `require(amount > 0)` checks to `pay`, `createHold`, and `captureHold` to prevent zero-value operations.

4. **12 fuzz tests added** -- 8 fuzz tests for `SardisAgentWallet` and 4 fuzz tests for `SardisEscrow`, testing invariants under randomized inputs.

5. **Safe ETH transfers** -- Factory refund and fee withdrawal updated to use OpenZeppelin `Address.sendValue` instead of raw `transfer` to avoid gas limit issues.

6. **`transferSardis` function** -- Added to allow migrating the Sardis co-signer role to a new address without redeploying wallets.

7. **`cancelEscrow` function** -- Added to allow buyers to cancel unfunded escrows.

8. **`releaseWithCondition` function** -- Added condition-based escrow release using hash verification.

---

## 7. Testing Summary

### Test Files

| File | Type | Test Count |
|------|------|-----------|
| `SardisAgentWallet.t.sol` | Unit tests | 26 |
| `SardisWalletFactory.t.sol` | Unit tests | 19 |
| `SardisEscrow.t.sol` | Unit tests | 24 |
| `E2E.t.sol` | End-to-end integration | 10 |
| `SardisAgentWallet.fuzz.t.sol` | Fuzz tests | 8 |
| `SardisEscrow.fuzz.t.sol` | Fuzz tests | 4 |
| **Total** | | **91** |

### Fuzz Tests

- Wallet fuzz tests (8): Cover spending limits with random amounts, hold create/capture/void with random values, daily reset edge cases, merchant list toggling
- Escrow fuzz tests (4): Cover escrow creation with random amounts, dispute resolution with random buyer percentages, milestone amount sums, funding and release flows

### What Is NOT Tested

- **Formal verification** -- No SMT-based or symbolic execution verification has been performed
- **Invariant testing** (Foundry `invariant_*` style) -- Not implemented; fuzz tests cover specific properties but not stateful invariant exploration
- **Cross-contract interaction fuzzing** -- Factory -> Wallet -> ERC20 interaction chains not fuzzed as a unit
- **Exotic ERC20 behavior** -- No tests with fee-on-transfer tokens, rebasing tokens, or tokens that return false instead of reverting
- **Gas profiling** -- No formal gas benchmarks or worst-case gas analysis
- **Mainnet fork testing** -- No tests run against forked mainnet state with real token contracts

---

## 8. Recommended Audit Focus Areas

### 8.1 Access Control (Critical)

- Verify that `onlyAgent`, `onlySardis`, `onlyAgentOrSardis`, and `onlyRecovery` modifiers correctly gate all privileged functions
- Verify that `transferSardis` cannot be used to escalate privileges or lock out the agent
- Verify that factory `onlyOwner` functions cannot affect already-deployed wallets
- Check that `recoveryAddress` of `address(0)` (constructor allows it) does not create a vulnerability

### 8.2 Hold Lifecycle (High)

- Confirm no double-capture: once `hold.captured = true`, the hold cannot be captured again
- Confirm no double-void: once `hold.voided = true`, the hold cannot be voided again
- Verify `totalHeldAmount` is correctly decremented on both capture and void paths
- Check that partial capture (captureAmount < hold.amount) correctly releases the full hold reservation from `totalHeldAmount`
- Verify that expired holds cannot be captured (the `block.timestamp <= hold.expiresAt` check)
- Note: expired holds CAN be voided (no expiry check on `voidHold`) -- verify this is intentional

### 8.3 Daily Limit Reset Timing (Medium)

- The daily reset uses `block.timestamp / 1 days` (UTC-aligned 86400-second periods)
- Verify no off-by-one in `_checkLimits` vs `_updateSpentAmount` -- both use the same `today > lastResetDay` pattern
- Check for potential race condition: `_checkLimits` reads `spentToday` before `_updateSpentAmount` modifies it, but both are in the same transaction
- Confirm `createHold` calls `_checkLimits` but does NOT call `_updateSpentAmount` -- holds reserve against the limit check but actual spending is deferred to `captureHold`

### 8.4 Escrow State Machine (High)

- Map all valid state transitions and confirm no invalid transitions are possible
- Verify that `releaseWithCondition` cannot bypass the Funded state requirement
- Verify that `raiseDispute` can only be called by buyer or seller (not arbiter or external parties)
- Check that `resolveDispute` correctly distributes `amount` to buyer/seller and `fee` to owner, with no residual funds left in contract
- Verify milestone release accounting: proportional fee calculation `(m.amount * e.fee) / e.amount` for rounding behavior -- total fees across all milestones may not exactly equal `e.fee` due to integer division

### 8.5 ERC20 Token Interaction Safety (Medium)

- All transfers use `SafeERC20` -- verify no raw `transfer` or `transferFrom` calls exist
- `fundEscrow` uses `safeTransferFrom` -- verify allowance is checked (handled by ERC20 itself)
- Verify behavior with USDC (6 decimals), USDT (non-standard return), and other supported tokens
- Check for approval front-running in escrow funding flow

### 8.6 Signature Verification (High)

- Verify `payWithCoSign` message hash includes all relevant fields (contract address, token, to, amount, nonce, deadline, chainid)
- Verify `ecrecover` return value is checked against `address(0)` -- currently it checks `recovered == signer`, which would fail if `ecrecover` returns `address(0)` and signer is not zero, but verify explicitly
- Confirm EIP-2 low-s enforcement is correct (the constant `0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0` is `secp256k1n / 2`)
- Verify no signature reuse across different wallets (contract address is in the hash) or chains (chainid is in the hash)

### 8.7 Factory CREATE2 (Low)

- Verify that CREATE2 salt derivation prevents address collision attacks
- Verify that `predictWalletAddress` matches actual deployed addresses
- Check that deterministic deployment with same salt + agent reverts (CREATE2 will fail if code already exists at address)

---

## Appendix: Contract Function Summary

### SardisAgentWallet (22 functions)

| Function | Access | Mutability | Reentrancy Guard |
|----------|--------|------------|-----------------|
| `pay` | agentOrSardis | state-changing | Yes |
| `payWithCoSign` | sardis | state-changing | Yes |
| `createHold` | agentOrSardis | state-changing | No |
| `captureHold` | agentOrSardis | state-changing | Yes |
| `voidHold` | agentOrSardis | state-changing | No |
| `setLimits` | sardis | state-changing | No |
| `allowMerchant` | agentOrSardis | state-changing | No |
| `denyMerchant` | agentOrSardis | state-changing | No |
| `removeMerchant` | agentOrSardis | state-changing | No |
| `setAllowlistMode` | sardis | state-changing | No |
| `pause` | agentOrSardis | state-changing | No |
| `unpause` | sardis | state-changing | No |
| `emergencyWithdraw` | recovery | state-changing | No |
| `setRecoveryAddress` | sardis | state-changing | No |
| `transferSardis` | sardis | state-changing | No |
| `getBalance` | public | view | -- |
| `getAvailableBalance` | public | view | -- |
| `getRemainingDailyLimit` | public | view | -- |
| `canPay` | public | view | -- |

### SardisWalletFactory (13 functions)

| Function | Access | Mutability |
|----------|--------|------------|
| `createWallet` | public (payable) | state-changing |
| `createWalletWithLimits` | public (payable) | state-changing |
| `createWalletDeterministic` | public (payable) | state-changing |
| `predictWalletAddress` | public | view |
| `setDefaultLimits` | owner | state-changing |
| `setDeploymentFee` | owner | state-changing |
| `setDefaultRecoveryAddress` | owner | state-changing |
| `withdrawFees` | owner | state-changing |
| `pause` / `unpause` | owner | state-changing |
| `getAgentWallets` | public | view |
| `getAgentWalletCount` | public | view |
| `getTotalWallets` | public | view |
| `verifyWallet` | public | view |

### SardisEscrow (17 functions)

| Function | Access | Mutability | Reentrancy Guard |
|----------|--------|------------|-----------------|
| `createEscrow` | public | state-changing | No |
| `createEscrowWithMilestones` | public | state-changing | No |
| `fundEscrow` | buyer | state-changing | Yes |
| `confirmDelivery` | seller | state-changing | No |
| `approveRelease` | buyer | state-changing | No |
| `release` | public | state-changing | Yes |
| `releaseWithCondition` | buyer/seller/arbiter | state-changing | Yes |
| `refund` | buyer | state-changing | Yes |
| `cancelEscrow` | buyer | state-changing | No |
| `completeMilestone` | seller | state-changing | No |
| `releaseMilestone` | buyer | state-changing | Yes |
| `raiseDispute` | buyer/seller | state-changing | No |
| `resolveDispute` | arbiter | state-changing | Yes |
| `setArbiter` | owner | state-changing | No |
| `setFeeBps` | owner | state-changing | No |
| `setMinAmount` | owner | state-changing | No |
| `getEscrow` / `getMilestones` / `getEscrowCount` / `verifyCondition` / `hasReleaseCondition` | public | view | -- |
