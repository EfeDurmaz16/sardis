/**
 * Sardis MCP Server - MPP (Machine Payments Protocol) Tools
 *
 * Tools for managing MPP payment sessions on Tempo.
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';

const CreateSessionSchema = z.object({
  spending_limit: z.number().positive().describe('Maximum spending for this session in USD'),
  method: z.enum(['tempo', 'stripe_spt']).optional().default('tempo'),
  chain: z.string().optional().default('tempo'),
  currency: z.string().optional().default('USDC'),
  mandate_id: z.string().optional().describe('Spending mandate to bind to'),
  wallet_id: z.string().optional().describe('Wallet ID to use'),
  agent_id: z.string().optional().describe('Agent ID for this session'),
  expires_in_seconds: z.number().int().positive().optional().default(3600),
});

const ExecutePaymentSchema = z.object({
  session_id: z.string().describe('MPP session ID'),
  amount: z.number().positive().describe('Payment amount'),
  merchant: z.string().describe('Merchant identifier or URL'),
  merchant_url: z.string().optional().describe('Merchant URL for MPP discovery'),
  memo: z.string().optional().describe('Payment memo'),
});

const SessionIdSchema = z.object({
  session_id: z.string().describe('MPP session ID'),
});

const EvaluatePolicySchema = z.object({
  amount: z.number().positive().describe('Payment amount to evaluate'),
  merchant: z.string().describe('Merchant identifier'),
  payment_type: z.string().optional().default('mpp_tempo'),
  currency: z.string().optional().default('USDC'),
  network: z.string().optional().default('tempo'),
});

function serialize(result: unknown): ToolResult {
  return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
}

function errorResult(message: string): ToolResult {
  return { content: [{ type: 'text', text: message }], isError: true };
}

const IssueCardSchema = z.object({
  amount: z.number().min(5).max(1000).describe('Card amount in USD ($5-$1,000)'),
  currency: z.string().optional().default('USD'),
  session_id: z.string().optional().describe('MPP session to charge against'),
});

export const mppToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_mpp_create_session',
    description:
      'Create an MPP payment session with a spending limit for agent payments on Tempo. Returns session ID for subsequent payments.',
    inputSchema: {
      type: 'object',
      properties: {
        spending_limit: {
          type: 'number',
          description: 'Maximum spending for this session in USD',
        },
        method: {
          type: 'string',
          enum: ['tempo', 'stripe_spt'],
          description: 'Payment method (default: tempo)',
        },
        chain: {
          type: 'string',
          description: 'Target chain (default: tempo)',
        },
        currency: {
          type: 'string',
          description: 'Payment currency (default: USDC)',
        },
        mandate_id: {
          type: 'string',
          description: 'Spending mandate to bind this session to',
        },
        wallet_id: {
          type: 'string',
          description: 'Wallet ID to use for payments',
        },
        agent_id: {
          type: 'string',
          description: 'Agent ID for this session',
        },
        expires_in_seconds: {
          type: 'number',
          description: 'Session TTL in seconds (default: 3600)',
        },
      },
      required: ['spending_limit'],
    },
  },
  {
    name: 'sardis_mpp_execute',
    description:
      'Execute an MPP payment within an active session. Validates against session spending limit before processing.',
    inputSchema: {
      type: 'object',
      properties: {
        session_id: {
          type: 'string',
          description: 'MPP session ID from sardis_mpp_create_session',
        },
        amount: {
          type: 'number',
          description: 'Payment amount in session currency',
        },
        merchant: {
          type: 'string',
          description: 'Merchant identifier or domain (e.g., "openai.com")',
        },
        merchant_url: {
          type: 'string',
          description: 'Full merchant URL for MPP service discovery',
        },
        memo: {
          type: 'string',
          description: 'Payment memo for audit trail',
        },
      },
      required: ['session_id', 'amount', 'merchant'],
    },
  },
  {
    name: 'sardis_mpp_close_session',
    description: 'Close an MPP session and settle remaining balance. Returns final session summary.',
    inputSchema: {
      type: 'object',
      properties: {
        session_id: {
          type: 'string',
          description: 'MPP session ID to close',
        },
      },
      required: ['session_id'],
    },
  },
  {
    name: 'sardis_mpp_get_session',
    description: 'Get MPP session status including remaining budget and payment count.',
    inputSchema: {
      type: 'object',
      properties: {
        session_id: {
          type: 'string',
          description: 'MPP session ID to query',
        },
      },
      required: ['session_id'],
    },
  },
  {
    name: 'sardis_mpp_issue_card',
    description:
      'Issue a virtual prepaid Visa card via Laso Finance MPP service. Cards are single-use, $5-$1,000, funded with USDC. Can be charged against an MPP session budget.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: {
          type: 'number',
          description: 'Card amount in USD ($5-$1,000). Must match checkout total exactly.',
        },
        currency: {
          type: 'string',
          description: 'Card currency (default: USD)',
        },
        session_id: {
          type: 'string',
          description: 'MPP session ID to charge the card against (optional)',
        },
      },
      required: ['amount'],
    },
  },
  {
    name: 'sardis_mpp_evaluate_policy',
    description: 'Evaluate Sardis spending policy for an MPP payment without executing it (dry-run).',
    inputSchema: {
      type: 'object',
      properties: {
        amount: {
          type: 'number',
          description: 'Payment amount to evaluate',
        },
        merchant: {
          type: 'string',
          description: 'Merchant identifier',
        },
        payment_type: {
          type: 'string',
          description: 'Payment type (default: mpp_tempo)',
        },
        currency: {
          type: 'string',
          description: 'Currency (default: USDC)',
        },
        network: {
          type: 'string',
          description: 'Network (default: tempo)',
        },
      },
      required: ['amount', 'merchant'],
    },
  },
];

export const mppToolHandlers: Record<string, ToolHandler> = {
  sardis_mpp_create_session: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateSessionSchema.safeParse(args);
    if (!parsed.success) return errorResult(`Invalid request: ${parsed.error.message}`);

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const sessionId = `mpp_sess_sim_${Date.now().toString(36)}`;
      return serialize({
        session_id: sessionId,
        mandate_id: parsed.data.mandate_id || null,
        wallet_id: parsed.data.wallet_id || config.walletId || null,
        agent_id: parsed.data.agent_id || config.agentId || null,
        method: parsed.data.method,
        chain: parsed.data.chain,
        currency: parsed.data.currency,
        spending_limit: parsed.data.spending_limit.toFixed(2),
        remaining: parsed.data.spending_limit.toFixed(2),
        total_spent: '0.00',
        payment_count: 0,
        status: 'active',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + (parsed.data.expires_in_seconds ?? 3600) * 1000).toISOString(),
      });
    }

    try {
      const result = await apiRequest('POST', '/api/v2/mpp/sessions', {
        spending_limit: parsed.data.spending_limit,
        method: parsed.data.method,
        chain: parsed.data.chain,
        currency: parsed.data.currency,
        mandate_id: parsed.data.mandate_id,
        wallet_id: parsed.data.wallet_id || config.walletId,
        agent_id: parsed.data.agent_id || config.agentId,
        expires_in_seconds: parsed.data.expires_in_seconds,
      });
      return serialize(result);
    } catch (error) {
      return errorResult(`Failed to create MPP session: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  sardis_mpp_execute: async (args: unknown): Promise<ToolResult> => {
    const parsed = ExecutePaymentSchema.safeParse(args);
    if (!parsed.success) return errorResult(`Invalid request: ${parsed.error.message}`);

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const paymentId = `mpp_pay_sim_${Date.now().toString(36)}`;
      const remaining = Math.max(0, 100 - parsed.data.amount); // simulated
      return serialize({
        payment_id: paymentId,
        session_id: parsed.data.session_id,
        amount: parsed.data.amount.toFixed(2),
        merchant: parsed.data.merchant,
        status: 'completed',
        tx_hash: '0x' + Math.random().toString(16).substring(2).padEnd(64, '0'),
        chain: 'tempo',
        remaining: remaining.toFixed(2),
      });
    }

    try {
      const result = await apiRequest('POST', `/api/v2/mpp/sessions/${parsed.data.session_id}/execute`, {
        amount: parsed.data.amount,
        merchant: parsed.data.merchant,
        merchant_url: parsed.data.merchant_url,
        memo: parsed.data.memo,
      });
      return serialize(result);
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Unknown error';
      if (msg.includes('exceeds') || msg.includes('budget') || msg.includes('limit')) {
        return serialize({
          success: false,
          status: 'BLOCKED',
          error: 'SESSION_BUDGET_EXCEEDED',
          message: msg,
          prevention: 'Financial Hallucination PREVENTED',
        });
      }
      return errorResult(`Failed to execute MPP payment: ${msg}`);
    }
  },

  sardis_mpp_close_session: async (args: unknown): Promise<ToolResult> => {
    const parsed = SessionIdSchema.safeParse(args);
    if (!parsed.success) return errorResult(`Invalid request: ${parsed.error.message}`);

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return serialize({
        session_id: parsed.data.session_id,
        status: 'closed',
        total_spent: '50.00',
        remaining: '50.00',
        payment_count: 2,
        closed_at: new Date().toISOString(),
      });
    }

    try {
      const result = await apiRequest('POST', `/api/v2/mpp/sessions/${parsed.data.session_id}/close`);
      return serialize(result);
    } catch (error) {
      return errorResult(`Failed to close MPP session: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  sardis_mpp_get_session: async (args: unknown): Promise<ToolResult> => {
    const parsed = SessionIdSchema.safeParse(args);
    if (!parsed.success) return errorResult(`Invalid request: ${parsed.error.message}`);

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return serialize({
        session_id: parsed.data.session_id,
        status: 'active',
        method: 'tempo',
        chain: 'tempo',
        currency: 'USDC',
        spending_limit: '100.00',
        remaining: '75.00',
        total_spent: '25.00',
        payment_count: 1,
        created_at: new Date(Date.now() - 600000).toISOString(),
        expires_at: new Date(Date.now() + 3000000).toISOString(),
      });
    }

    try {
      const result = await apiRequest('GET', `/api/v2/mpp/sessions/${parsed.data.session_id}`);
      return serialize(result);
    } catch (error) {
      return errorResult(`Failed to get MPP session: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  sardis_mpp_issue_card: async (args: unknown): Promise<ToolResult> => {
    const parsed = IssueCardSchema.safeParse(args);
    if (!parsed.success) return errorResult(`Invalid request: ${parsed.error.message}`);

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const cardId = `card_sim_${Date.now().toString(36)}`;
      return serialize({
        card_id: cardId,
        card_number: '4111XXXXXXXX' + Math.floor(1000 + Math.random() * 9000),
        cvv: '***',
        expiry: '12/27',
        amount: parsed.data.amount.toFixed(2),
        currency: parsed.data.currency,
        status: 'issued',
        card_type: 'single_use',
        provider: 'laso_finance',
        message: `Virtual Visa card issued for $${parsed.data.amount.toFixed(2)} via Laso Finance MPP`,
      });
    }

    try {
      const result = await apiRequest('POST', '/api/v2/mpp/cards/issue', {
        amount: parsed.data.amount,
        currency: parsed.data.currency,
        session_id: parsed.data.session_id,
      });
      return serialize(result);
    } catch (error) {
      return errorResult(`Failed to issue card: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  sardis_mpp_evaluate_policy: async (args: unknown): Promise<ToolResult> => {
    const parsed = EvaluatePolicySchema.safeParse(args);
    if (!parsed.success) return errorResult(`Invalid request: ${parsed.error.message}`);

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return serialize({
        allowed: true,
        reason: 'ALLOWED by default policy (simulated)',
        checks_passed: 12,
        checks_total: 12,
      });
    }

    try {
      const result = await apiRequest('POST', '/api/v2/mpp/evaluate', {
        amount: parsed.data.amount,
        merchant: parsed.data.merchant,
        payment_type: parsed.data.payment_type,
        currency: parsed.data.currency,
        network: parsed.data.network,
      });
      return serialize(result);
    } catch (error) {
      return errorResult(`Failed to evaluate policy: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },
};
