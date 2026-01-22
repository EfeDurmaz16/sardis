/**
 * Tests for LangChain.js Integration
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../../src/client.js';
import { createSardisLangChainTools, createSardisPaymentTool } from '../../src/integrations/langchain.js';
import { server } from '../setup.js';
import { http, HttpResponse } from 'msw';

describe('LangChain Integration', () => {
    let client: SardisClient;

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-key' });
    });

    describe('createSardisLangChainTools', () => {
        it('should create array of tools', () => {
            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });

            expect(Array.isArray(tools)).toBe(true);
            expect(tools.length).toBeGreaterThan(0);
        });

        it('should include all required tools', () => {
            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const toolNames = tools.map(t => t.name);

            expect(toolNames).toContain('sardis_pay');
            expect(toolNames).toContain('sardis_check_balance');
            expect(toolNames).toContain('sardis_get_wallet');
            expect(toolNames).toContain('sardis_check_policy');
        });

        it('should have correct LangChain tool structure', () => {
            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });

            for (const tool of tools) {
                expect(tool).toHaveProperty('name');
                expect(tool).toHaveProperty('description');
                expect(tool).toHaveProperty('schema');
                expect(tool).toHaveProperty('func');
                expect(typeof tool.name).toBe('string');
                expect(typeof tool.description).toBe('string');
                expect(typeof tool.func).toBe('function');
                expect(tool.schema.type).toBe('object');
            }
        });
    });

    describe('sardis_pay tool', () => {
        it('should execute payment successfully', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json({
                        status: 'completed',
                        payment_id: 'pay_123',
                        tx_hash: '0xabc123',
                        chain: 'base_sepolia',
                        ledger_tx_id: 'ltx_456',
                    });
                })
            );

            const tools = createSardisLangChainTools(client, {
                walletId: 'wallet_123',
                agentId: 'agent_456',
            });
            const payTool = tools.find(t => t.name === 'sardis_pay')!;

            const result = await payTool.func({
                amount: 50,
                vendor: 'OpenAI',
                purpose: 'API subscription',
            });

            const parsed = JSON.parse(result);
            expect(parsed.success).toBe(true);
            expect(parsed.status).toBe('completed');
            expect(parsed.payment_id).toBe('pay_123');
        });

        it('should return JSON string', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json({
                        status: 'completed',
                        payment_id: 'pay_123',
                    });
                })
            );

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const payTool = tools.find(t => t.name === 'sardis_pay')!;

            const result = await payTool.func({ amount: 50, vendor: 'Test' });

            expect(typeof result).toBe('string');
            expect(() => JSON.parse(result)).not.toThrow();
        });

        it('should return error when no wallet ID', async () => {
            const tools = createSardisLangChainTools(client);
            const payTool = tools.find(t => t.name === 'sardis_pay')!;

            const result = await payTool.func({ amount: 50, vendor: 'Test' });
            const parsed = JSON.parse(result);

            expect(parsed.success).toBe(false);
            expect(parsed.error).toContain('wallet ID');
        });

        it('should handle policy violation', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        { error: 'Payment blocked by policy' },
                        { status: 403 }
                    );
                })
            );

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const payTool = tools.find(t => t.name === 'sardis_pay')!;

            const result = await payTool.func({ amount: 10000, vendor: 'Expensive' });
            const parsed = JSON.parse(result);

            expect(parsed.success).toBe(false);
        });

        it('should have required parameters in schema', () => {
            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const payTool = tools.find(t => t.name === 'sardis_pay')!;

            expect(payTool.schema.required).toContain('amount');
            expect(payTool.schema.required).toContain('vendor');
        });
    });

    describe('sardis_check_balance tool', () => {
        it('should check balance successfully', async () => {
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

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const balanceTool = tools.find(t => t.name === 'sardis_check_balance')!;

            const result = await balanceTool.func({});
            const parsed = JSON.parse(result);

            expect(parsed.success).toBe(true);
            expect(parsed.balance).toBe('1000.00');
        });

        it('should respect token and chain parameters', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    return HttpResponse.json({
                        wallet_id: 'wallet_123',
                        balance: '500.00',
                        token: url.searchParams.get('token'),
                        chain: url.searchParams.get('chain'),
                    });
                })
            );

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const balanceTool = tools.find(t => t.name === 'sardis_check_balance')!;

            const result = await balanceTool.func({ token: 'USDT', chain: 'polygon' });
            const parsed = JSON.parse(result);

            expect(parsed.token).toBe('USDT');
            expect(parsed.chain).toBe('polygon');
        });
    });

    describe('sardis_get_wallet tool', () => {
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
                        addresses: { base: '0x123' },
                    });
                })
            );

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const walletTool = tools.find(t => t.name === 'sardis_get_wallet')!;

            const result = await walletTool.func({});
            const parsed = JSON.parse(result);

            expect(parsed.success).toBe(true);
            expect(parsed.wallet.id).toBe('wallet_123');
            expect(parsed.wallet.is_active).toBe(true);
        });
    });

    describe('sardis_check_policy tool', () => {
        it('should check policy successfully', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json({
                        id: 'wallet_123',
                        limit_per_tx: '1000.00',
                        limit_total: '10000.00',
                        is_active: true,
                    });
                })
            );

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const policyTool = tools.find(t => t.name === 'sardis_check_policy')!;

            const result = await policyTool.func({
                amount: 50,
                vendor: 'OpenAI',
            });
            const parsed = JSON.parse(result);

            expect(parsed.success).toBe(true);
            expect(parsed.allowed).toBe(true);
        });

        it('should detect policy violation', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json({
                        id: 'wallet_123',
                        limit_per_tx: '100.00',
                        limit_total: '1000.00',
                        is_active: true,
                    });
                })
            );

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const policyTool = tools.find(t => t.name === 'sardis_check_policy')!;

            const result = await policyTool.func({
                amount: 500,
                vendor: 'ExpensiveService',
            });
            const parsed = JSON.parse(result);

            expect(parsed.success).toBe(true);
            expect(parsed.allowed).toBe(false);
            expect(parsed.checks.some((c: any) => c.name === 'per_transaction_limit' && !c.passed)).toBe(true);
        });

        it('should detect inactive wallet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json({
                        id: 'wallet_123',
                        limit_per_tx: '1000.00',
                        limit_total: '10000.00',
                        is_active: false,
                    });
                })
            );

            const tools = createSardisLangChainTools(client, { walletId: 'wallet_123' });
            const policyTool = tools.find(t => t.name === 'sardis_check_policy')!;

            const result = await policyTool.func({
                amount: 50,
                vendor: 'OpenAI',
            });
            const parsed = JSON.parse(result);

            expect(parsed.allowed).toBe(false);
            expect(parsed.checks.some((c: any) => c.name === 'wallet_active' && !c.passed)).toBe(true);
        });
    });

    describe('createSardisPaymentTool', () => {
        it('should return only the payment tool', () => {
            const tool = createSardisPaymentTool(client, { walletId: 'wallet_123' });

            expect(tool.name).toBe('sardis_pay');
            expect(tool.func).toBeDefined();
        });

        it('should execute payment', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json({
                        status: 'completed',
                        payment_id: 'pay_single',
                    });
                })
            );

            const tool = createSardisPaymentTool(client, { walletId: 'wallet_123' });
            const result = await tool.func({ amount: 25, vendor: 'Vercel' });
            const parsed = JSON.parse(result);

            expect(parsed.success).toBe(true);
            expect(parsed.payment_id).toBe('pay_single');
        });
    });
});
