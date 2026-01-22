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
  using Model Context Protocol. It exposes the following tools:

  • sardis_pay          Execute a payment with policy validation
  • sardis_check_policy Check if a payment would be allowed
  • sardis_get_balance  Get wallet balance and limits

CONFIGURATION:
  Add to your Claude Desktop config (claude_desktop_config.json):

  {
    "mcpServers": {
      "sardis": {
        "command": "npx",
        "args": ["@sardis/mcp-server", "start"]
      }
    }
  }

ENVIRONMENT VARIABLES:
  SARDIS_API_KEY     Your Sardis API key (optional for demo mode)
  SARDIS_WALLET_ID   Your wallet ID (optional)

LEARN MORE:
  Documentation: https://docs.sardis.sh
  GitHub: https://github.com/EfeDurmaz16/sardis
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
    console.error('🚀 Starting Sardis MCP Server v0.1.0...');
    console.error('📋 Tools: sardis_pay, sardis_check_policy, sardis_get_balance');
    console.error('✅ Server ready. Waiting for MCP client connection...');
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
