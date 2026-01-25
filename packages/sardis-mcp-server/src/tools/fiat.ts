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
  wallet_id: z.string().describe('Wallet to fund'),
  amount: z.string().describe('Amount to fund in USD (e.g., "100.00")'),
  source: z.enum(['ach', 'wire', 'card']).optional().describe('Funding source type'),
  source_id: z.string().optional().describe('Saved payment method ID'),
});

const WithdrawSchema = z.object({
  wallet_id: z.string().describe('Wallet to withdraw from'),
  amount: z.string().describe('Amount to withdraw in USD'),
  destination_id: z.string().describe('Bank account ID to withdraw to'),
});

const StatusSchema = z.object({
  transfer_id: z.string().describe('Transfer ID to check'),
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
    description: 'Fund a wallet from a bank account, wire transfer, or card. USD is automatically converted to USDC.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet to fund' },
        amount: { type: 'string', description: 'Amount to fund in USD (e.g., "100.00")' },
        source: {
          type: 'string',
          enum: ['ach', 'wire', 'card'],
          description: 'Funding source type. ACH is free but slower, wire is faster, card has fees.',
        },
        source_id: { type: 'string', description: 'Saved payment method ID' },
      },
      required: ['wallet_id', 'amount'],
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
    if (!config.apiKey || config.mode === 'simulated') {
      const transferId = `fund_${Date.now().toString(36)}`;
      const source = parsed.data.source || 'ach';
      const eta = source === 'wire' ? '1 hour' : source === 'card' ? '5 minutes' : '2-3 business days';

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: transferId,
            wallet_id: parsed.data.wallet_id,
            amount: parsed.data.amount,
            source_type: source,
            status: 'processing',
            estimated_arrival: eta,
            created_at: new Date().toISOString(),
            message: `Funding of $${parsed.data.amount} initiated via ${source.toUpperCase()}`,
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
            type: 'funding',
            status: 'completed',
            amount: '100.00',
            completed_at: new Date().toISOString(),
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<FundingResult>('GET', `/api/v2/fiat/status/${parsed.data.transfer_id}`);
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
};
