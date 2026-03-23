/**
 * Sardis MCP Server - Payment Object Tools (Sardis Protocol v1.0)
 *
 * Payment Objects are tokenized payment instruments minted from spending mandates.
 * They encapsulate amount, token, chain, and policy constraints into a portable,
 * verifiable object that can be presented to merchants for payment.
 *
 * Tools:
 * - sardis_mint_payment_object: Mint a new payment object from a mandate
 * - sardis_present_payment_object: Present a payment object to a merchant
 * - sardis_verify_payment_object: Verify a payment object's authenticity and constraints
 * - sardis_get_payment_object: Get details of a payment object
 * - sardis_list_payment_objects: List payment objects with optional filters
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';

// Zod schemas
const MintPaymentObjectSchema = z.object({
  mandate_id: z.string().describe('Spending mandate ID to mint the payment object from'),
  amount: z.string().describe('Payment amount as a decimal string (e.g., "25.00")'),
  token: z.string().optional().default('USDC').describe('Token for the payment object (default: USDC)'),
  chain: z.string().optional().default('base').describe('Blockchain network (default: base)'),
  recipient: z.string().optional().describe('Intended recipient address or merchant domain'),
  purpose: z.string().optional().default('').describe('Human-readable purpose for audit trail'),
  expires_in_seconds: z.number().optional().default(3600).describe('Object expiration in seconds (default: 3600)'),
});

const PresentPaymentObjectSchema = z.object({
  payment_object_id: z.string().describe('ID of the payment object to present'),
  merchant: z.string().describe('Merchant domain or address to present the payment to'),
  metadata: z.record(z.string()).optional().describe('Optional metadata to include with the presentation'),
});

const VerifyPaymentObjectSchema = z.object({
  payment_object_id: z.string().describe('ID of the payment object to verify'),
  expected_amount: z.string().optional().describe('Expected amount for verification'),
  expected_token: z.string().optional().describe('Expected token for verification'),
});

const GetPaymentObjectSchema = z.object({
  payment_object_id: z.string().describe('ID of the payment object to retrieve'),
});

const ListPaymentObjectsSchema = z.object({
  mandate_id: z.string().optional().describe('Filter by mandate ID'),
  status: z.string().optional().describe('Filter by status: active, presented, settled, expired, revoked'),
  limit: z.number().optional().default(20).describe('Maximum results to return'),
  offset: z.number().optional().default(0).describe('Pagination offset'),
});

// Tool definitions
export const paymentObjectToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_mint_payment_object',
    description:
      'Mint a new payment object from a spending mandate. The payment object is a portable, ' +
      'verifiable payment instrument that encapsulates amount, token, chain, and policy constraints. ' +
      'It can be presented to merchants for payment without exposing wallet credentials.',
    inputSchema: {
      type: 'object',
      properties: {
        mandate_id: {
          type: 'string',
          description: 'Spending mandate ID to mint the payment object from',
        },
        amount: {
          type: 'string',
          description: 'Payment amount as a decimal string (e.g., "25.00")',
        },
        token: {
          type: 'string',
          description: 'Token for the payment object (default: USDC)',
          enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
        },
        chain: {
          type: 'string',
          description: 'Blockchain network (default: base)',
        },
        recipient: {
          type: 'string',
          description: 'Intended recipient address or merchant domain',
        },
        purpose: {
          type: 'string',
          description: 'Human-readable purpose for the audit trail',
        },
        expires_in_seconds: {
          type: 'number',
          description: 'Object expiration in seconds (default: 3600)',
        },
      },
      required: ['mandate_id', 'amount'],
    },
  },
  {
    name: 'sardis_present_payment_object',
    description:
      'Present a payment object to a merchant for settlement. The merchant verifies the object, ' +
      'confirms the amount, and initiates the on-chain transfer. The payment object transitions ' +
      'from "active" to "presented" and then "settled" once the transfer completes.',
    inputSchema: {
      type: 'object',
      properties: {
        payment_object_id: {
          type: 'string',
          description: 'ID of the payment object to present',
        },
        merchant: {
          type: 'string',
          description: 'Merchant domain or wallet address to present the payment to',
        },
        metadata: {
          type: 'object',
          description: 'Optional metadata to include with the presentation (e.g., order ID, invoice number)',
        },
      },
      required: ['payment_object_id', 'merchant'],
    },
  },
  {
    name: 'sardis_verify_payment_object',
    description:
      'Verify a payment object\'s authenticity, policy compliance, and available balance. ' +
      'Returns whether the object is valid, its current status, and any constraint violations. ' +
      'Typically used by merchants before accepting a payment object.',
    inputSchema: {
      type: 'object',
      properties: {
        payment_object_id: {
          type: 'string',
          description: 'ID of the payment object to verify',
        },
        expected_amount: {
          type: 'string',
          description: 'Expected amount to verify against (optional)',
        },
        expected_token: {
          type: 'string',
          description: 'Expected token to verify against (optional)',
        },
      },
      required: ['payment_object_id'],
    },
  },
  {
    name: 'sardis_get_payment_object',
    description:
      'Get full details of a payment object including its current status, mandate reference, ' +
      'amount, token, chain, recipient, expiration, and settlement information.',
    inputSchema: {
      type: 'object',
      properties: {
        payment_object_id: {
          type: 'string',
          description: 'ID of the payment object to retrieve',
        },
      },
      required: ['payment_object_id'],
    },
  },
  {
    name: 'sardis_list_payment_objects',
    description:
      'List payment objects with optional filtering by mandate, status, or pagination. ' +
      'Returns a paginated list of payment objects with summary information.',
    inputSchema: {
      type: 'object',
      properties: {
        mandate_id: {
          type: 'string',
          description: 'Filter by the spending mandate that minted the objects',
        },
        status: {
          type: 'string',
          enum: ['active', 'presented', 'settled', 'expired', 'revoked'],
          description: 'Filter by payment object status',
        },
        limit: {
          type: 'number',
          description: 'Maximum results to return (default: 20)',
        },
        offset: {
          type: 'number',
          description: 'Pagination offset (default: 0)',
        },
      },
      required: [],
    },
  },
];

// Tool handlers
export const paymentObjectToolHandlers: Record<string, ToolHandler> = {
  sardis_mint_payment_object: async (args: unknown): Promise<ToolResult> => {
    const parsed = MintPaymentObjectSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { mandate_id, amount, token, chain, recipient, purpose, expires_in_seconds } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simId = `po_sim_${Date.now().toString(36)}`;
      const expiresAt = new Date(Date.now() + expires_in_seconds * 1000).toISOString();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                payment_object_id: simId,
                mandate_id,
                amount,
                token,
                chain,
                recipient: recipient || null,
                status: 'active',
                expires_at: expiresAt,
                created_at: new Date().toISOString(),
                message: `Payment object minted: ${amount} ${token} from mandate ${mandate_id}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        '/api/v2/payment-objects/mint',
        { mandate_id, amount, token, chain, recipient, purpose, expires_in_seconds },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                ...result,
                message: `Payment object ${result.payment_object_id} minted (${amount} ${token})`,
              },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to mint payment object' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_present_payment_object: async (args: unknown): Promise<ToolResult> => {
    const parsed = PresentPaymentObjectSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { payment_object_id, merchant, metadata } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                payment_object_id,
                merchant,
                status: 'presented',
                presented_at: new Date().toISOString(),
                message: `Payment object ${payment_object_id} presented to ${merchant}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/payment-objects/${payment_object_id}/present`,
        { merchant, metadata },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Payment object presented to ${merchant}` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to present payment object' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_verify_payment_object: async (args: unknown): Promise<ToolResult> => {
    const parsed = VerifyPaymentObjectSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { payment_object_id, expected_amount, expected_token } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                payment_object_id,
                valid: true,
                status: 'active',
                checks: {
                  signature_valid: true,
                  mandate_active: true,
                  not_expired: true,
                  amount_match: expected_amount ? true : null,
                  token_match: expected_token ? true : null,
                  balance_sufficient: true,
                },
                verified_at: new Date().toISOString(),
                message: `Payment object ${payment_object_id} verified successfully`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const body: Record<string, unknown> = {};
      if (expected_amount) body.expected_amount = expected_amount;
      if (expected_token) body.expected_token = expected_token;

      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/payment-objects/${payment_object_id}/verify`,
        body,
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Payment object ${payment_object_id} verification complete` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to verify payment object' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_get_payment_object: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetPaymentObjectSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { payment_object_id } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                id: payment_object_id,
                mandate_id: 'mandate_sim_example',
                amount: '25.00',
                token: 'USDC',
                chain: config.chain,
                recipient: null,
                status: 'active',
                purpose: 'Simulated payment object',
                created_at: new Date().toISOString(),
                expires_at: new Date(Date.now() + 3600_000).toISOString(),
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'GET',
        `/api/v2/payment-objects/${payment_object_id}`,
      );

      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to get payment object' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_list_payment_objects: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListPaymentObjectsSchema.safeParse(args);
    const { mandate_id, status, limit, offset } = parsed.success
      ? parsed.data
      : { mandate_id: undefined, status: undefined, limit: 20, offset: 0 };

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simTime = new Date().toISOString();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                payment_objects: [
                  {
                    id: `po_sim_${Date.now().toString(36)}`,
                    mandate_id: mandate_id || 'mandate_sim_example',
                    amount: '25.00',
                    token: 'USDC',
                    chain: config.chain,
                    status: status || 'active',
                    created_at: simTime,
                    expires_at: new Date(Date.now() + 3600_000).toISOString(),
                  },
                ],
                total: 1,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });
      if (mandate_id) params.append('mandate_id', mandate_id);
      if (status) params.append('status', status);

      const result = await apiRequest<{ payment_objects: Record<string, unknown>[]; total: number }>(
        'GET',
        `/api/v2/payment-objects?${params}`,
      );

      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: `Failed to list payment objects: ${error instanceof Error ? error.message : 'Unknown error'}` },
        ],
        isError: true,
      };
    }
  },
};
