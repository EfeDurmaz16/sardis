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
  npx @sardis/mcp-server --help    Show this help message
  npx @sardis/mcp-server --version Show version

DESCRIPTION:
  Sardis MCP Server enables AI agents to execute secure payments
  using Model Context Protocol. It exposes ${toolCount} tools across ${categoryCount} categories:

  Wallet (5):     sardis_get_wallet, sardis_get_balance, sardis_create_wallet,
                  sardis_update_wallet_policy, sardis_list_wallets

  Payment (3):    sardis_pay, sardis_get_transaction, sardis_list_transactions

  Policy (3):     sardis_check_policy, sardis_validate_limits, sardis_check_compliance

  Hold (6):       sardis_create_hold, sardis_capture_hold, sardis_void_hold,
                  sardis_get_hold, sardis_list_holds, sardis_extend_hold

  Agent (4):      sardis_create_agent, sardis_get_agent, sardis_list_agents,
                  sardis_update_agent

  Card (6):       sardis_issue_card, sardis_get_card, sardis_list_cards,
                  sardis_freeze_card, sardis_unfreeze_card, sardis_cancel_card

  Fiat (4):       sardis_fund_wallet, sardis_withdraw_to_bank,
                  sardis_get_funding_status, sardis_get_withdrawal_status

  Approval (2):   sardis_request_approval, sardis_get_approval_status

  Analytics (3):  sardis_get_spending_summary, sardis_get_spending_by_vendor,
                  sardis_get_spending_by_category

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
  SARDIS_API_KEY     Your Sardis API key (optional for simulated mode)
  SARDIS_WALLET_ID   Default wallet ID
  SARDIS_AGENT_ID    Agent ID for this connection
  SARDIS_PAYMENT_IDENTITY  Signed one-click identity for MCP bootstrap
  SARDIS_MODE        'live' or 'simulated' (default: simulated)

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

  console.log('Sardis MCP initialization complete.');
  console.log(`Config file: ${outputFile}`);
  console.log(`Mode: ${options.mode}`);
  console.log(`Agent ID: ${agentId}`);
  console.log(`Wallet ID: ${walletId}`);
  console.log(`Chain: ${chain}`);
  if (cardId) {
    console.log(`Card ID: ${cardId}`);
  }
  if (!options.apiKey) {
    console.log('Note: SARDIS_API_KEY is empty. Set it before live API usage.');
  }
  if (warnings.length > 0) {
    console.log('');
    console.log('Warnings:');
    for (const warning of warnings) {
      console.log(`- ${warning}`);
    }
  }
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

  if (args[0] === 'start' || args.length === 0) {
    const registryValidation = validateToolRegistry();
    const toolCount = registryValidation.definitionCount;
    const categoryCount = Object.keys(toolCategories).length;
    const mode = process.env.SARDIS_MODE || 'simulated';
    const isSandbox = mode === 'simulated';

    if (isSandbox) {
      console.error('');
      console.error('╔══════════════════════════════════════════════════════════════╗');
      console.error(`║  Sardis MCP Server v${MCP_SERVER_VERSION} — SANDBOX MODE                   ║`);
      console.error('║                                                             ║');
      console.error('║  All transactions are SIMULATED (no real funds move)        ║');
      console.error('║  Policy validation runs REAL logic                          ║');
      console.error(
        `║  ${String(toolCount).padEnd(2, ' ')} tools available across ${String(categoryCount).padEnd(2, ' ')} categories                ║`
      );
      console.error('║                                                             ║');
      console.error('║  Set SARDIS_API_KEY + SARDIS_MODE=live for real txns        ║');
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
