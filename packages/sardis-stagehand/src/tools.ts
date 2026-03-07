/**
 * Sardis payment tools for Stagehand browser agents.
 */
import { z } from 'zod';

interface SardisToolsConfig {
  apiKey?: string;
  walletId?: string;
  chain?: string;
  token?: string;
}

export function createSardisTools(config: SardisToolsConfig = {}) {
  const apiKey = config.apiKey || process.env.SARDIS_API_KEY || '';
  const defaultWalletId = config.walletId || process.env.SARDIS_WALLET_ID || '';
  const defaultChain = config.chain || 'base';
  const defaultToken = config.token || 'USDC';

  // Lazy client initialization to avoid requiring @sardis/sdk at import time
  let _client: any = null;
  const getClient = () => {
    if (!_client) {
      // Dynamic import pattern - works with or without @sardis/sdk
      try {
        const { SardisClient } = require('@sardis/sdk');
        _client = new SardisClient({ apiKey });
      } catch {
        throw new Error('@sardis/sdk is required: npm install @sardis/sdk');
      }
    }
    return _client;
  };

  return {
    sardis_pay: {
      name: 'sardis_pay',
      description: 'Execute a policy-controlled payment from the agent\'s Sardis wallet',
      schema: z.object({
        amount: z.number().describe('Payment amount in USD'),
        merchant: z.string().describe('Merchant or recipient identifier'),
        purpose: z.string().optional().describe('Reason for payment'),
        walletId: z.string().optional().describe('Wallet ID override'),
      }),
      execute: async ({ amount, merchant, purpose, walletId }: {
        amount: number;
        merchant: string;
        purpose?: string;
        walletId?: string;
      }) => {
        const client = getClient();
        const wid = walletId || defaultWalletId;
        if (!wid) return { success: false, error: 'No wallet ID configured' };

        try {
          const result = await client.wallets.transfer(wid, {
            destination: merchant,
            amount: amount.toString(),
            token: defaultToken,
            chain: defaultChain,
            memo: purpose,
          });
          return {
            success: true,
            status: 'APPROVED',
            transactionHash: result.tx_hash,
            message: `Payment of $${amount} to ${merchant} completed`,
          };
        } catch (error: unknown) {
          const msg = error instanceof Error ? error.message : 'Payment failed';
          return { success: false, status: 'BLOCKED', error: msg };
        }
      },
    },

    sardis_check_balance: {
      name: 'sardis_check_balance',
      description: 'Check the current wallet balance before making a purchase',
      schema: z.object({
        walletId: z.string().optional().describe('Wallet ID override'),
        token: z.string().optional().describe('Token to check'),
      }),
      execute: async ({ walletId, token }: { walletId?: string; token?: string }) => {
        const client = getClient();
        const wid = walletId || defaultWalletId;
        if (!wid) return { success: false, error: 'No wallet ID configured' };

        try {
          const balance = await client.wallets.getBalance(wid, defaultChain, token || defaultToken);
          return {
            success: true,
            balance: balance.balance,
            token: balance.token,
            chain: balance.chain,
          };
        } catch (error: unknown) {
          return { success: false, error: error instanceof Error ? error.message : 'Failed' };
        }
      },
    },

    sardis_check_policy: {
      name: 'sardis_check_policy',
      description: 'Check if a purchase would be allowed by spending policy',
      schema: z.object({
        amount: z.number().describe('Amount to check'),
        merchant: z.string().describe('Merchant to check'),
      }),
      execute: async ({ amount, merchant }: { amount: number; merchant: string }) => {
        const client = getClient();
        const wid = defaultWalletId;
        if (!wid) return { success: false, error: 'No wallet ID configured' };

        try {
          const wallet = await client.wallets.get(wid);
          const limitPerTx = parseFloat(wallet.limit_per_tx || '0');
          return {
            allowed: amount <= limitPerTx,
            message: amount <= limitPerTx
              ? `$${amount} to ${merchant} would be allowed`
              : `$${amount} exceeds per-tx limit of $${limitPerTx}`,
          };
        } catch (error: unknown) {
          return { success: false, error: error instanceof Error ? error.message : 'Failed' };
        }
      },
    },
  };
}
