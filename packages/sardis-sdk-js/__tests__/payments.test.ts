/**
 * Tests for PaymentsResource
 */
import { describe, it, expect } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server, mockResponses } from './setup.js';
import { http, HttpResponse } from 'msw';

describe('PaymentsResource', () => {
    const client = new SardisClient({ apiKey: 'test-key' });

    describe('executeMandate', () => {
        it('should execute a payment mandate', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/mandates/execute', () => {
                    return HttpResponse.json({
                        id: 'mandate_abc123',
                        status: 'EXECUTED',
                        tx_hash: '0xabcdef1234567890',
                    });
                })
            );

            const result = await client.payments.executeMandate({
                mandate_id: 'test-mandate',
                subject: 'wallet_123',
                destination: 'merchant_456',
                amount_minor: 1000000,
                token: 'USDC',
                chain: 'base_sepolia',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('mandate_abc123');
            expect(result.status).toBe('EXECUTED');
        });

        it('should handle mandate execution failure', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/mandates/execute', () => {
                    return HttpResponse.json(
                        {
                            error: 'Policy violation',
                            code: 'POLICY_VIOLATION',
                        },
                        { status: 403 }
                    );
                })
            );

            await expect(
                client.payments.executeMandate({
                    mandate_id: 'test-mandate',
                    subject: 'wallet_123',
                    destination: 'blocked_merchant',
                    amount_minor: 1000000,
                    token: 'USDC',
                    chain: 'base_sepolia',
                })
            ).rejects.toThrow();
        });

        it('should include all mandate fields in request', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.sh/api/v2/mandates/execute',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json({
                            id: 'mandate_abc123',
                            status: 'EXECUTED',
                        });
                    }
                )
            );

            const mandate = {
                mandate_id: 'test-mandate-123',
                subject: 'wallet_agent',
                destination: 'vendor_openai',
                amount_minor: 2000000000,
                token: 'USDC',
                chain: 'base',
                audit_hash: '0x1234567890abcdef',
                metadata: {
                    purpose: 'API subscription',
                    agent_id: 'agent_001',
                },
            };

            await client.payments.executeMandate(mandate);

            expect(receivedBody).toBeDefined();
            expect(receivedBody.mandate).toEqual(mandate);
        });
    });

    describe('executeAP2', () => {
        it('should execute an AP2 payment', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/ap2/payments/execute', () => {
                    return HttpResponse.json({
                        id: 'ap2_xyz789',
                        status: 'EXECUTED',
                        steps: [
                            { step: 'intent', status: 'completed' },
                            { step: 'cart', status: 'completed' },
                            { step: 'payment', status: 'completed' },
                        ],
                    });
                })
            );

            const result = await client.payments.executeAP2(
                { type: 'subscription', service: 'OpenAI' },
                { items: [{ name: 'API Credits', quantity: 1, price: 20 }] },
                { wallet_id: 'wallet_123', amount_minor: 2000000000 }
            );

            expect(result).toBeDefined();
            expect(result.status).toBe('EXECUTED');
        });

        it('should send all AP2 components in request', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.sh/api/v2/ap2/payments/execute',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json({
                            id: 'ap2_xyz789',
                            status: 'EXECUTED',
                        });
                    }
                )
            );

            const intent = { type: 'purchase', merchant: 'GitHub' };
            const cart = { items: [{ sku: 'copilot-monthly', price: 1900 }] };
            const payment = { wallet_id: 'wallet_abc', amount_minor: 1900000000 };

            await client.payments.executeAP2(intent, cart, payment);

            expect(receivedBody.intent).toEqual(intent);
            expect(receivedBody.cart).toEqual(cart);
            expect(receivedBody.payment).toEqual(payment);
        });
    });

    describe('executeAP2Bundle', () => {
        it('should execute a pre-built AP2 bundle', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/ap2/payments/execute', () => {
                    return HttpResponse.json({
                        id: 'ap2_bundle_001',
                        status: 'EXECUTED',
                    });
                })
            );

            const bundle = {
                intent: { type: 'service_payment' },
                cart: { items: [] },
                payment: { wallet_id: 'wallet_123', amount_minor: 5000000000 },
            };

            const result = await client.payments.executeAP2Bundle(bundle);

            expect(result.id).toBe('ap2_bundle_001');
            expect(result.status).toBe('EXECUTED');
        });
    });
});
