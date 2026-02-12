/**
 * Wallet Management Tools Test Suite
 * Tests for MCP wallet management tools
 */

import { describe, it, expect, vi } from 'vitest';
import { walletManagementToolDefinitions, walletManagementToolHandlers } from '../tools/wallet-management.js';

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

describe('Wallet Management Tools', () => {
  describe('Tool Definitions', () => {
    it('should have sardis_create_wallet tool', () => {
      const createTool = walletManagementToolDefinitions.find(t => t.name === 'sardis_create_wallet');

      expect(createTool).toBeDefined();
      expect(createTool?.description).toContain('wallet');
    });

    it('should have sardis_list_wallets tool', () => {
      const listTool = walletManagementToolDefinitions.find(t => t.name === 'sardis_list_wallets');

      expect(listTool).toBeDefined();
    });

    it('should NOT expose sardis_update_wallet_limits (security: prevents privilege escalation)', () => {
      const updateTool = walletManagementToolDefinitions.find(t => t.name === 'sardis_update_wallet_limits');

      expect(updateTool).toBeUndefined();
    });

    it('should NOT expose sardis_archive_wallet (security: prevents privilege escalation)', () => {
      const archiveTool = walletManagementToolDefinitions.find(t => t.name === 'sardis_archive_wallet');

      expect(archiveTool).toBeUndefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_create_wallet', () => {
      it('should create new wallet', async () => {
        const handler = walletManagementToolHandlers['sardis_create_wallet'];
        const result = await handler({
          name: 'Test Wallet',
          chain: 'base',
          limit_per_tx: 100,
          limit_total: 1000,
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.wallet_id).toBeDefined();
        expect(parsed.address).toBeDefined();
        expect(parsed.status).toBeDefined();
      });

      it('should support different chains', async () => {
        const handler = walletManagementToolHandlers['sardis_create_wallet'];

        const baseResult = await handler({
          name: 'Base Wallet',
          chain: 'base',
        });
        expect(baseResult.isError).toBeFalsy();

        const polygonResult = await handler({
          name: 'Polygon Wallet',
          chain: 'polygon',
        });
        expect(polygonResult.isError).toBeFalsy();
      });
    });

    describe('sardis_list_wallets', () => {
      it('should list all wallets', async () => {
        const handler = walletManagementToolHandlers['sardis_list_wallets'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed)).toBe(true);
      });

      it('should filter by chain', async () => {
        const handler = walletManagementToolHandlers['sardis_list_wallets'];
        const result = await handler({
          chain: 'base',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });

      it('should filter by status', async () => {
        const handler = walletManagementToolHandlers['sardis_list_wallets'];
        const result = await handler({
          status: 'active',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_update_wallet_limits', () => {
      it('should return security error (blocked for agents)', async () => {
        const handler = walletManagementToolHandlers['sardis_update_wallet_limits'];
        const result = await handler({
          wallet_id: 'wallet_test_123',
          limit_per_tx: 200,
          limit_total: 2000,
        });

        expect(result).toBeDefined();
        expect(result.isError).toBe(true);

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.error).toContain('security');
      });
    });

    describe('sardis_archive_wallet', () => {
      it('should return security error (blocked for agents)', async () => {
        const handler = walletManagementToolHandlers['sardis_archive_wallet'];
        const result = await handler({
          wallet_id: 'wallet_test_123',
          reason: 'No longer needed',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBe(true);

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.error).toContain('security');
      });
    });
  });
});
