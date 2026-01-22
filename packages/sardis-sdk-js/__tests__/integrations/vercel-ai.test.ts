/**
 * Tests for Vercel AI SDK Integration
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../../src/client.js';
import { createSardisTools } from '../../src/integrations/vercel-ai.js';
import { server } from '../setup.js';
import { http, HttpResponse } from 'msw';

describe('Vercel AI Integration', () => {
    let client: SardisClient;

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-key' });
    });

    describe('createSardisTools', () => {
        it('should create tools object with all tools', () => {
            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            expect(tools).toHaveProperty('payVendor');
            expect(tools).toHaveProperty('checkBalance');
            expect(tools).toHaveProperty('getWallet');
        });

        it('should create tools without client (lazy initialization)', () => {
            const tools = createSardisTools(undefined, { walletId: 'wallet_123' });

            expect(tools).toBeDefined();
            expect(tools.payVendor).toBeDefined();
        });
    });

    describe('payVendor tool', () => {
        it('should have correct structure', () => {
            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            expect(tools.payVendor.description).toBeDefined();
            expect(tools.payVendor.parameters).toBeDefined();
            expect(typeof tools.payVendor.execute).toBe('function');
        });

        it('should execute payment successfully', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json({
                        status: 'completed',
                        payment_id: 'pay_123',
                        tx_hash: '0xabc123',
                        chain: 'base_sepolia',
                        ledger_tx_id: 'ltx_456',
                        audit_anchor: 'anchor_789',
                    });
                })
            );

            const tools = createSardisTools(client, {
                walletId: 'wallet_123',
                agentId: 'agent_456',
            });

            const result = await tools.payVendor.execute({
                amount: 50,
                vendor: 'OpenAI',
                purpose: 'API credits',
            });

            expect(result.success).toBe(true);
            expect(result.status).toBe('completed');
            expect(result.paymentId).toBe('pay_123');
            expect(result.transactionHash).toBe('0xabc123');
        });

        it('should return error when client not initialized', async () => {
            const tools = createSardisTools(undefined, { walletId: 'wallet_123' });

            const result = await tools.payVendor.execute({
                amount: 50,
                vendor: 'OpenAI',
            });

            expect(result.success).toBe(false);
            expect(result.error).toContain('not initialized');
        });

        it('should return error when no wallet ID provided', async () => {
            const tools = createSardisTools(client);

            const result = await tools.payVendor.execute({
                amount: 50,
                vendor: 'OpenAI',
            });

            expect(result.success).toBe(false);
            expect(result.error).toContain('No wallet ID');
        });

        it('should handle policy violation', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        { error: 'Payment blocked by policy: Amount exceeds limit' },
                        { status: 403 }
                    );
                })
            );

            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            const result = await tools.payVendor.execute({
                amount: 10000,
                vendor: 'ExpensiveVendor',
            });

            expect(result.success).toBe(false);
        });

        it('should use provided vendorAddress', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.network/api/v2/mandates/execute',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json({
                            status: 'completed',
                            payment_id: 'pay_123',
                        });
                    }
                )
            );

            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            await tools.payVendor.execute({
                amount: 50,
                vendor: 'OpenAI',
                vendorAddress: '0xvendor123456789',
            });

            expect(receivedBody.mandate.destination).toBe('0xvendor123456789');
        });

        it('should use pending prefix when no vendorAddress', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.network/api/v2/mandates/execute',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json({
                            status: 'completed',
                            payment_id: 'pay_123',
                        });
                    }
                )
            );

            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            await tools.payVendor.execute({
                amount: 50,
                vendor: 'GitHub',
            });

            expect(receivedBody.mandate.destination).toContain('pending:');
            expect(receivedBody.mandate.destination).toContain('GitHub');
        });
    });

    describe('checkBalance tool', () => {
        it('should check wallet balance', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', () => {
                    return HttpResponse.json({
                        wallet_id: 'wallet_123',
                        balance: '1000.00',
                        token: 'USDC',
                        chain: 'base_sepolia',
                        address: '0x123abc',
                    });
                })
            );

            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            const result = await tools.checkBalance.execute({});

            expect(result.success).toBe(true);
            expect(result.balance).toBe('1000.00');
            expect(result.token).toBe('USDC');
        });

        it('should check balance with custom token and chain', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    const token = url.searchParams.get('token');
                    const chain = url.searchParams.get('chain');
                    return HttpResponse.json({
                        wallet_id: 'wallet_123',
                        balance: '500.00',
                        token,
                        chain,
                        address: '0x456def',
                    });
                })
            );

            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            const result = await tools.checkBalance.execute({
                token: 'USDT',
                chain: 'polygon',
            });

            expect(result.success).toBe(true);
            expect(result.token).toBe('USDT');
            expect(result.chain).toBe('polygon');
        });

        it('should return error when no wallet ID', async () => {
            const tools = createSardisTools(client);

            const result = await tools.checkBalance.execute({});

            expect(result.success).toBe(false);
            expect(result.error).toContain('No wallet ID');
        });
    });

    describe('getWallet tool', () => {
        it('should get wallet information', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json({
                        id: 'wallet_123',
                        agent_id: 'agent_456',
                        currency: 'USD',
                        limit_per_tx: '1000.00',
                        limit_total: '10000.00',
                        is_active: true,
                        addresses: {
                            base: '0x123',
                            polygon: '0x456',
                        },
                    });
                })
            );

            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            const result = await tools.getWallet.execute({});

            expect(result.success).toBe(true);
            expect(result.wallet).toBeDefined();
            expect(result.wallet.id).toBe('wallet_123');
            expect(result.wallet.isActive).toBe(true);
        });

        it('should use provided wallet ID', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', ({ params }) => {
                    return HttpResponse.json({
                        id: params.id,
                        agent_id: 'agent_789',
                        currency: 'USD',
                        is_active: true,
                    });
                })
            );

            const tools = createSardisTools(client, { walletId: 'wallet_123' });

            const result = await tools.getWallet.execute({ walletId: 'wallet_other' });

            expect(result.success).toBe(true);
            expect(result.wallet.id).toBe('wallet_other');
        });
    });

    describe('options', () => {
        it('should use default chain from options', async () => {
            let requestedChain: string | null = null;
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    requestedChain = url.searchParams.get('chain');
                    return HttpResponse.json({
                        wallet_id: 'wallet_123',
                        balance: '100.00',
                        token: 'USDC',
                        chain: requestedChain,
                    });
                })
            );

            const tools = createSardisTools(client, {
                walletId: 'wallet_123',
                chain: 'polygon',
            });

            await tools.checkBalance.execute({});

            expect(requestedChain).toBe('polygon');
        });

        it('should use default token from options', async () => {
            let requestedToken: string | null = null;
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    requestedToken = url.searchParams.get('token');
                    return HttpResponse.json({
                        wallet_id: 'wallet_123',
                        balance: '100.00',
                        token: requestedToken,
                        chain: 'base_sepolia',
                    });
                })
            );

            const tools = createSardisTools(client, {
                walletId: 'wallet_123',
                token: 'USDT',
            });

            await tools.checkBalance.execute({});

            expect(requestedToken).toBe('USDT');
        });
    });
});
