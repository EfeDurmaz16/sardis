/**
 * Fiat Tools Test Suite
 * Tests for MCP fiat on/off ramp tools
 */

import { describe, it, expect, vi } from 'vitest';
import { fiatToolDefinitions, fiatToolHandlers } from '../tools/fiat.js';

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

describe('Fiat Tools', () => {
  describe('Tool Definitions', () => {
    it('should have sardis_fund_wallet tool', () => {
      const fundTool = fiatToolDefinitions.find(t => t.name === 'sardis_fund_wallet');

      expect(fundTool).toBeDefined();
      expect(fundTool?.description).toContain('fund');
    });

    it('should have sardis_withdraw tool', () => {
      const withdrawTool = fiatToolDefinitions.find(t => t.name === 'sardis_withdraw');

      expect(withdrawTool).toBeDefined();
    });

    it('should have sardis_get_funding_status tool', () => {
      const statusTool = fiatToolDefinitions.find(t => t.name === 'sardis_get_funding_status');

      expect(statusTool).toBeDefined();
    });

    it('should have sardis_list_funding_transactions tool', () => {
      const listTool = fiatToolDefinitions.find(t => t.name === 'sardis_list_funding_transactions');

      expect(listTool).toBeDefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_fund_wallet', () => {
      it('should initiate wallet funding', async () => {
        const handler = fiatToolHandlers['sardis_fund_wallet'];
        const result = await handler({
          amount: 1000,
          source: 'bank_account',
          currency: 'USD',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.funding_id).toBeDefined();
        expect(parsed.status).toBeDefined();
      });

      it('should support different funding sources', async () => {
        const handler = fiatToolHandlers['sardis_fund_wallet'];

        // Bank account
        const bankResult = await handler({
          amount: 500,
          source: 'bank_account',
        });
        expect(bankResult.isError).toBeFalsy();

        // Wire transfer
        const wireResult = await handler({
          amount: 5000,
          source: 'wire',
        });
        expect(wireResult.isError).toBeFalsy();
      });
    });

    describe('sardis_withdraw', () => {
      it('should initiate withdrawal to bank', async () => {
        const handler = fiatToolHandlers['sardis_withdraw'];
        const result = await handler({
          amount: 500,
          destination: 'bank_account',
          account_id: 'acct_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.withdrawal_id).toBeDefined();
        expect(parsed.status).toBeDefined();
      });

      it('should error without required fields', async () => {
        const handler = fiatToolHandlers['sardis_withdraw'];
        const result = await handler({});

        expect(result.isError).toBe(true);
      });
    });

    describe('sardis_get_funding_status', () => {
      it('should get funding status', async () => {
        const handler = fiatToolHandlers['sardis_get_funding_status'];
        const result = await handler({
          funding_id: 'fund_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.funding_id).toBeDefined();
        expect(parsed.status).toBeDefined();
      });
    });

    describe('sardis_list_funding_transactions', () => {
      it('should list funding transactions', async () => {
        const handler = fiatToolHandlers['sardis_list_funding_transactions'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed)).toBe(true);
      });

      it('should filter by type', async () => {
        const handler = fiatToolHandlers['sardis_list_funding_transactions'];

        const depositsResult = await handler({ type: 'deposit' });
        expect(depositsResult.isError).toBeFalsy();

        const withdrawalsResult = await handler({ type: 'withdrawal' });
        expect(withdrawalsResult.isError).toBeFalsy();
      });
    });
  });
});
