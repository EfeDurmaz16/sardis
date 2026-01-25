/**
 * Approval Flow tools for MCP server
 *
 * Tools for requesting human approval for payments that exceed limits.
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

// Schemas
const RequestApprovalSchema = z.object({
  vendor: z.string().describe('Vendor for the payment'),
  amount: z.number().describe('Payment amount requiring approval'),
  purpose: z.string().describe('Reason for the payment'),
  urgency: z.enum(['low', 'medium', 'high']).optional().describe('How urgent is this approval'),
  expires_in_hours: z.number().optional().describe('Hours until request expires (default: 24)'),
});

const ApprovalStatusSchema = z.object({
  approval_id: z.string().describe('Approval request ID'),
});

// Types
interface ApprovalRequest {
  id: string;
  vendor: string;
  amount: number;
  purpose: string;
  status: 'pending' | 'approved' | 'denied' | 'expired';
  urgency: 'low' | 'medium' | 'high';
  requested_by: string;
  reviewed_by?: string;
  created_at: string;
  expires_at: string;
  reviewed_at?: string;
}

// Tool definitions
export const approvalToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_request_approval',
    description: 'Request human approval for a payment that exceeds policy limits or requires manual review.',
    inputSchema: {
      type: 'object',
      properties: {
        vendor: { type: 'string', description: 'Vendor for the payment' },
        amount: { type: 'number', description: 'Payment amount requiring approval' },
        purpose: { type: 'string', description: 'Reason for the payment' },
        urgency: {
          type: 'string',
          enum: ['low', 'medium', 'high'],
          description: 'How urgent is this approval request',
        },
        expires_in_hours: { type: 'number', description: 'Hours until request expires (default: 24)' },
      },
      required: ['vendor', 'amount', 'purpose'],
    },
  },
  {
    name: 'sardis_get_approval_status',
    description: 'Check the status of a pending approval request.',
    inputSchema: {
      type: 'object',
      properties: {
        approval_id: { type: 'string', description: 'Approval request ID' },
      },
      required: ['approval_id'],
    },
  },
];

// Tool handlers
export const approvalToolHandlers: Record<string, ToolHandler> = {
  sardis_request_approval: async (args: unknown): Promise<ToolResult> => {
    const parsed = RequestApprovalSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      const approvalId = `appr_${Date.now().toString(36)}`;
      const expiresAt = new Date(
        Date.now() + (parsed.data.expires_in_hours || 24) * 3600000
      ).toISOString();

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: approvalId,
            vendor: parsed.data.vendor,
            amount: parsed.data.amount,
            purpose: parsed.data.purpose,
            status: 'pending',
            urgency: parsed.data.urgency || 'medium',
            requested_by: config.agentId || 'agent_simulated',
            created_at: new Date().toISOString(),
            expires_at: expiresAt,
            message: `Approval request submitted. Human review required for $${parsed.data.amount} payment to ${parsed.data.vendor}.`,
            next_steps: 'The request will be reviewed by an authorized approver. Check status using sardis_get_approval_status.',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<ApprovalRequest>('POST', '/api/v2/approvals', parsed.data);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to request approval: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_approval_status: async (args: unknown): Promise<ToolResult> => {
    const parsed = ApprovalStatusSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      // Simulate random status for demo
      const statuses: ApprovalRequest['status'][] = ['pending', 'approved', 'denied'];
      const status = statuses[Math.floor(Math.random() * statuses.length)];

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: parsed.data.approval_id,
            vendor: 'Example Vendor',
            amount: 500,
            purpose: 'Service payment',
            status,
            urgency: 'medium',
            requested_by: 'agent_simulated',
            reviewed_by: status !== 'pending' ? 'admin@example.com' : undefined,
            created_at: new Date(Date.now() - 3600000).toISOString(),
            expires_at: new Date(Date.now() + 20 * 3600000).toISOString(),
            reviewed_at: status !== 'pending' ? new Date().toISOString() : undefined,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<ApprovalRequest>('GET', `/api/v2/approvals/${parsed.data.approval_id}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get approval status: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
