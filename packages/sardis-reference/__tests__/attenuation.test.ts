import { describe, it, expect } from 'vitest';
import { checkAttenuation, resolveChain, scopeIsSubset, type ParentBounds } from '../src/policy/attenuation.js';
import { MAX_DELEGATION_DEPTH, type Delegation, type DelegationScope } from '../src/types/delegation.js';

const emptyScope = (): DelegationScope => ({ counterparties: [], categories: [], mcc: [], rails: [] });

function delegation(overrides: Partial<Delegation>): Delegation {
  return {
    id: 'dlg_test',
    delegatorKind: 'delegation',
    delegatorRef: 'parent',
    delegatorPrincipal: 'agentA',
    delegatee: 'agentB',
    rootMandateId: 'mandate_root',
    currency: 'USDC',
    scope: emptyScope(),
    depth: 1,
    spentTotal: { minor: 0n, currency: 'USDC' },
    status: 'active',
    ...overrides,
  };
}

describe('checkAttenuation — the cardinal narrowing rule', () => {
  const parent: ParentBounds = {
    remainingMinor: 50_000n,
    expiresAtMs: 2_000_000,
    scope: { counterparties: ['good.com', 'aws.com'], categories: ['cloud'], mcc: [], rails: ['usdc', 'card'] },
    depth: 0,
  };

  it('allows a properly narrowed child', () => {
    const child = delegation({
      amountCap: { minor: 20_000n, currency: 'USDC' },
      expiresAtMs: 1_000_000,
      scope: { counterparties: ['good.com'], categories: ['cloud'], mcc: [], rails: ['usdc'] },
      depth: 1,
    });
    expect(checkAttenuation(parent, child)).toEqual({ ok: true, reason: 'OK' });
  });

  it('rejects cap exceeding parent remaining', () => {
    const child = delegation({ amountCap: { minor: 60_000n, currency: 'USDC' }, expiresAtMs: 1_000_000, depth: 1 });
    expect(checkAttenuation(parent, child).reason).toBe('cap_exceeds_parent');
  });

  it('rejects an uncapped child under a capped parent', () => {
    const child = delegation({ amountCap: undefined, expiresAtMs: 1_000_000, depth: 1 });
    expect(checkAttenuation(parent, child).reason).toBe('cap_exceeds_parent');
  });

  it('rejects expiry beyond parent', () => {
    const child = delegation({ amountCap: { minor: 1n, currency: 'USDC' }, expiresAtMs: 3_000_000, depth: 1 });
    expect(checkAttenuation(parent, child).reason).toBe('expiry_exceeds_parent');
  });

  it('rejects a widened scope dimension', () => {
    const child = delegation({
      amountCap: { minor: 1n, currency: 'USDC' },
      expiresAtMs: 1_000_000,
      scope: { counterparties: ['evil.com'], categories: [], mcc: [], rails: [] },
      depth: 1,
    });
    expect(checkAttenuation(parent, child).reason).toBe('scope_widened:counterparties');
  });

  it('rejects wrong depth / too deep', () => {
    const child = delegation({ amountCap: { minor: 1n, currency: 'USDC' }, expiresAtMs: 1_000_000, depth: 3 });
    expect(checkAttenuation(parent, child).reason).toBe('depth_exceeded');

    const deepParent: ParentBounds = { ...parent, depth: MAX_DELEGATION_DEPTH };
    const tooDeep = delegation({ amountCap: { minor: 1n, currency: 'USDC' }, expiresAtMs: 1_000_000, depth: MAX_DELEGATION_DEPTH + 1 });
    expect(checkAttenuation(deepParent, tooDeep).reason).toBe('depth_exceeded');
  });
});

describe('scopeIsSubset', () => {
  it('empty parent dimension imposes no restriction', () => {
    expect(scopeIsSubset({ counterparties: ['x'], categories: [], mcc: [], rails: [] }, emptyScope()).ok).toBe(true);
  });
  it('child must be subset of a non-empty parent dimension', () => {
    const r = scopeIsSubset(
      { counterparties: ['x', 'z'], categories: [], mcc: [], rails: [] },
      { counterparties: ['x', 'y'], categories: [], mcc: [], rails: [] },
    );
    expect(r.ok).toBe(false);
    expect(r.dim).toBe('counterparties');
  });
});

describe('resolveChain — fail-closed whole-chain re-check', () => {
  const root: ParentBounds = {
    remainingMinor: 100_000n,
    expiresAtMs: 5_000_000,
    scope: { counterparties: ['a.com', 'b.com'], categories: ['cloud'], mcc: [], rails: ['usdc'] },
    depth: 0,
  };

  const hop1 = delegation({
    id: 'dlg1',
    amountCap: { minor: 50_000n, currency: 'USDC' },
    expiresAtMs: 4_000_000,
    scope: { counterparties: ['a.com'], categories: ['cloud'], mcc: [], rails: ['usdc'] },
    depth: 1,
  });
  const hop2 = delegation({
    id: 'dlg2',
    amountCap: { minor: 20_000n, currency: 'USDC' },
    expiresAtMs: 3_000_000,
    scope: { counterparties: ['a.com'], categories: ['cloud'], mcc: [], rails: ['usdc'] },
    depth: 2,
  });

  it('accepts a valid root→leaf chain', () => {
    expect(resolveChain(root, [hop1, hop2], { now: 1_000_000 })).toEqual({ ok: true, reason: 'OK' });
  });

  it('fails closed on a revoked hop', () => {
    const revoked = { ...hop2, status: 'revoked' as const };
    expect(resolveChain(root, [hop1, revoked], { now: 1_000_000 }).reason).toBe('hop_revoked');
  });

  it('fails closed on an expired hop', () => {
    expect(resolveChain(root, [hop1, hop2], { now: 3_500_000 }).reason).toBe('hop_expired');
  });

  it('fails closed on an exhausted hop', () => {
    const exhausted = { ...hop2, spentTotal: { minor: 20_000n, currency: 'USDC' } };
    expect(resolveChain(root, [hop1, exhausted], { now: 1_000_000 }).reason).toBe('hop_exhausted');
  });

  it('fails closed when a deeper hop widens the cap above its parent', () => {
    const widened = { ...hop2, amountCap: { minor: 60_000n, currency: 'USDC' } };
    expect(resolveChain(root, [hop1, widened], { now: 1_000_000 }).reason).toBe('cap_exceeds_parent');
  });
});
