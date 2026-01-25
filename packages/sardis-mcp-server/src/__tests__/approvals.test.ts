/**
 * Approvals Tools Test Suite
 * Tests for MCP approval workflow tools
 */

import { describe, it, expect, vi } from 'vitest';
import { approvalToolDefinitions, approvalToolHandlers } from '../tools/approvals.js';

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

describe('Approval Tools', () => {
  describe('Tool Definitions', () => {
    it('should have sardis_request_approval tool', () => {
      const requestTool = approvalToolDefinitions.find(t => t.name === 'sardis_request_approval');

      expect(requestTool).toBeDefined();
      expect(requestTool?.description).toContain('approval');
    });

    it('should have sardis_check_approval tool', () => {
      const checkTool = approvalToolDefinitions.find(t => t.name === 'sardis_check_approval');

      expect(checkTool).toBeDefined();
    });

    it('should have sardis_list_pending_approvals tool', () => {
      const listTool = approvalToolDefinitions.find(t => t.name === 'sardis_list_pending_approvals');

      expect(listTool).toBeDefined();
    });

    it('should have sardis_cancel_approval tool', () => {
      const cancelTool = approvalToolDefinitions.find(t => t.name === 'sardis_cancel_approval');

      expect(cancelTool).toBeDefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_request_approval', () => {
      it('should create approval request', async () => {
        const handler = approvalToolHandlers['sardis_request_approval'];
        const result = await handler({
          action: 'payment',
          vendor: 'OpenAI',
          amount: 500,
          reason: 'Monthly API subscription',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.approval_id).toBeDefined();
        expect(parsed.status).toBeDefined();
      });

      it('should support different action types', async () => {
        const handler = approvalToolHandlers['sardis_request_approval'];

        const paymentResult = await handler({
          action: 'payment',
          vendor: 'AWS',
          amount: 1000,
        });
        expect(paymentResult.isError).toBeFalsy();

        const cardResult = await handler({
          action: 'create_card',
          card_limit: 500,
        });
        expect(cardResult.isError).toBeFalsy();
      });
    });

    describe('sardis_check_approval', () => {
      it('should check approval status', async () => {
        const handler = approvalToolHandlers['sardis_check_approval'];
        const result = await handler({
          approval_id: 'approval_test_123',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.approval_id).toBeDefined();
        expect(parsed.status).toBeDefined();
      });

      it('should error without approval_id', async () => {
        const handler = approvalToolHandlers['sardis_check_approval'];
        const result = await handler({});

        expect(result.isError).toBe(true);
      });
    });

    describe('sardis_list_pending_approvals', () => {
      it('should list pending approvals', async () => {
        const handler = approvalToolHandlers['sardis_list_pending_approvals'];
        const result = await handler({});

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed)).toBe(true);
      });

      it('should filter by action type', async () => {
        const handler = approvalToolHandlers['sardis_list_pending_approvals'];
        const result = await handler({
          action: 'payment',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();
      });
    });

    describe('sardis_cancel_approval', () => {
      it('should cancel pending approval', async () => {
        const handler = approvalToolHandlers['sardis_cancel_approval'];
        const result = await handler({
          approval_id: 'approval_test_123',
          reason: 'Changed requirements',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.status).toContain('cancel');
      });

      it('should error without approval_id', async () => {
        const handler = approvalToolHandlers['sardis_cancel_approval'];
        const result = await handler({});

        expect(result.isError).toBe(true);
      });
    });
  });
});
