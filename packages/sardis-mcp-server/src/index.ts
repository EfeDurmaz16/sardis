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
 * - Events: sardis_subscribe_events, sardis_list_event_types, sardis_get_event_history, sardis_configure_webhook
 *
 * Environment Variables:
 * - SARDIS_API_KEY: API key for Sardis API (required)
 * - SARDIS_API_URL: API base URL (default: https://api.sardis.sh)
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
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { getConfig } from './config.js';
import {
  allToolDefinitions,
  allToolHandlers,
  getWalletInfo,
  getWalletBalance,
} from './tools/index.js';
import { MCP_SERVER_VERSION } from './version.js';

export async function createServer() {
  const server = new Server(
    {
      name: 'sardis-mcp-server',
      version: MCP_SERVER_VERSION,
    },
    {
      capabilities: {
        tools: {},
        resources: {},
        prompts: {},
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

  // Prompt templates
  server.setRequestHandler(ListPromptsRequestSchema, async () => {
    return {
      prompts: [
        {
          name: 'pay-vendor',
          description: 'Make a payment to a vendor with policy validation',
          arguments: [
            { name: 'vendor', description: 'Vendor name (e.g., openai, anthropic)', required: true },
            { name: 'amount', description: 'Amount in USD', required: true },
            { name: 'purpose', description: 'Payment purpose', required: false },
          ],
        },
        {
          name: 'check-balance',
          description: 'Check wallet balance and spending limits',
          arguments: [],
        },
        {
          name: 'sandbox-tour',
          description: 'Guided tour of Sardis sandbox capabilities',
          arguments: [
            {
              name: 'category',
              description: 'Focus area: quickstart, payments, cards, policy, holds, fiat, or all',
              required: false,
            },
          ],
        },
      ],
    };
  });

  server.setRequestHandler(GetPromptRequestSchema, async (request) => {
    const { name, arguments: promptArgs } = request.params;

    if (name === 'pay-vendor') {
      const vendor = promptArgs?.vendor || 'openai';
      const amount = promptArgs?.amount || '50';
      const purpose = promptArgs?.purpose || 'API usage';
      return {
        messages: [
          {
            role: 'user' as const,
            content: {
              type: 'text' as const,
              text: `Please pay $${amount} to ${vendor} for "${purpose}". First check the policy with sardis_check_policy, then execute with sardis_pay if allowed.`,
            },
          },
        ],
      };
    }

    if (name === 'check-balance') {
      return {
        messages: [
          {
            role: 'user' as const,
            content: {
              type: 'text' as const,
              text: 'Check my Sardis wallet balance using sardis_get_balance, then show my spending limits with sardis_validate_limits for a $100 payment.',
            },
          },
        ],
      };
    }

    if (name === 'sandbox-tour') {
      const category = promptArgs?.category || 'quickstart';
      return {
        messages: [
          {
            role: 'user' as const,
            content: {
              type: 'text' as const,
              text: `Run sardis_sandbox_demo with category="${category}" and then walk me through each step interactively. Execute the example commands one by one and explain the results.`,
            },
          },
        ],
      };
    }

    throw new Error(`Unknown prompt: ${name}`);
  });

  // SECURITY: Per-tool rate limiting to prevent abuse by compromised/injected agents.
  const toolCallCounts = new Map<string, { count: number; windowStart: number }>();
  const RATE_LIMIT_WINDOW_MS = 60_000; // 1 minute
  const RATE_LIMITS: Record<string, number> = {
    // Payment execution: strict limit
    sardis_pay: 5,
    sardis_execute_payment: 5,
    // Wallet mutations
    sardis_create_wallet: 3,
    // Hold operations
    sardis_create_hold: 10,
    sardis_capture_hold: 10,
    // Read operations: more lenient
    _default: 60,
  };

  function checkRateLimit(toolName: string): boolean {
    const now = Date.now();
    const limit = RATE_LIMITS[toolName] ?? RATE_LIMITS._default ?? 60;
    const entry = toolCallCounts.get(toolName);

    if (!entry || now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
      toolCallCounts.set(toolName, { count: 1, windowStart: now });
      return true;
    }

    if (entry.count >= limit) {
      return false;
    }

    entry.count++;
    return true;
  }

  // Handle tool calls (using modular handlers)
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    const handler = allToolHandlers[name];
    if (!handler) {
      throw new Error(`Unknown tool: ${name}`);
    }

    // Enforce rate limit
    if (!checkRateLimit(name)) {
      const limit = RATE_LIMITS[name] ?? RATE_LIMITS._default;
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            error: `Rate limit exceeded for ${name}. Maximum ${limit} calls per minute.`,
          }),
        }],
        isError: true,
      };
    }

    const result = await handler(args);

    // In simulated mode, inject _sandbox metadata into JSON responses
    const config = getConfig();
    if (config.mode === 'simulated' && result.content?.length > 0) {
      result.content = result.content.map((item) => {
        if (item.type === 'text') {
          try {
            const parsed = JSON.parse(item.text);
            parsed._sandbox = true;
            parsed._notice = 'Simulated response — no real funds were moved';
            return { ...item, text: JSON.stringify(parsed, null, 2) };
          } catch {
            // Not JSON, skip injection
          }
        }
        return item;
      });
    }

    return result;
  });

  return server;
}

export async function runServer() {
  const server = await createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);

  const config = getConfig();

  // Log configuration status
  console.error(`Sardis MCP Server v${MCP_SERVER_VERSION} running on stdio`);
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
