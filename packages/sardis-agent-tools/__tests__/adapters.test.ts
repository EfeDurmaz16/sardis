import { describe, it, expect } from 'vitest';
import { createSardisLangChainTools } from '../src/adapters/langchain.js';
import { createVercelAiTools } from '../src/adapters/vercel-ai.js';
import { createMcpTools } from '../src/adapters/mcp.js';
import { mockSardis, ctxFor } from './helpers.js';

const VERBS = [
  'sardis_give_wallet',
  'sardis_spend',
  'sardis_issue_card',
  'sardis_set_budget',
  'sardis_pay_invoice',
  'sardis_check_balance',
  'sardis_check_policy',
  'sardis_list_transactions',
  'sardis_freeze_card',
];

describe('langchain adapter', () => {
  it('exposes all verbs as structured tools', () => {
    const tools = createSardisLangChainTools(ctxFor(mockSardis().client));
    expect(tools.map((t) => t.name).sort()).toEqual([...VERBS].sort());
    for (const t of tools) {
      expect(typeof t.description).toBe('string');
      expect(t.schema).toBeDefined();
      expect(typeof t.invoke).toBe('function');
    }
  });

  it('invoke returns governed JSON and routes to the SDK', async () => {
    const { client, calls } = mockSardis();
    const tools = createSardisLangChainTools(ctxFor(client));
    const spend = tools.find((t) => t.name === 'sardis_spend')!;
    const out = JSON.parse(await spend.invoke({ to: 'm', amount: '5' }));
    expect(out.status).toBe('executed');
    expect(out.outcome).toBe('allow');
    expect(out.commitHash).toMatch(/^sardis_/);
    expect(calls[0]?.method).toBe('pay');
  });

  it('invoke surfaces requires_approval without calling the SDK', async () => {
    const { client, calls } = mockSardis();
    const tools = createSardisLangChainTools(ctxFor(client));
    const spend = tools.find((t) => t.name === 'sardis_spend')!;
    const out = JSON.parse(await spend.invoke({ to: 'm', amount: '9999' }));
    expect(out.status).toBe('awaiting_approval');
    expect(out.outcome).toBe('requires_approval');
    expect(calls).toHaveLength(0);
  });
});

describe('vercel-ai adapter', () => {
  it('returns a tool map with description/parameters/execute', () => {
    const tools = createVercelAiTools(ctxFor(mockSardis().client));
    expect(Object.keys(tools).sort()).toEqual([...VERBS].sort());
    for (const t of Object.values(tools)) {
      expect(typeof t.description).toBe('string');
      expect(t.parameters).toBeDefined();
      expect(typeof t.execute).toBe('function');
    }
  });

  it('execute returns the GovernedResult and routes to the SDK', async () => {
    const { client, calls } = mockSardis();
    const tools = createVercelAiTools(ctxFor(client));
    const res = await tools.sardis_set_budget!.execute({ policy: 'cap $10/day' });
    expect(res.status).toBe('executed');
    expect(calls[0]?.method).toBe('policies.apply');
  });

  it('execute denies an unknown-amount spend as requires_approval, no SDK call', async () => {
    const { client, calls } = mockSardis();
    const tools = createVercelAiTools(ctxFor(client));
    const res = await tools.sardis_spend!.execute({ to: 'm' }); // no amount
    expect(res.outcome).toBe('requires_approval');
    expect(calls).toHaveLength(0);
  });
});

describe('mcp adapter', () => {
  it('produces definitions + handlers in parity (one per verb)', () => {
    const { definitions, handlers } = createMcpTools(ctxFor(mockSardis().client));
    expect(definitions.map((d) => d.name).sort()).toEqual([...VERBS].sort());
    expect(Object.keys(handlers).sort()).toEqual([...VERBS].sort());
  });

  it('definitions carry a JSON-Schema object with the right required fields', () => {
    const { definitions } = createMcpTools(ctxFor(mockSardis().client));
    const spend = definitions.find((d) => d.name === 'sardis_spend')!;
    expect(spend.inputSchema.type).toBe('object');
    expect(spend.inputSchema.required).toContain('to');
    expect(spend.inputSchema.required).toContain('amount');
    expect(spend.inputSchema.properties.token).toMatchObject({ type: 'string' });
    // freeze_card requires cardId
    const freeze = definitions.find((d) => d.name === 'sardis_freeze_card')!;
    expect(freeze.inputSchema.required).toEqual(['cardId']);
  });

  it('handler returns a ToolResult whose text is the governed JSON', async () => {
    const { client, calls } = mockSardis();
    const { handlers } = createMcpTools(ctxFor(client));
    const result = await handlers.sardis_give_wallet!({ currency: 'USDC' });
    expect(result.isError).toBe(false);
    const body = JSON.parse(result.content[0]!.text);
    expect(body.status).toBe('executed');
    expect(body.outcome).toBe('allow');
    expect(calls[0]?.method).toBe('wallets.create');
  });

  it('handler reports a blocked verb in the body, not as a transport error', async () => {
    const { client } = mockSardis();
    const { handlers } = createMcpTools(ctxFor(client));
    // Spend above threshold -> awaiting_approval body, isError false.
    const result = await handlers.sardis_spend!({ to: 'm', amount: '9999' });
    expect(result.isError).toBe(false);
    expect(JSON.parse(result.content[0]!.text).status).toBe('awaiting_approval');
  });
});
