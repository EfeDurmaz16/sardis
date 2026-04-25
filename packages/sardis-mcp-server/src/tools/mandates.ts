/**
 * Spending Mandate tools for MCP server
 *
 * Tools for creating, managing, and validating spending mandates —
 * the core authorization primitive for AI agent payments.
 *
 * API base: /api/v2/spending-mandates (registered in sardis-api/main.py)
 * Query params: status_filter, agent_id (match API exactly)
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
      required: [],
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
async function handleCreateMandate(args: unknown): Promise<ToolResult> {
  const input = args as Record<string, unknown>;
  const config = getConfig();

  const body: Record<string, unknown> = {
    purpose_scope: input.purpose,
    amount_per_tx: input.amount_per_tx,
    amount_daily: input.amount_daily,
    amount_monthly: input.amount_monthly,
    amount_total: input.amount_total,
    approval_threshold: input.approval_threshold,
    approval_mode: input.approval_mode || 'auto',
    allowed_rails: input.allowed_rails || ['card', 'usdc', 'bank'],
    agent_id: input.agent_id,
  };

  if (input.allowed_merchants) {
    body.merchant_scope = { allowed: input.allowed_merchants };
  }

  if (!config.apiKey) {
    // Simulated mode
    const id = `mandate_sim_${Date.now().toString(36)}`;
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            _simulated: true,
            _warning: 'This is simulated data. Configure SARDIS_API_KEY for real data.',
            id,
            purpose: input.purpose,
            amount_per_tx: input.amount_per_tx,
            status: 'active',
            message: `Spending mandate created (simulated). Connect an API key for real mandates.`,
          }, null, 2),
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

async function handleListMandates(args: unknown): Promise<ToolResult> {
  const input = args as Record<string, unknown>;
  const config = getConfig();

  if (!config.apiKey) {
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            _simulated: true,
            _warning: 'This is simulated data. Configure SARDIS_API_KEY for real data.',
            mandates: [],
            message: 'No mandates (simulated mode). Connect an API key to manage real mandates.',
          }, null, 2),
        },
      ],
    };
  }

  let url = '/api/v2/spending-mandates';
  const params: string[] = [];
  if (input.status) params.push(`status_filter=${input.status}`);
  if (input.agent_id) params.push(`agent_id=${input.agent_id}`);
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

async function handleRevokeMandate(args: unknown): Promise<ToolResult> {
  const input = args as Record<string, unknown>;
  const config = getConfig();

  if (!config.apiKey) {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          _simulated: true,
          _warning: 'This is simulated data. Configure SARDIS_API_KEY for real data.',
          mandate_id: input.mandate_id,
          status: 'revoked',
          message: `Mandate ${input.mandate_id} revoked (simulated).`,
        }, null, 2),
      }],
    };
  }

  await apiRequest<Record<string, unknown>>('POST', `/api/v2/spending-mandates/${input.mandate_id}/revoke`, {
    reason: input.reason || 'Revoked via MCP',
  });

  return {
    content: [
      {
        type: 'text',
        text: `🚫 Mandate ${input.mandate_id} permanently revoked.\nReason: ${input.reason || 'Revoked via MCP'}\n\nAll future payments under this mandate are now blocked.`,
      },
    ],
  };
}

async function handleCheckMandate(args: unknown): Promise<ToolResult> {
  const input = args as Record<string, unknown>;
  const config = getConfig();

  if (!config.apiKey) {
    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            _simulated: true,
            _warning: 'This is simulated data. Configure SARDIS_API_KEY for real data.',
            amount: input.amount,
            authorized: true,
            message: `Payment of $${input.amount} would be authorized (simulated). Connect an API key for real mandate validation.`,
          }, null, 2),
        },
      ],
    };
  }

  // Get the mandate details to check locally
  const mandate = await apiRequest<Record<string, unknown>>('GET', `/api/v2/spending-mandates/${input.mandate_id}`);

  const perTx = mandate.amount_per_tx ? parseFloat(mandate.amount_per_tx as string) : Infinity;
  const amount = input.amount as number;
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
