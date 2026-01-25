/**
 * Holds Tools Test Suite
 * Tests for MCP hold-related tools
 */

import { describe, it, expect, vi } from 'vitest';
import { holdToolDefinitions, holdToolHandlers } from '../tools/holds.js';

// Mock config
vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    apiKey: '',
    chain: 'base_sepolia',
    mode: 'simulated',
    agentId: 'agent_test',
  })),
}));

describe('Hold Tools', () => {
  describe('Tool Definitions', () => {
    it('should have sardis_create_hold tool', () => {
      const holdTool = holdToolDefinitions.find(t => t.name === 'sardis_create_hold');

      expect(holdTool).toBeDefined();
      expect(holdTool?.inputSchema.required).toContain('amount');
      expect(holdTool?.inputSchema.properties).toHaveProperty('amount');
      expect(holdTool?.inputSchema.properties).toHaveProperty('purpose');
      expect(holdTool?.inputSchema.properties).toHaveProperty('expires_in');
    });

    it('should have sardis_release_hold tool', () => {
      const releaseTool = holdToolDefinitions.find(t => t.name === 'sardis_release_hold');

      expect(releaseTool).toBeDefined();
      expect(releaseTool?.inputSchema.required).toContain('hold_id');
    });

    it('should have sardis_capture_hold tool', () => {
      const captureTool = holdToolDefinitions.find(t => t.name === 'sardis_capture_hold');

      expect(captureTool).toBeDefined();
      expect(captureTool?.inputSchema.required).toContain('hold_id');
    });

    it('should have sardis_list_holds tool', () => {
      const listTool = holdToolDefinitions.find(t => t.name === 'sardis_list_holds');

      expect(listTool).toBeDefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_create_hold', () => {
      it('should create hold with valid amount', async () => {
        const handler = holdToolHandlers['sardis_create_hold'];
        const result = await handler({
          amount: 100,
          purpose: 'Pre-authorization for service',
          expires_in: 3600,
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.hold_id).toBeDefined();
        expect(parsed.status).toBeDefined();
        expect(parsed.amount).toBe(100);
      });

      it('should reject hold without amount', async () => {
        const handler = holdToolHandlers['sardis_create_hold'];
        const result = await handler({});

        expect(result.isError).toBe(true);
      });
    });

    describe('sardis_release_hold', () => {
      it('should release hold by ID', async () => {
        const handler = holdToolHandlers['sardis_release_hold'];
        const result = await handler({
          hold_id: 'hold_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.status).toContain('released');
      });

      it('should error without hold_id', async () => {
        const handler = holdToolHandlers['sardis_release_hold'];
        const result = await handler({});

        expect(result.isError).toBe(true);
      });
    });

    describe('sardis_capture_hold', () => {
      it('should capture full hold amount', async () => {
        const handler = holdToolHandlers['sardis_capture_hold'];
        const result = await handler({
          hold_id: 'hold_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.status).toContain('captured');
      });

      it('should capture partial hold amount', async () => {
        const handler = holdToolHandlers['sardis_capture_hold'];
        const result = await handler({
          hold_id: 'hold_test_123',
          amount: 50,  // Partial capture
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_list_holds', () => {
      it('should list active holds', async () => {
        const handler = holdToolHandlers['sardis_list_holds'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed)).toBe(true);
      });

      it('should filter by status', async () => {
        const handler = holdToolHandlers['sardis_list_holds'];
        const result = await handler({
          status: 'active',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });
  });
});
