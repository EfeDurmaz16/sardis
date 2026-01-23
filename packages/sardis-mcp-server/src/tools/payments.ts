/**
 * Sardis MCP Server - Payment Tools
 *
 * Tools for executing payments and checking transaction status.
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { PaymentRequestSchema, TransactionQuerySchema } from './types.js';
import { apiRequest, generateMandateId, createAuditHash } from '../api.js';
import { getConfig } from '../config.js';
import { checkPolicy } from './policy.js';

// Response types
interface PaymentResult {
  payment_id: string;
  status: string;
  tx_hash?: string;
  chain: string;
  ledger_tx_id?: string;
  audit_anchor?: string;
}

interface Transaction {
  id: string;
  payment_id: string;
  status: string;
  amount: string;
  token: string;
  chain: string;
  vendor: string;
  tx_hash?: string;
  created_at: string;
}

/**
 * Execute payment mandate via API
 */
export async function executePayment(
  vendor: string,
  amount: number,
  purpose: string,
  vendorAddress?: string,
  token: string = 'USDC'
): Promise<PaymentResult> {
  const config = getConfig();
  const mandateId = generateMandateId();
  const timestamp = new Date().toISOString();
  const amountMinor = Math.round(amount * 1_000_000).toString();

  const auditData = JSON.stringify({
    mandate_id: mandateId,
    subject: config.walletId,
    destination: vendorAddress || `pending:${vendor}`,
    amount_minor: amountMinor,
    token,
    purpose,
    timestamp,
  });
  const auditHash = await createAuditHash(auditData);

  const mandate = {
    mandate_id: mandateId,
    subject: config.walletId,
    destination: vendorAddress || `pending:${vendor}`,
    amount_minor: amountMinor,
    token,
    chain: config.chain,
    purpose,
    vendor_name: vendor,
    agent_id: config.agentId,
    timestamp,
    audit_hash: auditHash,
    metadata: {
      vendor,
      category: 'saas',
      initiated_by: 'ai_agent',
      tool: 'mcp_server',
    },
  };

  if (!config.apiKey || config.mode === 'simulated') {
    // Return simulated result
    return {
      payment_id: `pay_${Date.now().toString(36)}`,
      status: 'completed',
      tx_hash: '0x' + Math.random().toString(16).substring(2).padEnd(64, '0'),
      chain: config.chain,
      ledger_tx_id: `ltx_${Date.now().toString(36)}`,
      audit_anchor: `merkle::${auditHash.substring(0, 16)}`,
    };
  }

  return apiRequest<PaymentResult>('POST', '/api/v2/mandates/execute', { mandate });
}

/**
 * Get transaction by ID
 */
export async function getTransaction(transactionId: string): Promise<Transaction> {
  const config = getConfig();

  if (!config.apiKey || config.mode === 'simulated') {
    return {
      id: transactionId,
      payment_id: `pay_${Date.now().toString(36)}`,
      status: 'completed',
      amount: '100.00',
      token: 'USDC',
      chain: config.chain,
      vendor: 'simulated_vendor',
      tx_hash: '0x' + '0'.repeat(64),
      created_at: new Date().toISOString(),
    };
  }

  return apiRequest<Transaction>('GET', `/api/v2/transactions/${transactionId}`);
}

/**
 * List transactions with optional filters
 */
export async function listTransactions(
  limit: number = 20,
  offset: number = 0,
  status?: string
): Promise<Transaction[]> {
  const config = getConfig();

  if (!config.apiKey || config.mode === 'simulated') {
    return [
      {
        id: `tx_${Date.now().toString(36)}`,
        payment_id: `pay_${Date.now().toString(36)}`,
        status: 'completed',
        amount: '50.00',
        token: 'USDC',
        chain: config.chain,
        vendor: 'OpenAI',
        tx_hash: '0x' + '1'.repeat(64),
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: `tx_${(Date.now() - 1000).toString(36)}`,
        payment_id: `pay_${(Date.now() - 1000).toString(36)}`,
        status: 'completed',
        amount: '25.00',
        token: 'USDC',
        chain: config.chain,
        vendor: 'Anthropic',
        tx_hash: '0x' + '2'.repeat(64),
        created_at: new Date(Date.now() - 7200000).toISOString(),
      },
    ];
  }

  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (status) {
    params.append('status', status);
  }

  return apiRequest<Transaction[]>('GET', `/api/v2/transactions?${params}`);
}

// Tool definitions
export const paymentToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_pay',
    description:
      'Execute a secure payment using Sardis MPC wallet. Validates against spending policies before processing. Returns transaction details on success or policy violation message if blocked.',
    inputSchema: {
      type: 'object',
      properties: {
        vendor: {
          type: 'string',
          description: 'The merchant or service to pay (e.g., "OpenAI", "AWS")',
        },
        amount: {
          type: 'number',
          description: 'Payment amount in USD',
        },
        purpose: {
          type: 'string',
          description: 'Reason for the payment, used for policy validation and audit trail',
        },
        vendorAddress: {
          type: 'string',
          description: 'Wallet address of the vendor (0x...). Optional.',
        },
        token: {
          type: 'string',
          enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
          description: 'Token to use for payment. Defaults to USDC.',
        },
      },
      required: ['vendor', 'amount'],
    },
  },
  {
    name: 'sardis_get_transaction',
    description: 'Get details of a specific transaction by ID.',
    inputSchema: {
      type: 'object',
      properties: {
        transaction_id: {
          type: 'string',
          description: 'The transaction ID to retrieve',
        },
      },
      required: ['transaction_id'],
    },
  },
  {
    name: 'sardis_list_transactions',
    description: 'List recent transactions with optional filtering.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: {
          type: 'number',
          description: 'Maximum number of transactions to return (default: 20)',
        },
        offset: {
          type: 'number',
          description: 'Number of transactions to skip for pagination',
        },
        status: {
          type: 'string',
          enum: ['pending', 'completed', 'failed'],
          description: 'Filter by transaction status',
        },
      },
      required: [],
    },
  },
];

// Tool handlers
export const paymentToolHandlers: Record<string, ToolHandler> = {
  sardis_pay: async (args: unknown): Promise<ToolResult> => {
    const parsed = PaymentRequestSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [
          {
            type: 'text',
            text: `Invalid payment request: ${parsed.error.message}`,
          },
        ],
        isError: true,
      };
    }

    const { vendor, amount, purpose, vendorAddress, token } = parsed.data;

    // Check policy first
    const policyResult = await checkPolicy(vendor, amount);

    if (!policyResult.allowed) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: false,
                status: 'BLOCKED',
                error: 'POLICY_VIOLATION',
                message: policyResult.reason,
                risk_score: policyResult.risk_score,
                checks: policyResult.checks,
                prevention: 'Financial Hallucination PREVENTED',
              },
              null,
              2
            ),
          },
        ],
        isError: false,
      };
    }

    try {
      const result = await executePayment(
        vendor,
        amount,
        purpose || 'Service payment',
        vendorAddress,
        token || 'USDC'
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                status: 'APPROVED',
                payment_id: result.payment_id,
                vendor,
                amount,
                token: token || 'USDC',
                purpose: purpose || 'Service payment',
                transaction_hash: result.tx_hash,
                chain: result.chain,
                ledger_tx_id: result.ledger_tx_id,
                audit_anchor: result.audit_anchor,
                message: `Payment of $${amount} ${token || 'USDC'} to ${vendor} completed.`,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Payment failed';

      if (
        errorMessage.toLowerCase().includes('policy') ||
        errorMessage.toLowerCase().includes('blocked') ||
        errorMessage.toLowerCase().includes('limit')
      ) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(
                {
                  success: false,
                  status: 'BLOCKED',
                  error: 'POLICY_VIOLATION',
                  message: errorMessage,
                  prevention: 'Financial Hallucination PREVENTED',
                },
                null,
                2
              ),
            },
          ],
          isError: false,
        };
      }

      return {
        content: [
          {
            type: 'text',
            text: `Payment execution failed: ${errorMessage}`,
          },
        ],
        isError: true,
      };
    }
  },

  sardis_get_transaction: async (args: unknown): Promise<ToolResult> => {
    const parsed = z.object({ transaction_id: z.string() }).safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    try {
      const transaction = await getTransaction(parsed.data.transaction_id);
      return {
        content: [{ type: 'text', text: JSON.stringify(transaction, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to get transaction: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
        ],
        isError: true,
      };
    }
  },

  sardis_list_transactions: async (args: unknown): Promise<ToolResult> => {
    const parsed = TransactionQuerySchema.safeParse(args);
    const { limit, offset, status } = parsed.success
      ? parsed.data
      : { limit: 20, offset: 0, status: undefined };

    try {
      const transactions = await listTransactions(limit, offset, status);
      return {
        content: [{ type: 'text', text: JSON.stringify(transactions, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to list transactions: ${error instanceof Error ? error.message : 'Unknown error'}`,
          },
        ],
        isError: true,
      };
    }
  },
};
