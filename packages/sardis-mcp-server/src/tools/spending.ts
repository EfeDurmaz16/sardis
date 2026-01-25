/**
 * Spending Reports tools for MCP server
 *
 * Tools for getting spending analytics and reports.
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

// Schemas
const SpendingSummarySchema = z.object({
  wallet_id: z.string().optional().describe('Wallet ID (defaults to configured wallet)'),
  period: z.enum(['day', 'week', 'month', 'year']).optional().describe('Time period'),
});

const SpendingByVendorSchema = z.object({
  wallet_id: z.string().optional().describe('Wallet ID'),
  period: z.enum(['day', 'week', 'month', 'year']).optional().describe('Time period'),
  limit: z.number().optional().describe('Number of vendors to return'),
});

const SpendingByCategorySchema = z.object({
  wallet_id: z.string().optional().describe('Wallet ID'),
  period: z.enum(['day', 'week', 'month', 'year']).optional().describe('Time period'),
});

// Types
interface SpendingSummary {
  wallet_id: string;
  period: string;
  total_spent: string;
  transaction_count: number;
  average_transaction: string;
  remaining_daily_limit: string;
  remaining_monthly_limit: string;
  top_vendor: string;
  top_category: string;
}

interface VendorSpending {
  vendor: string;
  total_spent: string;
  transaction_count: number;
  percentage: number;
}

interface CategorySpending {
  category: string;
  total_spent: string;
  transaction_count: number;
  percentage: number;
}

// Tool definitions
export const spendingToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_get_spending_summary',
    description: 'Get a summary of spending activity including totals, limits, and top vendors.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet ID (defaults to configured wallet)' },
        period: {
          type: 'string',
          enum: ['day', 'week', 'month', 'year'],
          description: 'Time period for summary',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_spending_by_vendor',
    description: 'Get spending breakdown by vendor, sorted by total amount.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet ID' },
        period: {
          type: 'string',
          enum: ['day', 'week', 'month', 'year'],
          description: 'Time period',
        },
        limit: { type: 'number', description: 'Number of vendors to return (default: 10)' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_spending_by_category',
    description: 'Get spending breakdown by merchant category.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet ID' },
        period: {
          type: 'string',
          enum: ['day', 'week', 'month', 'year'],
          description: 'Time period',
        },
      },
      required: [],
    },
  },
];

// Tool handlers
export const spendingToolHandlers: Record<string, ToolHandler> = {
  sardis_get_spending_summary: async (args: unknown): Promise<ToolResult> => {
    const parsed = SpendingSummarySchema.safeParse(args);
    const config = getConfig();
    const walletId = (parsed.success && parsed.data.wallet_id) || config.walletId || 'wallet_default';
    const period = (parsed.success && parsed.data.period) || 'month';

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: walletId,
            period,
            total_spent: '450.00',
            transaction_count: 12,
            average_transaction: '37.50',
            remaining_daily_limit: '50.00',
            remaining_monthly_limit: '550.00',
            top_vendor: 'OpenAI',
            top_category: 'AI Services',
            period_start: new Date(Date.now() - 30 * 24 * 3600000).toISOString().split('T')[0],
            period_end: new Date().toISOString().split('T')[0],
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<SpendingSummary>(
        'GET',
        `/api/v2/spending/summary?wallet_id=${walletId}&period=${period}`
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get spending summary: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_spending_by_vendor: async (args: unknown): Promise<ToolResult> => {
    const parsed = SpendingByVendorSchema.safeParse(args);
    const config = getConfig();
    const walletId = (parsed.success && parsed.data.wallet_id) || config.walletId || 'wallet_default';
    const period = (parsed.success && parsed.data.period) || 'month';
    const limit = (parsed.success && parsed.data.limit) || 10;

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: walletId,
            period,
            vendors: [
              { vendor: 'OpenAI', total_spent: '150.00', transaction_count: 5, percentage: 33.3 },
              { vendor: 'Anthropic', total_spent: '100.00', transaction_count: 3, percentage: 22.2 },
              { vendor: 'AWS', total_spent: '80.00', transaction_count: 2, percentage: 17.8 },
              { vendor: 'Vercel', total_spent: '70.00', transaction_count: 1, percentage: 15.6 },
              { vendor: 'GitHub', total_spent: '50.00', transaction_count: 1, percentage: 11.1 },
            ].slice(0, limit),
            total_vendors: 5,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<{ vendors: VendorSpending[] }>(
        'GET',
        `/api/v2/spending/by-vendor?wallet_id=${walletId}&period=${period}&limit=${limit}`
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get vendor spending: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_spending_by_category: async (args: unknown): Promise<ToolResult> => {
    const parsed = SpendingByCategorySchema.safeParse(args);
    const config = getConfig();
    const walletId = (parsed.success && parsed.data.wallet_id) || config.walletId || 'wallet_default';
    const period = (parsed.success && parsed.data.period) || 'month';

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: walletId,
            period,
            categories: [
              { category: 'AI Services', total_spent: '250.00', transaction_count: 8, percentage: 55.6 },
              { category: 'Cloud Infrastructure', total_spent: '100.00', transaction_count: 2, percentage: 22.2 },
              { category: 'Developer Tools', total_spent: '70.00', transaction_count: 1, percentage: 15.6 },
              { category: 'SaaS', total_spent: '30.00', transaction_count: 1, percentage: 6.6 },
            ],
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<{ categories: CategorySpending[] }>(
        'GET',
        `/api/v2/spending/by-category?wallet_id=${walletId}&period=${period}`
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get category spending: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
