/**
 * MCP Server Integration Tests
 * Tests for full MCP server functionality
 */

import { describe, it, expect, vi, beforeAll } from 'vitest';
import { getAllTools, getAllToolHandlers } from '../tools/index.js';

// Mock config
vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    apiKey: '',
    chain: 'base_sepolia',
    mode: 'simulated',
    agentId: 'agent_test_123',
  })),
  getAllowedVendors: vi.fn(() => ['OpenAI', 'Anthropic', 'AWS', 'Vercel', 'GitHub']),
  getBlockedVendors: vi.fn(() => ['gambling-site', 'blocked-vendor']),
}));

describe('MCP Server Integration', () => {
  describe('Tool Registry', () => {
    it('should have 36+ tools registered', () => {
      const tools = getAllTools();

      expect(tools.length).toBeGreaterThanOrEqual(36);
    });

    it('should have unique tool names', () => {
      const tools = getAllTools();
      const names = tools.map(t => t.name);
      const uniqueNames = [...new Set(names)];

      expect(names.length).toBe(uniqueNames.length);
    });

    it('should have all tools prefixed with sardis_', () => {
      const tools = getAllTools();

      tools.forEach(tool => {
        expect(tool.name).toMatch(/^sardis_/);
      });
    });

    it('should have descriptions for all tools', () => {
      const tools = getAllTools();

      tools.forEach(tool => {
        expect(tool.description).toBeDefined();
        expect(tool.description.length).toBeGreaterThan(10);
      });
    });

    it('should have valid input schemas', () => {
      const tools = getAllTools();

      tools.forEach(tool => {
        expect(tool.inputSchema).toBeDefined();
        expect(tool.inputSchema.type).toBe('object');
        expect(tool.inputSchema.properties).toBeDefined();
      });
    });
  });

  describe('Tool Handlers', () => {
    it('should have handlers for all defined tools', () => {
      const tools = getAllTools();
      const handlers = getAllToolHandlers();

      tools.forEach(tool => {
        expect(handlers[tool.name]).toBeDefined();
        expect(typeof handlers[tool.name]).toBe('function');
      });
    });
  });

  describe('Tool Categories', () => {
    it('should have wallet tools', () => {
      const tools = getAllTools();
      const walletTools = tools.filter(t =>
        t.name.includes('wallet') || t.name.includes('balance')
      );

      expect(walletTools.length).toBeGreaterThanOrEqual(4);
    });

    it('should have payment tools', () => {
      const tools = getAllTools();
      const paymentTools = tools.filter(t =>
        t.name.includes('pay') || t.name.includes('transaction')
      );

      expect(paymentTools.length).toBeGreaterThanOrEqual(3);
    });

    it('should have policy tools', () => {
      const tools = getAllTools();
      const policyTools = tools.filter(t =>
        t.name.includes('policy') || t.name.includes('rules')
      );

      expect(policyTools.length).toBeGreaterThanOrEqual(3);
    });

    it('should have hold tools', () => {
      const tools = getAllTools();
      const holdTools = tools.filter(t => t.name.includes('hold'));

      expect(holdTools.length).toBeGreaterThanOrEqual(4);
    });

    it('should have card tools', () => {
      const tools = getAllTools();
      const cardTools = tools.filter(t => t.name.includes('card'));

      expect(cardTools.length).toBeGreaterThanOrEqual(5);
    });

    it('should have fiat tools', () => {
      const tools = getAllTools();
      const fiatTools = tools.filter(t =>
        t.name.includes('fund') || t.name.includes('withdraw')
      );

      expect(fiatTools.length).toBeGreaterThanOrEqual(2);
    });

    it('should have spending tools', () => {
      const tools = getAllTools();
      const spendingTools = tools.filter(t => t.name.includes('spending'));

      expect(spendingTools.length).toBeGreaterThanOrEqual(3);
    });

    it('should have agent tools', () => {
      const tools = getAllTools();
      const agentTools = tools.filter(t => t.name.includes('agent'));

      expect(agentTools.length).toBeGreaterThanOrEqual(2);
    });

    it('should have approval tools', () => {
      const tools = getAllTools();
      const approvalTools = tools.filter(t => t.name.includes('approval'));

      expect(approvalTools.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe('End-to-End Workflow', () => {
    it('should execute full payment workflow', async () => {
      const handlers = getAllToolHandlers();

      // Step 1: Check balance
      const balanceResult = await handlers['sardis_get_balance']({
        token: 'USDC',
      });
      expect(balanceResult.isError).toBeFalsy();
      const balance = JSON.parse(balanceResult.content[0].text);
      expect(parseFloat(balance.balance)).toBeGreaterThan(0);

      // Step 2: Check policy
      const policyResult = await handlers['sardis_check_policy']({
        vendor: 'OpenAI',
        amount: 50,
      });
      expect(policyResult.isError).toBeFalsy();

      // Step 3: Execute payment
      const payResult = await handlers['sardis_pay']({
        vendor: 'OpenAI',
        amount: 50,
        purpose: 'API credits',
      });
      expect(payResult.isError).toBeFalsy();
      const payment = JSON.parse(payResult.content[0].text);
      expect(payment.success).toBe(true);
      expect(payment.payment_id).toBeDefined();

      // Step 4: Check spending
      const spendingResult = await handlers['sardis_get_spending']({
        period: 'daily',
      });
      expect(spendingResult.isError).toBeFalsy();
    });

    it('should execute hold workflow', async () => {
      const handlers = getAllToolHandlers();

      // Step 1: Create hold
      const createResult = await handlers['sardis_create_hold']({
        amount: 100,
        purpose: 'Pre-authorization',
        expires_in: 3600,
      });
      expect(createResult.isError).toBeFalsy();
      const hold = JSON.parse(createResult.content[0].text);
      const holdId = hold.hold_id;

      // Step 2: List holds
      const listResult = await handlers['sardis_list_holds']({
        status: 'active',
      });
      expect(listResult.isError).toBeFalsy();

      // Step 3: Capture hold
      const captureResult = await handlers['sardis_capture_hold']({
        hold_id: holdId,
        amount: 75,  // Partial capture
      });
      expect(captureResult.isError).toBeFalsy();
    });

    it('should execute card workflow', async () => {
      const handlers = getAllToolHandlers();

      // Step 1: Create card
      const createResult = await handlers['sardis_create_card']({
        limit: 500,
        type: 'single_use',
        nickname: 'Integration Test Card',
      });
      expect(createResult.isError).toBeFalsy();
      const card = JSON.parse(createResult.content[0].text);
      const cardId = card.card_id;

      // Step 2: Get card details
      const getResult = await handlers['sardis_get_card']({
        card_id: cardId,
      });
      expect(getResult.isError).toBeFalsy();

      // Step 3: Freeze card
      const freezeResult = await handlers['sardis_freeze_card']({
        card_id: cardId,
        reason: 'Testing freeze',
      });
      expect(freezeResult.isError).toBeFalsy();

      // Step 4: Unfreeze card
      const unfreezeResult = await handlers['sardis_unfreeze_card']({
        card_id: cardId,
      });
      expect(unfreezeResult.isError).toBeFalsy();

      // Step 5: Cancel card
      const cancelResult = await handlers['sardis_cancel_card']({
        card_id: cardId,
      });
      expect(cancelResult.isError).toBeFalsy();
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid input gracefully', async () => {
      const handlers = getAllToolHandlers();

      // Missing required fields
      const payResult = await handlers['sardis_pay']({});
      expect(payResult.isError).toBe(true);

      // Invalid amount
      const payResult2 = await handlers['sardis_pay']({
        vendor: 'Test',
        amount: -100,
      });
      expect(payResult2.isError).toBe(true);
    });

    it('should handle policy violations correctly', async () => {
      const handlers = getAllToolHandlers();

      // Exceed limit (assuming $1000 limit in mock)
      const payResult = await handlers['sardis_pay']({
        vendor: 'Test',
        amount: 99999,
        purpose: 'Testing limits',
      });

      // Policy violation is NOT an error, but a blocked status
      expect(payResult.isError).toBe(false);
      const result = JSON.parse(payResult.content[0].text);
      expect(result.status).toBe('BLOCKED');
    });
  });
});
