import { describe, it, expect } from 'vitest';
import { classifyAction } from '../src/classify.js';
import { compareDecimalStrings, extractAmount } from '../src/amount.js';
import { SardisToolRegistry } from '../src/registry.js';
import type { SardisToolContext } from '../src/types.js';

const ctx = { client: {} as never, walletId: 'w', agentId: 'a', approvalThreshold: '50' } as SardisToolContext;

describe('classifyAction', () => {
  it('give_wallet / set_budget are undoable', () => {
    expect(classifyAction('sardis_give_wallet', {}, ctx)).toBe('undoable');
    expect(classifyAction('sardis_set_budget', { policy: 'x' }, ctx)).toBe('undoable');
  });

  it('read + compensating verbs are undoable', () => {
    expect(classifyAction('sardis_check_balance', {}, ctx)).toBe('undoable');
    expect(classifyAction('sardis_check_policy', {}, ctx)).toBe('undoable');
    expect(classifyAction('sardis_list_transactions', {}, ctx)).toBe('undoable');
    expect(classifyAction('sardis_freeze_card', { cardId: 'c' }, ctx)).toBe('undoable');
  });

  it('issue_card is compensatable', () => {
    expect(classifyAction('sardis_issue_card', {}, ctx)).toBe('compensatable');
  });

  it('spend below threshold is compensatable, at/above is approval_only', () => {
    expect(classifyAction('sardis_spend', { to: 'm', amount: '49.99' }, ctx)).toBe('compensatable');
    expect(classifyAction('sardis_spend', { to: 'm', amount: '50' }, ctx)).toBe('approval_only');
    expect(classifyAction('sardis_spend', { to: 'm', amount: '50.01' }, ctx)).toBe('approval_only');
    expect(classifyAction('sardis_spend', { to: 'm', amount: '1000' }, ctx)).toBe('approval_only');
  });

  it('pay_invoice respects the same threshold', () => {
    expect(classifyAction('sardis_pay_invoice', { to: 'm', amount: '10' }, ctx)).toBe('compensatable');
    expect(classifyAction('sardis_pay_invoice', { to: 'm', amount: '500' }, ctx)).toBe('approval_only');
  });

  it('a custom threshold moves the boundary', () => {
    const big = { ...ctx, approvalThreshold: '1000' };
    expect(classifyAction('sardis_spend', { to: 'm', amount: '500' }, big)).toBe('compensatable');
  });

  it('spend with no parseable amount is conservatively approval_only', () => {
    expect(classifyAction('sardis_spend', { to: 'm' }, ctx)).toBe('approval_only');
  });

  it('unknown verb fails closed', () => {
    expect(classifyAction('sardis_drain_treasury', {}, ctx)).toBe('irreversible_blocked');
  });
});

describe('amount helpers', () => {
  it('extractAmount pulls string/number/bigint amounts', () => {
    expect(extractAmount({ amount: '12.5' })).toBe('12.5');
    expect(extractAmount({ amount: 12 })).toBe('12');
    expect(extractAmount({ amount: 5n })).toBe('5');
    expect(extractAmount({})).toBeNull();
  });

  it('compareDecimalStrings orders decimals correctly without floats', () => {
    expect(compareDecimalStrings('49.99', '50')).toBe(-1);
    expect(compareDecimalStrings('50', '50')).toBe(0);
    expect(compareDecimalStrings('50.00', '50')).toBe(0);
    expect(compareDecimalStrings('100', '50')).toBe(1);
    expect(compareDecimalStrings('9', '10')).toBe(-1); // length-aware integer compare
    expect(compareDecimalStrings('0.10', '0.1')).toBe(0);
    expect(compareDecimalStrings('0.2', '0.19')).toBe(1);
  });
});

describe('SardisToolRegistry — fail-closed unknown', () => {
  it('classify of an unregistered tool is irreversible_blocked', () => {
    const r = new SardisToolRegistry();
    expect(r.classify('nope', {}, ctx)).toBe('irreversible_blocked');
    expect(r.has('nope')).toBe(false);
  });
});
