/**
 * Sardis MCP Server - Funding Tools (Sardis Protocol v1.0)
 *
 * Funding Commitments and Cells provide granular control over wallet liquidity.
 * A Funding Commitment reserves a specific amount for a purpose, creating one or
 * more Funding Cells. Cells can be split (subdivide a budget) or merged (consolidate
 * fragmented liquidity) without moving funds on-chain.
 *
 * Tools:
 * - sardis_create_funding_commitment: Reserve funds for a specific purpose
 * - sardis_list_funding_cells: List funding cells with optional filters
 * - sardis_split_cell: Split a funding cell into smaller cells
 * - sardis_merge_cells: Merge multiple funding cells into one
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';

// Zod schemas
const CreateFundingCommitmentSchema = z.object({
  amount: z.string().describe('Total amount to commit as a decimal string (e.g., "500.00")'),
  token: z.string().optional().default('USDC').describe('Token for the commitment (default: USDC)'),
  chain: z.string().optional().default('base').describe('Blockchain network (default: base)'),
  purpose: z.string().describe('Purpose of the funding commitment'),
  mandate_id: z.string().optional().describe('Optional spending mandate to bind this commitment to'),
  cell_count: z.number().optional().default(1).describe('Number of equal cells to create (default: 1)'),
  expires_in_hours: z.number().optional().default(720).describe('Commitment expiration in hours (default: 720 / 30 days)'),
});

const ListFundingCellsSchema = z.object({
  commitment_id: z.string().optional().describe('Filter by funding commitment ID'),
  status: z.string().optional().describe('Filter by status: available, reserved, spent, expired'),
  limit: z.number().optional().default(20).describe('Maximum results to return'),
  offset: z.number().optional().default(0).describe('Pagination offset'),
});

const SplitCellSchema = z.object({
  cell_id: z.string().describe('ID of the funding cell to split'),
  amounts: z.array(z.string()).describe('Array of amounts for the new cells (must sum to original cell amount)'),
  labels: z.array(z.string()).optional().describe('Optional labels for each new cell'),
});

const MergeCellsSchema = z.object({
  cell_ids: z.array(z.string()).min(2).describe('Array of funding cell IDs to merge (minimum 2)'),
  label: z.string().optional().describe('Optional label for the merged cell'),
});

// Tool definitions
export const fundingToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_funding_commitment',
    description:
      'Create a funding commitment that reserves wallet funds for a specific purpose. ' +
      'The commitment creates one or more funding cells that represent subdivided, ' +
      'trackable portions of the reserved amount. Useful for budgeting across multiple ' +
      'agents, projects, or time periods.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: {
          type: 'string',
          description: 'Total amount to commit as a decimal string (e.g., "500.00")',
        },
        token: {
          type: 'string',
          description: 'Token for the commitment (default: USDC)',
          enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
        },
        chain: {
          type: 'string',
          description: 'Blockchain network (default: base)',
        },
        purpose: {
          type: 'string',
          description: 'Purpose of the funding commitment (e.g., "Q1 marketing budget")',
        },
        mandate_id: {
          type: 'string',
          description: 'Optional spending mandate to bind this commitment to',
        },
        cell_count: {
          type: 'number',
          description: 'Number of equal cells to create (default: 1)',
        },
        expires_in_hours: {
          type: 'number',
          description: 'Commitment expiration in hours (default: 720 / 30 days)',
        },
      },
      required: ['amount', 'purpose'],
    },
  },
  {
    name: 'sardis_list_funding_cells',
    description:
      'List funding cells with optional filtering by commitment, status, or pagination. ' +
      'Funding cells are the atomic unit of reserved liquidity within a commitment.',
    inputSchema: {
      type: 'object',
      properties: {
        commitment_id: {
          type: 'string',
          description: 'Filter by funding commitment ID',
        },
        status: {
          type: 'string',
          enum: ['available', 'reserved', 'spent', 'expired'],
          description: 'Filter by cell status',
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
  {
    name: 'sardis_split_cell',
    description:
      'Split a funding cell into multiple smaller cells. The amounts must sum exactly to ' +
      'the original cell amount. Useful for subdividing a budget across multiple agents ' +
      'or purposes without moving funds on-chain.',
    inputSchema: {
      type: 'object',
      properties: {
        cell_id: {
          type: 'string',
          description: 'ID of the funding cell to split',
        },
        amounts: {
          type: 'array',
          items: { type: 'string' },
          description: 'Array of amounts for the new cells (must sum to original cell amount)',
        },
        labels: {
          type: 'array',
          items: { type: 'string' },
          description: 'Optional labels for each new cell',
        },
      },
      required: ['cell_id', 'amounts'],
    },
  },
  {
    name: 'sardis_merge_cells',
    description:
      'Merge multiple funding cells into a single cell. All cells must belong to the same ' +
      'commitment and be in "available" status. Useful for consolidating fragmented ' +
      'liquidity back into a single budget line.',
    inputSchema: {
      type: 'object',
      properties: {
        cell_ids: {
          type: 'array',
          items: { type: 'string' },
          description: 'Array of funding cell IDs to merge (minimum 2)',
        },
        label: {
          type: 'string',
          description: 'Optional label for the merged cell',
        },
      },
      required: ['cell_ids'],
    },
  },
];

// Tool handlers
export const fundingToolHandlers: Record<string, ToolHandler> = {
  sardis_create_funding_commitment: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateFundingCommitmentSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { amount, token, chain, purpose, mandate_id, cell_count, expires_in_hours } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simId = `fc_sim_${Date.now().toString(36)}`;
      const cellAmount = (parseFloat(amount) / cell_count).toFixed(2);
      const cells = Array.from({ length: cell_count }, (_, i) => ({
        cell_id: `cell_sim_${Date.now().toString(36)}_${i}`,
        amount: cellAmount,
        status: 'available',
      }));
      const expiresAt = new Date(Date.now() + expires_in_hours * 3600_000).toISOString();

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                commitment_id: simId,
                amount,
                token,
                chain,
                purpose,
                mandate_id: mandate_id || null,
                cells,
                expires_at: expiresAt,
                created_at: new Date().toISOString(),
                message: `Funding commitment created: ${amount} ${token} split into ${cell_count} cell(s)`,
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
        '/api/v2/funding/commitments',
        { amount, token, chain, purpose, mandate_id, cell_count, expires_in_hours },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                ...result,
                message: `Funding commitment ${result.commitment_id} created (${amount} ${token})`,
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
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to create funding commitment' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_list_funding_cells: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListFundingCellsSchema.safeParse(args);
    const { commitment_id, status, limit, offset } = parsed.success
      ? parsed.data
      : { commitment_id: undefined, status: undefined, limit: 20, offset: 0 };

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simTime = new Date().toISOString();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                cells: [
                  {
                    id: `cell_sim_${Date.now().toString(36)}`,
                    commitment_id: commitment_id || `fc_sim_example`,
                    amount: '100.00',
                    token: 'USDC',
                    status: status || 'available',
                    label: null,
                    created_at: simTime,
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
      if (commitment_id) params.append('commitment_id', commitment_id);
      if (status) params.append('status', status);

      const result = await apiRequest<{ cells: Record<string, unknown>[]; total: number }>(
        'GET',
        `/api/v2/funding/cells?${params}`,
      );

      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: `Failed to list funding cells: ${error instanceof Error ? error.message : 'Unknown error'}` },
        ],
        isError: true,
      };
    }
  },

  sardis_split_cell: async (args: unknown): Promise<ToolResult> => {
    const parsed = SplitCellSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { cell_id, amounts, labels } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const newCells = amounts.map((amt, i) => ({
        cell_id: `cell_sim_${Date.now().toString(36)}_${i}`,
        amount: amt,
        label: labels?.[i] || null,
        status: 'available',
      }));

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                original_cell_id: cell_id,
                new_cells: newCells,
                message: `Cell ${cell_id} split into ${amounts.length} cells`,
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
        `/api/v2/funding/cells/${cell_id}/split`,
        { amounts, labels },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Cell ${cell_id} split into ${amounts.length} cells` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to split cell' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_merge_cells: async (args: unknown): Promise<ToolResult> => {
    const parsed = MergeCellsSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { cell_ids, label } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const mergedId = `cell_sim_merged_${Date.now().toString(36)}`;
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                merged_cell_id: mergedId,
                source_cell_ids: cell_ids,
                amount: '200.00',
                label: label || null,
                status: 'available',
                message: `${cell_ids.length} cells merged into ${mergedId}`,
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
        '/api/v2/funding/cells/merge',
        { cell_ids, label },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `${cell_ids.length} cells merged successfully` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to merge cells' }, null, 2) },
        ],
        isError: true,
      };
    }
  },
};
