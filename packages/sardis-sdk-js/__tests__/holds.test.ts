/**
 * Tests for HoldsResource
 */
import { describe, it, expect } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

describe('HoldsResource', () => {
    const client = new SardisClient({ apiKey: 'test-key' });

    const mockHold = {
        id: 'hold_xyz789',
        wallet_id: 'wallet_test123',
        amount: '100.00',
        amount_minor: 100000000,
        status: 'active',
        expires_at: '2025-01-21T00:00:00Z',
        created_at: '2025-01-20T00:00:00Z',
    };

    describe('create', () => {
        it('should create a hold', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/holds', () => {
                    return HttpResponse.json(mockHold);
                })
            );

            const result = await client.holds.create({
                wallet_id: 'wallet_test123',
                amount_minor: 100000000,
                token: 'USDC',
                chain: 'base',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('hold_xyz789');
            expect(result.status).toBe('active');
        });

        it('should send correct creation parameters', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/holds', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockHold);
                })
            );

            await client.holds.create({
                wallet_id: 'wallet_abc',
                amount_minor: 50000000,
                token: 'USDT',
                chain: 'polygon',
                expires_in_seconds: 3600,
                metadata: { order_id: 'order_123' },
            });

            expect(receivedBody.wallet_id).toBe('wallet_abc');
            expect(receivedBody.amount_minor).toBe(50000000);
            expect(receivedBody.token).toBe('USDT');
            expect(receivedBody.chain).toBe('polygon');
            expect(receivedBody.expires_in_seconds).toBe(3600);
        });
    });

    describe('getById', () => {
        it('should get hold by ID', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/holds/:id', ({ params }) => {
                    return HttpResponse.json({ ...mockHold, id: params.id });
                })
            );

            const result = await client.holds.getById('hold_abc123');

            expect(result).toBeDefined();
            expect(result.id).toBe('hold_abc123');
        });

        it('should handle hold not found', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/holds/:id', () => {
                    return HttpResponse.json(
                        { error: 'Hold not found' },
                        { status: 404 }
                    );
                })
            );

            await expect(client.holds.getById('nonexistent')).rejects.toThrow();
        });
    });

    describe('capture', () => {
        it('should capture a hold', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/holds/:id/capture', () => {
                    return HttpResponse.json({ ...mockHold, status: 'captured' });
                })
            );

            const result = await client.holds.capture('hold_xyz789');

            expect(result.status).toBe('captured');
        });

        it('should capture with partial amount', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.network/api/v2/holds/:id/capture',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json({
                            ...mockHold,
                            status: 'captured',
                            amount: receivedBody.amount,
                        });
                    }
                )
            );

            const result = await client.holds.capture('hold_xyz789', '50.00');

            expect(receivedBody.amount).toBe('50.00');
            expect(result.status).toBe('captured');
        });

        it('should capture full amount when no amount specified', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.network/api/v2/holds/:id/capture',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json({ ...mockHold, status: 'captured' });
                    }
                )
            );

            await client.holds.capture('hold_xyz789');

            expect(receivedBody.amount).toBeUndefined();
        });
    });

    describe('void', () => {
        it('should void a hold', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/holds/:id/void', () => {
                    return HttpResponse.json({ ...mockHold, status: 'voided' });
                })
            );

            const result = await client.holds.void('hold_xyz789');

            expect(result.status).toBe('voided');
        });

        it('should handle void of already captured hold', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/holds/:id/void', () => {
                    return HttpResponse.json(
                        { error: 'Hold already captured' },
                        { status: 409 }
                    );
                })
            );

            await expect(client.holds.void('hold_captured')).rejects.toThrow();
        });
    });

    describe('listByWallet', () => {
        it('should list holds for a wallet', async () => {
            server.use(
                http.get(
                    'https://api.sardis.network/api/v2/holds/wallet/:walletId',
                    () => {
                        return HttpResponse.json({
                            holds: [
                                mockHold,
                                { ...mockHold, id: 'hold_2' },
                            ],
                        });
                    }
                )
            );

            const result = await client.holds.listByWallet('wallet_test123');

            expect(result).toHaveLength(2);
            expect(result[0].id).toBe('hold_xyz789');
            expect(result[1].id).toBe('hold_2');
        });

        it('should return empty array when no holds', async () => {
            server.use(
                http.get(
                    'https://api.sardis.network/api/v2/holds/wallet/:walletId',
                    () => {
                        return HttpResponse.json({ holds: [] });
                    }
                )
            );

            const result = await client.holds.listByWallet('wallet_empty');

            expect(result).toEqual([]);
        });
    });

    describe('listActive', () => {
        it('should list all active holds', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/holds', () => {
                    return HttpResponse.json({
                        holds: [mockHold, { ...mockHold, id: 'hold_3' }],
                    });
                })
            );

            const result = await client.holds.listActive();

            expect(result).toHaveLength(2);
        });

        it('should return empty array when no active holds', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/holds', () => {
                    return HttpResponse.json({ holds: [] });
                })
            );

            const result = await client.holds.listActive();

            expect(result).toEqual([]);
        });
    });
});
