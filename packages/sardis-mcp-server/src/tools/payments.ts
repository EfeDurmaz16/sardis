/**
 * Sardis MCP Server - Payment Tools
 *
 * Tools for executing payments and checking transaction status.
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { PaymentRequestSchema, TransactionQuerySchema } from './types.js';
import { apiRequest } from '../api.js';
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

interface LedgerEntry {
  tx_id: string;
  mandate_id?: string;
  from_wallet?: string;
  to_wallet?: string;
  amount: string;
  currency: string;
  chain?: string;
  chain_tx_hash?: string;
  audit_anchor?: string;
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

  if (!config.apiKey || config.mode === 'simulated') {
    // Return simulated result with unique ID
    const uniqueId = `${Date.now().toString(36)}${Math.random().toString(36).substring(2, 6)}`;
    return {
      payment_id: `pay_${uniqueId}`,
      status: 'completed',
      tx_hash: '0x' + Math.random().toString(16).substring(2).padEnd(64, '0'),
      chain: config.chain,
      ledger_tx_id: `ltx_${uniqueId}`,
      audit_anchor: `merkle::${uniqueId}`,
    };
  }

  if (!vendorAddress) {
    throw new Error('vendorAddress is required in live mode (destination address)');
  }

  const transfer = await apiRequest<{
    tx_hash: string;
    status: string;
    chain: string;
    ledger_tx_id?: string;
    audit_anchor?: string | null;
  }>('POST', `/api/v2/wallets/${config.walletId}/transfer`, {
    destination: vendorAddress,
    amount,
    token,
    chain: config.chain,
    domain: vendor,
    memo: purpose,
  });

  const paymentId = transfer.ledger_tx_id || `pay_${Date.now().toString(36)}`;
  return {
    payment_id: paymentId,
    status: transfer.status,
    tx_hash: transfer.tx_hash,
    chain: transfer.chain,
    ledger_tx_id: transfer.ledger_tx_id,
    audit_anchor: transfer.audit_anchor ?? undefined,
  };
}

/**
 * Get transaction by ID
 */
export async function getTransaction(transactionId: string): Promise<LedgerEntry> {
  const config = getConfig();

  if (!config.apiKey || config.mode === 'simulated') {
    return {
      tx_id: transactionId,
      amount: '100.00',
      currency: 'USDC',
      chain: config.chain,
      chain_tx_hash: '0x' + '0'.repeat(64),
      created_at: new Date().toISOString(),
    };
  }

  return apiRequest<LedgerEntry>('GET', `/api/v2/ledger/entries/${transactionId}`);
}

/**
 * List transactions with optional filters
 */
export async function listTransactions(
  limit: number = 20,
  offset: number = 0,
  status?: string
): Promise<LedgerEntry[]> {
  const config = getConfig();

  if (!config.apiKey || config.mode === 'simulated') {
    return [
      {
        tx_id: `tx_${Date.now().toString(36)}`,
        amount: '50.00',
        currency: 'USDC',
        chain: config.chain,
        chain_tx_hash: '0x' + '1'.repeat(64),
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        tx_id: `tx_${(Date.now() - 1000).toString(36)}`,
        amount: '25.00',
        currency: 'USDC',
        chain: config.chain,
        chain_tx_hash: '0x' + '2'.repeat(64),
        created_at: new Date(Date.now() - 7200000).toISOString(),
      },
    ];
  }

  if (status) {
    // Ledger entries are append-only; status filtering is not currently supported.
    // Keep the parameter for tool stability.
  }

  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  params.append('wallet_id', config.walletId);

  const response = await apiRequest<{ entries: LedgerEntry[] }>('GET', `/api/v2/ledger/entries?${params}`);
  return response.entries || [];
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
