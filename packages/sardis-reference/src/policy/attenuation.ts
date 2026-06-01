/**
 * Attenuation — the object-capability cardinal rule from `delegation.py`:
 * a child delegation may only NARROW its parent. Authority shrinks downward.
 *
 *   cap      <= parent.remaining
 *   expiry   <= parent.expiry
 *   scope    subset-of parent.scope (per dimension)
 *   depth    = parent.depth + 1  and  <= MAX_DELEGATION_DEPTH
 *
 * `resolveChain` re-checks a whole chain root→leaf, fail-closed on any revoked /
 * expired / over-cap / out-of-scope hop (mirrors "the WHOLE chain is re-checked
 * at execution time").
 */
import type { Delegation, DelegationScope, DelegationStatus } from '../types/delegation.js';
import { MAX_DELEGATION_DEPTH } from '../types/delegation.js';

export interface AttenuationResult {
  ok: boolean;
  reason: string;
}

/** A "parent" can be a delegation or the root authority bounds. */
export interface ParentBounds {
  /** parent remaining cap in minor units, or null if uncapped. */
  remainingMinor: bigint | null;
  /** parent expiry (epoch ms), or null if no expiry. */
  expiresAtMs: number | null;
  scope: DelegationScope;
  depth: number;
}

function scopeDimensionSubset(child: string[], parent: string[]): boolean {
  // Empty parent dimension = "no further restriction at this hop" — any child
  // dimension is acceptable (the parent's own ancestors still constrain it).
  if (parent.length === 0) return true;
  // Empty child = inherits parent (narrower-or-equal) — acceptable.
  if (child.length === 0) return true;
  const parentSet = new Set(parent);
  return child.every((c) => parentSet.has(c));
}

/** Whether `child` scope is a subset of `parent` across all four dimensions. */
export function scopeIsSubset(child: DelegationScope, parent: DelegationScope): { ok: boolean; dim?: string } {
  if (!scopeDimensionSubset(child.counterparties, parent.counterparties)) return { ok: false, dim: 'counterparties' };
  if (!scopeDimensionSubset(child.categories, parent.categories)) return { ok: false, dim: 'categories' };
  if (!scopeDimensionSubset(child.mcc, parent.mcc)) return { ok: false, dim: 'mcc' };
  if (!scopeDimensionSubset(child.rails, parent.rails)) return { ok: false, dim: 'rails' };
  return { ok: true };
}

/** Check that `child` is a valid attenuation of `parent`. */
export function checkAttenuation(parent: ParentBounds, child: Delegation): AttenuationResult {
  // Cap: child cap must not exceed parent remaining.
  if (parent.remainingMinor != null) {
    const childCap = child.amountCap?.minor;
    // An uncapped child under a capped parent widens authority → reject.
    if (childCap == null || childCap > parent.remainingMinor) {
      return { ok: false, reason: 'cap_exceeds_parent' };
    }
  }

  // Expiry: child expiry must not exceed parent expiry.
  if (parent.expiresAtMs != null) {
    if (child.expiresAtMs == null || child.expiresAtMs > parent.expiresAtMs) {
      return { ok: false, reason: 'expiry_exceeds_parent' };
    }
  }

  // Scope: per-dimension subset.
  const sub = scopeIsSubset(child.scope, parent.scope);
  if (!sub.ok) {
    return { ok: false, reason: `scope_widened:${sub.dim}` };
  }

  // Depth.
  if (child.depth !== parent.depth + 1 || child.depth > MAX_DELEGATION_DEPTH) {
    return { ok: false, reason: 'depth_exceeded' };
  }

  return { ok: true, reason: 'OK' };
}

const TERMINAL: ReadonlySet<DelegationStatus> = new Set<DelegationStatus>(['revoked', 'expired', 'exhausted']);

/**
 * Re-check a whole chain root→leaf (ordered: root mandate bounds first, then
 * each delegation hop). Fail-closed on the first broken link.
 *
 * `rootBounds` is the root mandate's authority surface; `chain` is the ordered
 * list of delegation hops (depth 1..N). `now` gates expiry/exhaustion.
 */
export function resolveChain(
  rootBounds: ParentBounds,
  chain: Delegation[],
  opts: { now?: number } = {},
): AttenuationResult {
  const now = opts.now ?? 0;
  let parent = rootBounds;
  for (const hop of chain) {
    // Lifecycle of this hop.
    if (TERMINAL.has(hop.status)) {
      return { ok: false, reason: `hop_${hop.status}` };
    }
    if (hop.expiresAtMs != null && now > hop.expiresAtMs) {
      return { ok: false, reason: 'hop_expired' };
    }
    if (hop.amountCap != null && hop.spentTotal.minor >= hop.amountCap.minor) {
      return { ok: false, reason: 'hop_exhausted' };
    }
    // Attenuation against the running parent.
    const att = checkAttenuation(parent, hop);
    if (!att.ok) {
      return att;
    }
    // Descend: this hop becomes the parent of the next.
    parent = {
      remainingMinor: hop.amountCap != null ? hop.amountCap.minor - hop.spentTotal.minor : null,
      expiresAtMs: hop.expiresAtMs ?? null,
      scope: hop.scope,
      depth: hop.depth,
    };
  }
  return { ok: true, reason: 'OK' };
}
