import { z } from 'zod';
import { SardisClient } from '../client.js';
import type { ExecutePaymentResponse } from '../types.js';

/**
 * Generate a unique mandate ID
 */
function generateMandateId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 10);
    return `mnd_${timestamp}${random}`;
}

/**
 * Create a SHA-256 hash for audit purposes (browser-compatible)
 */
async function createAuditHash(data: string): Promise<string> {
    if (typeof crypto !== 'undefined' && crypto.subtle) {
        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(data);
        const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    // Fallback for environments without crypto.subtle
    return `hash_${Date.now().toString(16)}`;
}

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
    const defaultAgentId = options.agentId || process.env.SARDIS_AGENT_ID || '';
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
                vendorAddress: z.string().optional().describe('The wallet address of the vendor (0x...). If not provided, will attempt to resolve.'),
                purpose: z.string().optional().describe('The reason for the payment, used for policy validation.'),
                walletId: z.string().optional().describe('The wallet ID to pay from. Defaults to configured wallet.'),
                token: z.enum(['USDC', 'USDT', 'PYUSD', 'EURC']).optional().describe('The stablecoin to use. Defaults to USDC.'),
            }),
            execute: async ({
                amount,
                vendor,
                vendorAddress,
                purpose,
                walletId,
                token
            }: {
                amount: number;
                vendor: string;
                vendorAddress?: string;
                purpose?: string;
                walletId?: string;
                token?: 'USDC' | 'USDT' | 'PYUSD' | 'EURC';
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
                    // Build the payment mandate
                    const mandateId = generateMandateId();
                    const timestamp = new Date().toISOString();
                    const effectiveToken = token || defaultToken;

                    // Convert amount to minor units (6 decimals for USDC/USDT)
                    const amountMinor = Math.round(amount * 1_000_000).toString();

                    // Create audit hash from mandate data
                    const auditData = JSON.stringify({
                        mandate_id: mandateId,
                        subject: effectiveWalletId,
                        destination: vendorAddress || `pending:${vendor}`,
                        amount_minor: amountMinor,
                        token: effectiveToken,
                        purpose: purpose || `Payment to ${vendor}`,
                        timestamp
                    });
                    const auditHash = await createAuditHash(auditData);

                    // Build mandate structure matching sardis_v2_core.mandates.PaymentMandate
                    const mandate = {
                        mandate_id: mandateId,
                        subject: effectiveWalletId,
                        destination: vendorAddress || `pending:${vendor}`,
                        amount_minor: amountMinor,
                        token: effectiveToken,
                        chain: defaultChain,
                        purpose: purpose || `Payment to ${vendor}`,
                        vendor_name: vendor,
                        agent_id: defaultAgentId,
                        timestamp,
                        audit_hash: auditHash,
                        // Policy metadata for validation
                        metadata: {
                            vendor,
                            category: 'saas', // Default category
                            initiated_by: 'ai_agent',
                            tool: 'vercel_ai_sdk'
                        }
                    };

                    // Execute the mandate via API
                    const result: ExecutePaymentResponse = await sardis.payments.executeMandate(mandate);

                    return {
                        success: true,
                        status: result.status,
                        paymentId: result.payment_id,
                        transactionHash: result.tx_hash,
                        chain: result.chain,
                        ledgerTxId: result.ledger_tx_id,
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
