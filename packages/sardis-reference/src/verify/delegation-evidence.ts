/**
 * verifyDelegationEvidence — mirrors `DelegationEvidence.verify`.
 *
 * Recompute the `decisionHash` (SHA-256 of the canonical decision payload),
 * then check the HMAC-SHA256 over `id|delegatorRef|delegatee|rootMandateId|
 * decisionHash`. Returns false on any mismatch.
 *
 * NOTE: HMAC is symmetric — this is *internal* tamper-evidence only. Portable,
 * public verification is the job of the Ed25519 AuthorityProof. Verification
 * here requires the same secret that signed it.
 */
import type { DelegationEvidence } from '../types/delegation.js';
import { canonicalize } from './canonical-json.js';
import { sha256Hex, hmacSha256Hex, constantTimeEqual } from '../crypto/hmac.js';

/** Canonical decision payload — mirrors `_canonical_decision`. */
function canonicalDecision(ev: DelegationEvidence): string {
  return canonicalize({
    delegation_id: ev.delegationId,
    delegator_kind: ev.delegatorKind,
    delegator_ref: ev.delegatorRef,
    delegator_principal: ev.delegatorPrincipal,
    delegatee: ev.delegatee,
    root_mandate_id: ev.rootMandateId,
    depth: ev.depth,
    amount_cap: ev.amountCap,
    currency: ev.currency,
    expires_at: ev.expiresAt,
    scope_hash: ev.scopeHash,
    created_at: ev.createdAt,
  });
}

export function computeDecisionHash(ev: DelegationEvidence): string {
  return sha256Hex(canonicalDecision(ev));
}

export function computeSignature(ev: DelegationEvidence, secret: string): string {
  const msg = [ev.delegationId, ev.delegatorRef, ev.delegatee, ev.rootMandateId, ev.decisionHash].join('|');
  return hmacSha256Hex(secret, msg);
}

export function verifyDelegationEvidence(ev: DelegationEvidence, secret: string): boolean {
  if (ev.decisionHash !== computeDecisionHash(ev)) {
    return false;
  }
  return constantTimeEqual(ev.signature, computeSignature(ev, secret));
}
