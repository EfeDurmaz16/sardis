/**
 * Shared types for MCP tools
 */

import { z } from 'zod';

// Tool result type - compatible with MCP SDK CallToolResult
export interface ToolResult {
  content: Array<{
    type: 'text';
    text: string;
  }>;
  isError?: boolean;
  // MCP SDK can add additional properties
  [key: string]: unknown;
}

// Tool definition
export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, unknown>;
    required: string[];
  };
}

// Tool handler function type
export type ToolHandler = (args: unknown) => Promise<ToolResult>;

// Wallet types
export interface WalletInfo {
  id: string;
  limit_per_tx: string;
  limit_total: string;
  is_active: boolean;
  currency: string;
}

export interface WalletBalance {
  wallet_id: string;
  balance: string;
  token: string;
  chain: string;
  address: string;
}

// Payment types
export interface PaymentResult {
  payment_id: string;
  status: string;
  tx_hash?: string;
  chain: string;
  ledger_tx_id?: string;
  audit_anchor?: string;
  execution_path?: 'legacy_tx' | 'erc4337_userop';
  user_op_hash?: string;
}

// Policy types
export interface PolicyResult {
  allowed: boolean;
  reason?: string;
  risk_score?: number;
  checks?: Array<{ name: string; passed: boolean; reason?: string }>;
}

// Hold types
export interface Hold {
  id: string;
  wallet_id: string;
  merchant_id?: string;
  amount: string;
  token: string;
  status: 'active' | 'captured' | 'voided' | 'expired';
  purpose?: string;
  expires_at: string;
  captured_amount?: string;
  created_at: string;
}

export interface CreateHoldResult {
  hold_id: string;
  status: string;
  expires_at: string;
}

// Agent types
export interface Agent {
  id: string;
  name: string;
  description?: string;
  wallet_id?: string;
  is_active: boolean;
  created_at: string;
}

// Zod schemas for input validation
export const PaymentRequestSchema = z.object({
  vendor: z.string().describe('The merchant or service to pay'),
  amount: z.number().positive().describe('Payment amount in USD'),
  purpose: z.string().optional().describe('Reason for the payment'),
  category: z.string().optional().describe('Merchant category'),
  vendorAddress: z.string().optional().describe('Wallet address of the vendor (0x...)'),
  token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().describe('Token to use'),
});

export const PolicyCheckSchema = z.object({
  vendor: z.string().describe('The merchant to check'),
  amount: z.number().positive().describe('Payment amount to validate'),
  category: z.string().optional().describe('Merchant category'),
});

export const ComplianceCheckSchema = z.object({
  address: z.string().describe('Wallet address to check (0x...)'),
  amount: z.number().positive().describe('Transaction amount for risk assessment'),
});

export const TransactionQuerySchema = z.object({
  limit: z.number().optional().default(20).describe('Maximum transactions to return'),
  offset: z.number().optional().default(0).describe('Pagination offset'),
  status: z.enum(['pending', 'completed', 'failed']).optional().describe('Filter by status'),
});

export const BalanceCheckSchema = z.object({
  token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().describe('Token to check'),
  chain: z.string().optional().describe('Chain to check balance on'),
});

export const CreateHoldSchema = z.object({
  wallet_id: z.string().optional().describe('Wallet ID to create hold on'),
  amount: z.union([z.string(), z.number()]).describe('Amount to hold'),
  token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().default('USDC'),
  merchant_id: z.string().optional().describe('Merchant identifier'),
  purpose: z.string().optional().describe('Purpose of the hold'),
  expires_in: z.number().optional().describe('Hold duration in seconds'),
  duration_hours: z.number().optional().default(168).describe('Hold duration in hours'),
});

export const CaptureHoldSchema = z.object({
  hold_id: z.string().describe('Hold ID to capture'),
  amount: z.union([z.string(), z.number()]).optional().describe('Amount to capture (defaults to full amount)'),
});

export const VoidHoldSchema = z.object({
  hold_id: z.string().describe('Hold ID to void'),
});

export const GetHoldSchema = z.object({
  hold_id: z.string().describe('Hold ID to retrieve'),
});

export const ListHoldsSchema = z.object({
  wallet_id: z.string().optional().describe('Wallet ID to list holds for'),
  status: z.enum(['active', 'captured', 'voided', 'expired']).optional(),
});

export const CreateAgentSchema = z.object({
  name: z.string().describe('Agent display name'),
  description: z.string().optional().describe('Agent description'),
});

export const GetAgentSchema = z.object({
  agent_id: z.string().describe('Agent ID to retrieve'),
});

export const ListAgentsSchema = z.object({
  limit: z.number().optional().default(100),
  offset: z.number().optional().default(0),
});

export const UpdateAgentSchema = z.object({
  agent_id: z.string().describe('Agent ID to update'),
  name: z.string().optional().describe('New name'),
  is_active: z.boolean().optional().describe('Active status'),
});
