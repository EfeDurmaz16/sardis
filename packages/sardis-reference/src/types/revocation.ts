/**
 * Revocation — the propagating-revocation primitive.
 *
 * Mirrors `revocation.py`. Fail-closed: any target not confirmed dead makes the
 * overall outcome `blocked_pending_downstream`, never `propagated`.
 */

export type RevocationTargetKind = 'agent' | 'mandate' | 'principal' | 'delegation';

export type RevocationStatus = 'propagated' | 'blocked_pending_downstream';

export type PropagationKind =
  | 'mandate'
  | 'delegation'
  | 'spend_object'
  | 'card'
  | 'approval'
  | 'in_flight';

export type KillStatus = 'killed' | 'blocked_pending' | 'failed' | 'already_dead';

export interface PropagationTarget {
  kind: PropagationKind;
  ref: string;
  killStatus: KillStatus;
  detail?: string;
  /** ISO timestamp or null. */
  killedAt?: string | null;
}

/**
 * Signed, independently-verifiable revocation proof. HMAC-SHA256 over
 * `revocationId|targetKind|targetRef|outcome|decisionHash`. The decision hash
 * binds the full, sorted target list, so a truncated/tampered list fails.
 */
export interface RevocationProof {
  revocationId: string;
  targetKind: RevocationTargetKind;
  targetRef: string;
  scope: string;
  requestedBy: string;
  /** ISO timestamp. */
  revokedAt: string;
  outcome: RevocationStatus;
  targets: PropagationTarget[];
  decisionHash: string;
  signature: string;
}
