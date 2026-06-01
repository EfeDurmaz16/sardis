import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { simulateSpend, checkExecutionContext } from '../src/policy/simulator.js';
import { createDefaultPolicy } from '../src/policy/defaults.js';
import { getMccInfo, isBlockedCategory } from '../src/policy/mcc.js';
import { categoriesMatch } from '../src/policy/category-match.js';
import { deserializePolicy, deserializeSpend } from './helpers.js';
import type { SpendingPolicy } from '../src/types/policy.js';
import type { SpendObject } from '../src/types/spend.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface PolicyVector {
  name: string;
  policy: Record<string, unknown>;
  spend: Record<string, unknown>;
  now: number;
  expected: { outcome: string; reason: string };
}

const vectors: PolicyVector[] = JSON.parse(
  readFileSync(join(__dirname, 'vectors', 'policy-decisions.json'), 'utf8'),
);

describe('simulateSpend — golden vectors (cross-language fidelity vs Python)', () => {
  for (const v of vectors) {
    it(`${v.name} → ${v.expected.outcome} (${v.expected.reason})`, () => {
      const policy = deserializePolicy(v.policy);
      const spend = deserializeSpend(v.spend);
      const decision = simulateSpend(policy, spend, { now: v.now });
      expect(decision.outcome).toBe(v.expected.outcome);
      expect(decision.reason).toBe(v.expected.reason);
    });
  }

  it('covers at least one allow, one requires_approval, and one deny', () => {
    const outcomes = new Set(vectors.map((v) => v.expected.outcome));
    expect(outcomes.has('allow')).toBe(true);
    expect(outcomes.has('requires_approval')).toBe(true);
    expect(outcomes.has('deny')).toBe(true);
  });
});

describe('simulateSpend — window rollover (deterministic, injectable now)', () => {
  function policyWithDaily(start: number): SpendingPolicy {
    const p = createDefaultPolicy('a', 'low', { now: start });
    // Seed the daily window at its limit so any spend would exceed it.
    p.daily = {
      windowType: 'daily',
      limit: { minor: 10_000n, currency: 'USDC' },
      currentSpent: { minor: 10_000n, currency: 'USDC' },
      windowStartMs: start,
    };
    return p;
  }
  const spend: SpendObject = { amount: { minor: 100n, currency: 'USDC' } };

  it('denies before the window expires', () => {
    const p = policyWithDaily(0);
    const d = simulateSpend(p, spend, { now: 1000 });
    expect(d.outcome).toBe('deny');
    expect(d.reason).toBe('time_window_limit');
  });

  it('allows after the daily window rolls over (now past start + 24h)', () => {
    const p = policyWithDaily(0);
    const dayMs = 24 * 60 * 60 * 1000;
    const d = simulateSpend(p, spend, { now: dayMs + 1 });
    expect(d.outcome).toBe('allow');
  });
});

describe('checkExecutionContext — case-normalized allow/block lists', () => {
  const base = createDefaultPolicy('a', 'low');

  it('allows when chain/token within allowlists (case-insensitive)', () => {
    const p: SpendingPolicy = { ...base, allowedChains: ['base'], allowedTokens: ['usdc'] };
    const d = checkExecutionContext(p, { amount: { minor: 1n, currency: 'USDC' }, chain: 'BASE', token: 'USDC' });
    expect(d.outcome).toBe('allow');
  });

  it('denies chain not on allowlist', () => {
    const p: SpendingPolicy = { ...base, allowedChains: ['base'] };
    const d = checkExecutionContext(p, { amount: { minor: 1n, currency: 'USDC' }, chain: 'polygon' });
    expect(d.reason).toBe('chain_not_allowlisted');
  });

  it('denies token not on allowlist', () => {
    const p: SpendingPolicy = { ...base, allowedTokens: ['USDC'] };
    const d = checkExecutionContext(p, { amount: { minor: 1n, currency: 'USDC' }, token: 'usdt' });
    expect(d.reason).toBe('token_not_allowlisted');
  });

  it('denies blocked destination', () => {
    const p: SpendingPolicy = { ...base, blockedDestinations: ['0xDEAD'] };
    const d = checkExecutionContext(p, { amount: { minor: 1n, currency: 'USDC' }, destination: '0xdead' });
    expect(d.reason).toBe('destination_blocked');
  });

  it('requires destination when an allowlist is present and none given', () => {
    const p: SpendingPolicy = { ...base, allowedDestinations: ['0xabc'] };
    const d = checkExecutionContext(p, { amount: { minor: 1n, currency: 'USDC' } });
    expect(d.reason).toBe('destination_required_for_allowlist');
  });
});

describe('MCC static mirror (category heuristics; fail-closed on unknown)', () => {
  it('blocks a known high-risk default-blocked code', () => {
    const p: SpendingPolicy = { ...createDefaultPolicy('a', 'low') };
    const d = simulateSpend(p, { amount: { minor: 100n, currency: 'USDC' }, mccCode: '7995' });
    expect(d.outcome).toBe('deny');
    expect(d.reason).toContain('high_risk_merchant');
  });

  it('blocks an unknown MCC against a blocked category (fail-closed)', () => {
    const p: SpendingPolicy = { ...createDefaultPolicy('a', 'low'), blockedMerchantCategories: ['gambling'] };
    const d = simulateSpend(p, { amount: { minor: 100n, currency: 'USDC' }, mccCode: '9999' });
    expect(d.outcome).toBe('deny');
    expect(d.reason).toContain('merchant_category_blocked');
  });

  it('allows a low-risk known code with no blocked categories', () => {
    const p: SpendingPolicy = { ...createDefaultPolicy('a', 'low') };
    const d = simulateSpend(p, { amount: { minor: 100n, currency: 'USDC' }, mccCode: '5411' });
    expect(d.outcome).toBe('allow');
  });

  it('isBlockedCategory fails closed on unknown code', () => {
    expect(isBlockedCategory('9999', [])).toBe(true);
    expect(getMccInfo('9999')).toBeNull();
  });
});

describe('categoriesMatch — singular/plural normalization', () => {
  it('matches groceries↔grocery', () => {
    expect(categoriesMatch('grocery', 'groceries')).toBe(true);
    expect(categoriesMatch('groceries', 'grocery')).toBe(true);
  });
  it('matches alcohol↔alcohols', () => {
    expect(categoriesMatch('alcohol', 'alcohols')).toBe(true);
    expect(categoriesMatch('alcohols', 'alcohol')).toBe(true);
  });
  it('does not match unrelated', () => {
    expect(categoriesMatch('alcohol', 'gambling')).toBe(false);
  });
});
