/**
 * ProviderPort capability ports — the contract the *private* backend implements.
 *
 * The reference package is pure and does no IO. Every check the Python
 * `SpendingPolicy.evaluate` gates behind an injectable (on-chain balance, DB
 * velocity/state, KYA attestation, merchant trust) and every money-moving
 * capability Sardis exposes (wallet, card, settlement, proof issuance,
 * revocation) is expressed here as an **interface** — a port — that the cloud
 * backend implements. This package ships the interfaces plus deterministic
 * in-memory test doubles so adapters can typecheck and demo without a backend.
 *
 * NONE of these are implemented against a live system here. The doubles are
 * deterministic and money-free.
 *
 * The nine ports mirror the boundary between "decide" (this package, pure) and
 * "execute" (the private backend):
 *
 *   1. WalletPort         — on-chain balance / wallet provisioning (evaluate Check 7)
 *   2. PolicyStatePort    — cumulative spend + velocity (evaluate Checks 5–6)
 *   3. KyaPort            — agent identity attestation (evaluate Check 12)
 *   4. MerchantTrustPort  — first-seen / trust scrutiny (evaluate Check 10)
 *   5. CardPort           — virtual card issuance / freeze
 *   6. SettlementPort     — payment settlement / execution
 *   7. ProofPort          — AuthorityProof issuance (the signing side)
 *   8. RevocationPort     — propagating revocation execution
 *   9. MandateStorePort   — mandate persistence + lookup
 */
import type { Money } from './money.js';
import type { TimeWindowLimit } from './policy.js';
import type { ProofOfAuthority } from './proof.js';
import type { RevocationProof, RevocationTargetKind } from './revocation.js';
import type { Mandate } from './mandate.js';

// ─────────────────────────────────────────────────────────────────────────
// 1. WalletPort — on-chain balance + wallet provisioning (evaluate Check 7).
// ─────────────────────────────────────────────────────────────────────────
export interface WalletPort {
  getBalance(chain: string, token: string, address: string): Promise<Money>;
  createWallet(agentId: string): Promise<{ walletId: string; address: string }>;
}

// ─────────────────────────────────────────────────────────────────────────
// 2. PolicyStatePort — cumulative spend / velocity, server-owned (Checks 5–6).
// ─────────────────────────────────────────────────────────────────────────
export interface PolicyState {
  spentTotal: Money;
  windows: Record<string, TimeWindowLimit>;
}
export interface PolicyStatePort {
  loadState(agentId: string): Promise<PolicyState | null>;
  checkVelocity(agentId: string): Promise<{ ok: boolean; reason: string }>;
}

// ─────────────────────────────────────────────────────────────────────────
// 3. KyaPort — agent identity attestation (evaluate Check 12).
// ─────────────────────────────────────────────────────────────────────────
export interface KyaPort {
  verify(uid: string): Promise<{ found: boolean; revoked: boolean }>;
}

// ─────────────────────────────────────────────────────────────────────────
// 4. MerchantTrustPort — first-seen / low-trust scrutiny (evaluate Check 10).
// ─────────────────────────────────────────────────────────────────────────
export interface MerchantProfile {
  merchantId: string;
  isFirstSeen: boolean;
}
export interface MerchantTrustPort {
  getOrCreateProfile(merchantId: string): Promise<MerchantProfile>;
  getApprovalThreshold(merchantId: string, base: Money): Promise<Money>;
}

// ─────────────────────────────────────────────────────────────────────────
// 5. CardPort — virtual card issuance / freeze.
// ─────────────────────────────────────────────────────────────────────────
export interface CardPort {
  issueCard(agentId: string, spendLimit: Money): Promise<{ cardId: string }>;
  freeze(cardId: string): Promise<{ frozen: boolean }>;
}

// ─────────────────────────────────────────────────────────────────────────
// 6. SettlementPort — payment settlement / execution (the money-mover).
// ─────────────────────────────────────────────────────────────────────────
export interface SettlementPort {
  settle(input: {
    from: string;
    to: string;
    amount: Money;
    chain: string;
    token: string;
  }): Promise<{ txHash: string }>;
}

// ─────────────────────────────────────────────────────────────────────────
// 7. ProofPort — AuthorityProof issuance (the signing side, server-owned key).
// ─────────────────────────────────────────────────────────────────────────
export interface ProofPort {
  issue(actionId: string, claim: Omit<ProofOfAuthority, 'signature' | 'contentHash'>): Promise<ProofOfAuthority>;
}

// ─────────────────────────────────────────────────────────────────────────
// 8. RevocationPort — propagating revocation execution.
// ─────────────────────────────────────────────────────────────────────────
export interface RevocationPort {
  revoke(targetKind: RevocationTargetKind, targetRef: string, requestedBy: string): Promise<RevocationProof>;
}

// ─────────────────────────────────────────────────────────────────────────
// 9. MandateStorePort — mandate persistence + lookup.
// ─────────────────────────────────────────────────────────────────────────
export interface MandateStorePort {
  load(mandateId: string): Promise<Mandate | null>;
  save(mandate: Mandate): Promise<void>;
}

// ─────────────────────────────────────────────────────────────────────────
// Deterministic, money-free test doubles. NEVER a live impl.
// ─────────────────────────────────────────────────────────────────────────

/** A wallet port that always reports zero balance and a deterministic address. */
export class DenyAllWalletPort implements WalletPort {
  async getBalance(_chain: string, token: string, _address: string): Promise<Money> {
    return { minor: 0n, currency: token };
  }
  async createWallet(agentId: string): Promise<{ walletId: string; address: string }> {
    return { walletId: `wal_ref_${agentId}`, address: `0x${'0'.repeat(40)}` };
  }
}

/** An in-memory policy-state port seeded by the caller. Deterministic, no IO. */
export class InMemoryPolicyState implements PolicyStatePort {
  private readonly states = new Map<string, PolicyState>();

  constructor(seed?: Record<string, PolicyState>) {
    if (seed) {
      for (const [agentId, state] of Object.entries(seed)) {
        this.states.set(agentId, state);
      }
    }
  }

  set(agentId: string, state: PolicyState): void {
    this.states.set(agentId, state);
  }

  async loadState(agentId: string): Promise<PolicyState | null> {
    return this.states.get(agentId) ?? null;
  }

  async checkVelocity(_agentId: string): Promise<{ ok: boolean; reason: string }> {
    return { ok: true, reason: 'OK' };
  }
}
