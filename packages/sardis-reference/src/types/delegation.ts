/**
 * Delegation — the attenuated capability primitive (object-capability for money).
 *
 * Mirrors `delegation.py`. The cardinal rule: a child may only NARROW its
 * parent (cap <= parent.remaining, expiry <= parent.expiry, scope subset of
 * parent.scope, depth = parent.depth + 1 <= MAX_DELEGATION_DEPTH).
 */
import type { Money, Currency } from './money.js';

export const MAX_DELEGATION_DEPTH = 8;

export type DelegatorKind = 'mandate' | 'delegation';
export type DelegationStatus = 'active' | 'revoked' | 'expired' | 'exhausted';

/**
 * Each dimension is a subset constraint: a delegation may only narrow each
 * field of its delegator's scope, never widen it.
 */
export interface DelegationScope {
  counterparties: string[];
  categories: string[];
  mcc: string[];
  rails: string[];
}

/**
 * Signed proof a delegation was minted with these attenuated bounds.
 * HMAC-SHA256 over `id|delegatorRef|delegatee|rootMandateId|decisionHash`
 * (mirrors `DelegationEvidence`). Symmetric — internal tamper-evidence only.
 */
export interface DelegationEvidence {
  delegationId: string;
  delegatorKind: DelegatorKind;
  delegatorRef: string;
  delegatorPrincipal: string;
  delegatee: string;
  rootMandateId: string;
  depth: number;
  /** token units as a string, Decimal-safe (mirrors Python `amount_cap`). */
  amountCap: string | null;
  currency: Currency;
  /** ISO timestamp or null. */
  expiresAt: string | null;
  /** SHA-256 of the attenuated scope. */
  scopeHash: string;
  /** ISO timestamp (the `created_at` bound into the decision hash). */
  createdAt: string;
  decisionHash: string;
  signature: string;
}

export interface Delegation {
  id: string;
  delegatorKind: DelegatorKind;
  delegatorRef: string;
  delegatorPrincipal: string;
  delegatee: string;
  rootMandateId: string;
  amountCap?: Money;
  currency: Currency;
  scope: DelegationScope;
  expiresAtMs?: number;
  validFromMs?: number;
  depth: number;
  spentTotal: Money;
  status: DelegationStatus;
  evidence?: DelegationEvidence;
}
