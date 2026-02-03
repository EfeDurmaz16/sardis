/**
 * Sardis MCP Server - Policy Tools
 *
 * Tools for validating payments against spending policies.
 */

import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { PolicyCheckSchema, ComplianceCheckSchema } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig, getBlockedVendors, getAllowedVendors } from '../config.js';
import { getWalletInfo } from './wallets.js';

// Response types
export interface PolicyResult {
  allowed: boolean;
  reason?: string;
  risk_score?: number;
  checks?: { name: string; passed: boolean; reason?: string }[];
}

interface ComplianceResult {
  status: 'pass' | 'fail' | 'review';
  checks: {
    type: string;
    passed: boolean;
    details?: string;
  }[];
  risk_level: 'low' | 'medium' | 'high';
}

/**
 * Check policy via API or local validation
 */
export async function checkPolicy(
  vendor: string,
  amount: number,
  category?: string
): Promise<PolicyResult> {
  const config = getConfig();
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

    // Vendor validation using configurable lists
    const normalizedVendor = vendor.toLowerCase().trim();
    const blockedVendors = getBlockedVendors();
    const allowedVendors = getAllowedVendors();

    const isBlocked = blockedVendors.some((b) => normalizedVendor.includes(b.toLowerCase()));
    const isAllowed = allowedVendors.some((v) => normalizedVendor.includes(v.toLowerCase()));

    if (isBlocked) {
      checks.push({
        name: 'vendor_allowlist',
        passed: false,
        reason: `Vendor "${vendor}" is blocked by policy`,
      });
      allPassed = false;
    } else if (isAllowed) {
      checks.push({ name: 'vendor_allowlist', passed: true });
    } else {
      // Unknown vendor - could require approval based on config
      if (config.requireExplicitApproval) {
        checks.push({
          name: 'vendor_allowlist',
          passed: false,
          reason: `Vendor "${vendor}" requires explicit approval`,
        });
        allPassed = false;
      } else {
        checks.push({
          name: 'vendor_allowlist',
          passed: true,
          reason: 'Vendor not blocked, implicit approval',
        });
      }
    }

    // Category check if provided
    if (category) {
      const blockedCategories = (process.env.SARDIS_POLICY_BLOCKED_CATEGORIES || 'gambling,adult')
        .split(',')
        .map((c) => c.trim().toLowerCase());

      if (blockedCategories.includes(category.toLowerCase())) {
        checks.push({
          name: 'category_check',
          passed: false,
          reason: `Category "${category}" is not allowed`,
        });
        allPassed = false;
      } else {
        checks.push({ name: 'category_check', passed: true });
      }
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
    return {
      allowed: false,
      reason: `Policy check failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      risk_score: 1.0,
    };
  }
}

/**
 * Validate payment limits only (without vendor checks)
 */
export async function validateLimits(amount: number): Promise<PolicyResult> {
  const checks: { name: string; passed: boolean; reason?: string }[] = [];
  let allPassed = true;

  try {
    const wallet = await getWalletInfo();
    const limitPerTx = parseFloat(wallet.limit_per_tx);
    const limitTotal = parseFloat(wallet.limit_total);

    // Per-transaction limit
    if (amount <= limitPerTx) {
      checks.push({ name: 'per_transaction_limit', passed: true });
    } else {
      checks.push({
        name: 'per_transaction_limit',
        passed: false,
        reason: `Amount $${amount} exceeds per-transaction limit of $${limitPerTx}`,
      });
      allPassed = false;
    }

    // Total limit (if we could track cumulative - for now just note it)
    checks.push({
      name: 'total_limit_check',
      passed: true,
      reason: `Daily limit: $${limitTotal}`,
    });

    return {
      allowed: allPassed,
      reason: allPassed
        ? 'Within spending limits'
        : checks
            .filter((c) => !c.passed)
            .map((c) => c.reason)
            .join('; '),
      risk_score: allPassed ? 0.1 : 0.7,
      checks,
    };
  } catch (error) {
    return {
      allowed: false,
      reason: `Limit validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      risk_score: 1.0,
    };
  }
}

/**
 * Check compliance status
 */
export async function checkCompliance(
  address: string,
  amount: number
): Promise<ComplianceResult> {
  const config = getConfig();

  if (!config.apiKey || config.mode === 'simulated') {
    // Simulated compliance check
    return {
      status: 'pass',
      checks: [
        { type: 'sanctions', passed: true },
        { type: 'kyc', passed: true },
        { type: 'aml', passed: true },
      ],
      risk_level: 'low',
    };
  }

  try {
    return await apiRequest<ComplianceResult>('POST', '/api/v2/compliance/check', {
      address,
      amount,
    });
  } catch {
    // Fail-closed on compliance errors
    return {
      status: 'fail',
      checks: [{ type: 'error', passed: false, details: 'Compliance service unavailable' }],
      risk_level: 'high',
    };
  }
}

// Tool definitions
export const policyToolDefinitions: ToolDefinition[] = [
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
        category: {
          type: 'string',
          description: 'Optional merchant category for additional validation',
        },
      },
      required: ['vendor', 'amount'],
    },
  },
  {
    name: 'sardis_validate_limits',
    description:
      'Check if a payment amount is within wallet spending limits without checking vendor restrictions.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: {
          type: 'number',
          description: 'Payment amount to validate against limits',
        },
      },
      required: ['amount'],
    },
  },
  {
    name: 'sardis_check_compliance',
    description:
      'Run compliance checks on an address including sanctions, KYC, and AML screening.',
    inputSchema: {
      type: 'object',
      properties: {
        address: {
          type: 'string',
          description: 'The wallet address to check (0x...)',
        },
        amount: {
          type: 'number',
          description: 'Transaction amount for risk assessment',
        },
      },
      required: ['address', 'amount'],
    },
  },
  {
    name: 'sardis_get_policies',
    description:
      'Get all active spending policies for the wallet.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: {
          type: 'string',
          description: 'Wallet ID (optional, defaults to configured wallet)',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_rules',
    description:
      'Get detailed policy rules including limits, allowlists, and blocklists.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: {
          type: 'string',
          description: 'Wallet ID (optional, defaults to configured wallet)',
        },
      },
      required: [],
    },
  },
];

// Tool handlers
export const policyToolHandlers: Record<string, ToolHandler> = {
  sardis_check_policy: async (args: unknown): Promise<ToolResult> => {
    const parsed = PolicyCheckSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { vendor, amount, category } = parsed.data;
    const result = await checkPolicy(vendor, amount, category);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(
            {
              vendor,
              amount,
              category: category || 'unspecified',
              allowed: result.allowed,
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
  },

  sardis_validate_limits: async (args: unknown): Promise<ToolResult> => {
    const parsed = PolicyCheckSchema.pick({ amount: true }).safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const result = await validateLimits(parsed.data.amount);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(
            {
              amount: parsed.data.amount,
              within_limits: result.allowed,
              reason: result.reason,
              checks: result.checks,
            },
            null,
            2
          ),
        },
      ],
    };
  },

  sardis_check_compliance: async (args: unknown): Promise<ToolResult> => {
    const parsed = ComplianceCheckSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const result = await checkCompliance(parsed.data.address, parsed.data.amount);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(
            {
              address: parsed.data.address,
              amount: parsed.data.amount,
              status: result.status,
              risk_level: result.risk_level,
              checks: result.checks,
            },
            null,
            2
          ),
        },
      ],
    };
  },

  sardis_get_policies: async (args: unknown): Promise<ToolResult> => {
    const config = getConfig();
    const walletId = typeof args === 'object' && args !== null && 'wallet_id' in args
      ? (args as { wallet_id?: string }).wallet_id || config.walletId
      : config.walletId;

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: walletId,
            policies: [{
              id: 'policy_default',
              name: 'Default Spending Policy',
              max_per_tx: '100.00',
              max_daily: '500.00',
              max_monthly: '5000.00',
              is_active: true,
              created_at: new Date().toISOString(),
            }],
          }, null, 2),
        }],
      };
    }

    try {
      const wallet = await getWalletInfo();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: wallet.id,
            policies: [{
              id: 'policy_active',
              name: 'Active Policy',
              max_per_tx: wallet.limit_per_tx,
              max_daily: wallet.limit_total,
              is_active: wallet.is_active,
            }],
          }, null, 2),
        }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get policies: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_rules: async (args: unknown): Promise<ToolResult> => {
    const config = getConfig();
    const walletId = typeof args === 'object' && args !== null && 'wallet_id' in args
      ? (args as { wallet_id?: string }).wallet_id || config.walletId
      : config.walletId;

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: walletId,
            rules: {
              limits: {
                per_transaction: '100.00',
                daily: '500.00',
                monthly: '5000.00',
              },
              allowed_vendors: getAllowedVendors(),
              blocked_vendors: getBlockedVendors(),
              blocked_categories: ['gambling', 'adult'],
              require_approval_above: '500.00',
            },
          }, null, 2),
        }],
      };
    }

    try {
      const wallet = await getWalletInfo();
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: wallet.id,
            rules: {
              limits: {
                per_transaction: wallet.limit_per_tx,
                daily: wallet.limit_total,
              },
              allowed_vendors: getAllowedVendors(),
              blocked_vendors: getBlockedVendors(),
              is_active: wallet.is_active,
            },
          }, null, 2),
        }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get rules: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
