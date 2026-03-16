/**
 * Spending Mandate tools for MCP server
 *
 * Tools for creating, managing, and validating spending mandates —
 * the core authorization primitive for AI agent payments.
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

// Tool definitions
export const mandateToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_mandate',
    description:
      'Create a spending mandate — a scoped, revocable payment authorization for an AI agent. ' +
      'Defines what the agent can spend, on what merchants, up to what amount, with what approval rules.',
    inputSchema: {
      type: 'object',
      properties: {
        purpose: { type: 'string', description: 'Natural language description of what this mandate allows' },
        amount_per_tx: { type: 'number', description: 'Maximum amount per transaction' },
        amount_daily: { type: 'number', description: 'Maximum daily spending aggregate' },
        amount_monthly: { type: 'number', description: 'Maximum monthly spending aggregate' },
        amount_total: { type: 'number', description: 'Total lifetime budget for this mandate' },
        allowed_merchants: {
          type: 'array',
          items: { type: 'string' },
          description: 'List of allowed merchant domains (e.g., ["openai.com", "anthropic.com"])',
        },
        approval_threshold: { type: 'number', description: 'Amount above which human approval is required' },
        approval_mode: {
          type: 'string',
          enum: ['auto', 'threshold', 'always_human'],
          description: 'How approval works: auto (no approval), threshold (above amount), always_human (every payment)',
        },
        allowed_rails: {
          type: 'array',
          items: { type: 'string', enum: ['card', 'usdc', 'bank'] },
          description: 'Permitted payment rails',
        },
        agent_id: { type: 'string', description: 'Agent ID to bind this mandate to' },
      },
      required: ['purpose', 'amount_per_tx'],
    },
  },
  {
    name: 'sardis_list_mandates',
    description: 'List spending mandates for the organization. Filter by status or agent.',
    inputSchema: {
      type: 'object',
      properties: {
        status: {
          type: 'string',
          enum: ['active', 'draft', 'suspended', 'revoked', 'expired', 'consumed'],
          description: 'Filter by mandate status',
        },
        agent_id: { type: 'string', description: 'Filter by agent ID' },
      },
    },
  },
  {
    name: 'sardis_revoke_mandate',
    description:
      'Permanently revoke a spending mandate. This is irreversible — the mandate cannot be reactivated. ' +
      'All future payments under this mandate will be blocked immediately.',
    inputSchema: {
      type: 'object',
      properties: {
        mandate_id: { type: 'string', description: 'ID of the mandate to revoke' },
        reason: { type: 'string', description: 'Reason for revoking the mandate' },
      },
      required: ['mandate_id'],
    },
  },
  {
    name: 'sardis_check_mandate',
    description:
      'Dry-run: check if a payment would be authorized by a specific spending mandate. ' +
      'Returns whether the payment would be approved, rejected, or require human approval.',
    inputSchema: {
      type: 'object',
      properties: {
        mandate_id: { type: 'string', description: 'ID of the mandate to check against' },
        amount: { type: 'number', description: 'Payment amount to check' },
        merchant: { type: 'string', description: 'Merchant domain to check' },
        rail: {
          type: 'string',
          enum: ['card', 'usdc', 'bank'],
          description: 'Payment rail to check',
        },
      },
      required: ['mandate_id', 'amount'],
    },
  },
];

// Tool handlers
async function handleCreateMandate(args: Record<string, unknown>): Promise<ToolResult> {
  const config = getConfig();

  const body: Record<string, unknown> = {
    purpose_scope: args.purpose,
    amount_per_tx: args.amount_per_tx,
    amount_daily: args.amount_daily,
    amount_monthly: args.amount_monthly,
    amount_total: args.amount_total,
    approval_threshold: args.approval_threshold,
    approval_mode: args.approval_mode || 'auto',
    allowed_rails: args.allowed_rails || ['card', 'usdc', 'bank'],
    agent_id: args.agent_id,
  };

  if (args.allowed_merchants) {
    body.merchant_scope = { allowed: args.allowed_merchants };
  }

  if (!config.apiKey) {
    // Simulated mode
    const id = `mandate_sim_${Date.now().toString(36)}`;
    return {
      content: [
        {
          type: 'text',
          text: `✅ Spending mandate created (simulated)\n\nID: ${id}\nPurpose: ${args.purpose}\nPer-tx limit: $${args.amount_per_tx}\nStatus: active\n\nNote: This is simulated. Connect an API key for real mandates.`,
        },
      ],
    };
  }

  const result = await apiRequest<Record<string, unknown>>('POST', '/api/v2/spending-mandates', body);
  return {
    content: [
      {
        type: 'text',
        text: `✅ Spending mandate created\n\nID: ${result.id}\nPurpose: ${result.purpose_scope}\nPer-tx limit: $${result.amount_per_tx}\nApproval mode: ${result.approval_mode}\nStatus: ${result.status}`,
      },
    ],
  };
}

async function handleListMandates(args: Record<string, unknown>): Promise<ToolResult> {
  const config = getConfig();

  if (!config.apiKey) {
    return {
      content: [
        {
          type: 'text',
          text: '📋 No mandates (simulated mode). Connect an API key to manage real mandates.',
        },
      ],
    };
  }

  let url = '/api/v2/spending-mandates';
  const params: string[] = [];
  if (args.status) params.push(`status_filter=${args.status}`);
  if (args.agent_id) params.push(`agent_id=${args.agent_id}`);
  if (params.length) url += `?${params.join('&')}`;

  const mandates = await apiRequest<Record<string, unknown>[]>('GET', url);

  if (!mandates.length) {
    return { content: [{ type: 'text', text: '📋 No spending mandates found.' }] };
  }

  const lines = mandates.map(
    (m) =>
      `• ${m.id} [${m.status}] — ${m.purpose_scope || 'No purpose'} | Per-tx: $${m.amount_per_tx || '∞'} | Spent: $${m.spent_total || '0'}`
  );

  return {
    content: [{ type: 'text', text: `📋 Spending Mandates (${mandates.length})\n\n${lines.join('\n')}` }],
  };
}

async function handleRevokeMandate(args: Record<string, unknown>): Promise<ToolResult> {
  const config = getConfig();

  if (!config.apiKey) {
    return {
      content: [{ type: 'text', text: `🚫 Mandate ${args.mandate_id} revoked (simulated).` }],
    };
  }

  await apiRequest<Record<string, unknown>>('POST', `/api/v2/spending-mandates/${args.mandate_id}/revoke`, {
    reason: args.reason || 'Revoked via MCP',
  });

  return {
    content: [
      {
        type: 'text',
        text: `🚫 Mandate ${args.mandate_id} permanently revoked.\nReason: ${args.reason || 'Revoked via MCP'}\n\nAll future payments under this mandate are now blocked.`,
      },
    ],
  };
}

async function handleCheckMandate(args: Record<string, unknown>): Promise<ToolResult> {
  const config = getConfig();

  if (!config.apiKey) {
    return {
      content: [
        {
          type: 'text',
          text: `✅ Payment of $${args.amount} would be authorized (simulated).\n\nConnect an API key for real mandate validation.`,
        },
      ],
    };
  }

  // Get the mandate details to check locally
  const mandate = await apiRequest<Record<string, unknown>>('GET', `/api/v2/spending-mandates/${args.mandate_id}`);

  const perTx = mandate.amount_per_tx ? parseFloat(mandate.amount_per_tx as string) : Infinity;
  const amount = args.amount as number;
  const status = mandate.status as string;

  if (status !== 'active') {
    return {
      content: [{ type: 'text', text: `❌ Mandate is ${status} — payment would be rejected.` }],
    };
  }

  if (amount > perTx) {
    return {
      content: [
        {
          type: 'text',
          text: `❌ Payment of $${amount} exceeds per-transaction limit of $${perTx}.\n\nSuggestion: Reduce amount or update mandate limits.`,
        },
      ],
    };
  }

  const threshold = mandate.approval_threshold ? parseFloat(mandate.approval_threshold as string) : Infinity;
  const needsApproval = amount > threshold;

  return {
    content: [
      {
        type: 'text',
        text: `✅ Payment of $${amount} would be authorized.${needsApproval ? '\n⚠️ Human approval required (above threshold).' : ''}`,
      },
    ],
  };
}

export const mandateToolHandlers: Record<string, ToolHandler> = {
  sardis_create_mandate: handleCreateMandate,
  sardis_list_mandates: handleListMandates,
  sardis_revoke_mandate: handleRevokeMandate,
  sardis_check_mandate: handleCheckMandate,
};
