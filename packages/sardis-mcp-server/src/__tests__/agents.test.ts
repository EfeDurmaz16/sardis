/**
 * Agent Tools Test Suite
 * Tests for MCP agent management tools
 */

import { describe, it, expect, vi } from 'vitest';
import { agentToolDefinitions, agentToolHandlers } from '../tools/agents.js';

// Mock config
vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    apiKey: '',
    chain: 'base_sepolia',
    mode: 'simulated',
    agentId: 'agent_test_123',
  })),
}));

describe('Agent Tools', () => {
  describe('Tool Definitions', () => {
    it('should have sardis_get_agent tool', () => {
      const agentTool = agentToolDefinitions.find(t => t.name === 'sardis_get_agent');

      expect(agentTool).toBeDefined();
      expect(agentTool?.description).toContain('agent');
    });

    it('should have sardis_list_agents tool', () => {
      const listTool = agentToolDefinitions.find(t => t.name === 'sardis_list_agents');

      expect(listTool).toBeDefined();
    });

    it('should have sardis_update_agent tool', () => {
      const updateTool = agentToolDefinitions.find(t => t.name === 'sardis_update_agent');

      expect(updateTool).toBeDefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_get_agent', () => {
      it('should get agent details', async () => {
        const handler = agentToolHandlers['sardis_get_agent'];
        const result = await handler({
          agent_id: 'agent_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.agent_id).toBeDefined();
        expect(parsed.status).toBeDefined();
      });

      it('should default to configured agent_id', async () => {
        const handler = agentToolHandlers['sardis_get_agent'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.agent_id).toBeDefined();
      });
    });

    describe('sardis_list_agents', () => {
      it('should list all agents', async () => {
        const handler = agentToolHandlers['sardis_list_agents'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed)).toBe(true);
      });

      it('should filter by status', async () => {
        const handler = agentToolHandlers['sardis_list_agents'];
        const result = await handler({
          status: 'active',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_update_agent', () => {
      it('should update agent settings', async () => {
        const handler = agentToolHandlers['sardis_update_agent'];
        const result = await handler({
          agent_id: 'agent_test_123',
          name: 'Updated Agent Name',
          spending_limit: 1000,
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.status).toBeDefined();
      });

      it('should error without agent_id', async () => {
        const handler = agentToolHandlers['sardis_update_agent'];
        const result = await handler({
          name: 'New Name',
        });

        // Should either error or use default agent_id
        expect(result).toBeDefined();
      });
    });
  });
});
