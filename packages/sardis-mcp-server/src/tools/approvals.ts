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
  action: z.string().describe('Type of action requiring approval'),
  vendor: z.string().optional().describe('Vendor for the payment'),
  amount: z.number().optional().describe('Payment amount requiring approval'),
  reason: z.string().optional().describe('Reason for the approval request'),
  purpose: z.string().optional().describe('Purpose of the payment'),
  card_limit: z.number().optional().describe('Card limit (for create_card action)'),
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
        action: { type: 'string', description: 'Type of action requiring approval (payment, create_card, etc.)' },
        vendor: { type: 'string', description: 'Vendor for the payment' },
        amount: { type: 'number', description: 'Payment amount requiring approval' },
        reason: { type: 'string', description: 'Reason for the approval request' },
        purpose: { type: 'string', description: 'Purpose of the payment' },
        card_limit: { type: 'number', description: 'Card limit (for create_card action)' },
        urgency: {
          type: 'string',
          enum: ['low', 'medium', 'high'],
          description: 'How urgent is this approval request',
        },
        expires_in_hours: { type: 'number', description: 'Hours until request expires (default: 24)' },
      },
      required: ['action'],
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
  {
    name: 'sardis_check_approval',
    description: 'Check the status of an approval request (alias for sardis_get_approval_status).',
    inputSchema: {
      type: 'object',
      properties: {
        approval_id: { type: 'string', description: 'Approval request ID' },
      },
      required: ['approval_id'],
    },
  },
  {
    name: 'sardis_list_pending_approvals',
    description: 'List all pending approval requests.',
    inputSchema: {
      type: 'object',
      properties: {
        action: { type: 'string', description: 'Filter by action type' },
        limit: { type: 'number', description: 'Maximum number of results' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_cancel_approval',
    description: 'Cancel a pending approval request.',
    inputSchema: {
      type: 'object',
      properties: {
        approval_id: { type: 'string', description: 'Approval request ID to cancel' },
        reason: { type: 'string', description: 'Reason for cancellation' },
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

      const description = parsed.data.action === 'payment' && parsed.data.vendor && parsed.data.amount
        ? `$${parsed.data.amount} payment to ${parsed.data.vendor}`
        : parsed.data.action === 'create_card'
        ? `Create card with limit $${parsed.data.card_limit || 'unlimited'}`
        : parsed.data.action;

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            approval_id: approvalId,
            action: parsed.data.action,
            vendor: parsed.data.vendor,
            amount: parsed.data.amount,
            reason: parsed.data.reason,
            purpose: parsed.data.purpose,
            card_limit: parsed.data.card_limit,
            status: 'pending',
            urgency: parsed.data.urgency || 'medium',
            requested_by: config.agentId || 'agent_simulated',
            created_at: new Date().toISOString(),
            expires_at: expiresAt,
            message: `Approval request submitted. Human review required for ${description}.`,
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
            approval_id: parsed.data.approval_id,
            action: 'payment',
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

  sardis_check_approval: async (args: unknown): Promise<ToolResult> => {
    // Alias for sardis_get_approval_status
    const handler = approvalToolHandlers['sardis_get_approval_status'];
    if (!handler) {
      return {
        content: [{ type: 'text', text: 'Handler not found' }],
        isError: true,
      };
    }
    return handler(args);
  },

  sardis_list_pending_approvals: async (args: unknown): Promise<ToolResult> => {
    const config = getConfig();
    const actionFilter = typeof args === 'object' && args !== null && 'action' in args
      ? (args as { action?: string }).action
      : undefined;

    if (!config.apiKey || config.mode === 'simulated') {
      const mockApprovals = [
        {
          approval_id: 'appr_pending_1',
          action: 'payment',
          vendor: 'OpenAI',
          amount: 500,
          status: 'pending',
          urgency: 'high',
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          approval_id: 'appr_pending_2',
          action: 'create_card',
          card_limit: 1000,
          status: 'pending',
          urgency: 'medium',
          created_at: new Date(Date.now() - 7200000).toISOString(),
        },
      ];

      const filtered = actionFilter
        ? mockApprovals.filter(a => a.action === actionFilter)
        : mockApprovals;

      return {
        content: [{
          type: 'text',
          text: JSON.stringify(filtered, null, 2),
        }],
      };
    }

    try {
      const params = new URLSearchParams({ status: 'pending' });
      if (actionFilter) params.append('action', actionFilter);

      const result = await apiRequest<ApprovalRequest[]>('GET', `/api/v2/approvals?${params}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list approvals: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_cancel_approval: async (args: unknown): Promise<ToolResult> => {
    const parsed = ApprovalStatusSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    const reason = typeof args === 'object' && args !== null && 'reason' in args
      ? (args as { reason?: string }).reason
      : 'Cancelled by agent';

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            approval_id: parsed.data.approval_id,
            status: 'cancelled',
            reason,
            cancelled_at: new Date().toISOString(),
            message: 'Approval request cancelled successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<ApprovalRequest>(
        'DELETE',
        `/api/v2/approvals/${parsed.data.approval_id}`,
        { reason }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to cancel approval: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
