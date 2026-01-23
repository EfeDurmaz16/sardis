/**
 * Wallet tools for MCP server
 */

import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type {
  ToolDefinition,
  ToolHandler,
  ToolResult,
  WalletInfo,
  WalletBalance,
} from './types.js';
import { BalanceCheckSchema } from './types.js';

/**
 * Get wallet info from API or return simulated data
 */
export async function getWalletInfo(): Promise<WalletInfo> {
  const config = getConfig();

  if (!config.apiKey || !config.walletId) {
    return {
      id: config.walletId || 'wallet_simulated',
      limit_per_tx: '100.00',
      limit_total: '500.00',
      is_active: true,
      currency: 'USDC',
    };
  }

  return apiRequest<WalletInfo>('GET', `/api/v2/wallets/${config.walletId}`);
}

/**
 * Get wallet balance from API or return simulated data
 */
export async function getWalletBalance(
  token: string = 'USDC',
  chain?: string
): Promise<WalletBalance> {
  const config = getConfig();
  const effectiveChain = chain || config.chain;

  if (!config.apiKey || !config.walletId) {
    return {
      wallet_id: config.walletId || 'wallet_simulated',
      balance: '1000.00',
      token,
      chain: effectiveChain,
      address: '0x' + '0'.repeat(40),
    };
  }

  return apiRequest<WalletBalance>(
    'GET',
    `/api/v2/wallets/${config.walletId}/balance?chain=${effectiveChain}&token=${token}`
  );
}

// Tool definitions
export const walletToolDefinitions: ToolDefinition[] = [
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
];

// Tool handlers
export const walletToolHandlers: Record<string, ToolHandler> = {
  sardis_get_balance: async (args: unknown): Promise<ToolResult> => {
    const parsed = BalanceCheckSchema.safeParse(args);
    const config = getConfig();
    const token = parsed.success ? parsed.data.token || 'USDC' : 'USDC';
    const chain = parsed.success ? parsed.data.chain || config.chain : config.chain;

    try {
      const balance = await getWalletBalance(token, chain);
      return {
        content: [{ type: 'text', text: JSON.stringify(balance, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get balance: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_wallet: async (): Promise<ToolResult> => {
    try {
      const wallet = await getWalletInfo();
      return {
        content: [{ type: 'text', text: JSON.stringify(wallet, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get wallet info: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
