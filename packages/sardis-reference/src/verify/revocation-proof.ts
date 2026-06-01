/**
 * verifyRevocationProof + computeOutcome — mirror `RevocationProof.verify` and
 * `Revocation.compute_outcome`.
 *
 * The decision hash binds the revocation identity + the full target list
 * (sorted by (kind, ref, killStatus)) + outcome + timestamp; the signature is
 * HMAC-SHA256 over `revocationId|targetKind|targetRef|outcome|decisionHash`.
 *
 * Fail-closed: `computeOutcome` returns `blocked_pending_downstream` if ANY
 * target is not confirmed dead (`killed` | `already_dead`), else `propagated`.
 */
import type { RevocationProof, PropagationTarget, RevocationStatus, KillStatus } from '../types/revocation.js';
import { canonicalize } from './canonical-json.js';
import { sha256Hex, hmacSha256Hex, constantTimeEqual } from '../crypto/hmac.js';

const CONFIRMED_DEAD: ReadonlySet<KillStatus> = new Set<KillStatus>(['killed', 'already_dead']);

/** Mirrors `compute_outcome` — fail-closed on any unconfirmed target. */
export function computeOutcome(targets: PropagationTarget[]): RevocationStatus {
  const anyUnconfirmed = targets.some((t) => !CONFIRMED_DEAD.has(t.killStatus));
  return anyUnconfirmed ? 'blocked_pending_downstream' : 'propagated';
}

/** Canonical decision payload — mirrors `_canonical_decision`. */
function canonicalDecision(proof: RevocationProof): string {
  const sorted = [...proof.targets].sort((a, b) => {
    if (a.kind !== b.kind) return a.kind < b.kind ? -1 : 1;
    if (a.ref !== b.ref) return a.ref < b.ref ? -1 : 1;
    if (a.killStatus !== b.killStatus) return a.killStatus < b.killStatus ? -1 : 1;
    return 0;
  });
  return canonicalize({
    revocation_id: proof.revocationId,
    target_kind: proof.targetKind,
    target_ref: proof.targetRef,
    scope: proof.scope,
    requested_by: proof.requestedBy,
    revoked_at: proof.revokedAt,
    outcome: proof.outcome,
    targets: sorted.map((t) => ({
      kind: t.kind,
      ref: t.ref,
      kill_status: t.killStatus,
      detail: t.detail ?? '',
    })),
  });
}

export function computeDecisionHash(proof: RevocationProof): string {
  return sha256Hex(canonicalDecision(proof));
}

export function computeSignature(proof: RevocationProof, secret: string): string {
  const msg = [proof.revocationId, proof.targetKind, proof.targetRef, proof.outcome, proof.decisionHash].join('|');
  return hmacSha256Hex(secret, msg);
}

export function verifyRevocationProof(proof: RevocationProof, secret: string): boolean {
  if (proof.decisionHash !== computeDecisionHash(proof)) {
    return false;
  }
  return constantTimeEqual(proof.signature, computeSignature(proof, secret));
}
