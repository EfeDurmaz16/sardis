/**
 * OpenAI Function Calling Integration for Sardis SDK
 *
 * Provides OpenAI-compatible function schemas and execution handlers
 * for AI agents to execute payments through Sardis MPC wallets.
 *
 * @example
 * ```typescript
 * import OpenAI from 'openai';
 * import { SardisClient } from '@sardis/sdk';
 * import { createSardisOpenAITools, handleSardisFunctionCall } from '@sardis/sdk/integrations/openai';
 *
 * const sardis = new SardisClient({ apiKey: 'your-api-key' });
 * const openai = new OpenAI();
 *
 * const tools = createSardisOpenAITools();
 *
 * const response = await openai.chat.completions.create({
 *   model: 'gpt-4',
 *   messages: [{ role: 'user', content: 'Pay $50 to OpenAI' }],
 *   tools
 * });
 *
 * // Handle tool calls
 * for (const toolCall of response.choices[0].message.tool_calls || []) {
 *   const result = await handleSardisFunctionCall(sardis, toolCall, { walletId: 'wallet_123' });
 *   console.log(result);
 * }
 * ```
 */

import { SardisClient } from '../client.js';
import type { ExecutePaymentResponse, WalletBalance, Wallet } from '../types.js';

/**
 * OpenAI tool definition
 */
export interface OpenAITool {
    type: 'function';
    function: {
        name: string;
        description: string;
        parameters: {
            type: 'object';
            properties: Record<string, {
                type: string;
                description: string;
                enum?: string[];
            }>;
            required?: string[];
        };
    };
}

/**
 * OpenAI function call from response
 */
export interface OpenAIFunctionCall {
    id: string;
    type: 'function';
    function: {
        name: string;
        arguments: string;
    };
}

/**
 * Options for Sardis OpenAI integration
 */
export interface SardisOpenAIOptions {
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
 * Create OpenAI-compatible tool definitions for Sardis functions.
 * Use these with the OpenAI Chat Completions API.
 */
export function createSardisOpenAITools(): OpenAITool[] {
    return [
        {
            type: 'function',
            function: {
                name: 'sardis_pay',
                description: 'Execute a secure payment using Sardis MPC wallet. Validates against spending policies before execution. Returns transaction details on success or error message if blocked by policy.',
                parameters: {
                    type: 'object',
                    properties: {
                        amount: {
                            type: 'number',
                            description: 'The amount to pay in USD (or token units)'
                        },
                        vendor: {
                            type: 'string',
                            description: 'The name of the merchant or service provider (e.g., "OpenAI", "GitHub", "Vercel")'
                        },
                        vendor_address: {
                            type: 'string',
                            description: 'The wallet address of the vendor (0x...). Optional - will be resolved if not provided.'
                        },
                        purpose: {
                            type: 'string',
                            description: 'The reason for the payment, used for policy validation and audit trail'
                        },
                        token: {
                            type: 'string',
                            description: 'The stablecoin to use for payment. Defaults to USDC.',
                            enum: ['USDC', 'USDT', 'PYUSD', 'EURC']
                        }
                    },
                    required: ['amount', 'vendor']
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'sardis_check_balance',
                description: 'Check the current balance of the Sardis wallet. Use this before making payments to ensure sufficient funds are available.',
                parameters: {
                    type: 'object',
                    properties: {
                        token: {
                            type: 'string',
                            description: 'The token to check balance for. Defaults to USDC.',
                            enum: ['USDC', 'USDT', 'PYUSD', 'EURC']
                        },
                        chain: {
                            type: 'string',
                            description: 'The blockchain to check balance on (e.g., "base", "polygon", "ethereum")'
                        }
                    }
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'sardis_get_wallet',
                description: 'Get information about the Sardis wallet including spending limits, policy settings, and configured addresses.',
                parameters: {
                    type: 'object',
                    properties: {}
                }
            }
        },
        {
            type: 'function',
            function: {
                name: 'sardis_check_policy',
                description: 'Check if a payment would be allowed by the spending policy without executing it. Use this to validate payments before execution.',
                parameters: {
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
                }
            }
        }
    ];
}

/**
 * Handle an OpenAI function call and execute the corresponding Sardis operation.
 *
 * @param client - Initialized SardisClient instance
 * @param toolCall - The tool call from OpenAI response
 * @param options - Configuration options including walletId
 * @returns JSON string with the result
 */
export async function handleSardisFunctionCall(
    client: SardisClient,
    toolCall: OpenAIFunctionCall,
    options: SardisOpenAIOptions = {}
): Promise<string> {
    const { function: func } = toolCall;
    const args = JSON.parse(func.arguments);

    const defaultWalletId = options.walletId || process.env.SARDIS_WALLET_ID || '';
    const defaultAgentId = options.agentId || process.env.SARDIS_AGENT_ID || '';
    const defaultChain = options.chain || 'base_sepolia';
    const defaultToken = options.token || 'USDC';

    switch (func.name) {
        case 'sardis_pay':
            return handlePayment(client, args, {
                walletId: defaultWalletId,
                agentId: defaultAgentId,
                chain: defaultChain,
                token: defaultToken
            });

        case 'sardis_check_balance':
            return handleCheckBalance(client, args, {
                walletId: defaultWalletId,
                chain: defaultChain,
                token: defaultToken
            });

        case 'sardis_get_wallet':
            return handleGetWallet(client, defaultWalletId);

        case 'sardis_check_policy':
            return handleCheckPolicy(client, args, defaultWalletId);

        default:
            return JSON.stringify({
                success: false,
                error: `Unknown function: ${func.name}`
            });
    }
}

async function handlePayment(
    client: SardisClient,
    args: Record<string, unknown>,
    options: Required<SardisOpenAIOptions>
): Promise<string> {
    const { walletId, agentId, chain, token: defaultToken } = options;

    if (!walletId) {
        return JSON.stringify({
            success: false,
            error: 'No wallet ID configured. Set walletId in options or SARDIS_WALLET_ID env var.'
        });
    }

    const amount = args.amount as number;
    const vendor = args.vendor as string;
    const vendorAddress = args.vendor_address as string | undefined;
    const purpose = args.purpose as string | undefined;
    const token = (args.token as 'USDC' | 'USDT' | 'PYUSD' | 'EURC') || defaultToken;

    try {
        const mandateId = generateMandateId();
        const timestamp = new Date().toISOString();
        const amountMinor = Math.round(amount * 1_000_000).toString();

        const auditData = JSON.stringify({
            mandate_id: mandateId,
            subject: walletId,
            destination: vendorAddress || `pending:${vendor}`,
            amount_minor: amountMinor,
            token,
            purpose: purpose || `Payment to ${vendor}`,
            timestamp
        });
        const auditHash = await createAuditHash(auditData);

        const mandate = {
            mandate_id: mandateId,
            subject: walletId,
            destination: vendorAddress || `pending:${vendor}`,
            amount_minor: amountMinor,
            token,
            chain,
            purpose: purpose || `Payment to ${vendor}`,
            vendor_name: vendor,
            agent_id: agentId,
            timestamp,
            audit_hash: auditHash,
            metadata: {
                vendor,
                category: 'saas',
                initiated_by: 'ai_agent',
                tool: 'openai_function_calling'
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
            audit_anchor: result.audit_anchor,
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

async function handleCheckBalance(
    client: SardisClient,
    args: Record<string, unknown>,
    options: { walletId: string; chain: string; token: string }
): Promise<string> {
    const { walletId } = options;

    if (!walletId) {
        return JSON.stringify({
            success: false,
            error: 'No wallet ID configured'
        });
    }

    const token = (args.token as string) || options.token;
    const chain = (args.chain as string) || options.chain;

    try {
        const balance: WalletBalance = await client.wallets.getBalance(
            walletId,
            chain,
            token as 'USDC' | 'USDT' | 'PYUSD' | 'EURC'
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

async function handleGetWallet(
    client: SardisClient,
    walletId: string
): Promise<string> {
    if (!walletId) {
        return JSON.stringify({
            success: false,
            error: 'No wallet ID configured'
        });
    }

    try {
        const wallet: Wallet = await client.wallets.get(walletId);

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

async function handleCheckPolicy(
    client: SardisClient,
    args: Record<string, unknown>,
    walletId: string
): Promise<string> {
    if (!walletId) {
        return JSON.stringify({
            success: false,
            error: 'No wallet ID configured'
        });
    }

    const amount = args.amount as number;
    const vendor = args.vendor as string;

    try {
        const wallet: Wallet = await client.wallets.get(walletId);
        const limitPerTx = parseFloat(wallet.limit_per_tx);

        const checks: { name: string; passed: boolean; reason?: string }[] = [];

        if (amount <= limitPerTx) {
            checks.push({ name: 'per_transaction_limit', passed: true });
        } else {
            checks.push({
                name: 'per_transaction_limit',
                passed: false,
                reason: `Amount $${amount} exceeds per-transaction limit of $${limitPerTx}`
            });
        }

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

/**
 * Helper to create tool response message for OpenAI conversation
 */
export function createToolResponse(toolCallId: string, content: string): {
    role: 'tool';
    tool_call_id: string;
    content: string;
} {
    return {
        role: 'tool',
        tool_call_id: toolCallId,
        content
    };
}

export type { OpenAITool, OpenAIFunctionCall, SardisOpenAIOptions };
