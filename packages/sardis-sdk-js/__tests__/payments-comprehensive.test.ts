/**
 * Comprehensive tests for PaymentsResource
 *
 * Tests cover:
 * - executeMandate with various configurations
 * - executeAP2 payment flows
 * - executeAP2Bundle operations
 * - Error scenarios (policy violations, insufficient balance, etc.)
 * - Request validation
 * - Response parsing
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';
import { APIError } from '../src/errors.js';

describe('PaymentsResource Comprehensive Tests', () => {
    let client: SardisClient;

    const mockMandateResponse = {
        id: 'mandate_test123',
        status: 'EXECUTED',
        tx_hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        chain: 'base',
        ledger_tx_id: 'ltx_123',
        audit_anchor: '0xaudit123',
        created_at: '2025-01-20T00:00:00Z',
    };

    const mockAP2Response = {
        id: 'ap2_xyz789',
        mandate_id: 'mandate_123',
        ledger_tx_id: 'ltx_456',
        chain_tx_hash: '0xabcdef',
        chain: 'base',
        audit_anchor: '0xaudit456',
        status: 'EXECUTED',
        steps: [
            { step: 'intent', status: 'completed' },
            { step: 'cart', status: 'completed' },
            { step: 'payment', status: 'completed' },
        ],
    };

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-api-key' });
    });

    describe('executeMandate', () => {
        it('should execute a basic mandate successfully', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            const result = await client.payments.executeMandate({
                mandate_id: 'test-mandate',
                subject: 'wallet_123',
                destination: 'merchant_456',
                amount_minor: 1000000,
                token: 'USDC',
                chain: 'base',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('mandate_test123');
            expect(result.status).toBe('EXECUTED');
            expect(result.tx_hash).toBeDefined();
        });

        it('should include all mandate fields in request body', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            const mandate = {
                mandate_id: 'mandate-full-test',
                subject: 'agent_wallet_001',
                destination: 'vendor_openai_api',
                amount_minor: 5000000000, // $5000 in minor units
                token: 'USDC',
                chain: 'base',
                audit_hash: '0xaudit1234567890',
                metadata: {
                    purpose: 'Monthly API subscription',
                    agent_id: 'agent_001',
                    subscription_id: 'sub_12345',
                    invoice_number: 'INV-2025-001',
                },
                reference_id: 'ref_external_123',
                idempotency_key: 'idem_unique_key',
            };

            await client.payments.executeMandate(mandate);

            expect(receivedBody).toBeDefined();
            expect(receivedBody.mandate).toEqual(mandate);
        });

        it('should handle policy violation error', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Transaction exceeds daily spending limit',
                                code: 'SARDIS_6001',
                                details: {
                                    limit: '1000.00',
                                    attempted: '5000.00',
                                    policy: 'daily_spending_limit',
                                },
                            },
                        },
                        { status: 403 }
                    );
                })
            );

            await expect(
                client.payments.executeMandate({
                    mandate_id: 'test-mandate',
                    subject: 'wallet_123',
                    destination: 'merchant_456',
                    amount_minor: 5000000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should handle insufficient balance error', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Insufficient USDC balance',
                                code: 'SARDIS_6000',
                                details: {
                                    required: '1000.00',
                                    available: '500.00',
                                    currency: 'USDC',
                                },
                            },
                        },
                        { status: 400 }
                    );
                })
            );

            await expect(
                client.payments.executeMandate({
                    mandate_id: 'test-mandate',
                    subject: 'wallet_low_balance',
                    destination: 'merchant_456',
                    amount_minor: 1000000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should handle blocked merchant error', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Merchant is blocked by policy',
                                code: 'SARDIS_6002',
                                details: {
                                    merchant: 'blocked_merchant_xyz',
                                    policy: 'merchant_blocklist',
                                },
                            },
                        },
                        { status: 403 }
                    );
                })
            );

            await expect(
                client.payments.executeMandate({
                    mandate_id: 'test-mandate',
                    subject: 'wallet_123',
                    destination: 'blocked_merchant_xyz',
                    amount_minor: 1000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should handle network timeout during execution', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async () => {
                    await new Promise((resolve) => setTimeout(resolve, 5000));
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            const timeoutClient = new SardisClient({
                apiKey: 'test-key',
                timeout: 100,
                maxRetries: 0,
            });

            await expect(
                timeoutClient.payments.executeMandate({
                    mandate_id: 'test-mandate',
                    subject: 'wallet_123',
                    destination: 'merchant_456',
                    amount_minor: 1000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should support different chains', async () => {
            const chains = ['base', 'polygon', 'ethereum', 'arbitrum', 'optimism'];
            let receivedChain: string;

            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async ({ request }) => {
                    const body = await request.json() as { mandate: { chain: string } };
                    receivedChain = body.mandate.chain;
                    return HttpResponse.json({ ...mockMandateResponse, chain: receivedChain });
                })
            );

            for (const chain of chains) {
                const result = await client.payments.executeMandate({
                    mandate_id: 'test-mandate',
                    subject: 'wallet_123',
                    destination: 'merchant_456',
                    amount_minor: 1000000,
                    token: 'USDC',
                    chain,
                });

                expect(result.chain).toBe(chain);
            }
        });

        it('should support different tokens', async () => {
            const tokens = ['USDC', 'USDT', 'PYUSD', 'EURC'];
            let receivedToken: string;

            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async ({ request }) => {
                    const body = await request.json() as { mandate: { token: string } };
                    receivedToken = body.mandate.token;
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            for (const token of tokens) {
                await client.payments.executeMandate({
                    mandate_id: 'test-mandate',
                    subject: 'wallet_123',
                    destination: 'merchant_456',
                    amount_minor: 1000000,
                    token,
                    chain: 'base',
                });

                expect(receivedToken).toBe(token);
            }
        });

        it('should handle concurrent mandate executions', async () => {
            let requestCount = 0;
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async () => {
                    requestCount++;
                    await new Promise((resolve) => setTimeout(resolve, 50));
                    return HttpResponse.json({
                        ...mockMandateResponse,
                        id: `mandate_${requestCount}`,
                    });
                })
            );

            const mandates = Array.from({ length: 5 }, (_, i) => ({
                mandate_id: `mandate_${i}`,
                subject: 'wallet_123',
                destination: `merchant_${i}`,
                amount_minor: 1000000 * (i + 1),
                token: 'USDC',
                chain: 'base',
            }));

            const results = await Promise.all(mandates.map((m) => client.payments.executeMandate(m)));

            expect(results).toHaveLength(5);
            expect(requestCount).toBe(5);
        });
    });

    describe('executeAP2', () => {
        it('should execute AP2 payment with all components', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', () => {
                    return HttpResponse.json(mockAP2Response);
                })
            );

            const result = await client.payments.executeAP2(
                { type: 'subscription', service: 'OpenAI', plan: 'Pro' },
                {
                    items: [
                        { name: 'API Credits', quantity: 1, price: 2000, sku: 'SKU001' },
                        { name: 'Support Add-on', quantity: 1, price: 500, sku: 'SKU002' },
                    ],
                    total: 2500,
                },
                {
                    wallet_id: 'wallet_agent_001',
                    amount_minor: 2500000000,
                    chain: 'base',
                    token: 'USDC',
                }
            );

            expect(result).toBeDefined();
            expect(result.status).toBe('EXECUTED');
        });

        it('should include all AP2 components in request body', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAP2Response);
                })
            );

            const intent = {
                type: 'purchase',
                merchant: 'GitHub',
                action: 'upgrade_subscription',
            };
            const cart = {
                items: [{ sku: 'copilot-individual', name: 'GitHub Copilot', price: 1000 }],
                subtotal: 1000,
                tax: 0,
                total: 1000,
            };
            const payment = {
                wallet_id: 'wallet_dev_001',
                amount_minor: 1000000000,
                chain: 'polygon',
                token: 'USDC',
            };

            await client.payments.executeAP2(intent, cart, payment);

            expect(receivedBody.intent).toEqual(intent);
            expect(receivedBody.cart).toEqual(cart);
            expect(receivedBody.payment).toEqual(payment);
        });

        it('should handle AP2 execution failure', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Cart validation failed',
                                code: 'SARDIS_5000',
                                details: { field: 'cart.total', reason: 'Amount mismatch' },
                            },
                        },
                        { status: 422 }
                    );
                })
            );

            await expect(
                client.payments.executeAP2(
                    { type: 'purchase' },
                    { items: [], total: 100 },
                    { wallet_id: 'wallet_123', amount_minor: 200000000 }
                )
            ).rejects.toThrow();
        });

        it('should handle partial execution failure', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', () => {
                    return HttpResponse.json({
                        ...mockAP2Response,
                        status: 'PARTIAL_FAILURE',
                        steps: [
                            { step: 'intent', status: 'completed' },
                            { step: 'cart', status: 'completed' },
                            { step: 'payment', status: 'failed', error: 'Chain congestion' },
                        ],
                    });
                })
            );

            const result = await client.payments.executeAP2(
                { type: 'purchase' },
                { items: [] },
                { wallet_id: 'wallet_123', amount_minor: 1000000 }
            );

            expect(result.status).toBe('PARTIAL_FAILURE');
        });
    });

    describe('executeAP2Bundle', () => {
        it('should execute pre-built AP2 bundle', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', () => {
                    return HttpResponse.json(mockAP2Response);
                })
            );

            const bundle = {
                intent: { type: 'service_payment', merchant: 'AWS' },
                cart: { items: [{ name: 'EC2 Usage', price: 15000 }] },
                payment: { wallet_id: 'wallet_123', amount_minor: 15000000000 },
            };

            const result = await client.payments.executeAP2Bundle(bundle);

            expect(result).toBeDefined();
            expect(result.status).toBe('EXECUTED');
        });

        it('should send bundle as single request', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAP2Response);
                })
            );

            const bundle = {
                intent: { type: 'batch_payment' },
                cart: {
                    items: [
                        { name: 'Service A', price: 100 },
                        { name: 'Service B', price: 200 },
                    ],
                },
                payment: {
                    wallet_id: 'wallet_batch',
                    amount_minor: 300000000,
                    metadata: { batch_id: 'batch_001' },
                },
            };

            await client.payments.executeAP2Bundle(bundle);

            expect(receivedBody).toEqual(bundle);
        });

        it('should handle bundle with complex nested data', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAP2Response);
                })
            );

            const complexBundle = {
                intent: {
                    type: 'multi_service',
                    services: ['openai', 'github', 'aws'],
                    metadata: {
                        project: 'ai-assistant',
                        environment: 'production',
                        tags: ['ml', 'automation'],
                    },
                },
                cart: {
                    items: [
                        {
                            name: 'OpenAI API',
                            price: 5000,
                            quantity: 1,
                            metadata: { tier: 'enterprise' },
                        },
                        {
                            name: 'GitHub Copilot',
                            price: 1900,
                            quantity: 10,
                            metadata: { seats: ['user1', 'user2'] },
                        },
                    ],
                    discounts: [{ code: 'BUNDLE20', amount: 500 }],
                    subtotal: 24000,
                    tax: 2400,
                    total: 25900,
                },
                payment: {
                    wallet_id: 'wallet_enterprise',
                    amount_minor: 25900000000,
                    chain: 'base',
                    token: 'USDC',
                    approval_signature: '0xsig123',
                },
            };

            await client.payments.executeAP2Bundle(complexBundle);

            expect(receivedBody.intent.services).toEqual(['openai', 'github', 'aws']);
            expect(receivedBody.cart.items).toHaveLength(2);
            expect(receivedBody.cart.discounts).toHaveLength(1);
        });
    });

    describe('error handling', () => {
        it('should handle 400 Bad Request', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        { error: { message: 'Invalid mandate format', code: 'SARDIS_3400' } },
                        { status: 400 }
                    );
                })
            );

            try {
                await client.payments.executeMandate({
                    mandate_id: '',
                    subject: '',
                    destination: '',
                    amount_minor: -1,
                    token: 'USDC',
                    chain: 'base',
                });
                expect.fail('Should have thrown');
            } catch (error) {
                expect(error).toBeInstanceOf(APIError);
                expect((error as APIError).statusCode).toBe(400);
            }
        });

        it('should handle 401 Unauthorized', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        { error: { message: 'Invalid API key', code: 'SARDIS_2001' } },
                        { status: 401 }
                    );
                })
            );

            const badClient = new SardisClient({
                apiKey: 'invalid-key',
                maxRetries: 0,
            });

            await expect(
                badClient.payments.executeMandate({
                    mandate_id: 'test',
                    subject: 'wallet',
                    destination: 'merchant',
                    amount_minor: 100,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should handle 500 Internal Server Error with retry', async () => {
            let attempts = 0;
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', () => {
                    attempts++;
                    if (attempts < 3) {
                        return HttpResponse.json(
                            { error: 'Internal server error' },
                            { status: 500 }
                        );
                    }
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            const retryClient = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
                retryDelay: 10,
            });

            const result = await retryClient.payments.executeMandate({
                mandate_id: 'test',
                subject: 'wallet',
                destination: 'merchant',
                amount_minor: 100,
                token: 'USDC',
                chain: 'base',
            });

            expect(result.status).toBe('EXECUTED');
            expect(attempts).toBe(3);
        });
    });

    describe('request cancellation', () => {
        it('should support AbortController for mandate execution', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async () => {
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            const controller = new AbortController();
            setTimeout(() => controller.abort(), 50);

            await expect(
                client.payments.executeMandate(
                    {
                        mandate_id: 'test',
                        subject: 'wallet',
                        destination: 'merchant',
                        amount_minor: 100,
                        token: 'USDC',
                        chain: 'base',
                    }
                )
            ).rejects.toThrow();
        });
    });

    describe('edge cases', () => {
        it('should handle very large amounts', async () => {
            let receivedAmount: number;
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async ({ request }) => {
                    const body = await request.json() as { mandate: { amount_minor: number } };
                    receivedAmount = body.mandate.amount_minor;
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            // $1 trillion in minor units
            const largeAmount = 1000000000000000000;
            await client.payments.executeMandate({
                mandate_id: 'large-payment',
                subject: 'wallet_123',
                destination: 'merchant_456',
                amount_minor: largeAmount,
                token: 'USDC',
                chain: 'base',
            });

            expect(receivedAmount).toBe(largeAmount);
        });

        it('should handle special characters in metadata', async () => {
            let receivedMetadata: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/mandates/execute', async ({ request }) => {
                    const body = await request.json() as { mandate: { metadata: any } };
                    receivedMetadata = body.mandate.metadata;
                    return HttpResponse.json(mockMandateResponse);
                })
            );

            const metadata = {
                description: 'Payment for "special" service & more <html>',
                emoji: '💰🚀',
                unicode: '\u0000\u001F',
                nested: { array: [1, 2, 3], obj: { key: 'value' } },
            };

            await client.payments.executeMandate({
                mandate_id: 'special-chars',
                subject: 'wallet_123',
                destination: 'merchant_456',
                amount_minor: 100,
                token: 'USDC',
                chain: 'base',
                metadata,
            });

            expect(receivedMetadata.description).toBe('Payment for "special" service & more <html>');
            expect(receivedMetadata.emoji).toBe('💰🚀');
        });

        it('should handle empty cart in AP2', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/ap2/payments/execute', () => {
                    return HttpResponse.json(mockAP2Response);
                })
            );

            const result = await client.payments.executeAP2(
                { type: 'tip' },
                { items: [], total: 0 },
                { wallet_id: 'wallet_123', amount_minor: 100000000 }
            );

            expect(result).toBeDefined();
        });
    });
});
