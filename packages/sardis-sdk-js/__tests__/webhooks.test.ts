/**
 * Tests for WebhooksResource
 */
import { describe, it, expect } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

describe('WebhooksResource', () => {
    const client = new SardisClient({ apiKey: 'test-key' });

    const mockWebhook = {
        id: 'webhook_def456',
        url: 'https://example.com/webhook',
        events: ['payment.completed', 'payment.failed'],
        active: true,
        secret: 'whsec_abc123',
        created_at: '2025-01-20T00:00:00Z',
    };

    const mockDelivery = {
        id: 'delivery_001',
        webhook_id: 'webhook_def456',
        event_type: 'payment.completed',
        status: 'success',
        response_code: 200,
        delivered_at: '2025-01-20T00:01:00Z',
    };

    describe('listEventTypes', () => {
        it('should list all event types', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/webhooks/event-types', () => {
                    return HttpResponse.json({
                        event_types: [
                            'payment.completed',
                            'payment.failed',
                            'hold.created',
                            'hold.captured',
                            'hold.voided',
                        ],
                    });
                })
            );

            const result = await client.webhooks.listEventTypes();

            expect(result).toContain('payment.completed');
            expect(result).toContain('hold.created');
            expect(result).toHaveLength(5);
        });
    });

    describe('create', () => {
        it('should create a webhook', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/webhooks', () => {
                    return HttpResponse.json(mockWebhook);
                })
            );

            const result = await client.webhooks.create({
                url: 'https://example.com/webhook',
                events: ['payment.completed', 'payment.failed'],
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('webhook_def456');
            expect(result.events).toContain('payment.completed');
        });

        it('should send correct creation parameters', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.sh/api/v2/webhooks', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockWebhook);
                })
            );

            await client.webhooks.create({
                url: 'https://myapp.com/hooks/sardis',
                events: ['hold.captured'],
                metadata: { environment: 'production' },
            });

            expect(receivedBody.url).toBe('https://myapp.com/hooks/sardis');
            expect(receivedBody.events).toContain('hold.captured');
        });
    });

    describe('list', () => {
        it('should list all webhooks', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/webhooks', () => {
                    return HttpResponse.json({
                        webhooks: [mockWebhook, { ...mockWebhook, id: 'webhook_2' }],
                    });
                })
            );

            const result = await client.webhooks.list();

            expect(result).toHaveLength(2);
            expect(result[0].id).toBe('webhook_def456');
        });

        it('should return empty array when no webhooks', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/webhooks', () => {
                    return HttpResponse.json({ webhooks: [] });
                })
            );

            const result = await client.webhooks.list();

            expect(result).toEqual([]);
        });
    });

    describe('getById', () => {
        it('should get webhook by ID', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/webhooks/:id', ({ params }) => {
                    return HttpResponse.json({ ...mockWebhook, id: params.id });
                })
            );

            const result = await client.webhooks.getById('webhook_abc');

            expect(result.id).toBe('webhook_abc');
        });
    });

    describe('update', () => {
        it('should update a webhook', async () => {
            server.use(
                http.patch('https://api.sardis.sh/api/v2/webhooks/:id', () => {
                    return HttpResponse.json({
                        ...mockWebhook,
                        url: 'https://newurl.com/webhook',
                    });
                })
            );

            const result = await client.webhooks.update('webhook_def456', {
                url: 'https://newurl.com/webhook',
            });

            expect(result.url).toBe('https://newurl.com/webhook');
        });

        it('should update webhook events', async () => {
            let receivedBody: any;
            server.use(
                http.patch(
                    'https://api.sardis.sh/api/v2/webhooks/:id',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json({
                            ...mockWebhook,
                            events: receivedBody.events,
                        });
                    }
                )
            );

            const result = await client.webhooks.update('webhook_def456', {
                events: ['payment.completed'],
            });

            expect(result.events).toEqual(['payment.completed']);
        });

        it('should toggle webhook active status', async () => {
            server.use(
                http.patch('https://api.sardis.sh/api/v2/webhooks/:id', () => {
                    return HttpResponse.json({ ...mockWebhook, active: false });
                })
            );

            const result = await client.webhooks.update('webhook_def456', {
                active: false,
            });

            expect(result.active).toBe(false);
        });
    });

    describe('delete', () => {
        it('should delete a webhook', async () => {
            server.use(
                http.delete('https://api.sardis.sh/api/v2/webhooks/:id', () => {
                    return new HttpResponse(null, { status: 204 });
                })
            );

            await expect(
                client.webhooks.delete('webhook_def456')
            ).resolves.toBeUndefined();
        });
    });

    describe('test', () => {
        it('should send test event', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/webhooks/:id/test', () => {
                    return HttpResponse.json(mockDelivery);
                })
            );

            const result = await client.webhooks.test('webhook_def456');

            expect(result).toBeDefined();
            expect(result.status).toBe('success');
        });
    });

    describe('listDeliveries', () => {
        it('should list webhook deliveries', async () => {
            server.use(
                http.get(
                    'https://api.sardis.sh/api/v2/webhooks/:id/deliveries',
                    () => {
                        return HttpResponse.json({
                            deliveries: [mockDelivery, { ...mockDelivery, id: 'delivery_002' }],
                        });
                    }
                )
            );

            const result = await client.webhooks.listDeliveries('webhook_def456');

            expect(result).toHaveLength(2);
            expect(result[0].status).toBe('success');
        });

        it('should respect limit parameter', async () => {
            server.use(
                http.get(
                    'https://api.sardis.sh/api/v2/webhooks/:id/deliveries',
                    ({ request }) => {
                        const url = new URL(request.url);
                        const limit = url.searchParams.get('limit');
                        expect(limit).toBe('10');
                        return HttpResponse.json({ deliveries: [mockDelivery] });
                    }
                )
            );

            await client.webhooks.listDeliveries('webhook_def456', 10);
        });
    });

    describe('rotateSecret', () => {
        it('should rotate webhook secret', async () => {
            server.use(
                http.post(
                    'https://api.sardis.sh/api/v2/webhooks/:id/rotate-secret',
                    () => {
                        return HttpResponse.json({ secret: 'whsec_new_secret_xyz' });
                    }
                )
            );

            const result = await client.webhooks.rotateSecret('webhook_def456');

            expect(result.secret).toBe('whsec_new_secret_xyz');
        });
    });
});
