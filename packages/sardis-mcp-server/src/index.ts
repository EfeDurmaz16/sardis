/**
 * Sardis MCP Server
 *
 * Model Context Protocol server that exposes Sardis payment capabilities
 * to AI agents running in Claude Desktop, Cursor, and other MCP-compatible clients.
 *
 * Features:
 * - sardis_pay: Execute secure payments with policy validation
 * - sardis_check_policy: Validate a payment against policies before execution
 * - sardis_get_balance: Check wallet balance
 * - sardis_list_transactions: List recent transactions
 *
 * Environment Variables:
 * - SARDIS_API_KEY: API key for Sardis API (required)
 * - SARDIS_API_URL: API base URL (default: https://api.sardis.network)
 * - SARDIS_WALLET_ID: Default wallet ID
 * - SARDIS_AGENT_ID: Agent ID for attribution
 * - SARDIS_CHAIN: Default chain (default: base_sepolia)
 * - SARDIS_MODE: 'live' or 'simulated' (default: simulated)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';

// Configuration from environment
const config = {
  apiKey: process.env.SARDIS_API_KEY || '',
  apiUrl: (process.env.SARDIS_API_URL || 'https://api.sardis.network').replace(/\/$/, ''),
  walletId: process.env.SARDIS_WALLET_ID || '',
  agentId: process.env.SARDIS_AGENT_ID || '',
  chain: process.env.SARDIS_CHAIN || 'base_sepolia',
  mode: process.env.SARDIS_MODE || 'simulated',
};

// Payment request schema
const PaymentRequestSchema = z.object({
  vendor: z.string().describe('The merchant or service to pay (e.g., "OpenAI", "AWS")'),
  amount: z.number().positive().describe('Payment amount in USD'),
  purpose: z.string().optional().describe('Reason for the payment, used for policy validation'),
  category: z.string().optional().describe('Merchant category (e.g., "SaaS", "DevTools", "Retail")'),
  vendorAddress: z.string().optional().describe('Wallet address of the vendor (0x...)'),
  token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().describe('Token to use for payment'),
});

// Policy check schema
const PolicyCheckSchema = z.object({
  vendor: z.string().describe('The merchant to check'),
  amount: z.number().positive().describe('Payment amount to validate'),
});

// Balance check schema
const BalanceCheckSchema = z.object({
  token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().describe('Token to check balance for'),
  chain: z.string().optional().describe('Chain to check balance on'),
});

interface PolicyResult {
  allowed: boolean;
  reason?: string;
  risk_score?: number;
  checks?: { name: string; passed: boolean; reason?: string }[];
}

interface WalletInfo {
  id: string;
  limit_per_tx: string;
  limit_total: string;
  is_active: boolean;
  currency: string;
}

interface WalletBalance {
  wallet_id: string;
  balance: string;
  token: string;
  chain: string;
  address: string;
}

interface PaymentResult {
  payment_id: string;
  status: string;
  tx_hash?: string;
  chain: string;
  ledger_tx_id?: string;
  audit_anchor?: string;
}

/**
 * Make API request to Sardis
 */
async function apiRequest<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const url = `${config.apiUrl}${path.startsWith('/') ? path : '/' + path}`;

  const response = await fetch(url, {
    method,
    headers: {
      'X-API-Key': config.apiKey,
      'Content-Type': 'application/json',
      'User-Agent': 'sardis-mcp-server/0.1.0',
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Generate unique mandate ID
 */
function generateMandateId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 10);
  return `mnd_${timestamp}${random}`;
}

/**
 * Create SHA-256 hash for audit
 */
async function createAuditHash(data: string): Promise<string> {
  if (typeof crypto !== 'undefined' && crypto.subtle) {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(data);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
  }
  // Fallback
  return `hash_${Date.now().toString(16)}`;
}

/**
 * Get wallet info from API
 */
async function getWalletInfo(): Promise<WalletInfo> {
  if (!config.apiKey || !config.walletId) {
    // Return simulated data if not configured
    return {
      id: config.walletId || 'wallet_simulated',
      limit_per_tx: '100.00',
      limit_total: '500.00',
      is_active: true,
      currency: 'USDC',
    };
  }

  return apiRequest<WalletInfo>('GET', `/wallets/${config.walletId}`);
}

/**
 * Get wallet balance from API
 */
async function getWalletBalance(
  token: string = 'USDC',
  chain: string = config.chain
): Promise<WalletBalance> {
  if (!config.apiKey || !config.walletId) {
    // Return simulated data if not configured
    return {
      wallet_id: config.walletId || 'wallet_simulated',
      balance: '1000.00',
      token,
      chain,
      address: '0x' + '0'.repeat(40),
    };
  }

  return apiRequest<WalletBalance>(
    'GET',
    `/wallets/${config.walletId}/balance?chain=${chain}&token=${token}`
  );
}

/**
 * Execute payment mandate via API
 */
async function executePayment(
  vendor: string,
  amount: number,
  purpose: string,
  vendorAddress?: string,
  token: string = 'USDC'
): Promise<PaymentResult> {
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
 * Check policy via API or local validation
 */
async function checkPolicy(
  vendor: string,
  amount: number,
  category?: string
): Promise<PolicyResult> {
  const checks: { name: string; passed: boolean; reason?: string }[] = [];
  let allPassed = true;

  try {
    // Get wallet limits
    const wallet = await getWalletInfo();
    const limitPerTx = parseFloat(wallet.limit_per_tx);

    // Per-transaction limit check
    if (amount <= limitPerTx) {
      checks.push({ name: 'per_transaction_limit', passed: true });
    } else {
      checks.push({
        name: 'per_transaction_limit',
        passed: false,
        reason: `Amount $${amount} exceeds limit of $${limitPerTx}`,
      });
      allPassed = false;
    }

    // Wallet active check
    if (wallet.is_active) {
      checks.push({ name: 'wallet_active', passed: true });
    } else {
      checks.push({
        name: 'wallet_active',
        passed: false,
        reason: 'Wallet is not active',
      });
      allPassed = false;
    }

    // Vendor allowlist check (local validation)
    const normalizedVendor = vendor.toLowerCase().trim();
    const blockedMerchants = ['amazon', 'ebay', 'aliexpress', 'wish'];
    const saasVendors = [
      'openai', 'anthropic', 'aws', 'gcp', 'azure', 'vercel',
      'supabase', 'stripe', 'github', 'netlify', 'cloudflare',
    ];

    const isBlocked = blockedMerchants.some((b) => normalizedVendor.includes(b));
    const isSaas = saasVendors.some((v) => normalizedVendor.includes(v));

    if (isBlocked) {
      checks.push({
        name: 'vendor_allowlist',
        passed: false,
        reason: `Vendor "${vendor}" is not in approved list`,
      });
      allPassed = false;
    } else if (isSaas) {
      checks.push({ name: 'vendor_allowlist', passed: true });
    } else {
      checks.push({
        name: 'vendor_allowlist',
        passed: false,
        reason: `Vendor "${vendor}" requires explicit approval`,
      });
      allPassed = false;
    }

    return {
      allowed: allPassed,
      reason: allPassed
        ? 'Payment allowed by policy'
        : checks
            .filter((c) => !c.passed)
            .map((c) => c.reason)
            .join('; '),
      risk_score: allPassed ? 0.1 : 0.8,
      checks,
    };
  } catch (error) {
    // Fallback to local validation
    return {
      allowed: false,
      reason: `Policy check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      risk_score: 1.0,
    };
  }
}

export async function createServer() {
  const server = new Server(
    {
      name: 'sardis-mcp-server',
      version: '0.1.0',
    },
    {
      capabilities: {
        tools: {},
        resources: {},
      },
    }
  );

  // List available tools
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
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
          name: 'sardis_check_policy',
          description:
            'Check if a payment would be allowed by the current spending policy without executing it. Use this to validate payments before execution.',
          inputSchema: {
            type: 'object',
            properties: {
              vendor: {
                type: 'string',
                description: 'The merchant to check',
              },
              amount: {
                type: 'number',
                description: 'Payment amount to validate',
              },
            },
            required: ['vendor', 'amount'],
          },
        },
        {
          name: 'sardis_get_balance',
          description: 'Get the current wallet balance. Use before making payments to ensure sufficient funds.',
          inputSchema: {
            type: 'object',
            properties: {
              token: {
                type: 'string',
                enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
                description: 'Token to check balance for. Defaults to USDC.',
              },
              chain: {
                type: 'string',
                description: 'Chain to check balance on (e.g., "base_sepolia", "polygon").',
              },
            },
            required: [],
          },
        },
        {
          name: 'sardis_get_wallet',
          description: 'Get wallet information including spending limits and policy settings.',
          inputSchema: {
            type: 'object',
            properties: {},
            required: [],
          },
        },
      ],
    };
  });

  // List resources (wallet info, transaction history)
  server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return {
      resources: [
        {
          uri: 'sardis://wallet/balance',
          name: 'Wallet Balance',
          description: 'Current wallet balance and limits',
          mimeType: 'application/json',
        },
        {
          uri: 'sardis://wallet/info',
          name: 'Wallet Info',
          description: 'Wallet configuration and spending limits',
          mimeType: 'application/json',
        },
        {
          uri: 'sardis://config',
          name: 'Server Configuration',
          description: 'Current MCP server configuration status',
          mimeType: 'application/json',
        },
      ],
    };
  });

  // Read resources
  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const { uri } = request.params;

    if (uri === 'sardis://wallet/balance') {
      try {
        const balance = await getWalletBalance();
        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(balance, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify({
                error: error instanceof Error ? error.message : 'Failed to get balance',
              }),
            },
          ],
        };
      }
    }

    if (uri === 'sardis://wallet/info') {
      try {
        const wallet = await getWalletInfo();
        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(wallet, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify({
                error: error instanceof Error ? error.message : 'Failed to get wallet info',
              }),
            },
          ],
        };
      }
    }

    if (uri === 'sardis://config') {
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(
              {
                api_url: config.apiUrl,
                wallet_id: config.walletId || '(not configured)',
                agent_id: config.agentId || '(not configured)',
                chain: config.chain,
                mode: config.mode,
                api_key_configured: !!config.apiKey,
              },
              null,
              2
            ),
          },
        ],
      };
    }

    throw new Error(`Unknown resource: ${uri}`);
  });

  // Handle tool calls
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    if (name === 'sardis_pay') {
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
          isError: false, // Not a system error, policy worked correctly
        };
      }

      // Execute payment via API
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

        // Check if error is a policy violation from API
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
    }

    if (name === 'sardis_check_policy') {
      const parsed = PolicyCheckSchema.safeParse(args);
      if (!parsed.success) {
        return {
          content: [
            {
              type: 'text',
              text: `Invalid request: ${parsed.error.message}`,
            },
          ],
          isError: true,
        };
      }

      const { vendor, amount } = parsed.data;
      const result = await checkPolicy(vendor, amount);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                vendor,
                amount,
                would_be_allowed: result.allowed,
                reason: result.reason,
                risk_score: result.risk_score,
                checks: result.checks,
              },
              null,
              2
            ),
          },
        ],
      };
    }

    if (name === 'sardis_get_balance') {
      const parsed = BalanceCheckSchema.safeParse(args);
      const token = parsed.success ? parsed.data.token || 'USDC' : 'USDC';
      const chain = parsed.success ? parsed.data.chain || config.chain : config.chain;

      try {
        const balance = await getWalletBalance(token, chain);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(balance, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Failed to get balance: ${error instanceof Error ? error.message : 'Unknown error'}`,
            },
          ],
          isError: true,
        };
      }
    }

    if (name === 'sardis_get_wallet') {
      try {
        const wallet = await getWalletInfo();
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(wallet, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Failed to get wallet info: ${error instanceof Error ? error.message : 'Unknown error'}`,
            },
          ],
          isError: true,
        };
      }
    }

    throw new Error(`Unknown tool: ${name}`);
  });

  return server;
}

export async function runServer() {
  const server = await createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Log configuration status
  console.error('Sardis MCP Server running on stdio');
  console.error(`Mode: ${config.mode}`);
  console.error(`API URL: ${config.apiUrl}`);
  console.error(`API Key configured: ${config.apiKey ? 'yes' : 'no'}`);
  console.error(`Wallet ID: ${config.walletId || '(not set)'}`);
}
