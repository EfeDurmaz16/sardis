/**
 * Wallet Management tools for MCP server
 *
 * Tools for creating and managing wallets and their policies.
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

// Schemas
const CreateWalletSchema = z.object({
  name: z.string().describe('Wallet name'),
  chain: z.enum(['base', 'polygon', 'ethereum', 'arbitrum', 'optimism']).optional().describe('Blockchain network'),
  policy: z.object({
    max_per_tx: z.string().optional().describe('Maximum amount per transaction'),
    max_daily: z.string().optional().describe('Maximum daily spending'),
    allowed_vendors: z.array(z.string()).optional().describe('Allowed vendor list'),
    blocked_categories: z.array(z.string()).optional().describe('Blocked categories'),
  }).optional().describe('Spending policy'),
});

const UpdatePolicySchema = z.object({
  wallet_id: z.string().describe('Wallet ID to update'),
  policy: z.object({
    max_per_tx: z.string().optional(),
    max_daily: z.string().optional(),
    max_monthly: z.string().optional(),
    allowed_vendors: z.array(z.string()).optional(),
    blocked_vendors: z.array(z.string()).optional(),
    blocked_categories: z.array(z.string()).optional(),
    require_approval_above: z.string().optional(),
  }).describe('New policy settings'),
});

const ListWalletsSchema = z.object({
  agent_id: z.string().optional().describe('Filter by agent ID'),
  status: z.enum(['active', 'inactive']).optional().describe('Filter by status'),
  limit: z.number().optional().describe('Maximum wallets to return'),
});

// Types
interface Wallet {
  id: string;
  name: string;
  address: string;
  chain: string;
  is_active: boolean;
  balance?: string;
  policy: {
    max_per_tx?: string;
    max_daily?: string;
    max_monthly?: string;
    allowed_vendors?: string[];
    blocked_vendors?: string[];
    blocked_categories?: string[];
  };
  created_at: string;
}

// Tool definitions
export const walletManagementToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_wallet',
    description: 'Create a new MPC wallet for an agent with optional spending policy.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Wallet name' },
        chain: {
          type: 'string',
          enum: ['base', 'polygon', 'ethereum', 'arbitrum', 'optimism'],
          description: 'Blockchain network (default: base)',
        },
        policy: {
          type: 'object',
          description: 'Spending policy settings',
          properties: {
            max_per_tx: { type: 'string', description: 'Maximum per transaction (e.g., "100.00")' },
            max_daily: { type: 'string', description: 'Maximum daily spending' },
            allowed_vendors: {
              type: 'array',
              items: { type: 'string' },
              description: 'List of allowed vendors',
            },
            blocked_categories: {
              type: 'array',
              items: { type: 'string' },
              description: 'Blocked spending categories',
            },
          },
        },
      },
      required: ['name'],
    },
  },
  {
    name: 'sardis_update_wallet_policy',
    description: 'Update the spending policy for a wallet.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet ID to update' },
        policy: {
          type: 'object',
          description: 'New policy settings',
          properties: {
            max_per_tx: { type: 'string', description: 'Maximum per transaction' },
            max_daily: { type: 'string', description: 'Maximum daily spending' },
            max_monthly: { type: 'string', description: 'Maximum monthly spending' },
            allowed_vendors: { type: 'array', items: { type: 'string' } },
            blocked_vendors: { type: 'array', items: { type: 'string' } },
            blocked_categories: { type: 'array', items: { type: 'string' } },
            require_approval_above: { type: 'string', description: 'Amount above which approval is required' },
          },
        },
      },
      required: ['wallet_id', 'policy'],
    },
  },
  {
    name: 'sardis_list_wallets',
    description: 'List all wallets, optionally filtered by agent or status.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: { type: 'string', description: 'Filter by agent ID' },
        status: { type: 'string', enum: ['active', 'inactive'], description: 'Filter by status' },
        limit: { type: 'number', description: 'Maximum wallets to return' },
      },
      required: [],
    },
  },
];

// Tool handlers
export const walletManagementToolHandlers: Record<string, ToolHandler> = {
  sardis_create_wallet: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateWalletSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      const walletId = `wallet_${Date.now().toString(36)}`;
      const address = '0x' + Array(40).fill(0).map(() => Math.floor(Math.random() * 16).toString(16)).join('');

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: walletId,
            name: parsed.data.name,
            address,
            chain: parsed.data.chain || 'base',
            is_active: true,
            balance: '0.00',
            policy: parsed.data.policy || { max_per_tx: '100.00', max_daily: '500.00' },
            created_at: new Date().toISOString(),
            message: `Wallet "${parsed.data.name}" created successfully`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Wallet>('POST', '/api/v2/wallets', parsed.data);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to create wallet: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_update_wallet_policy: async (args: unknown): Promise<ToolResult> => {
    const parsed = UpdatePolicySchema.safeParse(args);
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
            wallet_id: parsed.data.wallet_id,
            policy: parsed.data.policy,
            updated_at: new Date().toISOString(),
            message: 'Wallet policy updated successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Wallet>(
        'PATCH',
        `/api/v2/wallets/${parsed.data.wallet_id}/policy`,
        { policy: parsed.data.policy }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to update policy: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_list_wallets: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListWalletsSchema.safeParse(args);
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallets: [{
              id: 'wallet_simulated',
              name: 'Default Wallet',
              address: '0x' + '0'.repeat(40),
              chain: 'base',
              is_active: true,
              balance: '1000.00',
              policy: { max_per_tx: '100.00', max_daily: '500.00' },
              created_at: new Date().toISOString(),
            }],
            total: 1,
          }, null, 2),
        }],
      };
    }

    try {
      const params = new URLSearchParams();
      if (parsed.success) {
        if (parsed.data.agent_id) params.append('agent_id', parsed.data.agent_id);
        if (parsed.data.status) params.append('status', parsed.data.status);
        if (parsed.data.limit) params.append('limit', parsed.data.limit.toString());
      }

      const url = `/api/v2/wallets${params.toString() ? `?${params}` : ''}`;
      const result = await apiRequest<{ wallets: Wallet[] }>('GET', url);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list wallets: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
