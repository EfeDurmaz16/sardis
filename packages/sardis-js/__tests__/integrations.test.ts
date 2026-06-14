import { describe, expect, it, vi } from 'vitest';
import { createSardisTools } from '../src/langchain/index.js';
import type { Sardis } from '../src/index.js';
import type { LangChainStructuredTool } from '../src/langchain/index.js';

// Regression for the `as unknown as { ... }` casts that called resource
// methods which did not exist or had the wrong signature (getBalance with an
// object arg, policies.applyFromNaturalLanguage, transactions.list, etc.).
// These compiled because the casts suppressed type-checking but failed at
// runtime. Removing the casts lets tsc validate the calls; these tests pin the
// argument shapes so a future regression is caught at runtime too.

function fakeClient() {
  return {
    wallets: { getBalance: vi.fn().mockResolvedValue({ balance: '10' }) },
    policies: {
      check: vi.fn().mockResolvedValue({ allowed: true }),
      apply: vi.fn().mockResolvedValue({ ok: true }),
    },
    ledger: { listEntries: vi.fn().mockResolvedValue([]) },
  };
}

function tool(tools: LangChainStructuredTool[], name: string): LangChainStructuredTool {
  const t = tools.find((x) => x.name === name);
  if (!t) throw new Error(`tool ${name} not found`);
  return t;
}

function build(client: ReturnType<typeof fakeClient>, agentId?: string) {
  return createSardisTools({
    client: client as unknown as Sardis,
    walletId: 'wal_1',
    apiKey: 'test',
    ...(agentId ? { agentId } : {}),
  });
}

describe('langchain adapter binds to real resource methods', () => {
  it('check_balance calls wallets.getBalance(walletId, chain, token) positionally', async () => {
    const c = fakeClient();
    await tool(build(c), 'sardis_check_balance').invoke({ token: 'EURC', chain: 'tempo' });
    expect(c.wallets.getBalance).toHaveBeenCalledWith('wal_1', 'tempo', 'EURC');
  });

  it('check_balance falls back to default chain/token', async () => {
    const c = fakeClient();
    await tool(build(c), 'sardis_check_balance').invoke({});
    expect(c.wallets.getBalance).toHaveBeenCalledWith('wal_1', 'base', 'USDC');
  });

  it('check_policy calls policies.check with the real {agent_id, amount, merchant_id} shape', async () => {
    const c = fakeClient();
    await tool(build(c, 'agt_1'), 'sardis_check_policy').invoke({ amount: '5', to: 'merchant.example' });
    expect(c.policies.check).toHaveBeenCalledWith({
      agent_id: 'agt_1',
      amount: '5',
      merchant_id: 'merchant.example',
    });
  });

  it('set_policy calls policies.apply(natural_language, agent_id)', async () => {
    const c = fakeClient();
    await tool(build(c, 'agt_1'), 'sardis_set_policy').invoke({ policy: 'max $50 per day' });
    expect(c.policies.apply).toHaveBeenCalledWith('max $50 per day', 'agt_1');
  });

  it('list_transactions calls ledger.listEntries (transactions.list never existed)', async () => {
    const c = fakeClient();
    await tool(build(c), 'sardis_list_transactions').invoke({ limit: 5 });
    expect(c.ledger.listEntries).toHaveBeenCalledWith({ wallet_id: 'wal_1', limit: 5 });
  });
});
