/**
 * Policy Tools Test Suite
 * Tests for MCP policy-related tools
 */

import { describe, it, expect, vi } from 'vitest';
import { policyToolDefinitions, policyToolHandlers, checkPolicy } from '../tools/policy.js';

// Mock config
vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    apiKey: '',
    chain: 'base_sepolia',
    mode: 'simulated',
    agentId: 'agent_test',
  })),
  getAllowedVendors: vi.fn(() => ['OpenAI', 'Anthropic', 'AWS']),
  getBlockedVendors: vi.fn(() => ['gambling-site', 'blocked-vendor']),
}));

describe('Policy Tools', () => {
  describe('Policy Check Function', () => {
    it('should allow valid payment', async () => {
      const result = await checkPolicy('OpenAI', 50);

      expect(result).toBeDefined();
      expect(result.allowed).toBe(true);
      expect(result.checks).toBeInstanceOf(Array);
    });

    it('should block payment over limit', async () => {
      const result = await checkPolicy('OpenAI', 99999);

      expect(result.allowed).toBe(false);
      expect(result.reason).toBeDefined();
    });
  });

  describe('Tool Definitions', () => {
    it('should have sardis_check_policy tool', () => {
      const policyTool = policyToolDefinitions.find(t => t.name === 'sardis_check_policy');

      expect(policyTool).toBeDefined();
      expect(policyTool?.description).toBeDefined();
    });

    it('should have sardis_get_policies tool', () => {
      const policiesTool = policyToolDefinitions.find(t => t.name === 'sardis_get_policies');

      expect(policiesTool).toBeDefined();
    });

    it('should NOT expose sardis_get_rules (security: prevents policy leaking)', () => {
      const rulesTool = policyToolDefinitions.find(t => t.name === 'sardis_get_rules');

      expect(rulesTool).toBeUndefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_check_policy', () => {
      it('should evaluate payment policy', async () => {
        const handler = policyToolHandlers['sardis_check_policy'];
        const result = await handler({
          vendor: 'Stripe',
          amount: 100,
        });

        expect(result).toBeDefined();
        expect(result.content).toHaveLength(1);
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed).toHaveProperty('allowed');
      });

      it('should handle invalid parameters', async () => {
        const handler = policyToolHandlers['sardis_check_policy'];
        const result = await handler({});

        // Should still work with defaults or error gracefully
        expect(result).toBeDefined();
      });
    });

    describe('sardis_get_policies', () => {
      it('should return active policies', async () => {
        const handler = policyToolHandlers['sardis_get_policies'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed) || typeof parsed === 'object').toBe(true);
      });
    });

    describe('sardis_get_rules', () => {
      it('should return security error (blocked for agents)', async () => {
        const handler = policyToolHandlers['sardis_get_rules'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBe(true);
      });
    });
  });
});
