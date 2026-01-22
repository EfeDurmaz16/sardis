/**
 * LangChain.js Integration for Sardis SDK
 *
 * Provides LangChain-compatible tools for AI agents to execute payments
 * through Sardis MPC wallets with policy enforcement.
 *
 * @example
 * ```typescript
 * import { ChatOpenAI } from '@langchain/openai';
 * import { AgentExecutor, createOpenAIFunctionsAgent } from 'langchain/agents';
 * import { SardisClient } from '@sardis/sdk';
 * import { createSardisLangChainTools } from '@sardis/sdk/integrations/langchain';
 *
 * const client = new SardisClient({ apiKey: 'your-api-key' });
 * const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
 *
 * const agent = await createOpenAIFunctionsAgent({
 *   llm: new ChatOpenAI(),
 *   tools,
 *   prompt: yourPrompt
 * });
 *
 * const executor = new AgentExecutor({ agent, tools });
 * const result = await executor.invoke({ input: 'Pay $50 to OpenAI' });
 * ```
 */

import { SardisClient } from '../client.js';
import type { ExecutePaymentResponse, WalletBalance, Wallet } from '../types.js';

/**
 * Options for creating Sardis LangChain tools
 */
export interface SardisLangChainOptions {
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
 * LangChain tool interface
 */
interface LangChainTool {
    name: string;
    description: string;
    schema: {
        type: 'object';
        properties: Record<string, unknown>;
        required?: string[];
    };
    func: (input: Record<string, unknown>) => Promise<string>;
}

/**
 * Generate a unique mandate ID
 */
function generateMandateId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 10);
    return `mnd_${timestamp}${random}`;
}

/**
 * Create a SHA-256 hash for audit purposes
 */
async function createAuditHash(data: string): Promise<string> {
    if (typeof crypto !== 'undefined' && crypto.subtle) {
        const encoder = new TextEncoder();
        const dataBuffer = encoder.encode(data);
        const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    return `hash_${Date.now().toString(16)}`;
}

/**
 * Create LangChain-compatible tools for Sardis payments.
 *
 * @param client - Initialized SardisClient instance
 * @param options - Configuration options
 * @returns Array of LangChain-compatible tools
 */
export function createSardisLangChainTools(
    client: SardisClient,
    options: SardisLangChainOptions = {}
): LangChainTool[] {
    const defaultWalletId = options.walletId || process.env.SARDIS_WALLET_ID || '';
    const defaultAgentId = options.agentId || process.env.SARDIS_AGENT_ID || '';
    const defaultChain = options.chain || 'base_sepolia';
    const defaultToken = options.token || 'USDC';

    const tools: LangChainTool[] = [
        {
            name: 'sardis_pay',
            description: 'Execute a secure payment using Sardis MPC wallet. Validates against spending policies. Use this when the user wants to pay a vendor or service.',
            schema: {
                type: 'object',
                properties: {
                    amount: {
                        type: 'number',
                        description: 'The amount to pay in USD (or token units)'
                    },
                    vendor: {
                        type: 'string',
                        description: 'The name of the merchant or service provider'
                    },
                    vendor_address: {
                        type: 'string',
                        description: 'The wallet address of the vendor (0x...). Optional - will resolve if not provided.'
                    },
                    purpose: {
                        type: 'string',
                        description: 'The reason for the payment, used for policy validation'
                    },
                    token: {
                        type: 'string',
                        enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
                        description: 'The stablecoin to use. Defaults to USDC.'
                    }
                },
                required: ['amount', 'vendor']
            },
            func: async (input: Record<string, unknown>): Promise<string> => {
                const amount = input.amount as number;
                const vendor = input.vendor as string;
                const vendorAddress = input.vendor_address as string | undefined;
                const purpose = input.purpose as string | undefined;
                const token = (input.token as 'USDC' | 'USDT' | 'PYUSD' | 'EURC') || defaultToken;

                if (!defaultWalletId) {
                    return JSON.stringify({
                        success: false,
                        error: 'No wallet ID configured. Set walletId in options or SARDIS_WALLET_ID env var.'
                    });
                }

                try {
                    const mandateId = generateMandateId();
                    const timestamp = new Date().toISOString();
                    const amountMinor = Math.round(amount * 1_000_000).toString();

                    const auditData = JSON.stringify({
                        mandate_id: mandateId,
                        subject: defaultWalletId,
                        destination: vendorAddress || `pending:${vendor}`,
                        amount_minor: amountMinor,
                        token,
                        purpose: purpose || `Payment to ${vendor}`,
                        timestamp
                    });
                    const auditHash = await createAuditHash(auditData);

                    const mandate = {
                        mandate_id: mandateId,
                        subject: defaultWalletId,
                        destination: vendorAddress || `pending:${vendor}`,
                        amount_minor: amountMinor,
                        token,
                        chain: defaultChain,
                        purpose: purpose || `Payment to ${vendor}`,
                        vendor_name: vendor,
                        agent_id: defaultAgentId,
                        timestamp,
                        audit_hash: auditHash,
                        metadata: {
                            vendor,
                            category: 'saas',
                            initiated_by: 'ai_agent',
                            tool: 'langchain_js'
                        }
                    };

                    const result: ExecutePaymentResponse = await client.payments.executeMandate(mandate);

                    return JSON.stringify({
                        success: true,
                        status: result.status,
                        payment_id: result.payment_id,
                        transaction_hash: result.tx_hash,
                        chain: result.chain,
                        ledger_tx_id: result.ledger_tx_id,
                        message: `Payment of $${amount} ${token} to ${vendor} ${result.status === 'completed' ? 'completed' : 'initiated'}.`
                    });
                } catch (error: unknown) {
                    const errorMessage = error instanceof Error ? error.message : 'Payment failed';

                    if (errorMessage.includes('policy') || errorMessage.includes('blocked') || errorMessage.includes('limit')) {
                        return JSON.stringify({
                            success: false,
                            blocked: true,
                            error: errorMessage,
                            message: `Payment to ${vendor} blocked by policy: ${errorMessage}`
                        });
                    }

                    return JSON.stringify({
                        success: false,
                        error: errorMessage
                    });
                }
            }
        },

        {
            name: 'sardis_check_balance',
            description: 'Check the current balance of a Sardis wallet. Use this before making payments to ensure sufficient funds.',
            schema: {
                type: 'object',
                properties: {
                    token: {
                        type: 'string',
                        enum: ['USDC', 'USDT', 'PYUSD', 'EURC'],
                        description: 'The token to check balance for. Defaults to USDC.'
                    },
                    chain: {
                        type: 'string',
                        description: 'The blockchain to check balance on. Defaults to base_sepolia.'
                    }
                }
            },
            func: async (input: Record<string, unknown>): Promise<string> => {
                const token = (input.token as 'USDC' | 'USDT' | 'PYUSD' | 'EURC') || defaultToken;
                const chain = (input.chain as string) || defaultChain;

                if (!defaultWalletId) {
                    return JSON.stringify({
                        success: false,
                        error: 'No wallet ID configured'
                    });
                }

                try {
                    const balance: WalletBalance = await client.wallets.getBalance(
                        defaultWalletId,
                        chain,
                        token
                    );

                    return JSON.stringify({
                        success: true,
                        wallet_id: balance.wallet_id,
                        balance: balance.balance,
                        token: balance.token,
                        chain: balance.chain,
                        address: balance.address
                    });
                } catch (error: unknown) {
                    return JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Failed to get balance'
                    });
                }
            }
        },

        {
            name: 'sardis_get_wallet',
            description: 'Get information about the Sardis wallet including spending limits and policy settings.',
            schema: {
                type: 'object',
                properties: {}
            },
            func: async (): Promise<string> => {
                if (!defaultWalletId) {
                    return JSON.stringify({
                        success: false,
                        error: 'No wallet ID configured'
                    });
                }

                try {
                    const wallet: Wallet = await client.wallets.get(defaultWalletId);

                    return JSON.stringify({
                        success: true,
                        wallet: {
                            id: wallet.id,
                            agent_id: wallet.agent_id,
                            currency: wallet.currency,
                            limit_per_tx: wallet.limit_per_tx,
                            limit_total: wallet.limit_total,
                            is_active: wallet.is_active,
                            addresses: wallet.addresses
                        }
                    });
                } catch (error: unknown) {
                    return JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Failed to get wallet'
                    });
                }
            }
        },

        {
            name: 'sardis_check_policy',
            description: 'Check if a payment would be allowed by the spending policy without executing it. Use this to validate payments before execution.',
            schema: {
                type: 'object',
                properties: {
                    amount: {
                        type: 'number',
                        description: 'The amount to pay in USD'
                    },
                    vendor: {
                        type: 'string',
                        description: 'The name of the merchant or service provider'
                    },
                    purpose: {
                        type: 'string',
                        description: 'The reason for the payment'
                    }
                },
                required: ['amount', 'vendor']
            },
            func: async (input: Record<string, unknown>): Promise<string> => {
                const amount = input.amount as number;
                const vendor = input.vendor as string;
                const purpose = input.purpose as string | undefined;

                if (!defaultWalletId) {
                    return JSON.stringify({
                        success: false,
                        error: 'No wallet ID configured'
                    });
                }

                try {
                    // Get wallet to check limits
                    const wallet: Wallet = await client.wallets.get(defaultWalletId);
                    const limitPerTx = parseFloat(wallet.limit_per_tx);
                    const limitTotal = parseFloat(wallet.limit_total);

                    // Basic policy checks
                    const checks: { name: string; passed: boolean; reason?: string }[] = [];

                    // Per-transaction limit check
                    if (amount <= limitPerTx) {
                        checks.push({ name: 'per_transaction_limit', passed: true });
                    } else {
                        checks.push({
                            name: 'per_transaction_limit',
                            passed: false,
                            reason: `Amount $${amount} exceeds per-transaction limit of $${limitPerTx}`
                        });
                    }

                    // Wallet active check
                    if (wallet.is_active) {
                        checks.push({ name: 'wallet_active', passed: true });
                    } else {
                        checks.push({
                            name: 'wallet_active',
                            passed: false,
                            reason: 'Wallet is not active'
                        });
                    }

                    const allPassed = checks.every(c => c.passed);

                    return JSON.stringify({
                        success: true,
                        allowed: allPassed,
                        checks,
                        summary: allPassed
                            ? `Payment of $${amount} to ${vendor} would be allowed`
                            : `Payment of $${amount} to ${vendor} would be blocked: ${checks.filter(c => !c.passed).map(c => c.reason).join('; ')}`
                    });
                } catch (error: unknown) {
                    return JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Failed to check policy'
                    });
                }
            }
        }
    ];

    return tools;
}

/**
 * Create a single LangChain tool for payments only.
 * Use this if you only need the payment functionality.
 */
export function createSardisPaymentTool(
    client: SardisClient,
    options: SardisLangChainOptions = {}
): LangChainTool {
    const tools = createSardisLangChainTools(client, options);
    return tools.find(t => t.name === 'sardis_pay')!;
}

export type { LangChainTool };
