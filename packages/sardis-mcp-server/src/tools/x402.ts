/**
 * Sardis MCP Server - x402 Payment Tools
 *
 * Tools for interacting with x402-protected APIs:
 * - sardis_x402_pay: Pay an x402-protected endpoint
 * - sardis_x402_preview_cost: Dry-run cost preview
 * - sardis_x402_list_payments: Audit x402 payments
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';

// Zod schemas
const X402PaySchema = z.object({
  url: z.string().url().describe('URL of the x402-protected endpoint'),
  method: z.enum(['GET', 'POST', 'PUT', 'DELETE']).optional().default('GET'),
  body: z.string().optional().describe('Request body (JSON string)'),
  max_cost: z.string().optional().describe('Maximum amount willing to pay (e.g., "1.00")'),
  dry_run: z.boolean().optional().default(false).describe('Preview cost without paying'),
  preferred_network: z.string().optional().describe('Preferred blockchain network'),
});

const X402PreviewSchema = z.object({
  url: z.string().url().describe('URL to check for x402 pricing'),
});

const X402ListPaymentsSchema = z.object({
  limit: z.number().optional().default(20),
  offset: z.number().optional().default(0),
  status: z.string().optional().describe('Filter by status: verified, settled, failed'),
});

// Response types
interface X402PayResult {
  response: {
    status_code: number;
    body: string;
  };
  payment: {
    payment_id: string;
    amount: string;
    currency: string;
    network: string;
    tx_hash: string;
    dry_run: boolean;
  } | null;
  cost: string;
}

interface X402CostPreview {
  amount: string;
  currency: string;
  network: string;
  policy_check: boolean;
  estimated_total_cost: string;
  failure_reasons: string[];
}

interface X402PaymentRecord {
  payment_id: string;
  status: string;
  amount: string;
  currency: string;
  network: string;
  tx_hash: string | null;
  source: string;
  created_at: string;
}

// Tool definitions
export const x402ToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_x402_pay',
    description:
      'Pay an x402-protected endpoint. Makes an HTTP request, handles 402 Payment Required ' +
      'automatically by negotiating payment, checking spending policy, signing with MPC wallet, ' +
      'and retrying with payment. Returns the API response and payment receipt.',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'URL of the x402-protected endpoint',
        },
        method: {
          type: 'string',
          enum: ['GET', 'POST', 'PUT', 'DELETE'],
          description: 'HTTP method (default: GET)',
        },
        body: {
          type: 'string',
          description: 'Request body as JSON string (for POST/PUT)',
        },
        max_cost: {
          type: 'string',
          description: 'Maximum amount willing to pay in human-readable units (e.g., "1.00" USDC)',
        },
        dry_run: {
          type: 'boolean',
          description: 'If true, preview the cost without making payment',
        },
        preferred_network: {
          type: 'string',
          description: 'Preferred blockchain network (e.g., "base", "polygon")',
        },
      },
      required: ['url'],
    },
  },
  {
    name: 'sardis_x402_preview_cost',
    description:
      'Preview the cost of accessing an x402-protected endpoint without paying. ' +
      'Checks if the endpoint requires payment and whether the current spending policy would allow it.',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'URL to check for x402 pricing',
        },
      },
      required: ['url'],
    },
  },
  {
    name: 'sardis_x402_list_payments',
    description: 'List x402 payment records for audit and tracking.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of records to return (default: 20)',
        },
        offset: {
          type: 'number',
          description: 'Pagination offset',
        },
        status: {
          type: 'string',
          enum: ['verified', 'settled', 'failed'],
          description: 'Filter by payment status',
        },
      },
      required: [],
    },
  },
];

// Tool handlers
export const x402ToolHandlers: Record<string, ToolHandler> = {
  sardis_x402_pay: async (args: unknown): Promise<ToolResult> => {
    const parsed = X402PaySchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { url, method, body, max_cost, dry_run, preferred_network } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated mode
      const simId = `x402_sim_${Date.now().toString(36)}`;
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                response: { status_code: 200, body: '{"data": "simulated_x402_response"}' },
                payment: {
                  payment_id: simId,
                  amount: '1000000',
                  currency: 'USDC',
                  network: preferred_network || config.chain,
                  tx_hash: '0x' + Math.random().toString(16).substring(2).padEnd(64, '0'),
                  dry_run: dry_run || false,
                },
                cost: '$1.00 USDC',
                message: dry_run
                  ? `Dry run: accessing ${url} would cost ~$1.00 USDC`
                  : `Paid $1.00 USDC to access ${url}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<X402PayResult>('POST', '/api/v2/x402/client-request', {
        url,
        method,
        body: body || undefined,
        max_cost: max_cost || undefined,
        dry_run,
        preferred_network: preferred_network || undefined,
        wallet_id: config.walletId,
        agent_id: config.agentId,
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                ...result,
                message: result.payment?.dry_run
                  ? `Dry run: accessing ${url} would cost ${result.cost}`
                  : `Paid ${result.cost} to access ${url}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'x402 payment failed';
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({ success: false, error: msg, url }, null, 2),
          },
        ],
        isError: true,
      };
    }
  },

  sardis_x402_preview_cost: async (args: unknown): Promise<ToolResult> => {
    const parsed = X402PreviewSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { url } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                url,
                amount: '1000000',
                currency: 'USDC',
                network: config.chain,
                policy_check: true,
                estimated_total_cost: '$1.00 USDC',
                failure_reasons: [],
                message: `Endpoint ${url} requires ~$1.00 USDC per request (simulated)`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const preview = await apiRequest<X402CostPreview>('POST', '/api/v2/x402/dry-run', {
        url,
        wallet_id: config.walletId,
        agent_id: config.agentId,
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                ...preview,
                message: preview.policy_check
                  ? `Endpoint requires ${preview.estimated_total_cost} — policy allows`
                  : `Endpoint requires ${preview.estimated_total_cost} — BLOCKED: ${preview.failure_reasons.join(', ')}`,
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
          {
            type: 'text',
            text: `Failed to preview cost: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
        ],
        isError: true,
      };
    }
  },

  sardis_x402_list_payments: async (args: unknown): Promise<ToolResult> => {
    const parsed = X402ListPaymentsSchema.safeParse(args);
    const { limit, offset, status } = parsed.success
      ? parsed.data
      : { limit: 20, offset: 0, status: undefined };

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simTime = new Date().toISOString();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              [
                {
                  payment_id: `x402_sim_${Date.now().toString(36)}`,
                  status: 'settled',
                  amount: '1000000',
                  currency: 'USDC',
                  network: config.chain,
                  tx_hash: '0x' + '1'.repeat(64),
                  source: 'client',
                  created_at: simTime,
                },
              ],
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
      if (status) params.append('status', status);

      const payments = await apiRequest<X402PaymentRecord[]>(
        'GET',
        `/api/v2/x402/settlements?${params}`,
      );

      return {
        content: [{ type: 'text', text: JSON.stringify(payments, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to list x402 payments: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
        ],
        isError: true,
      };
    }
  },
};
