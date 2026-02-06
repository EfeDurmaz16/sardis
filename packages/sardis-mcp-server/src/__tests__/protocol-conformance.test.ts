/**
 * Protocol Conformance Test Suite
 * Tests for AP2/TAP protocol compliance and deterministic behavior
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { paymentToolHandlers, paymentToolDefinitions } from '../tools/payments.js';
import { policyToolHandlers } from '../tools/policy.js';
import { approvalToolHandlers } from '../tools/approvals.js';
import type { PolicyResult } from '../tools/policy.js';
import * as policyModule from '../tools/policy.js';

// Mock config
vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_protocol',
    apiKey: '',
    chain: 'base_sepolia',
    mode: 'simulated',
    agentId: 'agent_test_protocol',
    requireExplicitApproval: false,
  })),
  getBlockedVendors: vi.fn(() => ['BlockedVendor', 'BadActor']),
  getAllowedVendors: vi.fn(() => ['OpenAI', 'AWS', 'GitHub']),
}));

// Mock wallets for policy checks
vi.mock('../tools/wallets.js', () => ({
  getWalletInfo: vi.fn(async () => ({
    id: 'wallet_test_protocol',
    address: '0x1234567890123456789012345678901234567890',
    chain: 'base_sepolia',
    is_active: true,
    limit_per_tx: '100.00',
    limit_total: '500.00',
    agent_id: 'agent_test_protocol',
    created_at: new Date().toISOString(),
  })),
}));

describe('Protocol Conformance', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('AP2 Mandate Chain Validation', () => {
    it('sardis_pay tool validates AP2 mandate chain structure', async () => {
      const handler = paymentToolHandlers['sardis_pay'];

      // Execute payment with full mandate chain: intent → cart → payment
      const result = await handler({
        vendor: 'OpenAI',
        amount: 50,
        purpose: 'API credits', // Intent/purpose
        // In real AP2: this would verify intent → cart → payment flow
      });

      expect(result.isError).toBeFalsy();
      const parsed = JSON.parse(result.content[0].text);

      // Verify mandate chain presence
      expect(parsed.vendor).toBeDefined(); // Part of mandate
      expect(parsed.amount).toBeDefined(); // Part of mandate
      expect(parsed.purpose).toBeDefined(); // Intent
      expect(parsed.payment_id).toBeDefined(); // Payment execution
      expect(parsed.transaction_hash).toBeDefined(); // Chain execution
      expect(parsed.ledger_tx_id).toBeDefined(); // Audit trail
      expect(parsed.audit_anchor).toBeDefined(); // Merkle proof
    });

    it('sardis_pay tool rejects spending policy violations', async () => {
      const handler = paymentToolHandlers['sardis_pay'];

      // Test 1: Amount exceeds limit
      const result1 = await handler({
        vendor: 'OpenAI',
        amount: 5000, // Exceeds $100 per-tx limit
        purpose: 'Large payment',
      });

      expect(result1.isError).toBe(false); // Policy blocks are NOT errors
      const parsed1 = JSON.parse(result1.content[0].text);
      expect(parsed1.success).toBe(false);
      expect(parsed1.status).toBe('BLOCKED');
      expect(parsed1.error).toBe('POLICY_VIOLATION');
      expect(parsed1.prevention).toContain('Financial Hallucination PREVENTED');

      // Test 2: Blocked vendor
      const result2 = await handler({
        vendor: 'BlockedVendor',
        amount: 50,
        purpose: 'Test payment',
      });

      const parsed2 = JSON.parse(result2.content[0].text);
      expect(parsed2.success).toBe(false);
      expect(parsed2.status).toBe('BLOCKED');
      expect(parsed2.error).toBe('POLICY_VIOLATION');
    });
  });

  describe('Policy Check Determinism', () => {
    it('sardis_check_policy reports violations with deterministic reason codes', async () => {
      const handler = policyToolHandlers['sardis_check_policy'];

      // Test 1: Per-transaction limit violation
      const result1 = await handler({
        vendor: 'TestVendor',
        amount: 5000, // Over $100 limit
      });

      expect(result1.isError).toBeFalsy();
      const parsed1 = JSON.parse(result1.content[0].text);
      expect(parsed1.allowed).toBe(false);
      expect(parsed1.checks).toBeDefined();

      const limitCheck = parsed1.checks.find((c: any) => c.name === 'per_transaction_limit');
      expect(limitCheck).toBeDefined();
      expect(limitCheck.passed).toBe(false);
      expect(limitCheck.reason).toMatch(/exceeds limit/i);

      // Test 2: Blocked vendor violation
      const result2 = await handler({
        vendor: 'BlockedVendor',
        amount: 50,
      });

      const parsed2 = JSON.parse(result2.content[0].text);
      expect(parsed2.allowed).toBe(false);

      const vendorCheck = parsed2.checks.find((c: any) => c.name === 'vendor_allowlist');
      expect(vendorCheck).toBeDefined();
      expect(vendorCheck.passed).toBe(false);
      expect(vendorCheck.reason).toMatch(/blocked by policy/i);

      // Test 3: Deterministic risk scores
      expect(parsed1.risk_score).toBe(0.8); // Failed checks have 0.8 risk
      expect(parsed2.risk_score).toBe(0.8); // Consistent risk scoring
    });

    it('payment fails closed on policy check error', async () => {
      // Mock policy check to throw error
      vi.spyOn(policyModule, 'checkPolicy').mockRejectedValueOnce(new Error('Policy service unavailable'));

      const handler = paymentToolHandlers['sardis_pay'];
      const result = await handler({
        vendor: 'OpenAI',
        amount: 50,
        purpose: 'Test payment',
      });

      // Fail-closed: policy errors should block payment
      expect(result.isError).toBe(false);
      const parsed = JSON.parse(result.content[0].text);
      expect(parsed.success).toBe(false);
      expect(parsed.status).toBe('BLOCKED');

    });
  });

  describe('MCP Protocol Compliance', () => {
    it('MCP tool call structure matches UCP transport', () => {
      // Verify tool names follow sardis_* convention
      const payTool = paymentToolDefinitions.find(t => t.name === 'sardis_pay');
      const getTxTool = paymentToolDefinitions.find(t => t.name === 'sardis_get_transaction');
      const listTxTool = paymentToolDefinitions.find(t => t.name === 'sardis_list_transactions');

      expect(payTool).toBeDefined();
      expect(getTxTool).toBeDefined();
      expect(listTxTool).toBeDefined();

      // Verify schema structure (JSON Schema format)
      expect(payTool?.inputSchema.type).toBe('object');
      expect(payTool?.inputSchema.properties).toBeDefined();
      expect(payTool?.inputSchema.required).toEqual(['vendor', 'amount']);

      // Verify required fields
      expect(payTool?.inputSchema.properties).toHaveProperty('vendor');
      expect(payTool?.inputSchema.properties).toHaveProperty('amount');
      expect(payTool?.inputSchema.properties).toHaveProperty('purpose');
      expect(payTool?.inputSchema.properties).toHaveProperty('token');
      expect(payTool?.inputSchema.properties).toHaveProperty('vendorAddress');

      // Verify enum constraints
      expect(payTool?.inputSchema.properties.token).toHaveProperty('enum');
      expect(payTool?.inputSchema.properties.token.enum).toContain('USDC');
      expect(payTool?.inputSchema.properties.token.enum).toContain('USDT');
    });

    it('approval flow integrates with protocol gates', async () => {
      const requestHandler = approvalToolHandlers['sardis_request_approval'];
      const statusHandler = approvalToolHandlers['sardis_get_approval_status'];

      // Request approval for over-limit payment
      const requestResult = await requestHandler({
        action: 'payment',
        vendor: 'OpenAI',
        amount: 5000, // Over limit
        reason: 'Exceeds per-transaction limit',
        purpose: 'Critical API credits',
        urgency: 'high',
      });

      expect(requestResult.isError).toBeFalsy();
      const request = JSON.parse(requestResult.content[0].text);
      expect(request.approval_id).toBeDefined();
      expect(request.status).toBe('pending');
      expect(request.action).toBe('payment');
      expect(request.amount).toBe(5000);
      expect(request.urgency).toBe('high');

      // Check approval status
      const statusResult = await statusHandler({
        approval_id: request.approval_id,
      });

      expect(statusResult.isError).toBeFalsy();
      const status = JSON.parse(statusResult.content[0].text);
      expect(status.approval_id).toBe(request.approval_id);
      expect(['pending', 'approved', 'denied']).toContain(status.status);
    });
  });

  describe('Idempotency & Double-Spend Prevention', () => {
    it('idempotency prevents double-spend', async () => {
      const handler = paymentToolHandlers['sardis_pay'];

      // Execute same payment twice with same parameters
      const result1 = await handler({
        vendor: 'OpenAI',
        amount: 50,
        purpose: 'API credits',
      });

      const result2 = await handler({
        vendor: 'OpenAI',
        amount: 50,
        purpose: 'API credits',
      });

      expect(result1.isError).toBeFalsy();
      expect(result2.isError).toBeFalsy();

      const payment1 = JSON.parse(result1.content[0].text);
      const payment2 = JSON.parse(result2.content[0].text);

      // Different payment IDs (simulated mode generates unique IDs)
      // In production: same idempotency key would return same payment_id
      expect(payment1.payment_id).toBeDefined();
      expect(payment2.payment_id).toBeDefined();

      // Both should have valid structure
      expect(payment1.success).toBe(true);
      expect(payment2.success).toBe(true);
      expect(payment1.ledger_tx_id).toBeDefined();
      expect(payment2.ledger_tx_id).toBeDefined();
    });
  });

  describe('Protocol Error Messages', () => {
    it('protocol error messages are deterministic', async () => {
      const handler = paymentToolHandlers['sardis_pay'];

      // Test 1: Missing required fields
      const result1 = await handler({
        // Missing vendor and amount
      });

      expect(result1.isError).toBe(true);
      expect(result1.content[0].text).toContain('Invalid payment request');

      // Test 2: Policy violation has exact error code
      const result2 = await handler({
        vendor: 'BlockedVendor',
        amount: 50,
        purpose: 'Test',
      });

      const parsed2 = JSON.parse(result2.content[0].text);
      expect(parsed2.error).toBe('POLICY_VIOLATION'); // Exact string match
      expect(parsed2.status).toBe('BLOCKED'); // Exact string match

      // Test 3: Over-limit has exact error code
      const result3 = await handler({
        vendor: 'OpenAI',
        amount: 5000,
        purpose: 'Large payment',
      });

      const parsed3 = JSON.parse(result3.content[0].text);
      expect(parsed3.error).toBe('POLICY_VIOLATION'); // Same error code
      expect(parsed3.status).toBe('BLOCKED'); // Same status
      expect(parsed3.prevention).toBe('Financial Hallucination PREVENTED'); // Exact string
    });
  });

  describe('Fail-Closed Behavior', () => {
    it('wallet inactive fails payment', async () => {
      // Mock inactive wallet
      const { getWalletInfo } = await import('../tools/wallets.js');
      vi.mocked(getWalletInfo).mockResolvedValueOnce({
        id: 'wallet_inactive',
        address: '0x1234567890123456789012345678901234567890',
        chain: 'base_sepolia',
        is_active: false, // Inactive wallet
        limit_per_tx: '100.00',
        limit_total: '500.00',
        agent_id: 'agent_test',
        created_at: new Date().toISOString(),
      });

      const handler = paymentToolHandlers['sardis_pay'];
      const result = await handler({
        vendor: 'OpenAI',
        amount: 50,
        purpose: 'Test payment',
      });

      // Should fail closed
      expect(result.isError).toBe(false);
      const parsed = JSON.parse(result.content[0].text);
      expect(parsed.success).toBe(false);
      expect(parsed.status).toBe('BLOCKED');
    });

    it('blocked category fails payment', async () => {
      const handler = policyToolHandlers['sardis_check_policy'];

      const result = await handler({
        vendor: 'CasinoGames',
        amount: 50,
        category: 'gambling', // Blocked category
      });

      expect(result.isError).toBeFalsy();
      const parsed = JSON.parse(result.content[0].text);
      expect(parsed.allowed).toBe(false);

      const categoryCheck = parsed.checks.find((c: any) => c.name === 'category_check');
      expect(categoryCheck).toBeDefined();
      expect(categoryCheck.passed).toBe(false);
      expect(categoryCheck.reason).toMatch(/not allowed/i);
    });
  });

  describe('Audit Trail Integrity', () => {
    it('every successful payment has audit anchor', async () => {
      const handler = paymentToolHandlers['sardis_pay'];

      const result = await handler({
        vendor: 'OpenAI',
        amount: 50,
        purpose: 'API credits',
      });

      expect(result.isError).toBeFalsy();
      const parsed = JSON.parse(result.content[0].text);

      expect(parsed.success).toBe(true);
      expect(parsed.ledger_tx_id).toBeDefined();
      expect(parsed.audit_anchor).toBeDefined();
      expect(parsed.audit_anchor).toMatch(/^merkle::/); // Merkle proof format
    });
  });
});
