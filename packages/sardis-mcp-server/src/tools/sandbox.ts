/**
 * Sardis MCP Server - Sandbox Demo Tool
 *
 * Provides a guided walkthrough of Sardis capabilities in sandbox mode.
 * Designed to onboard developers quickly when no API key is configured.
 */

import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { getConfig } from '../config.js';

export const sandboxToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_sandbox_demo',
    description:
      'Interactive guided walkthrough of Sardis payment capabilities. ' +
      'Returns example commands you can run right now in sandbox mode. ' +
      'No API key required — perfect for first-time exploration.',
    inputSchema: {
      type: 'object',
      properties: {
        category: {
          type: 'string',
          enum: ['quickstart', 'payments', 'cards', 'policy', 'holds', 'fiat', 'all'],
          description:
            'Which capability to explore. Use "quickstart" for a 3-step intro, or "all" for the full guide.',
        },
      },
      required: [],
    },
  },
];

function quickstartGuide(): object {
  return {
    title: 'Sardis Sandbox — Quick Start (3 steps)',
    description:
      'Try these 3 commands in order to see Sardis in action. All responses are simulated — no real funds move.',
    steps: [
      {
        step: 1,
        action: 'Check your wallet balance',
        tool: 'sardis_get_balance',
        args: {},
        what_happens:
          'Returns a simulated USDC balance on Base Sepolia. Policy limits are real.',
      },
      {
        step: 2,
        action: 'Validate a payment policy',
        tool: 'sardis_check_policy',
        args: { vendor: 'openai', amount: 50 },
        what_happens:
          'Runs REAL policy logic — vendor allowlist, spending limits, compliance checks. ' +
          'Try "amazon" to see a blocked vendor.',
      },
      {
        step: 3,
        action: 'Execute a simulated payment',
        tool: 'sardis_pay',
        args: { vendor: 'openai', amount: 29.99, purpose: 'API credits' },
        what_happens:
          'Simulates the full payment flow: policy check → hold → execute → audit trail. ' +
          'Returns a simulated tx_hash and ledger entry.',
      },
    ],
    next: 'Run sardis_sandbox_demo with category="payments", "cards", "policy", "holds", or "fiat" for deeper exploration.',
  };
}

function paymentsGuide(): object {
  return {
    title: 'Sandbox — Payments',
    tools: [
      {
        tool: 'sardis_pay',
        description: 'Execute a payment from your agent wallet',
        example_args: { vendor: 'anthropic', amount: 100, purpose: 'Claude API usage' },
        try_also: [
          { vendor: 'amazon', amount: 50, note: 'Will be BLOCKED by policy' },
          { vendor: 'vercel', amount: 20, purpose: 'Hosting', note: 'Allowed SaaS vendor' },
        ],
      },
      {
        tool: 'sardis_get_transaction',
        description: 'Look up a transaction by ID',
        example_args: { transaction_id: 'tx_sandbox_001' },
      },
      {
        tool: 'sardis_list_transactions',
        description: 'List recent transactions',
        example_args: { limit: 10 },
      },
    ],
  };
}

function cardsGuide(): object {
  return {
    title: 'Sandbox — Virtual Cards',
    description:
      'Issue Lithic-powered virtual cards for your AI agent. Cards have per-tx, daily, and monthly limits.',
    tools: [
      {
        tool: 'sardis_issue_card',
        description: 'Issue a new virtual card',
        example_args: { card_type: 'SINGLE_USE', limit_per_tx: 100, limit_daily: 500 },
      },
      {
        tool: 'sardis_list_cards',
        description: 'List all cards for the current wallet',
        example_args: {},
      },
      {
        tool: 'sardis_freeze_card',
        description: 'Freeze a card instantly',
        example_args: { card_id: 'card_sandbox_001' },
      },
    ],
  };
}

function policyGuide(): object {
  return {
    title: 'Sandbox — Policy Engine',
    description:
      'The policy engine runs REAL validation logic even in sandbox mode. ' +
      'This is the core safety layer that prevents rogue agent spending.',
    tools: [
      {
        tool: 'sardis_check_policy',
        description: 'Check if a payment would be allowed',
        examples: [
          { args: { vendor: 'openai', amount: 50 }, expected: 'ALLOWED (on allowlist)' },
          { args: { vendor: 'amazon', amount: 50 }, expected: 'BLOCKED (on blocklist)' },
          { args: { vendor: 'unknown_vendor', amount: 50 }, expected: 'Depends on SARDIS_REQUIRE_EXPLICIT_APPROVAL' },
          { args: { vendor: 'openai', amount: 999999 }, expected: 'BLOCKED (exceeds limits)' },
        ],
      },
      {
        tool: 'sardis_validate_limits',
        description: 'Check spending limits without executing',
        example_args: { amount: 250 },
      },
      {
        tool: 'sardis_check_compliance',
        description: 'Run sanctions/AML screening on an address',
        example_args: { address: '0x1234567890abcdef1234567890abcdef12345678', amount: 500 },
      },
    ],
    config_tips: [
      'Set SARDIS_POLICY_BLOCKED_VENDORS to customize the blocklist',
      'Set SARDIS_POLICY_ALLOWED_VENDORS to customize the allowlist',
      'Set SARDIS_REQUIRE_EXPLICIT_APPROVAL=true for strict mode',
    ],
  };
}

function holdsGuide(): object {
  return {
    title: 'Sandbox — Payment Holds',
    description:
      'Two-phase payments: place a hold first, then capture or void. ' +
      'Essential for marketplace escrow and subscription billing.',
    tools: [
      {
        tool: 'sardis_create_hold',
        description: 'Place a hold on funds',
        example_args: { amount: 50, purpose: 'SaaS subscription', duration_hours: 72 },
      },
      {
        tool: 'sardis_capture_hold',
        description: 'Capture (settle) a hold',
        example_args: { hold_id: 'hold_sandbox_001' },
      },
      {
        tool: 'sardis_void_hold',
        description: 'Release a hold without charging',
        example_args: { hold_id: 'hold_sandbox_001' },
      },
      {
        tool: 'sardis_list_holds',
        description: 'List all holds',
        example_args: { status: 'active' },
      },
    ],
  };
}

function fiatGuide(): object {
  return {
    title: 'Sandbox — Fiat On/Off Ramp',
    description:
      'Bridge-powered fiat rails: fund wallets from bank accounts, withdraw to bank, or pay merchants in USD.',
    tools: [
      {
        tool: 'sardis_fund_wallet',
        description: 'Fund wallet from bank (ACH) or card',
        example_args: { amount_usd: 100, method: 'bank' },
      },
      {
        tool: 'sardis_withdraw_to_bank',
        description: 'Withdraw to bank account',
        example_args: { amount_usd: 50, account_holder_name: 'Test User', routing_number: '021000021', account_number: '1234567890' },
      },
      {
        tool: 'sardis_get_funding_status',
        description: 'Check funding transfer status',
        example_args: { transfer_id: 'transfer_sandbox_001' },
      },
    ],
  };
}

function fullGuide(): object {
  return {
    title: 'Sardis Sandbox — Complete Guide',
    mode: 'simulated',
    description:
      'You are running in sandbox mode. All 36+ tools work with simulated responses. ' +
      'Policy validation (vendor checks, spending limits) runs real logic.',
    categories: {
      quickstart: quickstartGuide(),
      payments: paymentsGuide(),
      cards: cardsGuide(),
      policy: policyGuide(),
      holds: holdsGuide(),
      fiat: fiatGuide(),
    },
    going_live: {
      step_1: 'Get an API key at https://sardis.sh',
      step_2: 'Set SARDIS_API_KEY=sk_... and SARDIS_MODE=live',
      step_3: 'All the same tools now execute real transactions',
    },
  };
}

const sandboxDemoHandler: ToolHandler = async (args: unknown) => {
  const parsed = args as { category?: string } | undefined;
  const category = parsed?.category || 'quickstart';
  const config = getConfig();

  let guide: object;

  switch (category) {
    case 'payments':
      guide = paymentsGuide();
      break;
    case 'cards':
      guide = cardsGuide();
      break;
    case 'policy':
      guide = policyGuide();
      break;
    case 'holds':
      guide = holdsGuide();
      break;
    case 'fiat':
      guide = fiatGuide();
      break;
    case 'all':
      guide = fullGuide();
      break;
    case 'quickstart':
    default:
      guide = quickstartGuide();
      break;
  }

  const response = {
    ...guide,
    _sandbox: true,
    _mode: config.mode,
    _api_key_configured: !!config.apiKey,
  };

  return {
    content: [
      {
        type: 'text' as const,
        text: JSON.stringify(response, null, 2),
      },
    ],
  };
};

export const sandboxToolHandlers: Record<string, ToolHandler> = {
  sardis_sandbox_demo: sandboxDemoHandler,
};
