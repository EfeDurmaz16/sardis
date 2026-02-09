/**
 * Comprehensive tests for HoldsResource
 *
 * Tests cover:
 * - Hold creation with various configurations
 * - Hold capture (full and partial)
 * - Hold voiding
 * - Hold listing and retrieval
 * - Hold expiration handling
 * - Error scenarios
 * - Edge cases
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';
import { APIError } from '../src/errors.js';

describe('HoldsResource Comprehensive Tests', () => {
    let client: SardisClient;

    const mockHold = {
        id: 'hold_comprehensive_001',
        wallet_id: 'wallet_test_001',
        merchant_id: 'merchant_test_001',
        amount: '100.00',
        amount_minor: 100000000,
        token: 'USDC',
        status: 'active',
        purpose: 'Pre-authorization for service payment',
        expires_at: '2025-01-21T00:00:00Z',
        captured_amount: null,
        captured_at: null,
        voided_at: null,
        created_at: '2025-01-20T00:00:00Z',
    };

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-api-key' });
    });

    describe('create', () => {
        it('should create hold with minimal parameters', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', () => {
                    return HttpResponse.json(mockHold);
                })
            );

            const result = await client.holds.create({
                wallet_id: 'wallet_test_001',
                amount_minor: 100000000,
                token: 'USDC',
                chain: 'base',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('hold_comprehensive_001');
            expect(result.status).toBe('active');
        });

        it('should create hold with all parameters', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockHold);
                })
            );

            await client.holds.create({
                wallet_id: 'wallet_full_001',
                amount_minor: 500000000,
                token: 'USDT',
                chain: 'polygon',
                expires_in_seconds: 7200, // 2 hours
                metadata: {
                    order_id: 'order_12345',
                    customer_id: 'cust_67890',
                    description: 'Pre-auth for subscription upgrade',
                },
            });

            expect(receivedBody.wallet_id).toBe('wallet_full_001');
            expect(receivedBody.amount_minor).toBe(500000000);
            expect(receivedBody.token).toBe('USDT');
            expect(receivedBody.chain).toBe('polygon');
            expect(receivedBody.expires_in_seconds).toBe(7200);
            expect(receivedBody.metadata.order_id).toBe('order_12345');
        });

        it('should handle insufficient balance error', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Insufficient balance to create hold',
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
                client.holds.create({
                    wallet_id: 'wallet_low_balance',
                    amount_minor: 1000000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should handle wallet not found error', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Wallet not found',
                                code: 'SARDIS_3404',
                            },
                        },
                        { status: 404 }
                    );
                })
            );

            await expect(
                client.holds.create({
                    wallet_id: 'nonexistent_wallet',
                    amount_minor: 100000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should handle inactive wallet error', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Wallet is inactive',
                                code: 'SARDIS_6003',
                            },
                        },
                        { status: 403 }
                    );
                })
            );

            await expect(
                client.holds.create({
                    wallet_id: 'wallet_inactive',
                    amount_minor: 100000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should create hold with different tokens', async () => {
            const tokens = ['USDC', 'USDT', 'PYUSD', 'EURC'];

            for (const token of tokens) {
                let receivedToken: string;
                server.use(
                    http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                        const body = await request.json() as { token: string };
                        receivedToken = body.token;
                        return HttpResponse.json({ ...mockHold, token });
                    })
                );

                const result = await client.holds.create({
                    wallet_id: 'wallet_test',
                    amount_minor: 100000000,
                    token,
                    chain: 'base',
                });

                expect(result.token).toBe(token);
            }
        });

        it('should create hold on different chains', async () => {
            const chains = ['base', 'polygon', 'ethereum', 'arbitrum', 'optimism'];

            for (const chain of chains) {
                let receivedChain: string;
                server.use(
                    http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                        const body = await request.json() as { chain: string };
                        receivedChain = body.chain;
                        return HttpResponse.json(mockHold);
                    })
                );

                await client.holds.create({
                    wallet_id: 'wallet_test',
                    amount_minor: 100000000,
                    token: 'USDC',
                    chain,
                });

                expect(receivedChain).toBe(chain);
            }
        });
    });

    describe('getById', () => {
        it('should retrieve hold by ID', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds/:id', ({ params }) => {
                    return HttpResponse.json({ ...mockHold, id: params.id as string });
                })
            );

            const result = await client.holds.getById('hold_test_123');

            expect(result.id).toBe('hold_test_123');
            expect(result.status).toBe('active');
            expect(result.amount).toBe('100.00');
        });

        it('should handle hold not found', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds/:id', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Hold not found',
                                code: 'SARDIS_3404',
                            },
                        },
                        { status: 404 }
                    );
                })
            );

            await expect(client.holds.getById('nonexistent_hold')).rejects.toThrow();
        });

        it('should return all hold fields', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds/:id', () => {
                    return HttpResponse.json(mockHold);
                })
            );

            const result = await client.holds.getById('hold_comprehensive_001');

            expect(result.id).toBe('hold_comprehensive_001');
            expect(result.wallet_id).toBe('wallet_test_001');
            expect(result.merchant_id).toBe('merchant_test_001');
            expect(result.amount).toBe('100.00');
            expect(result.amount_minor).toBe(100000000);
            expect(result.token).toBe('USDC');
            expect(result.status).toBe('active');
            expect(result.purpose).toBe('Pre-authorization for service payment');
            expect(result.expires_at).toBeDefined();
            expect(result.created_at).toBeDefined();
        });
    });

    describe('capture', () => {
        it('should capture hold for full amount', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/capture', () => {
                    return HttpResponse.json({
                        ...mockHold,
                        status: 'captured',
                        captured_amount: '100.00',
                        captured_at: '2025-01-20T12:00:00Z',
                    });
                })
            );

            const result = await client.holds.capture('hold_comprehensive_001');

            expect(result.status).toBe('captured');
            expect(result.captured_amount).toBe('100.00');
            expect(result.captured_at).toBeDefined();
        });

        it('should capture hold for partial amount', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/capture', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({
                        ...mockHold,
                        status: 'captured',
                        captured_amount: receivedBody.amount,
                        captured_at: '2025-01-20T12:00:00Z',
                    });
                })
            );

            const result = await client.holds.capture('hold_comprehensive_001', '50.00');

            expect(receivedBody.amount).toBe('50.00');
            expect(result.status).toBe('captured');
            expect(result.captured_amount).toBe('50.00');
        });

        it('should handle capturing already captured hold', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/capture', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Hold already captured',
                                code: 'SARDIS_6005',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(client.holds.capture('hold_already_captured')).rejects.toThrow();
        });

        it('should handle capturing expired hold', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/capture', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Hold has expired',
                                code: 'SARDIS_6004',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(client.holds.capture('hold_expired')).rejects.toThrow();
        });

        it('should handle capturing voided hold', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/capture', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Hold has been voided',
                                code: 'SARDIS_6006',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(client.holds.capture('hold_voided')).rejects.toThrow();
        });

        it('should handle capture amount exceeding hold', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/capture', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Capture amount exceeds hold amount',
                                code: 'SARDIS_5003',
                                details: {
                                    hold_amount: '100.00',
                                    capture_amount: '150.00',
                                },
                            },
                        },
                        { status: 422 }
                    );
                })
            );

            await expect(
                client.holds.capture('hold_comprehensive_001', '150.00')
            ).rejects.toThrow();
        });
    });

    describe('void', () => {
        it('should void an active hold', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/void', () => {
                    return HttpResponse.json({
                        ...mockHold,
                        status: 'voided',
                        voided_at: '2025-01-20T12:00:00Z',
                    });
                })
            );

            const result = await client.holds.void('hold_comprehensive_001');

            expect(result.status).toBe('voided');
            expect(result.voided_at).toBeDefined();
        });

        it('should handle voiding already captured hold', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/void', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Hold already captured',
                                code: 'SARDIS_6005',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(client.holds.void('hold_captured')).rejects.toThrow();
        });

        it('should handle voiding already voided hold', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/void', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Hold already voided',
                                code: 'SARDIS_6006',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(client.holds.void('hold_already_voided')).rejects.toThrow();
        });

        it('should handle voiding expired hold (should succeed)', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds/:id/void', () => {
                    return HttpResponse.json({
                        ...mockHold,
                        status: 'voided',
                        voided_at: '2025-01-22T00:00:00Z',
                    });
                })
            );

            const result = await client.holds.void('hold_expired');

            expect(result.status).toBe('voided');
        });
    });

    describe('listByWallet', () => {
        it('should list holds for a wallet', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds/wallet/:walletId', () => {
                    return HttpResponse.json({
                        holds: [
                            mockHold,
                            { ...mockHold, id: 'hold_002', amount: '200.00' },
                            { ...mockHold, id: 'hold_003', amount: '300.00' },
                        ],
                    });
                })
            );

            const result = await client.holds.listByWallet('wallet_test_001');

            expect(result).toHaveLength(3);
            expect(result[0].id).toBe('hold_comprehensive_001');
            expect(result[1].id).toBe('hold_002');
        });

        it('should return empty array when no holds exist', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds/wallet/:walletId', () => {
                    return HttpResponse.json({ holds: [] });
                })
            );

            const result = await client.holds.listByWallet('wallet_no_holds');

            expect(result).toEqual([]);
            expect(result).toHaveLength(0);
        });

        it('should handle wallet not found', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds/wallet/:walletId', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Wallet not found',
                                code: 'SARDIS_3404',
                            },
                        },
                        { status: 404 }
                    );
                })
            );

            await expect(
                client.holds.listByWallet('nonexistent_wallet')
            ).rejects.toThrow();
        });
    });

    describe('listActive', () => {
        it('should list all active holds', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds', () => {
                    return HttpResponse.json({
                        holds: [
                            mockHold,
                            { ...mockHold, id: 'hold_active_002' },
                        ],
                    });
                })
            );

            const result = await client.holds.listActive();

            expect(result).toHaveLength(2);
            expect(result.every((h) => h.status === 'active')).toBe(true);
        });

        it('should return empty array when no active holds', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/holds', () => {
                    return HttpResponse.json({ holds: [] });
                })
            );

            const result = await client.holds.listActive();

            expect(result).toEqual([]);
        });
    });

    describe('error handling', () => {
        it('should handle network timeout', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async () => {
                    await new Promise((resolve) => setTimeout(resolve, 5000));
                    return HttpResponse.json(mockHold);
                })
            );

            const timeoutClient = new SardisClient({
                apiKey: 'test-key',
                timeout: 100,
                maxRetries: 0,
            });

            await expect(
                timeoutClient.holds.create({
                    wallet_id: 'wallet_test',
                    amount_minor: 100000000,
                    token: 'USDC',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should retry on server errors', async () => {
            let attempts = 0;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', () => {
                    attempts++;
                    if (attempts < 3) {
                        return HttpResponse.json(
                            { error: 'Internal server error' },
                            { status: 500 }
                        );
                    }
                    return HttpResponse.json(mockHold);
                })
            );

            const retryClient = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
                retryDelay: 10,
            });

            const result = await retryClient.holds.create({
                wallet_id: 'wallet_test',
                amount_minor: 100000000,
                token: 'USDC',
                chain: 'base',
            });

            expect(result).toBeDefined();
            expect(attempts).toBe(3);
        });
    });

    describe('edge cases', () => {
        it('should handle very large hold amount', async () => {
            let receivedAmount: number;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                    const body = await request.json() as { amount_minor: number };
                    receivedAmount = body.amount_minor;
                    return HttpResponse.json({
                        ...mockHold,
                        amount_minor: receivedAmount,
                        amount: (receivedAmount / 1000000).toFixed(2),
                    });
                })
            );

            const largeAmount = 1000000000000000000; // Very large amount
            const result = await client.holds.create({
                wallet_id: 'wallet_whale',
                amount_minor: largeAmount,
                token: 'USDC',
                chain: 'base',
            });

            expect(receivedAmount).toBe(largeAmount);
        });

        it('should handle minimum hold amount', async () => {
            let receivedAmount: number;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                    const body = await request.json() as { amount_minor: number };
                    receivedAmount = body.amount_minor;
                    return HttpResponse.json({
                        ...mockHold,
                        amount_minor: receivedAmount,
                        amount: '0.01',
                    });
                })
            );

            const result = await client.holds.create({
                wallet_id: 'wallet_test',
                amount_minor: 10000, // 0.01 USDC
                token: 'USDC',
                chain: 'base',
            });

            expect(receivedAmount).toBe(10000);
        });

        it('should handle hold with very short expiration', async () => {
            let receivedExpiry: number;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                    const body = await request.json() as { expires_in_seconds: number };
                    receivedExpiry = body.expires_in_seconds;
                    return HttpResponse.json(mockHold);
                })
            );

            await client.holds.create({
                wallet_id: 'wallet_test',
                amount_minor: 100000000,
                token: 'USDC',
                chain: 'base',
                expires_in_seconds: 60, // 1 minute
            });

            expect(receivedExpiry).toBe(60);
        });

        it('should handle hold with very long expiration', async () => {
            let receivedExpiry: number;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                    const body = await request.json() as { expires_in_seconds: number };
                    receivedExpiry = body.expires_in_seconds;
                    return HttpResponse.json(mockHold);
                })
            );

            await client.holds.create({
                wallet_id: 'wallet_test',
                amount_minor: 100000000,
                token: 'USDC',
                chain: 'base',
                expires_in_seconds: 604800, // 7 days
            });

            expect(receivedExpiry).toBe(604800);
        });

        it('should handle concurrent hold operations', async () => {
            let requestCount = 0;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async () => {
                    requestCount++;
                    await new Promise((resolve) => setTimeout(resolve, 50));
                    return HttpResponse.json({
                        ...mockHold,
                        id: `hold_concurrent_${requestCount}`,
                    });
                })
            );

            const holds = Array.from({ length: 5 }, (_, i) => ({
                wallet_id: `wallet_${i}`,
                amount_minor: 100000000 * (i + 1),
                token: 'USDC',
                chain: 'base',
            }));

            const results = await Promise.all(holds.map((h) => client.holds.create(h)));

            expect(results).toHaveLength(5);
            expect(requestCount).toBe(5);
        });

        it('should handle special characters in metadata', async () => {
            let receivedMetadata: any;
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async ({ request }) => {
                    const body = await request.json() as { metadata: any };
                    receivedMetadata = body.metadata;
                    return HttpResponse.json(mockHold);
                })
            );

            const specialMetadata = {
                description: 'Hold for "special" order & more',
                emoji: '🔒💰',
                nested: { array: [1, 2, 3] },
            };

            await client.holds.create({
                wallet_id: 'wallet_test',
                amount_minor: 100000000,
                token: 'USDC',
                chain: 'base',
                metadata: specialMetadata,
            });

            expect(receivedMetadata).toEqual(specialMetadata);
        });
    });

    describe('request cancellation', () => {
        it('should support AbortController', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/holds', async () => {
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    return HttpResponse.json(mockHold);
                })
            );

            const controller = new AbortController();
            setTimeout(() => controller.abort(), 50);

            await expect(
                client.holds.create({
                    wallet_id: 'wallet_test',
                    amount_minor: 100000000,
                    token: 'USDC',
                    chain: 'base',
                }, { signal: controller.signal })
            ).rejects.toThrow();
        });
    });
});
