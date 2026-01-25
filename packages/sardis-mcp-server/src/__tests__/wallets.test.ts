/**
 * Wallet Tools Test Suite
 * Tests for MCP wallet-related tools
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getWalletInfo, getWalletBalance, walletToolHandlers, walletToolDefinitions } from '../tools/wallets.js';

// Mock config
vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    apiKey: '',  // Empty = simulated mode
    chain: 'base_sepolia',
    mode: 'simulated',
  })),
}));

describe('Wallet Tools', () => {
  describe('getWalletInfo', () => {
    it('should return simulated wallet info when no API key', async () => {
      const wallet = await getWalletInfo();

      expect(wallet).toBeDefined();
      expect(wallet.id).toBe('wallet_test_123');
      expect(wallet.is_active).toBe(true);
      expect(wallet.currency).toBe('USDC');
      expect(wallet.limit_per_tx).toBeDefined();
      expect(wallet.limit_total).toBeDefined();
    });
  });

  describe('getWalletBalance', () => {
    it('should return simulated balance with default token', async () => {
      const balance = await getWalletBalance();

      expect(balance).toBeDefined();
      expect(balance.token).toBe('USDC');
      expect(balance.chain).toBe('base_sepolia');
      expect(balance.wallet_id).toBe('wallet_test_123');
      expect(parseFloat(balance.balance)).toBeGreaterThan(0);
    });

    it('should accept custom token and chain', async () => {
      const balance = await getWalletBalance('USDT', 'polygon');

      expect(balance.token).toBe('USDT');
      expect(balance.chain).toBe('polygon');
    });
  });

  describe('Tool Definitions', () => {
    it('should have sardis_get_balance tool defined', () => {
      const balanceTool = walletToolDefinitions.find(t => t.name === 'sardis_get_balance');

      expect(balanceTool).toBeDefined();
      expect(balanceTool?.description).toContain('balance');
      expect(balanceTool?.inputSchema.properties).toHaveProperty('token');
      expect(balanceTool?.inputSchema.properties).toHaveProperty('chain');
    });

    it('should have sardis_get_wallet tool defined', () => {
      const walletTool = walletToolDefinitions.find(t => t.name === 'sardis_get_wallet');

      expect(walletTool).toBeDefined();
      expect(walletTool?.description).toContain('wallet');
    });
  });

  describe('Tool Handlers', () => {
    it('should handle sardis_get_balance request', async () => {
      const handler = walletToolHandlers['sardis_get_balance'];
      const result = await handler({ token: 'USDC' });

      expect(result).toBeDefined();
      expect(result.content).toHaveLength(1);
      expect(result.content[0].type).toBe('text');
      expect(result.isError).toBeFalsy();

      const parsed = JSON.parse(result.content[0].text);
      expect(parsed.token).toBe('USDC');
    });

    it('should handle sardis_get_wallet request', async () => {
      const handler = walletToolHandlers['sardis_get_wallet'];
      const result = await handler({});

      expect(result).toBeDefined();
      expect(result.content).toHaveLength(1);
      expect(result.isError).toBeFalsy();

      const parsed = JSON.parse(result.content[0].text);
      expect(parsed.is_active).toBe(true);
    });

    it('should handle missing parameters gracefully', async () => {
      const handler = walletToolHandlers['sardis_get_balance'];
      const result = await handler({});

      expect(result).toBeDefined();
      expect(result.isError).toBeFalsy();

      const parsed = JSON.parse(result.content[0].text);
      expect(parsed.token).toBe('USDC'); // Default
    });
  });
});
