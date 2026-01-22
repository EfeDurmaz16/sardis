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

// Payment request schema
const PaymentRequestSchema = z.object({
  vendor: z.string().describe('The merchant or service to pay (e.g., "OpenAI", "AWS")'),
  amount: z.number().positive().describe('Payment amount in USD'),
  purpose: z.string().optional().describe('Reason for the payment, used for policy validation'),
  category: z.string().optional().describe('Merchant category (e.g., "SaaS", "DevTools", "Retail")'),
});

// Policy check schema
const PolicyCheckSchema = z.object({
  vendor: z.string().describe('The merchant to check'),
  amount: z.number().positive().describe('Payment amount to validate'),
});

// Mock policy engine (in production, this calls the Sardis API)
const ALLOWED_CATEGORIES = ['SaaS', 'DevTools', 'Cloud', 'API'];
const BLOCKED_MERCHANTS = ['amazon.com', 'ebay.com', 'aliexpress.com'];
const MAX_TRANSACTION_AMOUNT = 100;
const DAILY_LIMIT = 500;

interface PolicyResult {
  allowed: boolean;
  reason?: string;
  risk_score?: number;
}

function checkPolicy(vendor: string, amount: number, category?: string): PolicyResult {
  // Normalize vendor
  const normalizedVendor = vendor.toLowerCase().trim();

  // Check blocked merchants
  for (const blocked of BLOCKED_MERCHANTS) {
    if (normalizedVendor.includes(blocked.replace('.com', ''))) {
      return {
        allowed: false,
        reason: `Merchant "${vendor}" is not in the approved vendor list`,
        risk_score: 0.9,
      };
    }
  }

  // Check category
  if (category && !ALLOWED_CATEGORIES.includes(category)) {
    return {
      allowed: false,
      reason: `Category "${category}" is not allowed by current policy`,
      risk_score: 0.7,
    };
  }

  // Check amount limits
  if (amount > MAX_TRANSACTION_AMOUNT) {
    return {
      allowed: false,
      reason: `Amount $${amount} exceeds per-transaction limit of $${MAX_TRANSACTION_AMOUNT}`,
      risk_score: 0.6,
    };
  }

  // Default: allow SaaS/DevTools vendors
  const saasVendors = ['openai', 'anthropic', 'aws', 'gcp', 'azure', 'vercel', 'supabase', 'stripe', 'github'];
  const isSaas = saasVendors.some((v) => normalizedVendor.includes(v));

  if (isSaas) {
    return {
      allowed: true,
      risk_score: 0.1,
    };
  }

  // Unknown vendor - require explicit approval
  return {
    allowed: false,
    reason: `Vendor "${vendor}" requires explicit approval. Add it to your allowlist.`,
    risk_score: 0.5,
  };
}

// Mock card issuance (in production, this calls Lithic API)
function issueVirtualCard(): { number: string; cvv: string; expiry: string } {
  return {
    number: '4242 **** **** ' + Math.floor(1000 + Math.random() * 9000),
    cvv: String(Math.floor(100 + Math.random() * 900)),
    expiry: '12/26',
  };
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
            'Execute a secure payment using Sardis MPC wallet. Validates against spending policies before processing.',
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
                description: 'Reason for the payment, used for policy validation',
              },
              category: {
                type: 'string',
                description: 'Merchant category (e.g., "SaaS", "DevTools", "Retail")',
              },
            },
            required: ['vendor', 'amount'],
          },
        },
        {
          name: 'sardis_check_policy',
          description:
            'Check if a payment would be allowed by the current spending policy without executing it.',
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
          description: 'Get the current wallet balance and available spending limit.',
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
          uri: 'sardis://wallet/policy',
          name: 'Active Policy',
          description: 'Current spending policy configuration',
          mimeType: 'application/json',
        },
      ],
    };
  });

  // Read resources
  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const { uri } = request.params;

    if (uri === 'sardis://wallet/balance') {
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(
              {
                balance: 1000.0,
                currency: 'USD',
                daily_limit: DAILY_LIMIT,
                daily_spent: 45.0,
                available: DAILY_LIMIT - 45.0,
              },
              null,
              2
            ),
          },
        ],
      };
    }

    if (uri === 'sardis://wallet/policy') {
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(
              {
                name: 'Default SaaS Policy',
                allowed_categories: ALLOWED_CATEGORIES,
                blocked_merchants: BLOCKED_MERCHANTS,
                max_transaction: MAX_TRANSACTION_AMOUNT,
                daily_limit: DAILY_LIMIT,
                description: 'Allow SaaS and DevTools only. Max $100/tx, $500/day.',
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

      const { vendor, amount, purpose, category } = parsed.data;

      // Check policy
      const policyResult = checkPolicy(vendor, amount, category);

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

      // Payment approved - issue virtual card
      const card = issueVirtualCard();
      const transactionId = 'tx_' + Math.random().toString(36).substring(2, 15);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                status: 'APPROVED',
                transaction_id: transactionId,
                vendor,
                amount,
                purpose: purpose || 'General',
                card: {
                  number: card.number,
                  cvv: card.cvv,
                  expiry: card.expiry,
                },
                message: `Payment of $${amount} to ${vendor} approved and card issued.`,
              },
              null,
              2
            ),
          },
        ],
      };
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
      const result = checkPolicy(vendor, amount);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                vendor,
                amount,
                would_be_allowed: result.allowed,
                reason: result.reason || 'Payment would be allowed',
                risk_score: result.risk_score,
              },
              null,
              2
            ),
          },
        ],
      };
    }

    if (name === 'sardis_get_balance') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                balance: 1000.0,
                currency: 'USD',
                daily_limit: DAILY_LIMIT,
                daily_spent: 45.0,
                available: DAILY_LIMIT - 45.0,
                wallet_id: 'wallet_0x7f4d3a91',
              },
              null,
              2
            ),
          },
        ],
      };
    }

    throw new Error(`Unknown tool: ${name}`);
  });

  return server;
}

export async function runServer() {
  const server = await createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Sardis MCP Server running on stdio');
}
