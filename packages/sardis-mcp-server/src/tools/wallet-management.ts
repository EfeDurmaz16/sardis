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
  chain: z.string().optional().describe('Filter by blockchain'),
  status: z.enum(['active', 'inactive']).optional().describe('Filter by status'),
  limit: z.number().optional().describe('Maximum wallets to return'),
});

const UpdateLimitsSchema = z.object({
  wallet_id: z.string().describe('Wallet ID to update'),
  limit_per_tx: z.number().optional().describe('Maximum per transaction'),
  limit_total: z.number().optional().describe('Maximum total/daily limit'),
});

const ArchiveWalletSchema = z.object({
  wallet_id: z.string().describe('Wallet ID to archive'),
  reason: z.string().optional().describe('Reason for archiving'),
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

// SECURITY: Only read-only and wallet creation tools are exposed to AI agents.
// Policy/limit modification and archival tools have been REMOVED to prevent
// prompt-injected agents from escalating their own privileges.
// These operations must be performed via the admin API or dashboard.
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
    name: 'sardis_list_wallets',
    description: 'List all wallets, optionally filtered by agent or status.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: { type: 'string', description: 'Filter by agent ID' },
        chain: { type: 'string', description: 'Filter by blockchain' },
        status: { type: 'string', enum: ['active', 'inactive'], description: 'Filter by status' },
        limit: { type: 'number', description: 'Maximum wallets to return' },
      },
      required: [],
    },
  },
];

// SECURITY: Blocked tool handler — returns an error directing users to the admin API.
const blockedToolHandler = async (_args: unknown): Promise<ToolResult> => ({
  content: [{
    type: 'text',
    text: JSON.stringify({
      error: 'This operation has been disabled for AI agents for security reasons. '
        + 'Policy and limit changes must be made via the admin dashboard or admin API.',
    }),
  }],
  isError: true,
});

// Tool handlers
export const walletManagementToolHandlers: Record<string, ToolHandler> = {
  // SECURITY: Block mutation tools — agents must not modify their own policies/limits
  sardis_update_wallet_policy: blockedToolHandler,
  sardis_update_wallet_limits: blockedToolHandler,
  sardis_archive_wallet: blockedToolHandler,

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
            wallet_id: walletId,
            id: walletId,
            name: parsed.data.name,
            address,
            chain: parsed.data.chain || 'base',
            status: 'active',
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

  // sardis_update_wallet_policy: REMOVED — blocked handler is defined above.
  // The full implementation was previously here but it OVERRODE the blocked handler
  // because in JS object literals the last duplicate key wins. This was a security bug:
  // agents could still modify their own policies despite the intended block.

  sardis_list_wallets: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListWalletsSchema.safeParse(args);
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const wallets = [{
        id: 'wallet_simulated',
        name: 'Default Wallet',
        address: '0x' + '0'.repeat(40),
        chain: 'base',
        is_active: true,
        balance: '1000.00',
        policy: { max_per_tx: '100.00', max_daily: '500.00' },
        created_at: new Date().toISOString(),
      }];

      return {
        content: [{
          type: 'text',
          text: JSON.stringify(wallets, null, 2),
        }],
      };
    }

    try {
      const params = new URLSearchParams();
      if (parsed.success) {
        if (parsed.data.agent_id) params.append('agent_id', parsed.data.agent_id);
        if (parsed.data.chain) params.append('chain', parsed.data.chain);
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

  // sardis_update_wallet_limits: REMOVED — blocked handler is defined above.
  // sardis_archive_wallet: REMOVED — blocked handler is defined above.
  // See security comment above sardis_update_wallet_policy for rationale.
};
