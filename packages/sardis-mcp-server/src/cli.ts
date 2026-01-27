#!/usr/bin/env node
/**
 * Sardis MCP Server CLI
 *
 * Usage:
 *   npx @sardis/mcp-server start
 *   npx @sardis/mcp-server --version
 *   npx @sardis/mcp-server --help
 */

import { runServer } from './index.js';

const args = process.argv.slice(2);

function printHelp() {
  console.log(`
Sardis MCP Server v0.1.0
The Payment OS for the Agent Economy

USAGE:
  npx @sardis/mcp-server start     Start the MCP server (stdio transport)
  npx @sardis/mcp-server --help    Show this help message
  npx @sardis/mcp-server --version Show version

DESCRIPTION:
  Sardis MCP Server enables AI agents to execute secure payments
  using Model Context Protocol. It exposes 36 tools across 8 categories:

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
  SARDIS_MODE        'live' or 'simulated' (default: simulated)

LEARN MORE:
  Documentation: https://docs.sardis.network
  GitHub: https://github.com/sardis-network/sardis
`);
}

function printVersion() {
  console.log('Sardis MCP Server v0.1.0');
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

  if (args[0] === 'start' || args.length === 0) {
    console.error('Sardis MCP Server v0.1.0 starting...');
    console.error('Mode: ' + (process.env.SARDIS_MODE || 'simulated'));
    console.error('Tools: 36 tools across 8 categories');
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
