import { z } from 'zod';
import { SardisClient } from '../client.js';

export interface SardisToolsOptions {
    /** Default wallet ID to use for payments */
    walletId?: string;
    /** Default agent ID */
    agentId?: string;
    /** Default chain for transactions */
    chain?: 'base' | 'base_sepolia' | 'polygon' | 'polygon_amoy' | 'ethereum' | 'ethereum_sepolia';
    /** Default token */
    token?: 'USDC' | 'USDT' | 'PYUSD' | 'EURC';
}

/**
 * Create Sardis tools for Vercel AI SDK integration.
 *
 * @example
 * ```typescript
 * import { generateText } from 'ai';
 * import { SardisClient } from '@sardis/sdk';
 * import { createSardisTools } from '@sardis/sdk/integrations/vercel-ai';
 *
 * const client = new SardisClient({ apiKey: 'your-api-key' });
 * const tools = createSardisTools(client, {
 *   walletId: 'wallet_123',
 *   agentId: 'agent_456'
 * });
 *
 * const result = await generateText({
 *   model: yourModel,
 *   tools,
 *   prompt: 'Pay $50 to OpenAI for API credits'
 * });
 * ```
 */
export const createSardisTools = (client?: SardisClient, options: SardisToolsOptions = {}) => {
    const sardis = client;
    const defaultWalletId = options.walletId || process.env.SARDIS_WALLET_ID || '';
    const defaultChain = options.chain || 'base_sepolia';
    const defaultToken = options.token || 'USDC';

    return {
        /**
         * Execute a secure payment using Sardis MPC wallet.
         */
        payVendor: {
            description: 'Execute a secure payment using Sardis MPC wallet. Validates against spending policies before execution.',
            parameters: z.object({
                amount: z.number().describe('The amount to pay in USD (or token units).'),
                vendor: z.string().describe('The name of the merchant or service provider.'),
                vendorAddress: z.string().optional().describe('The wallet address of the vendor (0x...).'),
                purpose: z.string().optional().describe('The reason for the payment, used for policy validation.'),
                walletId: z.string().optional().describe('The wallet ID to pay from. Defaults to configured wallet.'),
                token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().describe('The stablecoin to use. Defaults to USDC.'),
                chain: z.string().optional().describe('The chain to use (e.g. base_sepolia). Defaults to configured chain.'),
                domain: z.string().optional().describe('Policy context label (e.g. aws.amazon.com). Defaults to vendor.'),
            }),
            execute: async ({
                amount,
                vendor,
                vendorAddress,
                purpose,
                walletId,
                token,
                chain,
                domain,
            }: {
                amount: number;
                vendor: string;
                vendorAddress?: string;
                purpose?: string;
                walletId?: string;
                token?: 'USDC' | 'USDT' | 'PYUSD' | 'EURC';
                chain?: SardisToolsOptions['chain'];
                domain?: string;
            }) => {
                if (!sardis) {
                    return {
                        success: false,
                        error: "SardisClient not initialized. Please provide a client instance."
                    };
                }

                const effectiveWalletId = walletId || defaultWalletId;
                if (!effectiveWalletId) {
                    return {
                        success: false,
                        error: "No wallet ID provided. Set walletId in options or SARDIS_WALLET_ID env var."
                    };
                }

                try {
                    const effectiveToken = token || defaultToken;
                    const effectiveChain = chain || defaultChain;
                    const effectiveDomain = domain || vendor;

                    if (!vendorAddress) {
                        return {
                            success: false,
                            error: "Missing vendorAddress (destination). Provide a wallet address (0x...) for the vendor."
                        };
                    }

                    const result = await sardis.wallets.transfer(effectiveWalletId, {
                        destination: vendorAddress,
                        amount: amount.toString(),
                        token: effectiveToken,
                        chain: effectiveChain,
                        domain: effectiveDomain,
                        memo: purpose,
                    });

                    return {
                        success: true,
                        status: result.status,
                        transactionHash: result.tx_hash,
                        chain: result.chain,
                        auditAnchor: result.audit_anchor,
                        message: `Payment of $${amount} ${effectiveToken} to ${vendor} ${result.status === 'completed' ? 'completed' : 'initiated'} successfully.`
                    };
                } catch (error: unknown) {
                    const errorMessage = error instanceof Error ? error.message : 'Payment failed';

                    // Check if this is a policy violation
                    if (errorMessage.includes('policy') || errorMessage.includes('blocked') || errorMessage.includes('limit')) {
                        return {
                            success: false,
                            blocked: true,
                            error: errorMessage,
                            message: `Payment to ${vendor} was blocked by spending policy: ${errorMessage}`
                        };
                    }

                    return {
                        success: false,
                        error: errorMessage
                    };
                }
            },
        },

        /**
         * Check wallet balance before making a payment.
         */
        checkBalance: {
            description: 'Check the current balance of a Sardis wallet.',
            parameters: z.object({
                walletId: z.string().optional().describe('The wallet ID to check. Defaults to configured wallet.'),
                token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().describe('The token to check balance for.'),
                chain: z.string().optional().describe('The chain to check balance on.'),
            }),
            execute: async ({
                walletId,
                token,
                chain
            }: {
                walletId?: string;
                token?: 'USDC' | 'USDT' | 'PYUSD' | 'EURC';
                chain?: string;
            }) => {
                if (!sardis) {
                    return {
                        success: false,
                        error: "SardisClient not initialized"
                    };
                }

                const effectiveWalletId = walletId || defaultWalletId;
                if (!effectiveWalletId) {
                    return {
                        success: false,
                        error: "No wallet ID provided"
                    };
                }

                try {
                    const balance = await sardis.wallets.getBalance(
                        effectiveWalletId,
                        chain || defaultChain,
                        token || defaultToken
                    );

                    return {
                        success: true,
                        walletId: balance.wallet_id,
                        balance: balance.balance,
                        token: balance.token,
                        chain: balance.chain,
                        address: balance.address
                    };
                } catch (error: unknown) {
                    return {
                        success: false,
                        error: error instanceof Error ? error.message : 'Failed to get balance'
                    };
                }
            },
        },

        /**
         * Get wallet information.
         */
        getWallet: {
            description: 'Get information about a Sardis wallet including spending limits.',
            parameters: z.object({
                walletId: z.string().optional().describe('The wallet ID to get info for. Defaults to configured wallet.'),
            }),
            execute: async ({ walletId }: { walletId?: string }) => {
                if (!sardis) {
                    return {
                        success: false,
                        error: "SardisClient not initialized"
                    };
                }

                const effectiveWalletId = walletId || defaultWalletId;
                if (!effectiveWalletId) {
                    return {
                        success: false,
                        error: "No wallet ID provided"
                    };
                }

                try {
                    const wallet = await sardis.wallets.get(effectiveWalletId);

                    return {
                        success: true,
                        wallet: {
                            id: wallet.id,
                            agentId: wallet.agent_id,
                            currency: wallet.currency,
                            limitPerTx: wallet.limit_per_tx,
                            limitTotal: wallet.limit_total,
                            isActive: wallet.is_active,
                            addresses: wallet.addresses
                        }
                    };
                } catch (error: unknown) {
                    return {
                        success: false,
                        error: error instanceof Error ? error.message : 'Failed to get wallet'
                    };
                }
            },
        },
    };
};
