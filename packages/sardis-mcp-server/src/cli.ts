#!/usr/bin/env node
/**
 * Sardis MCP Server CLI
 *
 * Usage:
 *   npx @sardis/mcp-server start
 *   npx @sardis/mcp-server init
 *   npx @sardis/mcp-server --version
 *   npx @sardis/mcp-server --help
 */

import fs from 'node:fs/promises';
import path from 'node:path';

import { runServer } from './index.js';
import { getValidatedToolCount, toolCategories, validateToolRegistry } from './tools/index.js';
import { MCP_SERVER_VERSION } from './version.js';

const args = process.argv.slice(2);

type InitMode = 'live' | 'simulated';

interface InitOptions {
  mode: InitMode;
  apiUrl: string;
  apiKey: string;
  paymentIdentity: string;
  agentId: string;
  agentName: string;
  walletId: string;
  chain: string;
  output: string;
  issueCard: boolean;
}

function printHelp() {
  const toolCount = getValidatedToolCount();
  const categoryCount = Object.keys(toolCategories).length;

  console.log(`
Sardis MCP Server v${MCP_SERVER_VERSION}
The Payment OS for the Agent Economy

USAGE:
  npx @sardis/mcp-server start     Start the MCP server (stdio transport)
  npx @sardis/mcp-server init      Bootstrap local MCP config (.env.sardis)
  npx @sardis/mcp-server doctor    Check configuration and connectivity
  npx @sardis/mcp-server --help    Show this help message
  npx @sardis/mcp-server --version Show version

DESCRIPTION:
  Sardis MCP Server enables AI agents to execute secure payments
  using Model Context Protocol. It exposes ${toolCount} tools across ${categoryCount} categories.

  Tools marked [sim] return simulated/fake data when SARDIS_MODE=simulated
  or when SARDIS_API_KEY is not set. Set both for real data.

  Wallet:         sardis_get_wallet [sim], sardis_get_balance [sim],
                  sardis_create_wallet [sim], sardis_list_wallets [sim]

  Payment:        sardis_pay [sim], sardis_get_transaction [sim],
                  sardis_list_transactions [sim]

  Policy:         sardis_check_policy, sardis_validate_limits,
                  sardis_check_compliance [sim], sardis_get_policies [sim]

  Hold:           sardis_create_hold [sim], sardis_capture_hold [sim],
                  sardis_void_hold [sim], sardis_release_hold [sim],
                  sardis_get_hold [sim], sardis_list_holds [sim],
                  sardis_extend_hold [sim]

  Agent:          sardis_create_agent [sim], sardis_get_agent [sim],
                  sardis_list_agents [sim], sardis_update_agent [sim]

  Card:           sardis_issue_card [sim], sardis_create_card [sim],
                  sardis_get_card [sim], sardis_list_cards [sim],
                  sardis_freeze_card [sim], sardis_unfreeze_card [sim],
                  sardis_cancel_card [sim]

  Fiat/Treasury:  sardis_sync_treasury_account_holder [sim],
                  sardis_list_financial_accounts [sim],
                  sardis_link_external_bank_account [sim],
                  sardis_verify_micro_deposits [sim],
                  sardis_fund_wallet [sim], sardis_withdraw_to_bank [sim],
                  sardis_withdraw [sim], sardis_get_funding_status [sim],
                  sardis_get_withdrawal_status [sim],
                  sardis_get_treasury_balances [sim],
                  sardis_list_funding_transactions [sim]

  Approval:       sardis_request_approval [sim],
                  sardis_get_approval_status [sim],
                  sardis_list_pending_approvals [sim],
                  sardis_cancel_approval [sim]

  Analytics:      sardis_get_spending_summary [sim],
                  sardis_get_spending_by_vendor [sim],
                  sardis_get_spending_by_category [sim],
                  sardis_get_spending_trends [sim]

  Events:         sardis_subscribe_events [sim],
                  sardis_list_event_types,
                  sardis_get_event_history [sim],
                  sardis_configure_webhook [sim]

  Guardrails:     sardis_check_circuit_breaker [sim],
                  sardis_activate_kill_switch [sim],
                  sardis_deactivate_kill_switch [sim],
                  sardis_check_rate_limits [sim],
                  sardis_get_behavioral_alerts [sim]

  x402:           sardis_x402_pay [sim], sardis_x402_preview_cost [sim],
                  sardis_x402_list_payments [sim]

  Trust:          sardis_check_agent_trust, sardis_verify_agent_identity,
                  sardis_view_policy_history

  Jobs:           sardis_create_job [sim], sardis_fund_job [sim],
                  sardis_submit_deliverable [sim], sardis_evaluate_job [sim],
                  sardis_get_job [sim], sardis_list_jobs [sim],
                  sardis_dispute_job [sim]

  Mandate:        sardis_create_mandate [sim], sardis_list_mandates [sim],
                  sardis_revoke_mandate [sim], sardis_check_mandate [sim]

  MPP:            sardis_mpp_create_session [sim], sardis_mpp_execute [sim],
                  sardis_mpp_close_session [sim], sardis_mpp_get_session [sim],
                  sardis_mpp_issue_card [sim], sardis_mpp_evaluate_policy [sim]

  Payment Object: sardis_mint_payment_object [sim],
                  sardis_present_payment_object [sim],
                  sardis_verify_payment_object [sim],
                  sardis_get_payment_object [sim],
                  sardis_list_payment_objects [sim]

  Funding:        sardis_create_funding_commitment [sim],
                  sardis_list_funding_cells [sim],
                  sardis_split_cell [sim], sardis_merge_cells [sim]

  Escrow:         sardis_create_escrow [sim], sardis_confirm_delivery [sim],
                  sardis_file_dispute [sim], sardis_submit_evidence [sim],
                  sardis_resolve_dispute [sim]

  Proxy:          sardis_call_paid_api [sim], sardis_preview_paid_api

  Projects:       sardis_discover_services, sardis_provision_service,
                  sardis_list_provisioned

  Sandbox:        sardis_sandbox_demo

CONFIGURATION (Claude Desktop):
  Add to ~/Library/Application Support/Claude/claude_desktop_config.json:

  {
    "mcpServers": {
      "sardis": {
        "command": "npx",
        "args": ["@sardis/mcp-server", "start"]
      }
    }
  }

ENVIRONMENT VARIABLES:
  SARDIS_API_KEY     Your Sardis API key (required for live mode)
  SARDIS_WALLET_ID   Default wallet ID
  SARDIS_AGENT_ID    Agent ID for this connection
  SARDIS_PAYMENT_IDENTITY  Signed one-click identity for MCP bootstrap
  SARDIS_MODE        'live' or 'simulated' (default: simulated)

  NOTE: Without SARDIS_API_KEY, ALL tools marked [sim] return fake data.
  Set SARDIS_API_KEY=sk_... and SARDIS_MODE=live for real transactions.

LEARN MORE:
  Documentation: https://sardis.sh/docs
  GitHub: https://github.com/EfeDurmaz16/sardis
`);
}

function printVersion() {
  console.log(`Sardis MCP Server v${MCP_SERVER_VERSION}`);
}

function readArgValue(argv: string[], name: string): string | undefined {
  const eqPrefix = `--${name}=`;
  const eqMatch = argv.find((a) => a.startsWith(eqPrefix));
  if (eqMatch) {
    return eqMatch.slice(eqPrefix.length);
  }
  const idx = argv.indexOf(`--${name}`);
  if (idx >= 0 && idx + 1 < argv.length) {
    return argv[idx + 1];
  }
  return undefined;
}

function hasFlag(argv: string[], name: string): boolean {
  return argv.includes(`--${name}`) || argv.some((a) => a.startsWith(`--${name}=`));
}

function parseInitOptions(argv: string[]): InitOptions {
  const mode = (readArgValue(argv, 'mode') || process.env.SARDIS_MODE || 'simulated') as InitMode;
  const output = readArgValue(argv, 'output') || '.env.sardis';
  const issueCard = hasFlag(argv, 'issue-card');

  return {
    mode,
    apiUrl: (readArgValue(argv, 'api-url') || process.env.SARDIS_API_URL || 'https://api.sardis.sh').replace(/\/$/, ''),
    apiKey: readArgValue(argv, 'api-key') || process.env.SARDIS_API_KEY || '',
    paymentIdentity:
      readArgValue(argv, 'payment-identity') || process.env.SARDIS_PAYMENT_IDENTITY || '',
    agentId: readArgValue(argv, 'agent-id') || process.env.SARDIS_AGENT_ID || '',
    agentName: readArgValue(argv, 'agent-name') || `Sardis MCP Agent ${new Date().toISOString().slice(0, 10)}`,
    walletId: readArgValue(argv, 'wallet-id') || process.env.SARDIS_WALLET_ID || '',
    chain: readArgValue(argv, 'chain') || process.env.SARDIS_CHAIN || 'base_sepolia',
    output,
    issueCard,
  };
}

async function apiRequestWithKey<T>(
  apiUrl: string,
  apiKey: string,
  method: string,
  route: string,
  body?: unknown
): Promise<T> {
  const response = await fetch(`${apiUrl}${route}`, {
    method,
    headers: {
      'X-API-Key': apiKey,
      'Content-Type': 'application/json',
      'User-Agent': `sardis-mcp-server/${MCP_SERVER_VERSION}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`${method} ${route} failed (${response.status}): ${errorBody}`);
  }

  return response.json() as Promise<T>;
}

async function upsertEnvFile(filePath: string, updates: Record<string, string>): Promise<void> {
  let existing = '';
  try {
    existing = await fs.readFile(filePath, 'utf8');
  } catch {
    existing = '';
  }

  const lineMap = new Map<string, string>();
  for (const line of existing.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) {
      continue;
    }
    const idx = trimmed.indexOf('=');
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim();
    lineMap.set(key, value);
  }

  for (const [key, value] of Object.entries(updates)) {
    lineMap.set(key, value);
  }

  const output: string[] = [
    '# Sardis MCP bootstrap configuration',
    '# Generated by: npx @sardis/mcp-server init',
    '',
  ];

  for (const key of Array.from(lineMap.keys()).sort()) {
    output.push(`${key}=${lineMap.get(key) || ''}`);
  }

  output.push('');
  await fs.writeFile(filePath, output.join('\n'), 'utf8');
}

function randomId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36).slice(-4)}`;
}

interface PaymentIdentityResolveResponse {
  payment_identity_id: string;
  agent_id: string;
  wallet_id: string;
  policy_ref?: string;
  mode?: InitMode;
  chain?: string;
  issued_at?: string;
  expires_at?: string;
  mcp_init_snippet?: string;
}

async function runInit(argv: string[]) {
  const options = parseInitOptions(argv);
  const outputFile = path.resolve(process.cwd(), options.output);

  let agentId = options.agentId;
  let walletId = options.walletId;
  let chain = options.chain;
  let cardId: string | null = null;
  const warnings: string[] = [];

  if (options.mode === 'live' && options.apiKey) {
    try {
      if (options.paymentIdentity) {
        const identity = await apiRequestWithKey<PaymentIdentityResolveResponse>(
          options.apiUrl,
          options.apiKey,
          'GET',
          `/api/v2/agents/payment-identities/${encodeURIComponent(options.paymentIdentity)}`
        );
        agentId = agentId || identity.agent_id || '';
        walletId = walletId || identity.wallet_id || '';
        if (identity.chain && !readArgValue(argv, 'chain') && !process.env.SARDIS_CHAIN) {
          chain = identity.chain;
        }
      }

      if (!agentId) {
        const createdAgent = await apiRequestWithKey<{ agent_id?: string; id?: string }>(
          options.apiUrl,
          options.apiKey,
          'POST',
          '/api/v2/agents',
          {
            name: options.agentName,
            create_wallet: false,
          }
        );
        agentId = createdAgent.agent_id || createdAgent.id || '';
      }

      if (!walletId && agentId) {
        const createdWallet = await apiRequestWithKey<{ wallet_id?: string; id?: string }>(
          options.apiUrl,
          options.apiKey,
          'POST',
          '/api/v2/wallets',
          {
            agent_id: agentId,
            mpc_provider: 'turnkey',
            currency: 'USDC',
          }
        );
        walletId = createdWallet.wallet_id || createdWallet.id || '';
      }

      if (options.issueCard && walletId) {
        const createdCard = await apiRequestWithKey<{ card_id?: string; id?: string }>(
          options.apiUrl,
          options.apiKey,
          'POST',
          '/api/v2/cards',
          {
            wallet_id: walletId,
          }
        );
        cardId = createdCard.card_id || createdCard.id || null;
      }
    } catch (error) {
      warnings.push(error instanceof Error ? error.message : 'Live provisioning failed');
    }
  }

  if (!agentId) {
    agentId = options.mode === 'live' ? randomId('agent') : 'agent_simulated';
  }
  if (!walletId) {
    walletId = options.mode === 'live' ? randomId('wallet') : 'wallet_simulated';
  }

  await upsertEnvFile(outputFile, {
    SARDIS_API_KEY: options.apiKey,
    SARDIS_API_URL: options.apiUrl,
    SARDIS_AGENT_ID: agentId,
    SARDIS_WALLET_ID: walletId,
    SARDIS_CHAIN: chain,
    SARDIS_MODE: options.mode,
    SARDIS_PAYMENT_IDENTITY: options.paymentIdentity,
  });

  console.log('');
  console.log('Sardis MCP initialization complete.');
  console.log('');
  console.log(`  Config file: ${outputFile}`);
  console.log(`  Mode:        ${options.mode}`);
  console.log(`  Agent ID:    ${agentId}`);
  console.log(`  Wallet ID:   ${walletId}`);
  console.log(`  Chain:       ${chain}`);
  if (cardId) {
    console.log(`  Card ID:     ${cardId}`);
  }
  if (!options.apiKey) {
    console.log('');
    console.log('  Note: No API key set. Running in sandbox mode (simulated transactions).');
  }
  if (warnings.length > 0) {
    console.log('');
    console.log('  Warnings:');
    for (const warning of warnings) {
      console.log(`  - ${warning}`);
    }
  }

  // Next steps guidance
  console.log('');
  console.log('What to do next:');
  console.log('');
  if (options.mode === 'simulated') {
    console.log('  1. Add Sardis to Claude Desktop:');
    console.log('     Edit ~/Library/Application Support/Claude/claude_desktop_config.json');
    console.log('');
    console.log('     {');
    console.log('       "mcpServers": {');
    console.log('         "sardis": {');
    console.log('           "command": "npx",');
    console.log('           "args": ["@sardis/mcp-server", "start"]');
    console.log('         }');
    console.log('       }');
    console.log('     }');
    console.log('');
    console.log('  2. Restart Claude Desktop');
    console.log('');
    console.log('  3. Try these in Claude:');
    console.log('     "Check my Sardis wallet balance"');
    console.log('     "Pay $29.99 to OpenAI for API credits"');
    console.log('     "Issue a virtual card with $100 limit"');
    console.log('');
    console.log('  All transactions are simulated. Policy validation runs real logic.');
    console.log('  Ask Claude to run sardis_sandbox_demo for a guided walkthrough.');
  } else {
    console.log('  1. Verify your setup:  npx @sardis/mcp-server doctor');
    console.log('  2. Start the server:   npx @sardis/mcp-server start');
    console.log('  3. Try a payment:      Ask Claude to "Pay $50 to OpenAI for API credits"');
  }
  console.log('');
}

async function runDoctor() {
  const { getValidatedToolCount, validateToolRegistry } = await import('./tools/index.js');
  console.log(`Sardis MCP Server v${MCP_SERVER_VERSION} - Health Check`);
  console.log('');

  const checks: { name: string; ok: boolean; detail: string }[] = [];

  // Check env file
  const envFile = path.resolve(process.cwd(), '.env.sardis');
  try {
    await fs.access(envFile);
    checks.push({ name: 'Config file (.env.sardis)', ok: true, detail: envFile });
  } catch {
    checks.push({ name: 'Config file (.env.sardis)', ok: false, detail: 'Not found. Run: npx @sardis/mcp-server init' });
  }

  // Check API key
  const apiKey = process.env.SARDIS_API_KEY || '';
  if (apiKey && apiKey.startsWith('sk_')) {
    checks.push({ name: 'API key (SARDIS_API_KEY)', ok: true, detail: `${apiKey.slice(0, 6)}...${apiKey.slice(-4)}` });
  } else if (apiKey) {
    checks.push({ name: 'API key (SARDIS_API_KEY)', ok: false, detail: 'Set but does not start with sk_' });
  } else {
    checks.push({ name: 'API key (SARDIS_API_KEY)', ok: false, detail: 'Not set. Sandbox mode only.' });
  }

  // Check mode
  const mode = process.env.SARDIS_MODE || 'simulated';
  checks.push({ name: 'Mode (SARDIS_MODE)', ok: true, detail: mode });

  // Check wallet ID
  const walletId = process.env.SARDIS_WALLET_ID || '';
  checks.push({
    name: 'Wallet ID (SARDIS_WALLET_ID)',
    ok: !!walletId,
    detail: walletId || 'Not set',
  });

  // Check agent ID
  const agentId = process.env.SARDIS_AGENT_ID || '';
  checks.push({
    name: 'Agent ID (SARDIS_AGENT_ID)',
    ok: !!agentId,
    detail: agentId || 'Not set',
  });

  // Check tool registry
  const registry = validateToolRegistry();
  checks.push({
    name: 'Tool registry',
    ok: registry.isValid,
    detail: `${registry.definitionCount} tools registered`,
  });

  // Check Claude Desktop config
  const claudeConfigPath = path.join(
    process.env.HOME || process.env.USERPROFILE || '',
    'Library', 'Application Support', 'Claude', 'claude_desktop_config.json'
  );
  try {
    const claudeConfig = await fs.readFile(claudeConfigPath, 'utf8');
    const hasSardis = claudeConfig.includes('sardis');
    checks.push({
      name: 'Claude Desktop config',
      ok: hasSardis,
      detail: hasSardis ? 'Sardis server configured' : 'Config exists but Sardis not found',
    });
  } catch {
    checks.push({
      name: 'Claude Desktop config',
      ok: false,
      detail: 'Not found at expected path',
    });
  }

  // Check API connectivity (only if API key is set)
  if (apiKey && mode === 'live') {
    try {
      const apiUrl = process.env.SARDIS_API_URL || 'https://api.sardis.sh';
      const response = await fetch(`${apiUrl}/health`, {
        method: 'GET',
        headers: { 'User-Agent': `sardis-mcp-server/${MCP_SERVER_VERSION}` },
        signal: AbortSignal.timeout(5000),
      });
      checks.push({
        name: 'API connectivity',
        ok: response.ok,
        detail: response.ok ? `${apiUrl} reachable` : `HTTP ${response.status}`,
      });
    } catch (error) {
      checks.push({
        name: 'API connectivity',
        ok: false,
        detail: error instanceof Error ? error.message : 'Connection failed',
      });
    }
  }

  // Print results
  let allOk = true;
  for (const check of checks) {
    const icon = check.ok ? '\u2713' : '\u2717';
    console.log(`  ${icon} ${check.name}: ${check.detail}`);
    if (!check.ok) allOk = false;
  }

  console.log('');
  if (allOk) {
    console.log('All checks passed. Your Sardis MCP server is ready.');
  } else if (!apiKey) {
    console.log('Running in sandbox mode. Set SARDIS_API_KEY for live transactions.');
  } else {
    console.log('Some checks failed. Fix the issues above and run doctor again.');
  }
  console.log('');
}

async function main() {
  if (args.includes('--help') || args.includes('-h')) {
    printHelp();
    process.exit(0);
  }

  if (args.includes('--version') || args.includes('-v')) {
    printVersion();
    process.exit(0);
  }

  if (args[0] === 'init') {
    await runInit(args.slice(1));
    process.exit(0);
  }

  if (args[0] === 'doctor') {
    await runDoctor();
    process.exit(0);
  }

  if (args[0] === 'start' || args.length === 0) {
    const registryValidation = validateToolRegistry();
    const toolCount = registryValidation.definitionCount;
    const categoryCount = Object.keys(toolCategories).length;
    const mode = process.env.SARDIS_MODE || 'simulated';
    const isSandbox = mode === 'simulated';

    if (isSandbox) {
      console.error('');
      console.error('╔══════════════════════════════════════════════════════════════╗');
      console.error(`║  Sardis MCP Server v${MCP_SERVER_VERSION} — SIMULATED MODE                 ║`);
      console.error('║                                                             ║');
      console.error('║  ⚠ Running in SIMULATED mode. Responses are NOT real.      ║');
      console.error('║  ⚠ All data returned by tools is FAKE / generated.         ║');
      console.error('║  ⚠ No real funds move. No real wallets are created.        ║');
      console.error('║                                                             ║');
      console.error('║  Policy validation runs REAL logic.                         ║');
      console.error(
        `║  ${String(toolCount).padEnd(2, ' ')} tools available across ${String(categoryCount).padEnd(2, ' ')} categories                ║`
      );
      console.error('║                                                             ║');
      console.error('║  Set SARDIS_API_KEY for live mode:                          ║');
      console.error('║    export SARDIS_API_KEY=sk_live_...                        ║');
      console.error('║    export SARDIS_MODE=live                                  ║');
      console.error('║                                                             ║');
      console.error('║  Try: sardis_sandbox_demo for a guided walkthrough          ║');
      console.error('╚══════════════════════════════════════════════════════════════╝');
      console.error('');
    } else {
      console.error(`Sardis MCP Server v${MCP_SERVER_VERSION} starting...`);
      console.error('Mode: live');
      console.error(`Tools: ${toolCount} tools across ${categoryCount} categories`);
    }

    if (!registryValidation.isValid) {
      console.error(
        `Warning: tool registry mismatch (definitions=${registryValidation.definitionCount}, handlers=${registryValidation.handlerCount})`
      );
    }
    console.error('Ready. Waiting for MCP client connection...');
    await runServer();
  } else {
    console.error(`Unknown command: ${args[0]}`);
    console.error('Run "npx @sardis/mcp-server --help" for usage.');
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
