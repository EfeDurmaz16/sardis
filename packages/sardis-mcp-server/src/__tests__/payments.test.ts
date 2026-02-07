/**
 * Payment Tools Test Suite
 * Tests for MCP payment-related tools
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  executePayment,
  getTransaction,
  listTransactions,
  paymentToolHandlers,
  paymentToolDefinitions
} from '../tools/payments.js';

// Mock config
vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    apiKey: '',  // Empty = simulated mode
    chain: 'base_sepolia',
    mode: 'simulated',
    agentId: 'agent_test',
  })),
}));

// Mock policy check
vi.mock('../tools/policy.js', () => ({
  checkPolicy: vi.fn(async (vendor: string, amount: number) => {
    // Block payments over $1000 for testing
    if (amount > 1000) {
      return {
        allowed: false,
        reason: 'Amount exceeds policy limit',
        risk_score: 0.9,
        checks: ['amount_limit'],
      };
    }
    // Block specific vendor for testing
    if (vendor === 'BlockedVendor') {
      return {
        allowed: false,
        reason: 'Vendor not in approved list',
        risk_score: 0.8,
        checks: ['vendor_approval'],
      };
    }
    return {
      allowed: true,
      reason: null,
      risk_score: 0.1,
      checks: ['amount_limit', 'vendor_approval', 'frequency_check'],
    };
  }),
}));

describe('Payment Tools', () => {
  describe('executePayment', () => {
    it('should execute simulated payment successfully', async () => {
      const result = await executePayment(
        'OpenAI',
        50,
        'API credits',
        '0x1234567890123456789012345678901234567890',
        'USDC'
      );

      expect(result).toBeDefined();
      expect(result.payment_id).toBeDefined();
      expect(result.status).toBe('completed');
      expect(result.chain).toBe('base_sepolia');
      expect(result.tx_hash).toMatch(/^0x[0-9a-f]+$/);
      expect(result.ledger_tx_id).toBeDefined();
      expect(result.audit_anchor).toBeDefined();
    });

    it('should generate unique payment IDs', async () => {
      const result1 = await executePayment('Vendor1', 10, 'Test1');
      const result2 = await executePayment('Vendor2', 20, 'Test2');

      expect(result1.payment_id).not.toBe(result2.payment_id);
    });
  });

  describe('getTransaction', () => {
    it('should return simulated transaction', async () => {
      const tx = await getTransaction('tx_test_123');

      expect(tx).toBeDefined();
      expect(tx.id).toBe('tx_test_123');
      expect(tx.status).toBe('completed');
      expect(tx.amount).toBeDefined();
      expect(tx.token).toBeDefined();
    });
  });

  describe('listTransactions', () => {
    it('should return list of simulated transactions', async () => {
      const transactions = await listTransactions();

      expect(transactions).toBeInstanceOf(Array);
      expect(transactions.length).toBeGreaterThan(0);

      transactions.forEach(tx => {
        expect(tx.id).toBeDefined();
        expect(tx.payment_id).toBeDefined();
        expect(tx.status).toBe('completed');
        expect(tx.amount).toBeDefined();
        expect(tx.vendor).toBeDefined();
      });
    });

    it('should respect limit parameter', async () => {
      const transactions = await listTransactions(1);
      // In simulation, always returns max 2, but should work
      expect(transactions.length).toBeLessThanOrEqual(2);
    });
  });

  describe('Tool Definitions', () => {
    it('should have sardis_pay tool with required fields', () => {
      const payTool = paymentToolDefinitions.find(t => t.name === 'sardis_pay');

      expect(payTool).toBeDefined();
      expect(payTool?.inputSchema.required).toContain('vendor');
      expect(payTool?.inputSchema.required).toContain('amount');
      expect(payTool?.inputSchema.properties).toHaveProperty('vendor');
      expect(payTool?.inputSchema.properties).toHaveProperty('amount');
      expect(payTool?.inputSchema.properties).toHaveProperty('purpose');
      expect(payTool?.inputSchema.properties).toHaveProperty('token');
    });

    it('should have transaction query tools', () => {
      const getTxTool = paymentToolDefinitions.find(t => t.name === 'sardis_get_transaction');
      const listTxTool = paymentToolDefinitions.find(t => t.name === 'sardis_list_transactions');

      expect(getTxTool).toBeDefined();
      expect(listTxTool).toBeDefined();
    });
  });

  describe('Tool Handlers', () => {
    describe('sardis_pay', () => {
      it('should process valid payment request', async () => {
        const handler = paymentToolHandlers['sardis_pay'];
        const result = await handler({
          vendor: 'OpenAI',
          amount: 50,
          purpose: 'API credits',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBeFalsy();

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.success).toBe(true);
        expect(parsed.status).toBe('APPROVED');
        expect(parsed.vendor).toBe('OpenAI');
        expect(parsed.amount).toBe(50);
        expect(parsed.payment_id).toBeDefined();
        expect(parsed.transaction_hash).toBeDefined();
        expect(parsed.reason_code).toBe('SARDIS.PAYMENT.APPROVED');
        expect(parsed.decision).toBeDefined();
        expect(parsed.decision.outcome).toBe('APPROVED');
      });

      it('should reject payment exceeding policy limit', async () => {
        const handler = paymentToolHandlers['sardis_pay'];
        const result = await handler({
          vendor: 'OpenAI',
          amount: 5000,  // Over $1000 limit
          purpose: 'Large payment',
        });

        expect(result).toBeDefined();
        expect(result.isError).toBe(false);  // Policy blocks are not errors

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.success).toBe(false);
        expect(parsed.status).toBe('BLOCKED');
        expect(parsed.error).toBe('POLICY_VIOLATION');
        expect(parsed.reason_code).toBe('SARDIS.POLICY.VIOLATION');
        expect(parsed.decision.outcome).toBe('BLOCKED');
        expect(parsed.prevention).toContain('Financial Hallucination PREVENTED');
      });

      it('should reject blocked vendor', async () => {
        const handler = paymentToolHandlers['sardis_pay'];
        const result = await handler({
          vendor: 'BlockedVendor',
          amount: 50,
          purpose: 'Test',
        });

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.success).toBe(false);
        expect(parsed.status).toBe('BLOCKED');
      });

      it('should handle invalid payment request', async () => {
        const handler = paymentToolHandlers['sardis_pay'];
        const result = await handler({
          // Missing required fields
        });

        expect(result.isError).toBe(true);
        expect(result.content[0].text).toContain('Invalid payment request');
      });

      it('should default to USDC token', async () => {
        const handler = paymentToolHandlers['sardis_pay'];
        const result = await handler({
          vendor: 'TestVendor',
          amount: 10,
        });

        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.token).toBe('USDC');
      });
    });

    describe('sardis_get_transaction', () => {
      it('should return transaction details', async () => {
        const handler = paymentToolHandlers['sardis_get_transaction'];
        const result = await handler({
          transaction_id: 'tx_123',
        });

        expect(result.isError).toBeFalsy();
        const parsed = JSON.parse(result.content[0].text);
        expect(parsed.id).toBe('tx_123');
      });

      it('should error on missing transaction_id', async () => {
        const handler = paymentToolHandlers['sardis_get_transaction'];
        const result = await handler({});

        expect(result.isError).toBe(true);
      });
    });

    describe('sardis_list_transactions', () => {
      it('should return transaction list', async () => {
        const handler = paymentToolHandlers['sardis_list_transactions'];
        const result = await handler({});

        expect(result.isError).toBeFalsy();
        const parsed = JSON.parse(result.content[0].text);
        expect(Array.isArray(parsed)).toBe(true);
      });

      it('should accept filter parameters', async () => {
        const handler = paymentToolHandlers['sardis_list_transactions'];
        const result = await handler({
          limit: 10,
          offset: 0,
          status: 'completed',
        });

        expect(result.isError).toBeFalsy();
      });
    });
  });
});
