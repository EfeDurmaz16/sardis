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
  execution_path?: 'legacy_tx' | 'erc4337_userop';
  user_op_hash?: string;
}

interface LedgerEntry {
  id?: string;
  payment_id?: string;
  status?: string;
  vendor?: string;
  token?: string;
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

interface DecisionEnvelope {
  decision_id: string;
  outcome: 'APPROVED' | 'BLOCKED' | 'ERROR';
  reason_code: string;
  reason: string;
  policy_ref?: string;
  context: {
    agent_id: string | null;
    wallet_id: string | null;
    chain: string;
    mode: 'live' | 'simulated';
    payment_identity_id: string | null;
  };
}

function buildDecisionEnvelope(input: {
  outcome: DecisionEnvelope['outcome'];
  reason_code: string;
  reason: string;
  chain: string;
  payment_id?: string;
}): DecisionEnvelope {
  const config = getConfig();
  const decisionId = input.payment_id
    ? `dec_${input.payment_id}`
    : `dec_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;

  return {
    decision_id: decisionId,
    outcome: input.outcome,
    reason_code: input.reason_code,
    reason: input.reason,
    context: {
      agent_id: config.agentId || null,
      wallet_id: config.walletId || null,
      chain: input.chain,
      mode: config.mode,
      payment_identity_id: process.env.SARDIS_PAYMENT_IDENTITY || null,
    },
  };
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
    // SECURITY: Log a warning when falling into simulated mode.
    // Without an explicit API key, ALL payments silently succeed without executing
    // on-chain. If this happens in production due to a missing env var, real
    // payments appear successful but no money actually moves.
    if (!config.apiKey) {
      console.error(
        '[SARDIS SECURITY WARNING] No API key configured — all payments are SIMULATED. '
        + 'Set SARDIS_API_KEY to enable real transactions. '
        + 'If this is intentional, set SARDIS_MODE=simulated explicitly.'
      );
    }
    // Return simulated result with unique ID
    const uniqueId = `${Date.now().toString(36)}${Math.random().toString(36).substring(2, 6)}`;
    return {
      payment_id: `pay_sim_${uniqueId}`,
      status: 'simulated',
      tx_hash: '0x' + Math.random().toString(16).substring(2).padEnd(64, '0'),
      chain: config.chain,
      ledger_tx_id: `ltx_sim_${uniqueId}`,
      audit_anchor: `merkle::sim::${uniqueId}`,
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
    execution_path?: 'legacy_tx' | 'erc4337_userop';
    user_op_hash?: string | null;
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
    execution_path: transfer.execution_path,
    user_op_hash: transfer.user_op_hash ?? undefined,
  };
}

/**
 * Get transaction by ID
 */
export async function getTransaction(transactionId: string): Promise<LedgerEntry> {
  const config = getConfig();

  if (!config.apiKey || config.mode === 'simulated') {
    return {
      id: transactionId,
      payment_id: transactionId,
      status: 'completed',
      vendor: 'simulated-vendor',
      token: 'USDC',
      tx_id: transactionId,
      amount: '100.00',
      currency: 'USDC',
      chain: config.chain,
      chain_tx_hash: '0x' + '0'.repeat(64),
      created_at: new Date().toISOString(),
    };
  }

  const entry = await apiRequest<LedgerEntry>('GET', `/api/v2/ledger/entries/${transactionId}`);
  return {
    ...entry,
    id: entry.id ?? entry.tx_id,
    payment_id: entry.payment_id ?? entry.tx_id,
    token: entry.token ?? entry.currency,
    status: entry.status ?? 'completed',
    vendor: entry.vendor ?? 'unknown',
  };
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
        id: `tx_${Date.now().toString(36)}`,
        payment_id: `tx_${Date.now().toString(36)}`,
        status: 'completed',
        vendor: 'simulated-vendor-a',
        token: 'USDC',
        tx_id: `tx_${Date.now().toString(36)}`,
        amount: '50.00',
        currency: 'USDC',
        chain: config.chain,
        chain_tx_hash: '0x' + '1'.repeat(64),
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: `tx_${(Date.now() - 1000).toString(36)}`,
        payment_id: `tx_${(Date.now() - 1000).toString(36)}`,
        status: 'completed',
        vendor: 'simulated-vendor-b',
        token: 'USDC',
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
  return (response.entries || []).map((entry) => ({
    ...entry,
    id: entry.id ?? entry.tx_id,
    payment_id: entry.payment_id ?? entry.tx_id,
    token: entry.token ?? entry.currency,
    status: entry.status ?? 'completed',
    vendor: entry.vendor ?? 'unknown',
  }));
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

    // Check policy first (fail-closed)
    let policyResult;
    try {
      policyResult = await checkPolicy(vendor, amount);
    } catch (error) {
      const config = getConfig();
      const reason = error instanceof Error ? error.message : 'Policy check failed';
      const decision = buildDecisionEnvelope({
        outcome: 'BLOCKED',
        reason_code: 'SARDIS.POLICY.CHECK_FAILED',
        reason,
        chain: config.chain,
      });
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: false,
                status: 'BLOCKED',
                error: 'POLICY_CHECK_FAILED',
                message: reason,
                reason_code: decision.reason_code,
                decision,
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

    if (!policyResult.allowed) {
      const config = getConfig();
      const reason = policyResult.reason || 'Blocked by policy';
      const decision = buildDecisionEnvelope({
        outcome: 'BLOCKED',
        reason_code: 'SARDIS.POLICY.VIOLATION',
        reason,
        chain: config.chain,
      });
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: false,
                status: 'BLOCKED',
                error: 'POLICY_VIOLATION',
                message: reason,
                reason_code: decision.reason_code,
                risk_score: policyResult.risk_score,
                checks: policyResult.checks,
                decision,
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
      const decision = buildDecisionEnvelope({
        outcome: 'APPROVED',
        reason_code: 'SARDIS.PAYMENT.APPROVED',
        reason: 'Payment approved and submitted',
        chain: result.chain,
        payment_id: result.payment_id,
      });

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
                reason_code: decision.reason_code,
                decision,
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
        const config = getConfig();
        const decision = buildDecisionEnvelope({
          outcome: 'BLOCKED',
          reason_code: 'SARDIS.POLICY.VIOLATION',
          reason: errorMessage,
          chain: config.chain,
        });
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
                  reason_code: decision.reason_code,
                  decision,
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

      const config = getConfig();
      const decision = buildDecisionEnvelope({
        outcome: 'ERROR',
        reason_code: 'SARDIS.PAYMENT.EXECUTION_FAILED',
        reason: errorMessage,
        chain: config.chain,
      });
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: false,
                status: 'ERROR',
                error: 'PAYMENT_EXECUTION_FAILED',
                message: errorMessage,
                reason_code: decision.reason_code,
                decision,
              },
              null,
              2
            ),
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
