/**
 * Hold (pre-authorization) tools for MCP server
 */

import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type {
  ToolDefinition,
  ToolHandler,
  ToolResult,
  Hold,
  CreateHoldResult,
} from './types.js';
import {
  CreateHoldSchema,
  CaptureHoldSchema,
  VoidHoldSchema,
  GetHoldSchema,
  ListHoldsSchema,
} from './types.js';

// Tool definitions
export const holdToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_hold',
    description: 'Create a pre-authorization hold on funds. The funds are reserved but not transferred until captured.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet ID to create hold on' },
        amount: { type: ['string', 'number'], description: 'Amount to hold (e.g., "100.00" or 100)' },
        token: {
          type: 'string',
          enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
          description: 'Token type. Defaults to USDC.',
        },
        merchant_id: { type: 'string', description: 'Optional merchant identifier' },
        purpose: { type: 'string', description: 'Purpose of the hold' },
        expires_in: { type: 'number', description: 'Hold duration in seconds (alias for duration_hours * 3600)' },
        duration_hours: { type: 'number', description: 'Hold duration in hours. Defaults to 168 (7 days).' },
      },
      required: ['amount'],
    },
  },
  {
    name: 'sardis_capture_hold',
    description: 'Capture a hold to complete the payment. Can capture partial or full amount.',
    inputSchema: {
      type: 'object',
      properties: {
        hold_id: { type: 'string', description: 'Hold ID to capture' },
        amount: { type: 'string', description: 'Amount to capture. Defaults to full hold amount.' },
      },
      required: ['hold_id'],
    },
  },
  {
    name: 'sardis_void_hold',
    description: 'Void a hold to release the reserved funds without completing payment.',
    inputSchema: {
      type: 'object',
      properties: {
        hold_id: { type: 'string', description: 'Hold ID to void' },
      },
      required: ['hold_id'],
    },
  },
  {
    name: 'sardis_release_hold',
    description: 'Release a hold (alias for sardis_void_hold). Releases the reserved funds without completing payment.',
    inputSchema: {
      type: 'object',
      properties: {
        hold_id: { type: 'string', description: 'Hold ID to release' },
      },
      required: ['hold_id'],
    },
  },
  {
    name: 'sardis_get_hold',
    description: 'Get details of a specific hold.',
    inputSchema: {
      type: 'object',
      properties: {
        hold_id: { type: 'string', description: 'Hold ID to retrieve' },
      },
      required: ['hold_id'],
    },
  },
  {
    name: 'sardis_list_holds',
    description: 'List all holds for a wallet, optionally filtered by status.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: { type: 'string', description: 'Wallet ID to list holds for' },
        status: {
          type: 'string',
          enum: ['active', 'captured', 'voided', 'expired'],
          description: 'Filter by status',
        },
      },
      required: ['wallet_id'],
    },
  },
  {
    name: 'sardis_extend_hold',
    description: 'Extend the expiration time of an active hold.',
    inputSchema: {
      type: 'object',
      properties: {
        hold_id: { type: 'string', description: 'Hold ID to extend' },
        additional_hours: { type: 'number', description: 'Hours to add to expiration' },
      },
      required: ['hold_id', 'additional_hours'],
    },
  },
];

// Tool handlers
export const holdToolHandlers: Record<string, ToolHandler> = {
  sardis_create_hold: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateHoldSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    const walletId = parsed.data.wallet_id || config.walletId || 'wallet_default';
    const amount = typeof parsed.data.amount === 'number' ? parsed.data.amount.toString() : parsed.data.amount;

    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated response
      const holdId = `hold_${Date.now().toString(36)}`;
      const durationHours = parsed.data.expires_in
        ? parsed.data.expires_in / 3600
        : (parsed.data.duration_hours || 168);
      const expiresAt = new Date(Date.now() + durationHours * 3600000).toISOString();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            hold_id: holdId,
            wallet_id: walletId,
            status: 'active',
            amount: typeof parsed.data.amount === 'number' ? parsed.data.amount : parseFloat(parsed.data.amount),
            token: parsed.data.token || 'USDC',
            purpose: parsed.data.purpose,
            expires_at: expiresAt,
            message: `Hold created for ${amount} ${parsed.data.token || 'USDC'}`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<CreateHoldResult>('POST', '/api/v2/holds', parsed.data);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to create hold: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_capture_hold: async (args: unknown): Promise<ToolResult> => {
    const parsed = CaptureHoldSchema.safeParse(args);
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
            hold_id: parsed.data.hold_id,
            status: 'captured',
            captured_amount: parsed.data.amount || '100.00',
            captured_at: new Date().toISOString(),
            message: 'Hold captured successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Hold>(
        'POST',
        `/api/v2/holds/${parsed.data.hold_id}/capture`,
        parsed.data.amount ? { amount: parsed.data.amount } : {}
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to capture hold: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_void_hold: async (args: unknown): Promise<ToolResult> => {
    const parsed = VoidHoldSchema.safeParse(args);
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
            hold_id: parsed.data.hold_id,
            status: 'voided',
            voided_at: new Date().toISOString(),
            message: 'Hold voided successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Hold>('POST', `/api/v2/holds/${parsed.data.hold_id}/void`, {});
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to void hold: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_release_hold: async (args: unknown): Promise<ToolResult> => {
    // Alias for sardis_void_hold
    const parsed = VoidHoldSchema.safeParse(args);
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
            hold_id: parsed.data.hold_id,
            status: 'released',
            released_at: new Date().toISOString(),
            message: 'Hold released successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Hold>('POST', `/api/v2/holds/${parsed.data.hold_id}/void`, {});
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to release hold: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_hold: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetHoldSchema.safeParse(args);
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
            id: parsed.data.hold_id,
            wallet_id: 'wallet_simulated',
            amount: '100.00',
            token: 'USDC',
            status: 'active',
            expires_at: new Date(Date.now() + 7 * 24 * 3600000).toISOString(),
            created_at: new Date().toISOString(),
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Hold>('GET', `/api/v2/holds/${parsed.data.hold_id}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get hold: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_list_holds: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListHoldsSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    const walletId = (parsed.success && parsed.data.wallet_id) || config.walletId || 'wallet_default';
    const statusFilter = parsed.success && parsed.data.status;

    if (!config.apiKey || config.mode === 'simulated') {
      const holds = [{
        hold_id: 'hold_simulated',
        id: 'hold_simulated',
        wallet_id: walletId,
        amount: '100.00',
        token: 'USDC',
        status: statusFilter || 'active',
        expires_at: new Date(Date.now() + 7 * 24 * 3600000).toISOString(),
      }];

      return {
        content: [{
          type: 'text',
          text: JSON.stringify(holds, null, 2),
        }],
      };
    }

    try {
      let url = `/api/v2/holds/wallet/${parsed.data.wallet_id}`;
      if (parsed.data.status) {
        url += `?status=${parsed.data.status}`;
      }
      const result = await apiRequest<{ holds: Hold[] }>('GET', url);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list holds: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_extend_hold: async (args: unknown): Promise<ToolResult> => {
    const schema = GetHoldSchema.extend({
      additional_hours: CreateHoldSchema.shape.duration_hours,
    });
    const parsed = schema.safeParse(args);
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
            hold_id: parsed.data.hold_id,
            status: 'active',
            expires_at: new Date(Date.now() + (168 + (parsed.data.additional_hours || 0)) * 3600000).toISOString(),
            message: `Hold extended by ${parsed.data.additional_hours} hours`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Hold>(
        'POST',
        `/api/v2/holds/${parsed.data.hold_id}/extend`,
        { additional_hours: parsed.data.additional_hours }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to extend hold: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
