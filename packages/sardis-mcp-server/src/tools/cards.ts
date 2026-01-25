/**
 * Virtual Card tools for MCP server
 *
 * Tools for issuing and managing virtual Visa/Mastercard cards via Lithic integration.
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

// Schemas
const IssueCardSchema = z.object({
  wallet_id: z.string().describe('Wallet to link the card to'),
  spending_limit: z.string().optional().describe('Card spending limit (e.g., "500.00")'),
  merchant_lock: z.string().optional().describe('Lock card to specific merchant domain'),
  nickname: z.string().optional().describe('Card nickname for identification'),
});

const CardIdSchema = z.object({
  card_id: z.string().describe('Card ID'),
});

const ListCardsSchema = z.object({
  wallet_id: z.string().optional().describe('Filter by wallet ID'),
  status: z.enum(['active', 'frozen', 'cancelled']).optional().describe('Filter by status'),
});

// Types
interface VirtualCard {
  id: string;
  wallet_id: string;
  last_four: string;
  network: 'visa' | 'mastercard';
  status: 'active' | 'frozen' | 'cancelled';
  spending_limit?: string;
  merchant_lock?: string;
  nickname?: string;
  created_at: string;
}

// Tool definitions
export const cardToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_issue_card',
    description: 'Issue a new virtual Visa/Mastercard linked to a wallet. Cards can be used for online and physical purchases.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet to link the card to' },
        spending_limit: { type: 'string', description: 'Card spending limit (e.g., "500.00")' },
        merchant_lock: { type: 'string', description: 'Lock card to specific merchant domain (e.g., "aws.amazon.com")' },
        nickname: { type: 'string', description: 'Card nickname for identification' },
      },
      required: ['wallet_id'],
    },
  },
  {
    name: 'sardis_get_card',
    description: 'Get details of a specific virtual card including masked card number.',
    inputSchema: {
      type: 'object',
      properties: {
        card_id: { type: 'string', description: 'Card ID to retrieve' },
      },
      required: ['card_id'],
    },
  },
  {
    name: 'sardis_list_cards',
    description: 'List all virtual cards, optionally filtered by wallet or status.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Filter by wallet ID' },
        status: { type: 'string', enum: ['active', 'frozen', 'cancelled'], description: 'Filter by status' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_freeze_card',
    description: 'Temporarily freeze a card. Frozen cards cannot be used for transactions.',
    inputSchema: {
      type: 'object',
      properties: {
        card_id: { type: 'string', description: 'Card ID to freeze' },
      },
      required: ['card_id'],
    },
  },
  {
    name: 'sardis_unfreeze_card',
    description: 'Unfreeze a previously frozen card.',
    inputSchema: {
      type: 'object',
      properties: {
        card_id: { type: 'string', description: 'Card ID to unfreeze' },
      },
      required: ['card_id'],
    },
  },
  {
    name: 'sardis_cancel_card',
    description: 'Permanently cancel a card. This action cannot be undone.',
    inputSchema: {
      type: 'object',
      properties: {
        card_id: { type: 'string', description: 'Card ID to cancel' },
      },
      required: ['card_id'],
    },
  },
];

// Tool handlers
export const cardToolHandlers: Record<string, ToolHandler> = {
  sardis_issue_card: async (args: unknown): Promise<ToolResult> => {
    const parsed = IssueCardSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      const cardId = `card_${Date.now().toString(36)}`;
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: cardId,
            wallet_id: parsed.data.wallet_id,
            last_four: '4242',
            network: 'visa',
            status: 'active',
            spending_limit: parsed.data.spending_limit || 'unlimited',
            merchant_lock: parsed.data.merchant_lock,
            nickname: parsed.data.nickname,
            created_at: new Date().toISOString(),
            message: 'Virtual card issued successfully (simulated)',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<VirtualCard>('POST', '/api/v2/cards', parsed.data);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to issue card: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_card: async (args: unknown): Promise<ToolResult> => {
    const parsed = CardIdSchema.safeParse(args);
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
            id: parsed.data.card_id,
            wallet_id: 'wallet_simulated',
            last_four: '4242',
            network: 'visa',
            status: 'active',
            spending_limit: '500.00',
            created_at: new Date().toISOString(),
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<VirtualCard>('GET', `/api/v2/cards/${parsed.data.card_id}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get card: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_list_cards: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListCardsSchema.safeParse(args);
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            cards: [{
              id: 'card_simulated',
              wallet_id: parsed.success ? parsed.data.wallet_id || 'wallet_simulated' : 'wallet_simulated',
              last_four: '4242',
              network: 'visa',
              status: 'active',
              spending_limit: '500.00',
              created_at: new Date().toISOString(),
            }],
          }, null, 2),
        }],
      };
    }

    try {
      const params = new URLSearchParams();
      if (parsed.success && parsed.data.wallet_id) params.append('wallet_id', parsed.data.wallet_id);
      if (parsed.success && parsed.data.status) params.append('status', parsed.data.status);

      const url = `/api/v2/cards${params.toString() ? `?${params}` : ''}`;
      const result = await apiRequest<{ cards: VirtualCard[] }>('GET', url);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list cards: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_freeze_card: async (args: unknown): Promise<ToolResult> => {
    const parsed = CardIdSchema.safeParse(args);
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
            id: parsed.data.card_id,
            status: 'frozen',
            frozen_at: new Date().toISOString(),
            message: 'Card frozen successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<VirtualCard>('POST', `/api/v2/cards/${parsed.data.card_id}/freeze`, {});
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to freeze card: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_unfreeze_card: async (args: unknown): Promise<ToolResult> => {
    const parsed = CardIdSchema.safeParse(args);
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
            id: parsed.data.card_id,
            status: 'active',
            unfrozen_at: new Date().toISOString(),
            message: 'Card unfrozen successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<VirtualCard>('POST', `/api/v2/cards/${parsed.data.card_id}/unfreeze`, {});
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to unfreeze card: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_cancel_card: async (args: unknown): Promise<ToolResult> => {
    const parsed = CardIdSchema.safeParse(args);
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
            id: parsed.data.card_id,
            status: 'cancelled',
            cancelled_at: new Date().toISOString(),
            message: 'Card cancelled permanently',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<VirtualCard>('DELETE', `/api/v2/cards/${parsed.data.card_id}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to cancel card: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
