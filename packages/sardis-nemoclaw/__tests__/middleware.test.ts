import { describe, it, expect } from 'vitest';
import type { Sardis } from 'sardis';
import { governedSpend, governedToolCall, createNemoTools, type SardisNemoContext } from '../src/index.js';

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
function ctx(client: Sardis, sandboxId: string): SardisNemoContext {
  return { client, walletId: 'wal_n', agentId: 'agt_n', approvalThreshold: '50', sandboxId };
}

describe('@sardis/nemoclaw — sandbox-bound governance', () => {
  it('governedSpend executes a low spend and routes the REAL args to the SDK', async () => {
    const { client, calls } = mockSardis();
    const res = await governedSpend(ctx(client, 'sbx_1'), { to: 'm', amount: '10', purpose: 'x' });
    expect(res.status).toBe('executed');
    expect(res.outcome).toBe('allow');
    expect(res.commitHash).toMatch(/^sardis_/);
    // The sandbox envelope must NOT leak into the money call.
    expect(calls).toEqual([
      { method: 'pay', args: [{ from: 'wal_n', to: 'm', amount: '10', memo: 'x' }] },
    ]);
  });

  it('binds the sandboxId into the commit hash (different sandbox -> different hash)', async () => {
    const { client } = mockSardis();
    const a = await governedSpend(ctx(client, 'sbx_A'), { to: 'm', amount: '10' });
    const b = await governedSpend(ctx(client, 'sbx_B'), { to: 'm', amount: '10' });
    expect(a.commitHash).not.toBe(b.commitHash);
    // same sandbox + same action -> stable hash
    const a2 = await governedSpend(ctx(client, 'sbx_A'), { to: 'm', amount: '10' });
    expect(a.commitHash).toBe(a2.commitHash);
  });

  it('a high spend awaits approval and never calls the SDK', async () => {
    const { client, calls } = mockSardis();
    const res = await governedSpend(ctx(client, 'sbx_1'), { to: 'm', amount: '9999' });
    expect(res.status).toBe('awaiting_approval');
    expect(res.outcome).toBe('requires_approval');
    expect(calls).toHaveLength(0);
  });

  it('unknown tool fails closed', async () => {
    const { client, calls } = mockSardis();
    const res = await governedToolCall('sardis_unknown', {}, ctx(client, 'sbx_1'), async () => ({}));
    expect(res.status).toBe('blocked');
    expect(res.outcome).toBe('deny');
    expect(calls).toHaveLength(0);
  });

  it('createNemoTools exposes all verbs bound to the sandbox', async () => {
    const { client, calls } = mockSardis();
    const tools = createNemoTools(ctx(client, 'sbx_1'));
    expect(Object.keys(tools)).toContain('sardis_give_wallet');
    const res = await tools.sardis_give_wallet!({ currency: 'USDC' });
    expect(res.status).toBe('executed');
    expect(calls[0]).toEqual({
      method: 'wallets.create',
      args: [{ agent_id: 'agt_n', currency: 'USDC' }],
    });
  });

  it('userId also binds into the commit when present', async () => {
    const { client } = mockSardis();
    const base = ctx(client, 'sbx_1');
    const noUser = await governedSpend(base, { to: 'm', amount: '10' });
    const withUser = await governedSpend({ ...base, userId: 'usr_9' }, { to: 'm', amount: '10' });
    expect(noUser.commitHash).not.toBe(withUser.commitHash);
  });
});
