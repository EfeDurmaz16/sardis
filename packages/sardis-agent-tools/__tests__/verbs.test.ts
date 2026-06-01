import { describe, it, expect } from 'vitest';
import { runGoverned } from '../src/index.js';
import { mockSardis, ctxFor } from './helpers.js';

describe('verb routing — each verb maps to the right Sardis SDK call', () => {
  it('sardis_give_wallet -> wallets.create({ agent_id })', async () => {
    const { client, calls } = mockSardis();
    const res = await runGoverned('sardis_give_wallet', { currency: 'USDC' }, ctxFor(client));
    expect(res.status).toBe('executed');
    expect(res.outcome).toBe('allow');
    expect(calls).toEqual([
      { method: 'wallets.create', args: [{ agent_id: 'agt_test', currency: 'USDC' }] },
    ]);
  });

  it('sardis_spend (below threshold) -> client.pay({ from, to, amount })', async () => {
    const { client, calls } = mockSardis();
    const res = await runGoverned(
      'sardis_spend',
      { to: 'aws.com', amount: '12.50', purpose: 'cloud' },
      ctxFor(client),
    );
    expect(res.status).toBe('executed');
    expect(calls).toEqual([
      { method: 'pay', args: [{ from: 'wal_test', to: 'aws.com', amount: '12.50', memo: 'cloud' }] },
    ]);
  });

  it('sardis_spend (above threshold) -> awaiting_approval, no pay() call', async () => {
    const { client, calls } = mockSardis();
    const res = await runGoverned('sardis_spend', { to: 'm', amount: '5000' }, ctxFor(client));
    expect(res.status).toBe('awaiting_approval');
    expect(res.outcome).toBe('requires_approval');
    expect(calls).toHaveLength(0); // money path NEVER touched
  });

  it('sardis_issue_card -> cards.issue({ wallet_id })', async () => {
    const { client, calls } = mockSardis();
    await runGoverned('sardis_issue_card', { limitDaily: '100' }, ctxFor(client));
    expect(calls).toEqual([
      { method: 'cards.issue', args: [{ wallet_id: 'wal_test', limit_daily: '100' }] },
    ]);
  });

  it('sardis_set_budget -> policies.apply(policy, agentId)', async () => {
    const { client, calls } = mockSardis();
    const res = await runGoverned(
      'sardis_set_budget',
      { policy: 'Allow up to $50/day on AI APIs' },
      ctxFor(client),
    );
    expect(res.outcome).toBe('allow');
    expect(calls).toEqual([
      { method: 'policies.apply', args: ['Allow up to $50/day on AI APIs', 'agt_test'] },
    ]);
  });

  it('sardis_pay_invoice with mandate -> payments.executeMandate(mandate)', async () => {
    const { client, calls } = mockSardis();
    const mandate = { type: 'ap2', amount: '10' };
    await runGoverned('sardis_pay_invoice', { mandate }, ctxFor(client));
    expect(calls).toEqual([{ method: 'payments.executeMandate', args: [mandate] }]);
  });

  it('sardis_pay_invoice without mandate falls back to client.pay', async () => {
    const { client, calls } = mockSardis();
    await runGoverned('sardis_pay_invoice', { to: 'm', amount: '5' }, ctxFor(client));
    expect(calls).toEqual([{ method: 'pay', args: [{ from: 'wal_test', to: 'm', amount: '5' }] }]);
  });

  it('sardis_pay_invoice above threshold (fallback path) awaits approval, no call', async () => {
    const { client, calls } = mockSardis();
    const res = await runGoverned('sardis_pay_invoice', { to: 'm', amount: '900' }, ctxFor(client));
    expect(res.status).toBe('awaiting_approval');
    expect(calls).toHaveLength(0);
  });

  it('sardis_check_balance -> wallets.getBalance(walletId, chain, token)', async () => {
    const { client, calls } = mockSardis();
    await runGoverned('sardis_check_balance', { chain: 'tempo', token: 'EURC' }, ctxFor(client));
    expect(calls).toEqual([{ method: 'wallets.getBalance', args: ['wal_test', 'tempo', 'EURC'] }]);
  });

  it('sardis_check_policy -> policies.check({ agent_id, amount, merchant_id })', async () => {
    const { client, calls } = mockSardis();
    await runGoverned('sardis_check_policy', { to: 'm', amount: '20' }, ctxFor(client));
    expect(calls).toEqual([
      { method: 'policies.check', args: [{ agent_id: 'agt_test', amount: '20', merchant_id: 'm' }] },
    ]);
  });

  it('sardis_list_transactions -> ledger.listEntries({ wallet_id, limit })', async () => {
    const { client, calls } = mockSardis();
    await runGoverned('sardis_list_transactions', { limit: 5 }, ctxFor(client));
    expect(calls).toEqual([{ method: 'ledger.listEntries', args: [{ wallet_id: 'wal_test', limit: 5 }] }]);
  });

  it('sardis_freeze_card -> cards.freeze(cardId)', async () => {
    const { client, calls } = mockSardis();
    await runGoverned('sardis_freeze_card', { cardId: 'card_1' }, ctxFor(client));
    expect(calls).toEqual([{ method: 'cards.freeze', args: ['card_1'] }]);
  });

  it('a backend error surfaces as blocked/deny without crashing the loop', async () => {
    const { client } = mockSardis({
      pay: () => {
        throw new Error('insufficient balance');
      },
    });
    const res = await runGoverned('sardis_spend', { to: 'm', amount: '5' }, ctxFor(client));
    expect(res.status).toBe('blocked');
    expect(res.outcome).toBe('deny');
    expect(res.error).toBe('insufficient balance');
  });

  it('spend with no wallet in context fails closed (blocked, not executed)', async () => {
    const { client, calls } = mockSardis();
    const res = await runGoverned(
      'sardis_spend',
      { to: 'm', amount: '5' },
      ctxFor(client, { walletId: undefined }),
    );
    expect(res.status).toBe('blocked');
    expect(calls).toHaveLength(0);
  });
});
