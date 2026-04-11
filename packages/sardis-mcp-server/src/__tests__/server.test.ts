/**
 * Server startup and tool-registration smoke tests.
 *
 * These exercise the top-level `createServer()` factory (not just the tool
 * registry helpers) to make sure the MCP Server instance can be constructed,
 * advertises the expected tool list, and dispatches a representative tool
 * call without requiring a live API key.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ListPromptsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { createServer } from '../index.js';
import { allToolDefinitions } from '../tools/index.js';
import packageJson from '../../package.json' with { type: 'json' };

vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    agentId: 'agent_test_123',
    apiKey: '',
    apiUrl: 'https://api.sardis.sh',
    chain: 'base_sepolia',
    mode: 'simulated',
    policyBlockedVendors: [],
    policyAllowedVendors: [],
    requireExplicitApproval: false,
    fetchAgentPolicy: false,
  })),
  getAllowedVendors: vi.fn(() => []),
  getBlockedVendors: vi.fn(() => []),
}));

// Grab the handlers registered against the Server so we can invoke them
// without spinning up a transport.
function extractHandlers(server: any): Map<any, any> {
  const impl =
    server._requestHandlers ??
    server.requestHandlers ??
    server['_requestHandlers'];
  return impl as Map<any, any>;
}

async function invoke(server: any, schema: any, params: Record<string, unknown> = {}) {
  const handlers = extractHandlers(server);
  const method = schema.shape.method.value;
  const handler =
    handlers.get(method) ??
    [...handlers.entries()].find(([key]) => key === method || (key as any)?.method === method)?.[1];

  if (!handler) {
    throw new Error(`No handler registered for ${method}`);
  }
  return handler({ method, params }, {});
}

describe('MCP Server startup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('instantiates without throwing', async () => {
    const server = await createServer();
    expect(server).toBeDefined();
  });

  it('advertises all modular tools via ListTools', async () => {
    const server = await createServer();
    const result = await invoke(server, ListToolsRequestSchema);

    expect(Array.isArray(result.tools)).toBe(true);
    expect(result.tools.length).toBe(allToolDefinitions.length);

    const names = new Set(result.tools.map((t: any) => t.name));
    for (const def of allToolDefinitions) {
      expect(names.has(def.name)).toBe(true);
    }
  });

  it('covers every tool listed in the package.json mcp manifest', async () => {
    const manifestTools: string[] = (packageJson as any).mcp?.tools ?? [];
    expect(manifestTools.length).toBeGreaterThan(0);

    const server = await createServer();
    const result = await invoke(server, ListToolsRequestSchema);
    const names = new Set(result.tools.map((t: any) => t.name));

    const missing = manifestTools.filter((name) => !names.has(name));
    expect(missing).toEqual([]);
  });

  it('registers resource and prompt handlers', async () => {
    const server = await createServer();

    const resources = await invoke(server, ListResourcesRequestSchema);
    expect(Array.isArray(resources.resources)).toBe(true);
    expect(resources.resources.length).toBeGreaterThan(0);

    const prompts = await invoke(server, ListPromptsRequestSchema);
    expect(Array.isArray(prompts.prompts)).toBe(true);
    expect(prompts.prompts.length).toBeGreaterThan(0);
  });

  it('dispatches a representative tool call through the rate-limited handler', async () => {
    const server = await createServer();
    const result = await invoke(server, CallToolRequestSchema, {
      name: 'sardis_get_balance',
      arguments: {},
    });

    expect(result).toBeDefined();
    expect(Array.isArray(result.content)).toBe(true);
    expect(result.content.length).toBeGreaterThan(0);
    expect(result.content[0].type).toBe('text');
  });

  it('rejects unknown tool names with a clear error', async () => {
    const server = await createServer();
    await expect(
      invoke(server, CallToolRequestSchema, {
        name: 'sardis_not_a_real_tool',
        arguments: {},
      }),
    ).rejects.toThrow(/Unknown tool/);
  });
});
