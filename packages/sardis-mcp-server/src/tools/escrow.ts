/**
 * Sardis MCP Server - Escrow Tools (Sardis Protocol v1.0)
 *
 * Escrow provides trustless payment guarantees between agents and merchants.
 * Funds are locked in a smart contract escrow until delivery is confirmed or
 * a dispute is resolved. Supports multi-party dispute resolution with evidence
 * submission.
 *
 * Tools:
 * - sardis_create_escrow: Create an escrow hold for a transaction
 * - sardis_confirm_delivery: Confirm delivery and release escrow funds
 * - sardis_file_dispute: File a dispute against an escrow
 * - sardis_submit_evidence: Submit evidence for an ongoing dispute
 * - sardis_resolve_dispute: Resolve a dispute (arbiter only)
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';

// Zod schemas
const CreateEscrowSchema = z.object({
  amount: z.string().describe('Escrow amount as a decimal string (e.g., "100.00")'),
  token: z.string().optional().default('USDC').describe('Token for the escrow (default: USDC)'),
  chain: z.string().optional().default('base').describe('Blockchain network (default: base)'),
  recipient: z.string().describe('Recipient address or merchant domain'),
  description: z.string().optional().default('').describe('Description of the goods or services being escrowed'),
  deadline_hours: z.number().optional().default(168).describe('Hours until escrow expires if not confirmed (default: 168 / 7 days)'),
  arbiter: z.string().optional().describe('Optional arbiter agent ID or address for dispute resolution'),
});

const ConfirmDeliverySchema = z.object({
  escrow_id: z.string().describe('ID of the escrow to confirm delivery for'),
  rating: z.number().optional().describe('Optional satisfaction rating (1-5)'),
  feedback: z.string().optional().default('').describe('Optional feedback message'),
});

const FileDisputeSchema = z.object({
  escrow_id: z.string().describe('ID of the escrow to dispute'),
  reason: z.string().describe('Detailed reason for the dispute'),
  category: z.string().optional().describe('Dispute category: non_delivery, partial_delivery, quality, fraud, other'),
  evidence_uri: z.string().optional().describe('URI of initial evidence (IPFS, HTTPS)'),
});

const SubmitEvidenceSchema = z.object({
  escrow_id: z.string().describe('ID of the disputed escrow'),
  evidence_uri: z.string().describe('URI of the evidence file (IPFS, HTTPS)'),
  evidence_type: z.string().optional().default('document').describe('Type of evidence: document, screenshot, log, communication, other'),
  description: z.string().optional().default('').describe('Description of the evidence'),
});

const ResolveDisputeSchema = z.object({
  escrow_id: z.string().describe('ID of the disputed escrow to resolve'),
  resolution: z.string().describe('Resolution outcome: release_to_recipient, refund_to_sender, split'),
  split_percentage: z.number().optional().describe('Percentage to release to recipient if resolution is "split" (0-100)'),
  reason: z.string().optional().default('').describe('Reason for the resolution decision'),
});

// Tool definitions
export const escrowToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_escrow',
    description:
      'Create an escrow hold that locks funds until delivery is confirmed. The sender\'s funds ' +
      'are held in a smart contract escrow and released to the recipient only when the sender ' +
      'confirms delivery, or resolved through dispute arbitration. An optional arbiter can be ' +
      'designated for dispute resolution.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: {
          type: 'string',
          description: 'Escrow amount as a decimal string (e.g., "100.00")',
        },
        token: {
          type: 'string',
          description: 'Token for the escrow (default: USDC)',
          enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
        },
        chain: {
          type: 'string',
          description: 'Blockchain network (default: base)',
        },
        recipient: {
          type: 'string',
          description: 'Recipient address or merchant domain',
        },
        description: {
          type: 'string',
          description: 'Description of the goods or services being escrowed',
        },
        deadline_hours: {
          type: 'number',
          description: 'Hours until escrow expires if not confirmed (default: 168 / 7 days)',
        },
        arbiter: {
          type: 'string',
          description: 'Optional arbiter agent ID or address for dispute resolution',
        },
      },
      required: ['amount', 'recipient'],
    },
  },
  {
    name: 'sardis_confirm_delivery',
    description:
      'Confirm delivery and release escrow funds to the recipient. Only the original sender ' +
      '(or their agent) can confirm delivery. Once confirmed, funds are transferred to the ' +
      'recipient and the escrow is marked as settled.',
    inputSchema: {
      type: 'object',
      properties: {
        escrow_id: {
          type: 'string',
          description: 'ID of the escrow to confirm delivery for',
        },
        rating: {
          type: 'number',
          description: 'Optional satisfaction rating (1-5)',
        },
        feedback: {
          type: 'string',
          description: 'Optional feedback message',
        },
      },
      required: ['escrow_id'],
    },
  },
  {
    name: 'sardis_file_dispute',
    description:
      'File a dispute against an active escrow. Freezes the escrowed funds until the dispute ' +
      'is resolved by the designated arbiter. Provide a detailed reason and optionally attach ' +
      'initial evidence.',
    inputSchema: {
      type: 'object',
      properties: {
        escrow_id: {
          type: 'string',
          description: 'ID of the escrow to dispute',
        },
        reason: {
          type: 'string',
          description: 'Detailed reason for the dispute',
        },
        category: {
          type: 'string',
          enum: ['non_delivery', 'partial_delivery', 'quality', 'fraud', 'other'],
          description: 'Dispute category',
        },
        evidence_uri: {
          type: 'string',
          description: 'URI of initial evidence (IPFS hash, HTTPS URL)',
        },
      },
      required: ['escrow_id', 'reason'],
    },
  },
  {
    name: 'sardis_submit_evidence',
    description:
      'Submit additional evidence for an ongoing escrow dispute. Both the sender and recipient ' +
      'can submit evidence. The arbiter reviews all evidence before making a resolution decision.',
    inputSchema: {
      type: 'object',
      properties: {
        escrow_id: {
          type: 'string',
          description: 'ID of the disputed escrow',
        },
        evidence_uri: {
          type: 'string',
          description: 'URI of the evidence file (IPFS hash, HTTPS URL)',
        },
        evidence_type: {
          type: 'string',
          enum: ['document', 'screenshot', 'log', 'communication', 'other'],
          description: 'Type of evidence',
        },
        description: {
          type: 'string',
          description: 'Description of the evidence',
        },
      },
      required: ['escrow_id', 'evidence_uri'],
    },
  },
  {
    name: 'sardis_resolve_dispute',
    description:
      'Resolve an escrow dispute as the designated arbiter. The arbiter can release funds to ' +
      'the recipient, refund to the sender, or split the escrowed amount between both parties. ' +
      'Only the arbiter designated at escrow creation can resolve disputes.',
    inputSchema: {
      type: 'object',
      properties: {
        escrow_id: {
          type: 'string',
          description: 'ID of the disputed escrow to resolve',
        },
        resolution: {
          type: 'string',
          enum: ['release_to_recipient', 'refund_to_sender', 'split'],
          description: 'Resolution outcome',
        },
        split_percentage: {
          type: 'number',
          description: 'Percentage to release to recipient if resolution is "split" (0-100)',
        },
        reason: {
          type: 'string',
          description: 'Reason for the resolution decision',
        },
      },
      required: ['escrow_id', 'resolution'],
    },
  },
];

// Tool handlers
export const escrowToolHandlers: Record<string, ToolHandler> = {
  sardis_create_escrow: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateEscrowSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { amount, token, chain, recipient, description, deadline_hours, arbiter } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simId = `esc_sim_${Date.now().toString(36)}`;
      const deadline = new Date(Date.now() + deadline_hours * 3600_000).toISOString();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                escrow_id: simId,
                amount,
                token,
                chain,
                recipient,
                arbiter: arbiter || null,
                status: 'active',
                deadline,
                created_at: new Date().toISOString(),
                message: `Escrow created: ${amount} ${token} held for ${recipient}`,
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
        '/api/v2/escrows',
        { amount, token, chain, recipient, description, deadline_hours, arbiter },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                ...result,
                message: `Escrow ${result.escrow_id} created (${amount} ${token} for ${recipient})`,
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
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to create escrow' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_confirm_delivery: async (args: unknown): Promise<ToolResult> => {
    const parsed = ConfirmDeliverySchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { escrow_id, rating, feedback } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                escrow_id,
                status: 'settled',
                settled_at: new Date().toISOString(),
                rating: rating || null,
                message: `Delivery confirmed for escrow ${escrow_id}. Funds released to recipient.`,
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
        `/api/v2/escrows/${escrow_id}/confirm`,
        { rating, feedback },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Delivery confirmed for escrow ${escrow_id}` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to confirm delivery' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_file_dispute: async (args: unknown): Promise<ToolResult> => {
    const parsed = FileDisputeSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { escrow_id, reason, category, evidence_uri } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const disputeId = `disp_sim_${Date.now().toString(36)}`;
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                escrow_id,
                dispute_id: disputeId,
                status: 'disputed',
                category: category || 'other',
                filed_at: new Date().toISOString(),
                message: `Dispute filed on escrow ${escrow_id}: ${reason}`,
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
        `/api/v2/escrows/${escrow_id}/dispute`,
        { reason, category, evidence_uri },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Dispute filed on escrow ${escrow_id}` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to file dispute' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_submit_evidence: async (args: unknown): Promise<ToolResult> => {
    const parsed = SubmitEvidenceSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { escrow_id, evidence_uri, evidence_type, description } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const evidenceId = `ev_sim_${Date.now().toString(36)}`;
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                escrow_id,
                evidence_id: evidenceId,
                evidence_type,
                evidence_uri,
                submitted_at: new Date().toISOString(),
                message: `Evidence submitted for escrow ${escrow_id} dispute`,
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
        `/api/v2/escrows/${escrow_id}/evidence`,
        { evidence_uri, evidence_type, description },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Evidence submitted for escrow ${escrow_id}` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to submit evidence' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_resolve_dispute: async (args: unknown): Promise<ToolResult> => {
    const parsed = ResolveDisputeSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { escrow_id, resolution, split_percentage, reason } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const resolutionLabel =
        resolution === 'release_to_recipient' ? 'Funds released to recipient' :
        resolution === 'refund_to_sender' ? 'Funds refunded to sender' :
        `Funds split: ${split_percentage || 50}% to recipient, ${100 - (split_percentage || 50)}% refunded`;

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                escrow_id,
                resolution,
                split_percentage: resolution === 'split' ? (split_percentage || 50) : null,
                status: 'resolved',
                resolved_at: new Date().toISOString(),
                message: `Dispute resolved for escrow ${escrow_id}: ${resolutionLabel}`,
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
        `/api/v2/escrows/${escrow_id}/resolve`,
        { resolution, split_percentage, reason },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Dispute resolved for escrow ${escrow_id}` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to resolve dispute' }, null, 2) },
        ],
        isError: true,
      };
    }
  },
};
