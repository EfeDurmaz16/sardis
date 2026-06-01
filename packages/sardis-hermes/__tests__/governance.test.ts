import { describe, it, expect, vi } from 'vitest';
import type { Sardis } from 'sardis';
import type { SardisToolContext } from '@sardis/agent-tools';
import { createGovernanceMiddleware } from '../src/index.js';

interface RecordedCall {
  method: string;
  args: unknown[];
}
function mockSardis(): { client: Sardis; calls: RecordedCall[] } {
  const calls: RecordedCall[] = [];
  const rec =
    (method: string) =>
    async (...args: unknown[]) => {
      calls.push({ method, args });
      return { ok: true, method };
    };
  const client = {
    pay: rec('pay'),
    wallets: { create: rec('wallets.create'), getBalance: rec('wallets.getBalance') },
    cards: { issue: rec('cards.issue'), freeze: rec('cards.freeze') },
    policies: { apply: rec('policies.apply'), check: rec('policies.check') },
    payments: { executeMandate: rec('payments.executeMandate') },
    ledger: { listEntries: rec('ledger.listEntries') },
  } as unknown as Sardis;
  return { client, calls };
}
function ctx(client: Sardis): SardisToolContext {
  return { client, walletId: 'wal_h', agentId: 'agt_h', approvalThreshold: '50' };
}

describe('@sardis/hermes — GovernanceMiddleware.wrap', () => {
  it('pre-wraps the five verbs and a low spend executes via the SDK', async () => {
    const { client, calls } = mockSardis();
    const mw = createGovernanceMiddleware({ context: ctx(client) });
    const tools = mw.tools();
    expect(Object.keys(tools)).toContain('sardis_spend');

    const res = await tools.sardis_spend!({ to: 'm', amount: '10' });
    expect(res.status).toBe('executed');
    expect(res.outcome).toBe('allow');
    expect(res.commitHash).toMatch(/^sardis_/);
    expect(calls[0]?.method).toBe('pay');
  });

  it('blocks an unknown wrapped tool (fail-closed) and fires onBlocked', async () => {
    const { client, calls } = mockSardis();
    const onBlocked = vi.fn();
    const mw = createGovernanceMiddleware({ context: ctx(client), onBlocked });
    const governed = mw.wrap('sardis_unknown', async () => ({ nope: true }));
    const res = await governed({});
    expect(res.status).toBe('blocked');
    expect(res.outcome).toBe('deny');
    expect(onBlocked).toHaveBeenCalledOnce();
    expect(calls).toHaveLength(0);
  });

  it('a high spend awaits approval by default and does NOT execute', async () => {
    const { client, calls } = mockSardis();
    const mw = createGovernanceMiddleware({ context: ctx(client) });
    const tools = mw.tools();
    const res = await tools.sardis_spend!({ to: 'm', amount: '5000' });
    expect(res.status).toBe('awaiting_approval');
    expect(res.outcome).toBe('requires_approval');
    expect(calls).toHaveLength(0);
  });

  it('onApprovalNeeded returning true lets a high spend execute', async () => {
    const { client, calls } = mockSardis();
    const onApprovalNeeded = vi.fn().mockResolvedValue(true);
    const mw = createGovernanceMiddleware({ context: ctx(client), onApprovalNeeded });
    const tools = mw.tools();
    const res = await tools.sardis_spend!({ to: 'm', amount: '5000' });
    expect(onApprovalNeeded).toHaveBeenCalledOnce();
    expect(res.status).toBe('executed');
    // the record keeps the true reversibility class even after approval
    expect(res.reversibilityClass).toBe('approval_only');
    expect(calls[0]?.method).toBe('pay');
  });

  it('onApprovalNeeded returning false keeps it awaiting_approval, no SDK call', async () => {
    const { client, calls } = mockSardis();
    const onApprovalNeeded = vi.fn().mockResolvedValue(false);
    const mw = createGovernanceMiddleware({ context: ctx(client), onApprovalNeeded });
    const res = await mw.tools().sardis_pay_invoice!({ to: 'm', amount: '900' });
    expect(res.status).toBe('awaiting_approval');
    expect(calls).toHaveLength(0);
  });

  it('wrap works for an arbitrary (non-verb) governed fn', async () => {
    const { client } = mockSardis();
    const mw = createGovernanceMiddleware({ context: ctx(client) });
    const governed = mw.wrap('sardis_set_budget', async () => ({ applied: true }));
    const res = await governed({ policy: 'cap $10/day' });
    expect(res.status).toBe('executed');
    expect(res.result).toEqual({ applied: true });
  });
});
