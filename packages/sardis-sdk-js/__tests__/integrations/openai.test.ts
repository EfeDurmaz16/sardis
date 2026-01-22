/**
 * Tests for OpenAI Function Calling Integration
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../../src/client.js';
import {
    createSardisOpenAITools,
    handleSardisFunctionCall,
    createToolResponse,
    type OpenAIFunctionCall
} from '../../src/integrations/openai.js';
import { server } from '../setup.js';
import { http, HttpResponse } from 'msw';

describe('OpenAI Integration', () => {
    let client: SardisClient;

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-key' });
    });

    describe('createSardisOpenAITools', () => {
        it('should create array of OpenAI tools', () => {
            const tools = createSardisOpenAITools();

            expect(Array.isArray(tools)).toBe(true);
            expect(tools.length).toBeGreaterThan(0);
        });

        it('should have correct OpenAI tool structure', () => {
            const tools = createSardisOpenAITools();

            for (const tool of tools) {
                expect(tool.type).toBe('function');
                expect(tool.function).toBeDefined();
                expect(tool.function.name).toBeDefined();
                expect(tool.function.description).toBeDefined();
                expect(tool.function.parameters).toBeDefined();
                expect(tool.function.parameters.type).toBe('object');
            }
        });

        it('should include all required functions', () => {
            const tools = createSardisOpenAITools();
            const names = tools.map(t => t.function.name);

            expect(names).toContain('sardis_pay');
            expect(names).toContain('sardis_check_balance');
            expect(names).toContain('sardis_get_wallet');
            expect(names).toContain('sardis_check_policy');
        });

        it('should have required parameters for sardis_pay', () => {
            const tools = createSardisOpenAITools();
            const payTool = tools.find(t => t.function.name === 'sardis_pay')!;

            expect(payTool.function.parameters.required).toContain('amount');
            expect(payTool.function.parameters.required).toContain('vendor');
        });

        it('should have token enum values', () => {
            const tools = createSardisOpenAITools();
            const payTool = tools.find(t => t.function.name === 'sardis_pay')!;

            const tokenProp = payTool.function.parameters.properties.token;
            expect(tokenProp.enum).toContain('USDC');
            expect(tokenProp.enum).toContain('USDT');
            expect(tokenProp.enum).toContain('PYUSD');
            expect(tokenProp.enum).toContain('EURC');
        });
    });

    describe('handleSardisFunctionCall', () => {
        describe('sardis_pay', () => {
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

                const toolCall: OpenAIFunctionCall = {
                    id: 'call_123',
                    type: 'function',
                    function: {
                        name: 'sardis_pay',
                        arguments: JSON.stringify({
                            amount: 50,
                            vendor: 'OpenAI',
                            purpose: 'API credits',
                        }),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
                    agentId: 'agent_456',
                });

                const parsed = JSON.parse(result);
                expect(parsed.success).toBe(true);
                expect(parsed.status).toBe('completed');
                expect(parsed.payment_id).toBe('pay_123');
            });

            it('should return error when no wallet ID', async () => {
                const toolCall: OpenAIFunctionCall = {
                    id: 'call_123',
                    type: 'function',
                    function: {
                        name: 'sardis_pay',
                        arguments: JSON.stringify({ amount: 50, vendor: 'Test' }),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall);
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

                const toolCall: OpenAIFunctionCall = {
                    id: 'call_123',
                    type: 'function',
                    function: {
                        name: 'sardis_pay',
                        arguments: JSON.stringify({ amount: 10000, vendor: 'Blocked' }),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
                });

                const parsed = JSON.parse(result);
                expect(parsed.success).toBe(false);
            });
        });

        describe('sardis_check_balance', () => {
            it('should check balance successfully', async () => {
                server.use(
                    http.get('https://api.sardis.network/api/v2/wallets/:id/balance', () => {
                        return HttpResponse.json({
                            wallet_id: 'wallet_123',
                            balance: '1000.00',
                            token: 'USDC',
                            chain: 'base_sepolia',
                            address: '0x123',
                        });
                    })
                );

                const toolCall: OpenAIFunctionCall = {
                    id: 'call_456',
                    type: 'function',
                    function: {
                        name: 'sardis_check_balance',
                        arguments: JSON.stringify({}),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
                });

                const parsed = JSON.parse(result);
                expect(parsed.success).toBe(true);
                expect(parsed.balance).toBe('1000.00');
            });

            it('should use specified token and chain', async () => {
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

                const toolCall: OpenAIFunctionCall = {
                    id: 'call_456',
                    type: 'function',
                    function: {
                        name: 'sardis_check_balance',
                        arguments: JSON.stringify({ token: 'USDT', chain: 'polygon' }),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
                });

                const parsed = JSON.parse(result);
                expect(parsed.token).toBe('USDT');
                expect(parsed.chain).toBe('polygon');
            });
        });

        describe('sardis_get_wallet', () => {
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

                const toolCall: OpenAIFunctionCall = {
                    id: 'call_789',
                    type: 'function',
                    function: {
                        name: 'sardis_get_wallet',
                        arguments: JSON.stringify({}),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
                });

                const parsed = JSON.parse(result);
                expect(parsed.success).toBe(true);
                expect(parsed.wallet.id).toBe('wallet_123');
                expect(parsed.wallet.is_active).toBe(true);
            });
        });

        describe('sardis_check_policy', () => {
            it('should check policy and approve', async () => {
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

                const toolCall: OpenAIFunctionCall = {
                    id: 'call_policy',
                    type: 'function',
                    function: {
                        name: 'sardis_check_policy',
                        arguments: JSON.stringify({ amount: 50, vendor: 'OpenAI' }),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
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

                const toolCall: OpenAIFunctionCall = {
                    id: 'call_policy',
                    type: 'function',
                    function: {
                        name: 'sardis_check_policy',
                        arguments: JSON.stringify({ amount: 500, vendor: 'Expensive' }),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
                });

                const parsed = JSON.parse(result);
                expect(parsed.allowed).toBe(false);
            });
        });

        describe('unknown function', () => {
            it('should return error for unknown function', async () => {
                const toolCall: OpenAIFunctionCall = {
                    id: 'call_unknown',
                    type: 'function',
                    function: {
                        name: 'unknown_function',
                        arguments: JSON.stringify({}),
                    },
                };

                const result = await handleSardisFunctionCall(client, toolCall, {
                    walletId: 'wallet_123',
                });

                const parsed = JSON.parse(result);
                expect(parsed.success).toBe(false);
                expect(parsed.error).toContain('Unknown function');
            });
        });
    });

    describe('createToolResponse', () => {
        it('should create correct tool response format', () => {
            const response = createToolResponse('call_123', '{"success": true}');

            expect(response.role).toBe('tool');
            expect(response.tool_call_id).toBe('call_123');
            expect(response.content).toBe('{"success": true}');
        });

        it('should be usable in OpenAI conversation', () => {
            const result = JSON.stringify({ success: true, balance: '1000.00' });
            const response = createToolResponse('call_456', result);

            // Verify the structure matches OpenAI expected format
            expect(response).toHaveProperty('role');
            expect(response).toHaveProperty('tool_call_id');
            expect(response).toHaveProperty('content');
        });
    });

    describe('options handling', () => {
        it('should use default chain from options', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async ({ request }) => {
                    const body = await request.json() as any;
                    expect(body.mandate.chain).toBe('polygon');
                    return HttpResponse.json({
                        status: 'completed',
                        payment_id: 'pay_123',
                    });
                })
            );

            const toolCall: OpenAIFunctionCall = {
                id: 'call_123',
                type: 'function',
                function: {
                    name: 'sardis_pay',
                    arguments: JSON.stringify({ amount: 50, vendor: 'Test' }),
                },
            };

            await handleSardisFunctionCall(client, toolCall, {
                walletId: 'wallet_123',
                chain: 'polygon',
            });
        });

        it('should use default token from options', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async ({ request }) => {
                    const body = await request.json() as any;
                    expect(body.mandate.token).toBe('USDT');
                    return HttpResponse.json({
                        status: 'completed',
                        payment_id: 'pay_123',
                    });
                })
            );

            const toolCall: OpenAIFunctionCall = {
                id: 'call_123',
                type: 'function',
                function: {
                    name: 'sardis_pay',
                    arguments: JSON.stringify({ amount: 50, vendor: 'Test' }),
                },
            };

            await handleSardisFunctionCall(client, toolCall, {
                walletId: 'wallet_123',
                token: 'USDT',
            });
        });
    });
});
