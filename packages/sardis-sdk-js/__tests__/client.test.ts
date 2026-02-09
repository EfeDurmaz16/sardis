/**
 * Tests for SardisClient
 */
import { describe, it, expect } from 'vitest';
import { SardisClient } from '../src/client.js';
import { AuthenticationError, RateLimitError, APIError } from '../src/errors.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

describe('SardisClient', () => {
    describe('initialization', () => {
        it('should create client with required options', () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            expect(client).toBeInstanceOf(SardisClient);
        });

        it('should throw error when apiKey is missing', () => {
            expect(() => new SardisClient({} as any)).toThrow('API key is required');
        });

        it('should initialize all resource classes', () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            expect(client.payments).toBeDefined();
            expect(client.holds).toBeDefined();
            expect(client.webhooks).toBeDefined();
            expect(client.marketplace).toBeDefined();
            expect(client.transactions).toBeDefined();
            expect(client.ledger).toBeDefined();
            expect(client.wallets).toBeDefined();
        });

        it('should accept custom baseUrl', () => {
            const client = new SardisClient({
                apiKey: 'test-key',
                baseUrl: 'https://custom.api.example.com',
            });
            expect(client).toBeInstanceOf(SardisClient);
        });

        it('should accept custom timeout', () => {
            const client = new SardisClient({
                apiKey: 'test-key',
                timeout: 60000,
            });
            expect(client).toBeInstanceOf(SardisClient);
        });

        it('should accept custom maxRetries', () => {
            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
            });
            expect(client).toBeInstanceOf(SardisClient);
        });
    });

    describe('health check', () => {
        it('should return health status', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            const health = await client.health();
            expect(health).toEqual({
                status: 'healthy',
                version: '0.3.0',
            });
        });
    });

    describe('error handling', () => {
        it('should throw AuthenticationError on 401', async () => {
            const client = new SardisClient({ apiKey: 'invalid-key' });
            await expect(client.request('GET', '/v1/error/401')).rejects.toThrow(
                AuthenticationError
            );
        });

        it('should throw RateLimitError on 429', async () => {
            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 0, // Don't retry to avoid waiting for Retry-After delay
            });
            await expect(client.request('GET', '/v1/error/429')).rejects.toThrow(
                RateLimitError
            );
        });

        it('should throw APIError on 500', async () => {
            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 1,
                retryDelay: 10, // Short delay for testing
            });
            await expect(client.request('GET', '/v1/error/500')).rejects.toThrow(
                APIError
            );
        });
    });

    describe('retry logic', () => {
        it('should retry on network errors', async () => {
            let attempts = 0;
            server.use(
                http.get('https://api.sardis.sh/v1/retry-test', () => {
                    attempts++;
                    if (attempts < 2) {
                        return HttpResponse.error();
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key', maxRetries: 3 });
            const result = await client.request('GET', '/v1/retry-test');
            expect(result).toEqual({ success: true });
            expect(attempts).toBe(2);
        });

        it('should retry on rate limit with backoff', async () => {
            let attempts = 0;
            server.use(
                http.get('https://api.sardis.sh/v1/rate-limit-test', () => {
                    attempts++;
                    if (attempts < 2) {
                        return HttpResponse.json(
                            { error: 'Rate limited' },
                            {
                                status: 429,
                                headers: { 'Retry-After': '1' },
                            }
                        );
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key', maxRetries: 3 });
            const result = await client.request('GET', '/v1/rate-limit-test');
            expect(result).toEqual({ success: true });
            expect(attempts).toBe(2);
        }, 10000);

        it('should fail after max retries exceeded', async () => {
            server.use(
                http.get('https://api.sardis.sh/v1/always-fail', () => {
                    return HttpResponse.error();
                })
            );

            const client = new SardisClient({ apiKey: 'test-key', maxRetries: 2 });
            await expect(client.request('GET', '/v1/always-fail')).rejects.toThrow();
        });
    });

    describe('request method', () => {
        it('should make GET request with params', async () => {
            server.use(
                http.get('https://api.sardis.sh/v1/test', ({ request }) => {
                    const url = new URL(request.url);
                    const param = url.searchParams.get('foo');
                    return HttpResponse.json({ param });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key' });
            const result = await client.request<{ param: string }>('GET', '/v1/test', {
                params: { foo: 'bar' },
            });
            expect(result.param).toBe('bar');
        });

        it('should make POST request with data', async () => {
            server.use(
                http.post('https://api.sardis.sh/v1/test', async ({ request }) => {
                    const body = await request.json();
                    return HttpResponse.json({ received: body });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key' });
            const result = await client.request<{ received: unknown }>(
                'POST',
                '/v1/test',
                { data: { foo: 'bar' } }
            );
            expect(result.received).toEqual({ foo: 'bar' });
        });
    });
});
