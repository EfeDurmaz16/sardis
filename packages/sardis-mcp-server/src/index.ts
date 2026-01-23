/**
 * Sardis MCP Server
 *
 * Model Context Protocol server that exposes Sardis payment capabilities
 * to AI agents running in Claude Desktop, Cursor, and other MCP-compatible clients.
 *
 * Tools:
 * - Wallet: sardis_get_wallet, sardis_get_balance
 * - Payments: sardis_pay, sardis_get_transaction, sardis_list_transactions
 * - Policy: sardis_check_policy, sardis_validate_limits, sardis_check_compliance
 * - Holds: sardis_create_hold, sardis_capture_hold, sardis_void_hold, sardis_get_hold, sardis_list_holds, sardis_extend_hold
 * - Agents: sardis_create_agent, sardis_get_agent, sardis_list_agents, sardis_update_agent
 *
 * Environment Variables:
 * - SARDIS_API_KEY: API key for Sardis API (required)
 * - SARDIS_API_URL: API base URL (default: https://api.sardis.network)
 * - SARDIS_WALLET_ID: Default wallet ID
 * - SARDIS_AGENT_ID: Agent ID for attribution
 * - SARDIS_CHAIN: Default chain (default: base_sepolia)
 * - SARDIS_MODE: 'live' or 'simulated' (default: simulated)
 * - SARDIS_POLICY_BLOCKED_VENDORS: Comma-separated blocked vendors
 * - SARDIS_POLICY_ALLOWED_VENDORS: Comma-separated allowed vendors
 * - SARDIS_REQUIRE_EXPLICIT_APPROVAL: Require explicit vendor approval (default: false)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { getConfig } from './config.js';
import {
  allToolDefinitions,
  allToolHandlers,
  getWalletInfo,
  getWalletBalance,
} from './tools/index.js';

export async function createServer() {
  const server = new Server(
    {
      name: 'sardis-mcp-server',
      version: '0.2.0',
    },
    {
      capabilities: {
        tools: {},
        resources: {},
      },
    }
  );

  // List available tools (from modular tool definitions)
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: allToolDefinitions.map((tool) => ({
        name: tool.name,
        description: tool.description,
        inputSchema: tool.inputSchema,
      })),
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
        {
          uri: 'sardis://tools',
          name: 'Available Tools',
          description: 'List of all available Sardis MCP tools',
          mimeType: 'application/json',
        },
      ],
    };
  });

  // Read resources
  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const { uri } = request.params;
    const config = getConfig();

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
                policy: {
                  blocked_vendors_count: config.policyBlockedVendors.length,
                  allowed_vendors_count: config.policyAllowedVendors.length,
                  require_explicit_approval: config.requireExplicitApproval,
                  fetch_agent_policy: config.fetchAgentPolicy,
                },
              },
              null,
              2
            ),
          },
        ],
      };
    }

    if (uri === 'sardis://tools') {
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(
              {
                total_tools: allToolDefinitions.length,
                tools: allToolDefinitions.map((t) => ({
                  name: t.name,
                  description: t.description,
                })),
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

  // Handle tool calls (using modular handlers)
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    const handler = allToolHandlers[name];
    if (!handler) {
      throw new Error(`Unknown tool: ${name}`);
    }

    return handler(args);
  });

  return server;
}

export async function runServer() {
  const server = await createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);

  const config = getConfig();

  // Log configuration status
  console.error('Sardis MCP Server v0.2.0 running on stdio');
  console.error(`Mode: ${config.mode}`);
  console.error(`API URL: ${config.apiUrl}`);
  console.error(`API Key configured: ${config.apiKey ? 'yes' : 'no'}`);
  console.error(`Wallet ID: ${config.walletId || '(not set)'}`);
  console.error(`Tools available: ${allToolDefinitions.length}`);
}

// Auto-start if run directly
const isMainModule =
  typeof process !== 'undefined' &&
  process.argv[1] &&
  (process.argv[1].endsWith('index.js') || process.argv[1].endsWith('index.ts'));

if (isMainModule) {
  runServer().catch(console.error);
}
