/**
 * Tests for SardisClient token refresh functionality
 *
 * Tests cover:
 * - Automatic token refresh on 401 responses
 * - Token refresh failure handling
 * - Token refresh configuration
 */
import { describe, it, expect, vi } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';
import { AuthenticationError } from '../src/errors.js';

describe('SardisClient Token Refresh', () => {
    describe('automatic token refresh', () => {
        it('should refresh token on 401 and retry request', async () => {
            let requestCount = 0;
            let receivedApiKey: string | null = null;

            server.use(
                http.get('https://api.sardis.network/api/v2/protected', ({ request }) => {
                    requestCount++;
                    receivedApiKey = request.headers.get('X-API-Key');

                    if (receivedApiKey === 'expired-token') {
                        return HttpResponse.json(
                            { error: 'Token expired' },
                            { status: 401 }
                        );
                    }

                    return HttpResponse.json({ data: 'success' });
                })
            );

            const refreshToken = vi.fn().mockResolvedValue('new-valid-token');

            const client = new SardisClient({
                apiKey: 'expired-token',
                tokenRefresh: {
                    refreshToken,
                },
            });

            const result = await client.request<{ data: string }>(
                'GET',
                '/api/v2/protected'
            );

            expect(refreshToken).toHaveBeenCalledTimes(1);
            expect(requestCount).toBe(2); // First request + retry
            expect(result.data).toBe('success');
            expect(client.getApiKey()).toBe('new-valid-token');
        });

        it('should throw AuthenticationError when refresh fails', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/protected', () => {
                    return HttpResponse.json(
                        { error: 'Token expired' },
                        { status: 401 }
                    );
                })
            );

            const refreshToken = vi.fn().mockRejectedValue(new Error('Refresh failed'));

            const client = new SardisClient({
                apiKey: 'expired-token',
                tokenRefresh: {
                    refreshToken,
                },
            });

            await expect(
                client.request('GET', '/api/v2/protected')
            ).rejects.toThrow(AuthenticationError);
        });

        it('should not retry refresh on second 401', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/api/v2/protected', () => {
                    requestCount++;
                    return HttpResponse.json(
                        { error: 'Token expired' },
                        { status: 401 }
                    );
                })
            );

            const refreshToken = vi.fn().mockResolvedValue('still-invalid-token');

            const client = new SardisClient({
                apiKey: 'expired-token',
                tokenRefresh: {
                    refreshToken,
                },
            });

            await expect(
                client.request('GET', '/api/v2/protected')
            ).rejects.toThrow(AuthenticationError);

            // Should only try refresh once
            expect(refreshToken).toHaveBeenCalledTimes(1);
            // Initial request + one retry after refresh
            expect(requestCount).toBe(2);
        });

        it('should throw AuthenticationError without refresh when not configured', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/protected', () => {
                    return HttpResponse.json(
                        { error: 'Token expired' },
                        { status: 401 }
                    );
                })
            );

            const client = new SardisClient({
                apiKey: 'expired-token',
                // No tokenRefresh configured
            });

            await expect(
                client.request('GET', '/api/v2/protected')
            ).rejects.toThrow(AuthenticationError);
        });
    });

    describe('setApiKey', () => {
        it('should update the API key for subsequent requests', async () => {
            const receivedKeys: string[] = [];

            server.use(
                http.get('https://api.sardis.network/api/v2/test', ({ request }) => {
                    receivedKeys.push(request.headers.get('X-API-Key') || '');
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({ apiKey: 'key-1' });

            await client.request('GET', '/api/v2/test');
            expect(receivedKeys[0]).toBe('key-1');

            client.setApiKey('key-2');

            await client.request('GET', '/api/v2/test');
            expect(receivedKeys[1]).toBe('key-2');

            client.setApiKey('key-3');

            await client.request('GET', '/api/v2/test');
            expect(receivedKeys[2]).toBe('key-3');
        });

        it('should return the current API key', () => {
            const client = new SardisClient({ apiKey: 'test-key' });

            expect(client.getApiKey()).toBe('test-key');

            client.setApiKey('new-key');

            expect(client.getApiKey()).toBe('new-key');
        });
    });
});

describe('SardisClient Retry Logic', () => {
    describe('retry configuration', () => {
        it('should retry on configured status codes', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/api/v2/flaky', () => {
                    requestCount++;
                    if (requestCount < 3) {
                        return HttpResponse.json(
                            { error: 'Service unavailable' },
                            { status: 503 }
                        );
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
                retryDelay: 10, // Short delay for testing
            });

            const result = await client.request<{ success: boolean }>(
                'GET',
                '/api/v2/flaky'
            );

            expect(result.success).toBe(true);
            expect(requestCount).toBe(3);
        });

        it('should fail after max retries exceeded', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/always-503', () => {
                    return HttpResponse.json(
                        { error: 'Service unavailable' },
                        { status: 503 }
                    );
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 2,
                retryDelay: 10,
            });

            await expect(
                client.request('GET', '/api/v2/always-503')
            ).rejects.toThrow();
        });

        it('should use custom retryOn status codes', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/api/v2/custom-error', () => {
                    requestCount++;
                    if (requestCount < 2) {
                        return HttpResponse.json(
                            { error: 'Custom error' },
                            { status: 418 } // I'm a teapot
                        );
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 3,
                retryDelay: 10,
                retryOn: [418], // Only retry on 418
            });

            const result = await client.request<{ success: boolean }>(
                'GET',
                '/api/v2/custom-error'
            );

            expect(result.success).toBe(true);
            expect(requestCount).toBe(2);
        });

        it('should not retry on non-configured status codes', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/api/v2/bad-request', () => {
                    requestCount++;
                    return HttpResponse.json(
                        { error: 'Bad request' },
                        { status: 400 }
                    );
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
                retryDelay: 10,
            });

            await expect(
                client.request('GET', '/api/v2/bad-request')
            ).rejects.toThrow();

            // Should not retry 400 errors
            expect(requestCount).toBe(1);
        });
    });

    describe('retry on network errors', () => {
        it('should retry on network errors when enabled', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/api/v2/network-flaky', () => {
                    requestCount++;
                    if (requestCount < 2) {
                        return HttpResponse.error();
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 3,
                retryDelay: 10,
                retryOnNetworkError: true,
            });

            const result = await client.request<{ success: boolean }>(
                'GET',
                '/api/v2/network-flaky'
            );

            expect(result.success).toBe(true);
            expect(requestCount).toBe(2);
        });

        it('should not retry on network errors when disabled', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/api/v2/network-fail', () => {
                    requestCount++;
                    return HttpResponse.error();
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 3,
                retryDelay: 10,
                retryOnNetworkError: false,
            });

            await expect(
                client.request('GET', '/api/v2/network-fail')
            ).rejects.toThrow();

            expect(requestCount).toBe(1);
        });
    });

    describe('rate limit handling', () => {
        it('should respect Retry-After header', async () => {
            let requestCount = 0;
            const startTime = Date.now();

            server.use(
                http.get('https://api.sardis.network/api/v2/rate-limited', () => {
                    requestCount++;
                    if (requestCount < 2) {
                        return HttpResponse.json(
                            { error: 'Rate limited' },
                            {
                                status: 429,
                                headers: { 'Retry-After': '1' }, // 1 second
                            }
                        );
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 3,
            });

            const result = await client.request<{ success: boolean }>(
                'GET',
                '/api/v2/rate-limited'
            );

            const elapsedTime = Date.now() - startTime;

            expect(result.success).toBe(true);
            expect(requestCount).toBe(2);
            // Should have waited at least 1 second
            expect(elapsedTime).toBeGreaterThanOrEqual(1000);
        }, 10000);
    });
});

describe('SardisClient Health Check', () => {
    it('should return health status', async () => {
        server.use(
            http.get('https://api.sardis.network/health', () => {
                return HttpResponse.json({
                    status: 'healthy',
                    version: '1.0.0',
                });
            })
        );

        const client = new SardisClient({ apiKey: 'test-key' });
        const health = await client.health();

        expect(health.status).toBe('healthy');
        expect(health.version).toBe('1.0.0');
    });

    it('should handle unhealthy status', async () => {
        server.use(
            http.get('https://api.sardis.network/health', () => {
                return HttpResponse.json({
                    status: 'unhealthy',
                    version: '1.0.0',
                });
            })
        );

        const client = new SardisClient({ apiKey: 'test-key' });
        const health = await client.health();

        expect(health.status).toBe('unhealthy');
    });

    it('should handle health check failure', async () => {
        server.use(
            http.get('https://api.sardis.network/health', () => {
                return HttpResponse.json(
                    { error: 'Service unavailable' },
                    { status: 503 }
                );
            })
        );

        const client = new SardisClient({
            apiKey: 'test-key',
            maxRetries: 1,
        });

        await expect(client.health()).rejects.toThrow();
    });
});

describe('SardisClient Configuration', () => {
    it('should accept all configuration options', () => {
        const client = new SardisClient({
            apiKey: 'test-key',
            baseUrl: 'https://custom.api.example.com',
            timeout: 60000,
            connectTimeout: 15000,
            maxRetries: 5,
            retryDelay: 2000,
            maxRetryDelay: 60000,
            retryOn: [408, 429, 500, 502, 503, 504],
            retryOnNetworkError: true,
            tokenRefresh: {
                refreshToken: async () => 'new-token',
            },
        });

        expect(client).toBeInstanceOf(SardisClient);
    });

    it('should use default values when not specified', () => {
        const client = new SardisClient({ apiKey: 'test-key' });

        expect(client).toBeInstanceOf(SardisClient);
        // Default values are set internally
    });

    it('should strip trailing slash from baseUrl', async () => {
        let requestUrl = '';

        server.use(
            http.get('https://custom.api.example.com/api/v2/test', ({ request }) => {
                requestUrl = request.url;
                return HttpResponse.json({ success: true });
            })
        );

        const client = new SardisClient({
            apiKey: 'test-key',
            baseUrl: 'https://custom.api.example.com/', // Trailing slash
        });

        await client.request('GET', '/api/v2/test');

        // Should not have double slash
        expect(requestUrl).not.toContain('//api');
    });
});
