/**
 * Fiat Rails tools for MCP server
 *
 * Tools for funding wallets from bank accounts and withdrawing to fiat.
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

// Schemas
const FundWalletSchema = z.object({
  wallet_id: z.string().optional().describe('Wallet to fund'),
  amount: z.union([z.string(), z.number()]).describe('Amount to fund in USD'),
  source: z.enum(['ach', 'wire', 'card', 'bank_account']).optional().describe('Funding source type'),
  currency: z.string().optional().describe('Currency code'),
  source_id: z.string().optional().describe('Saved payment method ID'),
});

const WithdrawSchema = z.object({
  wallet_id: z.string().describe('Wallet to withdraw from'),
  amount: z.string().describe('Amount to withdraw in USD'),
  destination_id: z.string().describe('Bank account ID to withdraw to'),
});

const StatusSchema = z.object({
  transfer_id: z.string().optional().describe('Transfer ID to check'),
  funding_id: z.string().optional().describe('Funding ID to check (alias for transfer_id)'),
});

// Types
interface FundingResult {
  id: string;
  wallet_id: string;
  amount: string;
  source_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  estimated_arrival?: string;
  created_at: string;
}

interface WithdrawalResult {
  id: string;
  wallet_id: string;
  amount: string;
  destination_bank: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  estimated_arrival?: string;
  created_at: string;
}

// Tool definitions
export const fiatToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_fund_wallet',
    description: 'Fund a wallet from a bank account, wire transfer, or card. Use this to add funds to a wallet. USD is automatically converted to USDC.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: { type: 'number', description: 'Amount to fund in USD' },
        wallet_id: { type: 'string', description: 'Wallet to fund' },
        source: {
          type: 'string',
          enum: ['ach', 'wire', 'card', 'bank_account'],
          description: 'Funding source type. ACH is free but slower, wire is faster, card has fees.',
        },
        currency: { type: 'string', description: 'Currency code (default: USD)' },
        source_id: { type: 'string', description: 'Saved payment method ID' },
      },
      required: ['amount'],
    },
  },
  {
    name: 'sardis_withdraw_to_bank',
    description: 'Withdraw funds from wallet to a bank account. USDC is converted to USD.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet to withdraw from' },
        amount: { type: 'string', description: 'Amount to withdraw in USD' },
        destination_id: { type: 'string', description: 'Bank account ID to withdraw to' },
      },
      required: ['wallet_id', 'amount', 'destination_id'],
    },
  },
  {
    name: 'sardis_withdraw',
    description: 'Withdraw funds from wallet to a bank account (alias for sardis_withdraw_to_bank).',
    inputSchema: {
      type: 'object',
      properties: {
        amount: { type: 'number', description: 'Amount to withdraw' },
        destination: { type: 'string', description: 'Destination type (bank_account, wire)' },
        account_id: { type: 'string', description: 'Bank account ID to withdraw to' },
        wallet_id: { type: 'string', description: 'Wallet to withdraw from' },
      },
      required: ['amount'],
    },
  },
  {
    name: 'sardis_get_funding_status',
    description: 'Check the status of a funding transfer.',
    inputSchema: {
      type: 'object',
      properties: {
        transfer_id: { type: 'string', description: 'Funding transfer ID' },
      },
      required: ['transfer_id'],
    },
  },
  {
    name: 'sardis_get_withdrawal_status',
    description: 'Check the status of a withdrawal to bank.',
    inputSchema: {
      type: 'object',
      properties: {
        transfer_id: { type: 'string', description: 'Withdrawal transfer ID' },
      },
      required: ['transfer_id'],
    },
  },
  {
    name: 'sardis_list_funding_transactions',
    description: 'List all funding and withdrawal transactions.',
    inputSchema: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['deposit', 'withdrawal', 'all'], description: 'Filter by transaction type' },
        limit: { type: 'number', description: 'Maximum number of results' },
      },
      required: [],
    },
  },
];

// Tool handlers
export const fiatToolHandlers: Record<string, ToolHandler> = {
  sardis_fund_wallet: async (args: unknown): Promise<ToolResult> => {
    const parsed = FundWalletSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    const walletId = parsed.data.wallet_id || config.walletId || 'wallet_default';
    const amount = typeof parsed.data.amount === 'number'
      ? parsed.data.amount.toString()
      : parsed.data.amount;

    if (!config.apiKey || config.mode === 'simulated') {
      const transferId = `fund_${Date.now().toString(36)}`;
      const source = parsed.data.source || 'ach';
      const eta = source === 'wire' ? '1 hour' : source === 'card' ? '5 minutes' : '2-3 business days';

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            funding_id: transferId,
            wallet_id: walletId,
            amount: amount,
            source_type: source,
            currency: parsed.data.currency || 'USD',
            status: 'processing',
            estimated_arrival: eta,
            created_at: new Date().toISOString(),
            message: `Funding of $${amount} initiated via ${source.toUpperCase()}`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<FundingResult>('POST', '/api/v2/fiat/fund', parsed.data);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to fund wallet: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_withdraw_to_bank: async (args: unknown): Promise<ToolResult> => {
    const parsed = WithdrawSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      const transferId = `wd_${Date.now().toString(36)}`;
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: transferId,
            wallet_id: parsed.data.wallet_id,
            amount: parsed.data.amount,
            destination_bank: '****1234',
            status: 'processing',
            estimated_arrival: '1-2 business days',
            created_at: new Date().toISOString(),
            message: `Withdrawal of $${parsed.data.amount} initiated`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<WithdrawalResult>('POST', '/api/v2/fiat/withdraw', parsed.data);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to withdraw: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_funding_status: async (args: unknown): Promise<ToolResult> => {
    const parsed = StatusSchema.safeParse(args);

    const transferId = parsed.success && (parsed.data.transfer_id || parsed.data.funding_id);
    if (!transferId) {
      return {
        content: [{ type: 'text', text: 'Invalid request: transfer_id or funding_id is required' }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            funding_id: transferId,
            id: transferId,
            type: 'funding',
            status: 'completed',
            amount: '100.00',
            completed_at: new Date().toISOString(),
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<FundingResult>('GET', `/api/v2/fiat/status/${transferId}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get status: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_withdrawal_status: async (args: unknown): Promise<ToolResult> => {
    const parsed = StatusSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: parsed.data.transfer_id,
            type: 'withdrawal',
            status: 'processing',
            amount: '100.00',
            estimated_arrival: '1-2 business days',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<WithdrawalResult>('GET', `/api/v2/fiat/status/${parsed.data.transfer_id}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get status: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_withdraw: async (args: unknown): Promise<ToolResult> => {
    const config = getConfig();
    const amount = typeof args === 'object' && args !== null && 'amount' in args
      ? (args as { amount: number }).amount
      : 0;
    const accountId = typeof args === 'object' && args !== null && 'account_id' in args
      ? (args as { account_id?: string }).account_id
      : 'acct_default';
    const walletId = typeof args === 'object' && args !== null && 'wallet_id' in args
      ? (args as { wallet_id?: string }).wallet_id || config.walletId
      : config.walletId;

    if (amount === 0) {
      return {
        content: [{ type: 'text', text: 'Invalid request: amount is required' }],
        isError: true,
      };
    }

    if (!config.apiKey || config.mode === 'simulated') {
      const transferId = `wd_${Date.now().toString(36)}`;
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            withdrawal_id: transferId,
            wallet_id: walletId,
            amount: amount.toString(),
            destination_bank: '****1234',
            account_id: accountId,
            status: 'processing',
            estimated_arrival: '1-2 business days',
            created_at: new Date().toISOString(),
            message: `Withdrawal of $${amount} initiated`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<WithdrawalResult>('POST', '/api/v2/fiat/withdraw', {
        wallet_id: walletId,
        amount: amount.toString(),
        destination_id: accountId,
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to withdraw: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_list_funding_transactions: async (args: unknown): Promise<ToolResult> => {
    const config = getConfig();
    const typeFilter = typeof args === 'object' && args !== null && 'type' in args
      ? (args as { type?: string }).type
      : 'all';

    if (!config.apiKey || config.mode === 'simulated') {
      const mockTransactions = [
        {
          id: 'fund_001',
          type: 'deposit',
          amount: '1000.00',
          status: 'completed',
          source: 'bank_account',
          created_at: new Date(Date.now() - 86400000).toISOString(),
        },
        {
          id: 'wd_001',
          type: 'withdrawal',
          amount: '200.00',
          status: 'processing',
          destination: 'bank_account',
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
      ];

      const filtered = typeFilter === 'all'
        ? mockTransactions
        : mockTransactions.filter(t => t.type === typeFilter);

      return {
        content: [{
          type: 'text',
          text: JSON.stringify(filtered, null, 2),
        }],
      };
    }

    try {
      const params = new URLSearchParams();
      if (typeFilter && typeFilter !== 'all') params.append('type', typeFilter);

      const result = await apiRequest<Array<FundingResult | WithdrawalResult>>(
        'GET',
        `/api/v2/fiat/transactions?${params}`
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list transactions: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
