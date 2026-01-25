/**
 * Spending Tools Test Suite
 * Tests for MCP spending tracking tools
 */

import { describe, it, expect, vi } from 'vitest';
import { spendingToolDefinitions, spendingToolHandlers } from '../tools/spending.js';

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

describe('Spending Tools', () => {
  describe('Tool Definitions', () => {
    it('should have sardis_get_spending tool', () => {
      const spendingTool = spendingToolDefinitions.find(t => t.name === 'sardis_get_spending');

      expect(spendingTool).toBeDefined();
      expect(spendingTool?.description).toContain('spending');
    });

    it('should have sardis_get_spending_by_vendor tool', () => {
      const vendorTool = spendingToolDefinitions.find(t => t.name === 'sardis_get_spending_by_vendor');

      expect(vendorTool).toBeDefined();
    });

    it('should have sardis_get_spending_by_category tool', () => {
      const categoryTool = spendingToolDefinitions.find(t => t.name === 'sardis_get_spending_by_category');

      expect(categoryTool).toBeDefined();
    });

    it('should have sardis_get_spending_trends tool', () => {
      const trendsTool = spendingToolDefinitions.find(t => t.name === 'sardis_get_spending_trends');

      expect(trendsTool).toBeDefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_get_spending', () => {
      it('should get spending summary', async () => {
        const handler = spendingToolHandlers['sardis_get_spending'];
        const result = await handler({
          period: 'daily',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.total).toBeDefined();
        expect(parsed.period).toBeDefined();
      });

      it('should support different periods', async () => {
        const handler = spendingToolHandlers['sardis_get_spending'];

        const dailyResult = await handler({ period: 'daily' });
        expect(dailyResult.isError).toBeFalsy();

        const weeklyResult = await handler({ period: 'weekly' });
        expect(weeklyResult.isError).toBeFalsy();

        const monthlyResult = await handler({ period: 'monthly' });
        expect(monthlyResult.isError).toBeFalsy();
      });
    });

    describe('sardis_get_spending_by_vendor', () => {
      it('should get spending by vendor', async () => {
        const handler = spendingToolHandlers['sardis_get_spending_by_vendor'];
        const result = await handler({
          vendor: 'OpenAI',
          period: 'monthly',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.vendor).toBeDefined();
        expect(parsed.total).toBeDefined();
      });

      it('should list all vendors when no vendor specified', async () => {
        const handler = spendingToolHandlers['sardis_get_spending_by_vendor'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_get_spending_by_category', () => {
      it('should get spending by category', async () => {
        const handler = spendingToolHandlers['sardis_get_spending_by_category'];
        const result = await handler({
          category: 'saas',
          period: 'monthly',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.category).toBeDefined();
      });

      it('should handle unknown category gracefully', async () => {
        const handler = spendingToolHandlers['sardis_get_spending_by_category'];
        const result = await handler({
          category: 'nonexistent_category',
        });

        expect(result).toBeDefined();
        // Should return empty or zero, not error
      });
    });

    describe('sardis_get_spending_trends', () => {
      it('should get spending trends', async () => {
        const handler = spendingToolHandlers['sardis_get_spending_trends'];
        const result = await handler({
          granularity: 'daily',
          lookback: 7,
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.trends).toBeDefined();
        expect(Array.isArray(parsed.trends)).toBe(true);
      });

      it('should support different granularities', async () => {
        const handler = spendingToolHandlers['sardis_get_spending_trends'];

        const hourlyResult = await handler({ granularity: 'hourly', lookback: 24 });
        expect(hourlyResult.isError).toBeFalsy();

        const weeklyResult = await handler({ granularity: 'weekly', lookback: 4 });
        expect(weeklyResult.isError).toBeFalsy();
      });
    });
  });
});
