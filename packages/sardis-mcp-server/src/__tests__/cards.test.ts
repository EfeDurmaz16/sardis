/**
 * Cards Tools Test Suite
 * Tests for MCP virtual card tools
 */

import { describe, it, expect, vi } from 'vitest';
import { cardToolDefinitions, cardToolHandlers } from '../tools/cards.js';

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

describe('Card Tools', () => {
  describe('Tool Definitions', () => {
    it('should have sardis_create_card tool', () => {
      const createTool = cardToolDefinitions.find(t => t.name === 'sardis_create_card');

      expect(createTool).toBeDefined();
      expect(createTool?.description).toContain('virtual card');
    });

    it('should have sardis_get_card tool', () => {
      const getTool = cardToolDefinitions.find(t => t.name === 'sardis_get_card');

      expect(getTool).toBeDefined();
    });

    it('should have sardis_list_cards tool', () => {
      const listTool = cardToolDefinitions.find(t => t.name === 'sardis_list_cards');

      expect(listTool).toBeDefined();
    });

    it('should have card management tools', () => {
      const freezeTool = cardToolDefinitions.find(t => t.name === 'sardis_freeze_card');
      const unfreezetool = cardToolDefinitions.find(t => t.name === 'sardis_unfreeze_card');
      const cancelTool = cardToolDefinitions.find(t => t.name === 'sardis_cancel_card');

      expect(freezeTool).toBeDefined();
      expect(unfreezetool).toBeDefined();
      expect(cancelTool).toBeDefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_create_card', () => {
      it('should create virtual card with limits', async () => {
        const handler = cardToolHandlers['sardis_create_card'];
        const result = await handler({
          limit: 500,
          type: 'single_use',
          nickname: 'Test Card',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.card_id).toBeDefined();
        expect(parsed.status).toBeDefined();
      });

      it('should create card with spending controls', async () => {
        const handler = cardToolHandlers['sardis_create_card'];
        const result = await handler({
          limit: 1000,
          type: 'merchant_locked',
          merchant_categories: ['software', 'cloud'],
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_get_card', () => {
      it('should retrieve card details', async () => {
        const handler = cardToolHandlers['sardis_get_card'];
        const result = await handler({
          card_id: 'card_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.card_id).toBeDefined();
      });

      it('should error without card_id', async () => {
        const handler = cardToolHandlers['sardis_get_card'];
        const result = await handler({});

        expect(result.isError).toBe(true);
      });
    });

    describe('sardis_list_cards', () => {
      it('should list all cards', async () => {
        const handler = cardToolHandlers['sardis_list_cards'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed)).toBe(true);
      });

      it('should filter by status', async () => {
        const handler = cardToolHandlers['sardis_list_cards'];
        const result = await handler({
          status: 'active',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_freeze_card', () => {
      it('should freeze card', async () => {
        const handler = cardToolHandlers['sardis_freeze_card'];
        const result = await handler({
          card_id: 'card_test_123',
          reason: 'Suspicious activity',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.status).toContain('frozen');
      });
    });

    describe('sardis_unfreeze_card', () => {
      it('should unfreeze card', async () => {
        const handler = cardToolHandlers['sardis_unfreeze_card'];
        const result = await handler({
          card_id: 'card_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_cancel_card', () => {
      it('should cancel card', async () => {
        const handler = cardToolHandlers['sardis_cancel_card'];
        const result = await handler({
          card_id: 'card_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.status).toContain('cancel');
      });
    });
  });
});
