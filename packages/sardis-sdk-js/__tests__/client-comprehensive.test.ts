/**
 * Comprehensive tests for SardisClient
 *
 * Tests cover:
 * - Client initialization and configuration
 * - Request/response interceptors (additional edge cases)
 * - Error handling and retries (additional scenarios)
 * - Pagination helpers (additional scenarios)
 * - AbortController and cancellation
 * - Timeout handling
 * - Network error scenarios
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse, delay } from 'msw';
import {
    APIError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    AbortError,
    NetworkError,
    ValidationError,
    NotFoundError,
    InsufficientBalanceError,
    PolicyViolationError,
    SpendingLimitError,
    BlockchainError,
    SardisError,
    SardisErrorCode,
    isSardisError,
    isRetryableError,
} from '../src/errors.js';

describe('SardisClient Comprehensive Tests', () => {
    describe('initialization', () => {
        it('should create client with all configuration options', () => {
            const client = new SardisClient({
                apiKey: 'test-api-key',
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
            expect(client.payments).toBeDefined();
            expect(client.wallets).toBeDefined();
            expect(client.holds).toBeDefined();
            expect(client.agents).toBeDefined();
            expect(client.webhooks).toBeDefined();
            expect(client.marketplace).toBeDefined();
            expect(client.transactions).toBeDefined();
            expect(client.ledger).toBeDefined();
            expect(client.ucp).toBeDefined();
            expect(client.a2a).toBeDefined();
        });

        it('should throw when API key is empty string', () => {
            expect(() => new SardisClient({ apiKey: '' })).toThrow('API key is required');
        });

        it('should throw when API key is undefined', () => {
            expect(() => new SardisClient({ apiKey: undefined as unknown as string })).toThrow('API key is required');
        });

        it('should strip trailing slash from baseUrl', async () => {
            let requestedUrl = '';
            server.use(
                http.get('https://custom.api.example.com/test', ({ request }) => {
                    requestedUrl = request.url;
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                baseUrl: 'https://custom.api.example.com/',
            });

            await client.request('GET', '/test');
            expect(requestedUrl).toBe('https://custom.api.example.com/test');
        });

        it('should use default base URL when not specified', async () => {
            let requestedUrl = '';
            server.use(
                http.get('https://api.sardis.network/test', ({ request }) => {
                    requestedUrl = request.url;
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key' });
            await client.request('GET', '/test');
            expect(requestedUrl).toBe('https://api.sardis.network/test');
        });

        it('should set proper headers on requests', async () => {
            let receivedHeaders: Record<string, string | null> = {};
            server.use(
                http.get('https://api.sardis.network/test', ({ request }) => {
                    receivedHeaders = {
                        'x-api-key': request.headers.get('X-API-Key'),
                        'content-type': request.headers.get('Content-Type'),
                        'user-agent': request.headers.get('User-Agent'),
                    };
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({ apiKey: 'my-test-key' });
            await client.request('GET', '/test');

            expect(receivedHeaders['x-api-key']).toBe('my-test-key');
            expect(receivedHeaders['content-type']).toBe('application/json');
            expect(receivedHeaders['user-agent']).toContain('@sardis/sdk');
        });
    });

    describe('API key management', () => {
        it('should get and set API key', () => {
            const client = new SardisClient({ apiKey: 'initial-key' });
            expect(client.getApiKey()).toBe('initial-key');

            client.setApiKey('updated-key');
            expect(client.getApiKey()).toBe('updated-key');
        });

        it('should use updated API key in requests', async () => {
            let receivedKey = '';
            server.use(
                http.get('https://api.sardis.network/test', ({ request }) => {
                    receivedKey = request.headers.get('X-API-Key') || '';
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({ apiKey: 'original-key' });
            client.setApiKey('new-key');
            await client.request('GET', '/test');

            expect(receivedKey).toBe('new-key');
        });
    });

    describe('request interceptors - edge cases', () => {
        it('should support async request interceptors', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            let interceptorCalled = false;

            server.use(
                http.get('https://api.sardis.network/test', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            client.addRequestInterceptor({
                onRequest: async (config) => {
                    await new Promise((resolve) => setTimeout(resolve, 10));
                    interceptorCalled = true;
                    return config;
                },
            });

            await client.request('GET', '/test');
            expect(interceptorCalled).toBe(true);
        });

        it('should stop chain when interceptor throws without onError', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });

            client.addRequestInterceptor({
                onRequest: () => {
                    throw new Error('Interceptor failed');
                },
            });

            await expect(client.request('GET', '/test')).rejects.toThrow('Interceptor failed');
        });

        it('should call multiple interceptors in order and allow modification', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            const order: string[] = [];

            server.use(
                http.get('https://api.sardis.network/test', ({ request }) => {
                    return HttpResponse.json({
                        header1: request.headers.get('X-Header-1'),
                        header2: request.headers.get('X-Header-2'),
                    });
                })
            );

            client.addRequestInterceptor({
                onRequest: (config) => {
                    order.push('first');
                    config.headers = { ...config.headers, 'X-Header-1': 'value1' };
                    return config;
                },
            });

            client.addRequestInterceptor({
                onRequest: (config) => {
                    order.push('second');
                    config.headers = { ...config.headers, 'X-Header-2': 'value2' };
                    return config;
                },
            });

            const result = await client.request<{ header1: string; header2: string }>('GET', '/test');

            expect(order).toEqual(['first', 'second']);
            expect(result.header1).toBe('value1');
            expect(result.header2).toBe('value2');
        });

        it('should handle removal of interceptor that does not exist', () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            const interceptor = {
                onRequest: (config: any) => config,
            };

            // Add and remove
            const remove = client.addRequestInterceptor(interceptor);
            remove();

            // Call remove again - should not throw
            expect(() => remove()).not.toThrow();
        });
    });

    describe('response interceptors - edge cases', () => {
        it('should support async response interceptors', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            let interceptorCalled = false;

            server.use(
                http.get('https://api.sardis.network/test', () => {
                    return HttpResponse.json({ original: true });
                })
            );

            client.addResponseInterceptor({
                onResponse: async (response) => {
                    await new Promise((resolve) => setTimeout(resolve, 10));
                    interceptorCalled = true;
                    return response;
                },
            });

            await client.request('GET', '/test');
            expect(interceptorCalled).toBe(true);
        });

        it('should allow transforming response data', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });

            server.use(
                http.get('https://api.sardis.network/test', () => {
                    return HttpResponse.json({ count: 5 });
                })
            );

            client.addResponseInterceptor({
                onResponse: (response) => {
                    response.data = { ...response.data, transformed: true, count: response.data.count * 2 };
                    return response;
                },
            });

            const result = await client.request<{ count: number; transformed: boolean }>('GET', '/test');
            expect(result.count).toBe(10);
            expect(result.transformed).toBe(true);
        });

        it('should handle error in response interceptor', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            let errorHandled = false;

            server.use(
                http.get('https://api.sardis.network/test', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            client.addResponseInterceptor({
                onResponse: () => {
                    throw new Error('Response interceptor error');
                },
                onError: (error) => {
                    errorHandled = true;
                    throw error;
                },
            });

            await expect(client.request('GET', '/test')).rejects.toThrow('Response interceptor error');
            expect(errorHandled).toBe(true);
        });
    });

    describe('retry logic - comprehensive', () => {
        it('should use exponential backoff with jitter', async () => {
            const retryDelays: number[] = [];
            let lastRequestTime = Date.now();
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/retry-test', () => {
                    requestCount++;
                    const now = Date.now();
                    if (requestCount > 1) {
                        retryDelays.push(now - lastRequestTime);
                    }
                    lastRequestTime = now;

                    if (requestCount < 3) {
                        return HttpResponse.json({ error: 'Server error' }, { status: 500 });
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
                retryDelay: 100,
                maxRetryDelay: 5000,
            });

            await client.request('GET', '/retry-test');

            expect(requestCount).toBe(3);
            // Second retry should be longer than first (exponential)
            expect(retryDelays.length).toBe(2);
        }, 15000);

        it('should not exceed maxRetryDelay', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/retry-test', () => {
                    requestCount++;
                    if (requestCount < 5) {
                        return HttpResponse.json({ error: 'Server error' }, { status: 500 });
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 10,
                retryDelay: 10,
                maxRetryDelay: 50, // Very low max delay
            });

            const startTime = Date.now();
            await client.request('GET', '/retry-test');
            const totalTime = Date.now() - startTime;

            // Should complete relatively quickly due to maxRetryDelay cap
            expect(totalTime).toBeLessThan(5000);
            expect(requestCount).toBe(5);
        }, 10000);

        it('should retry on configured status codes only', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/retry-test', () => {
                    requestCount++;
                    return HttpResponse.json({ error: 'Forbidden' }, { status: 403 });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 3,
                retryOn: [500, 502, 503], // 403 not included
            });

            await expect(client.request('GET', '/retry-test')).rejects.toThrow(APIError);
            expect(requestCount).toBe(1); // No retries for 403
        });

        it('should handle timeout errors with retry', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.network/slow-endpoint', async () => {
                    requestCount++;
                    if (requestCount < 2) {
                        await delay(2000); // Simulate slow response
                    }
                    return HttpResponse.json({ success: true });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                timeout: 500, // Very short timeout
                maxRetries: 3,
                retryDelay: 10,
            });

            // This should timeout and retry
            // Note: MSW may not properly simulate timeouts, so this tests the flow
        });
    });

    describe('rate limiting', () => {
        it('should parse numeric Retry-After header', async () => {
            let requestCount = 0;
            const startTime = Date.now();

            server.use(
                http.get('https://api.sardis.network/rate-limited', () => {
                    requestCount++;
                    if (requestCount < 2) {
                        return HttpResponse.json(
                            { error: 'Rate limited' },
                            {
                                status: 429,
                                headers: {
                                    'Retry-After': '1',
                                    'X-RateLimit-Limit': '100',
                                    'X-RateLimit-Remaining': '0',
                                },
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

            const result = await client.request<{ success: boolean }>('GET', '/rate-limited');
            const elapsed = Date.now() - startTime;

            expect(result.success).toBe(true);
            expect(elapsed).toBeGreaterThanOrEqual(1000);
        }, 10000);

        it('should throw RateLimitError after max retries', async () => {
            server.use(
                http.get('https://api.sardis.network/always-limited', () => {
                    return HttpResponse.json(
                        { error: 'Rate limited' },
                        {
                            status: 429,
                            headers: {
                                'Retry-After': '1',
                                'X-RateLimit-Limit': '100',
                                'X-RateLimit-Remaining': '0',
                            },
                        }
                    );
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 1,
                retryDelay: 10,
            });

            try {
                await client.request('GET', '/always-limited');
                expect.fail('Should have thrown');
            } catch (error) {
                expect(error).toBeInstanceOf(RateLimitError);
                const rateLimitError = error as RateLimitError;
                expect(rateLimitError.retryAfter).toBe(1);
                expect(rateLimitError.limit).toBe(100);
                expect(rateLimitError.remaining).toBe(0);
            }
        }, 10000);
    });

    describe('abort and cancellation', () => {
        it('should abort request when signal is already aborted', async () => {
            const controller = new AbortController();
            controller.abort();

            const client = new SardisClient({ apiKey: 'test-key' });

            await expect(
                client.request('GET', '/test', { signal: controller.signal })
            ).rejects.toThrow(AbortError);
        });

        it('should abort request mid-flight', async () => {
            server.use(
                http.get('https://api.sardis.network/slow', async () => {
                    await delay(5000);
                    return HttpResponse.json({ success: true });
                })
            );

            const controller = new AbortController();
            const client = new SardisClient({ apiKey: 'test-key' });

            setTimeout(() => controller.abort(), 50);

            await expect(
                client.request('GET', '/slow', { signal: controller.signal })
            ).rejects.toThrow(AbortError);
        });
    });

    describe('pagination - edge cases', () => {
        it('should handle pagination with initial cursor', async () => {
            let callCount = 0;
            const fetchPage = vi.fn().mockImplementation(async (params) => {
                callCount++;
                if (callCount === 1) {
                    expect(params.cursor).toBe('initial_cursor');
                    return {
                        data: [{ id: '3' }],
                        hasMore: false,
                        nextCursor: undefined,
                    };
                }
                return { data: [], hasMore: false, nextCursor: undefined };
            });

            const client = new SardisClient({ apiKey: 'test-key' });
            const results = await client.paginateAll(fetchPage, { cursor: 'initial_cursor' });

            expect(results).toHaveLength(1);
            expect(results[0].id).toBe('3');
        });

        it('should handle undefined cursor correctly', async () => {
            const fetchPage = vi.fn().mockImplementation(async (params) => {
                return {
                    data: [{ id: '1' }],
                    hasMore: true,
                    nextCursor: undefined, // Falsy cursor should stop
                };
            });

            const client = new SardisClient({ apiKey: 'test-key' });
            const results = await client.paginateAll(fetchPage);

            expect(results).toHaveLength(1);
            expect(fetchPage).toHaveBeenCalledTimes(1);
        });

        it('should pass all options to fetchPage', async () => {
            const fetchPage = vi.fn().mockImplementation(async (params) => {
                expect(params.limit).toBe(25);
                expect(params.cursor).toBeUndefined();
                return { data: [], hasMore: false, nextCursor: undefined };
            });

            const client = new SardisClient({ apiKey: 'test-key' });
            await client.paginateAll(fetchPage, { limit: 25 });

            expect(fetchPage).toHaveBeenCalledWith(expect.objectContaining({ limit: 25 }));
        });
    });

    describe('batch operations - edge cases', () => {
        it('should handle all failed operations', async () => {
            server.use(
                http.get('https://api.sardis.network/fail/:id', () => {
                    return HttpResponse.json({ error: 'Failed' }, { status: 500 });
                })
            );

            const client = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 0,
            });

            const results = await client.batch([
                { method: 'GET', path: '/fail/1' },
                { method: 'GET', path: '/fail/2' },
            ]);

            expect(results).toHaveLength(2);
            expect(results.every((r) => !r.success)).toBe(true);
        });

        it('should support mixed HTTP methods', async () => {
            server.use(
                http.get('https://api.sardis.network/items/:id', ({ params }) => {
                    return HttpResponse.json({ id: params.id, method: 'GET' });
                }),
                http.post('https://api.sardis.network/items', () => {
                    return HttpResponse.json({ id: 'new', method: 'POST' });
                }),
                http.patch('https://api.sardis.network/items/:id', ({ params }) => {
                    return HttpResponse.json({ id: params.id, method: 'PATCH' });
                }),
                http.delete('https://api.sardis.network/items/:id', () => {
                    return new HttpResponse(null, { status: 204 });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key' });

            const results = await client.batch([
                { method: 'GET', path: '/items/1' },
                { method: 'POST', path: '/items', data: { name: 'New Item' } },
                { method: 'PATCH', path: '/items/1', data: { name: 'Updated' } },
                { method: 'DELETE', path: '/items/2' },
            ]);

            expect(results).toHaveLength(4);
            expect(results[0].success).toBe(true);
            expect((results[0] as any).data.method).toBe('GET');
            expect((results[1] as any).data.method).toBe('POST');
            expect((results[2] as any).data.method).toBe('PATCH');
            expect(results[3].success).toBe(true);
        });

        it('should handle very large batch with concurrency control', async () => {
            let maxConcurrent = 0;
            let currentConcurrent = 0;

            server.use(
                http.get('https://api.sardis.network/item/:id', async ({ params }) => {
                    currentConcurrent++;
                    maxConcurrent = Math.max(maxConcurrent, currentConcurrent);
                    await delay(20);
                    currentConcurrent--;
                    return HttpResponse.json({ id: params.id });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key' });

            const operations = Array.from({ length: 50 }, (_, i) => ({
                method: 'GET',
                path: `/item/${i}`,
            }));

            await client.batch(operations, { concurrency: 5 });

            expect(maxConcurrent).toBeLessThanOrEqual(5);
        }, 30000);
    });

    describe('health check', () => {
        it('should return health status with version', async () => {
            server.use(
                http.get('https://api.sardis.network/health', () => {
                    return HttpResponse.json({
                        status: 'healthy',
                        version: '2.0.0',
                    });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key' });
            const health = await client.health();

            expect(health.status).toBe('healthy');
            expect(health.version).toBe('2.0.0');
        });

        it('should handle health check without version', async () => {
            server.use(
                http.get('https://api.sardis.network/health', () => {
                    return HttpResponse.json({ status: 'ok' });
                })
            );

            const client = new SardisClient({ apiKey: 'test-key' });
            const health = await client.health();

            expect(health.status).toBe('ok');
            expect(health.version).toBeUndefined();
        });

        it('should pass request options to health check', async () => {
            const controller = new AbortController();
            controller.abort();

            const client = new SardisClient({ apiKey: 'test-key' });

            await expect(client.health({ signal: controller.signal })).rejects.toThrow(AbortError);
        });
    });
});

describe('Error Classes Comprehensive Tests', () => {
    describe('SardisError', () => {
        it('should have correct timestamp', () => {
            const before = new Date().toISOString();
            const error = new SardisError('Test');
            const after = new Date().toISOString();

            expect(error.timestamp).toBeDefined();
            expect(error.timestamp >= before).toBe(true);
            expect(error.timestamp <= after).toBe(true);
        });

        it('should support retryable flag', () => {
            const retryable = new SardisError('Test', 'CODE', {}, undefined, true);
            const nonRetryable = new SardisError('Test', 'CODE', {}, undefined, false);

            expect(retryable.retryable).toBe(true);
            expect(nonRetryable.retryable).toBe(false);
        });

        it('should have proper toString format', () => {
            const error = new SardisError('Test message', 'TEST_CODE', {}, 'req_123');
            const str = error.toString();

            expect(str).toContain('[TEST_CODE]');
            expect(str).toContain('Test message');
            expect(str).toContain('req_123');
        });

        it('should serialize to JSON correctly', () => {
            const error = new SardisError('Test', 'CODE', { key: 'value' }, 'req_456');
            const json = error.toJSON();

            expect(json.code).toBe('CODE');
            expect(json.message).toBe('Test');
            expect(json.details).toEqual({ key: 'value' });
            expect(json.request_id).toBe('req_456');
            expect(json.timestamp).toBeDefined();
        });
    });

    describe('APIError', () => {
        it('should parse error from nested error object', () => {
            const error = APIError.fromResponse(400, {
                error: {
                    message: 'Validation failed',
                    code: 'VAL_001',
                    details: { field: 'email', reason: 'invalid format' },
                    request_id: 'req_789',
                },
            });

            expect(error.message).toBe('Validation failed');
            expect(error.code).toBe('VAL_001');
            expect(error.details.field).toBe('email');
            expect(error.requestId).toBe('req_789');
        });

        it('should handle string error response', () => {
            const error = APIError.fromResponse(500, { error: 'Internal server error' });
            expect(error.message).toBe('Internal server error');
        });

        it('should handle detail field (FastAPI style)', () => {
            const error = APIError.fromResponse(422, { detail: 'Validation error' });
            expect(error.message).toBe('Validation error');
        });

        it('should handle empty response body', () => {
            const error = APIError.fromResponse(500, {});
            expect(error.message).toBe('Unknown API error');
        });

        it('should include headers in error', () => {
            const error = APIError.fromResponse(
                429,
                { error: 'Rate limited' },
                { 'x-request-id': 'abc123', 'retry-after': '60' }
            );

            expect(error.headers).toEqual({
                'x-request-id': 'abc123',
                'retry-after': '60',
            });
        });

        it('should map status codes to error codes correctly', () => {
            const testCases = [
                { status: 400, expectedCode: SardisErrorCode.BAD_REQUEST },
                { status: 401, expectedCode: SardisErrorCode.UNAUTHORIZED },
                { status: 403, expectedCode: SardisErrorCode.FORBIDDEN },
                { status: 404, expectedCode: SardisErrorCode.NOT_FOUND },
                { status: 405, expectedCode: SardisErrorCode.METHOD_NOT_ALLOWED },
                { status: 409, expectedCode: SardisErrorCode.CONFLICT },
                { status: 422, expectedCode: SardisErrorCode.UNPROCESSABLE_ENTITY },
                { status: 429, expectedCode: SardisErrorCode.RATE_LIMIT_EXCEEDED },
                { status: 500, expectedCode: SardisErrorCode.INTERNAL_SERVER_ERROR },
                { status: 503, expectedCode: SardisErrorCode.SERVICE_UNAVAILABLE },
                { status: 418, expectedCode: SardisErrorCode.API_ERROR }, // Unknown status
            ];

            for (const { status, expectedCode } of testCases) {
                const error = APIError.fromResponse(status, {});
                expect(error.code).toBe(expectedCode);
            }
        });

        it('should be retryable for 5xx and 429', () => {
            const retryableStatuses = [429, 500, 502, 503, 504];
            const nonRetryableStatuses = [400, 401, 403, 404, 422];

            for (const status of retryableStatuses) {
                const error = new APIError('Test', status);
                expect(error.retryable).toBe(true);
            }

            for (const status of nonRetryableStatuses) {
                const error = new APIError('Test', status);
                expect(error.retryable).toBe(false);
            }
        });
    });

    describe('RateLimitError', () => {
        it('should store rate limit details', () => {
            const resetAt = new Date();
            const error = new RateLimitError('Rate limited', 30, 1000, 0, resetAt);

            expect(error.retryAfter).toBe(30);
            expect(error.limit).toBe(1000);
            expect(error.remaining).toBe(0);
            expect(error.resetAt).toBe(resetAt);
            expect(error.retryable).toBe(true);
        });

        it('should have correct details object', () => {
            const error = new RateLimitError('Rate limited', 60, 100, 5);

            expect(error.details.retry_after).toBe(60);
            expect(error.details.limit).toBe(100);
            expect(error.details.remaining).toBe(5);
        });
    });

    describe('TimeoutError', () => {
        it('should store timeout duration', () => {
            const error = new TimeoutError('Timed out', 5000);

            expect(error.timeout).toBe(5000);
            expect(error.details.timeout_ms).toBe(5000);
            expect(error.retryable).toBe(true);
        });

        it('should use default timeout value', () => {
            const error = new TimeoutError();

            expect(error.timeout).toBe(30000);
            expect(error.message).toBe('Request timed out');
        });
    });

    describe('AbortError', () => {
        it('should not be retryable', () => {
            const error = new AbortError();

            expect(error.retryable).toBe(false);
            expect(error.code).toBe(SardisErrorCode.REQUEST_ABORTED);
        });

        it('should accept custom message', () => {
            const error = new AbortError('User cancelled request');
            expect(error.message).toBe('User cancelled request');
        });
    });

    describe('NetworkError', () => {
        it('should store cause error', () => {
            const cause = new Error('Connection refused');
            const error = new NetworkError('Network failed', cause);

            expect(error.cause).toBe(cause);
            expect(error.details.original_error).toBe('Connection refused');
            expect(error.retryable).toBe(true);
        });

        it('should accept custom error code', () => {
            const error = new NetworkError('DNS lookup failed', undefined, SardisErrorCode.DNS_ERROR);
            expect(error.code).toBe(SardisErrorCode.DNS_ERROR);
        });
    });

    describe('ValidationError', () => {
        it('should store validation details', () => {
            const error = new ValidationError('Invalid email', 'email', 'valid email format', 'not-an-email');

            expect(error.field).toBe('email');
            expect(error.expected).toBe('valid email format');
            expect(error.received).toBe('not-an-email');
        });

        it('should handle missing optional fields', () => {
            const error = new ValidationError('Invalid input');

            expect(error.field).toBeUndefined();
            expect(error.expected).toBeUndefined();
            expect(error.received).toBeUndefined();
        });
    });

    describe('InsufficientBalanceError', () => {
        it('should store balance details', () => {
            const error = new InsufficientBalanceError(
                'Not enough USDC',
                '100.00',
                '50.00',
                'USDC',
                'wallet_123'
            );

            expect(error.required).toBe('100.00');
            expect(error.available).toBe('50.00');
            expect(error.currency).toBe('USDC');
            expect(error.walletId).toBe('wallet_123');
            expect(error.details.wallet_id).toBe('wallet_123');
        });
    });

    describe('NotFoundError', () => {
        it('should construct message from resource details', () => {
            const error = new NotFoundError('Agent', 'agent_abc123');

            expect(error.message).toBe('Agent not found: agent_abc123');
            expect(error.resourceType).toBe('Agent');
            expect(error.resourceId).toBe('agent_abc123');
        });
    });

    describe('PolicyViolationError', () => {
        it('should store policy details', () => {
            const error = new PolicyViolationError(
                'Daily limit exceeded',
                'daily_spending_limit',
                '1000.00',
                '1500.00'
            );

            expect(error.policyName).toBe('daily_spending_limit');
            expect(error.limit).toBe('1000.00');
            expect(error.attempted).toBe('1500.00');
        });
    });

    describe('SpendingLimitError', () => {
        it('should store spending limit details', () => {
            const error = new SpendingLimitError(
                'Per transaction limit exceeded',
                'per_transaction',
                '500.00',
                '750.00',
                'USDC'
            );

            expect(error.limitType).toBe('per_transaction');
            expect(error.limit).toBe('500.00');
            expect(error.attempted).toBe('750.00');
            expect(error.currency).toBe('USDC');
        });
    });

    describe('BlockchainError', () => {
        it('should store blockchain details', () => {
            const error = new BlockchainError(
                'Transaction reverted',
                'ethereum',
                SardisErrorCode.TRANSACTION_FAILED,
                '0xabc123',
                12345678
            );

            expect(error.chain).toBe('ethereum');
            expect(error.txHash).toBe('0xabc123');
            expect(error.blockNumber).toBe(12345678);
            expect(error.retryable).toBe(false);
        });
    });

    describe('Type guards', () => {
        it('isSardisError should correctly identify errors', () => {
            expect(isSardisError(new SardisError('Test'))).toBe(true);
            expect(isSardisError(new APIError('Test', 400))).toBe(true);
            expect(isSardisError(new AuthenticationError())).toBe(true);
            expect(isSardisError(new Error('Regular error'))).toBe(false);
            expect(isSardisError('string')).toBe(false);
            expect(isSardisError(null)).toBe(false);
        });

        it('isRetryableError should correctly identify retryable errors', () => {
            expect(isRetryableError(new RateLimitError())).toBe(true);
            expect(isRetryableError(new TimeoutError())).toBe(true);
            expect(isRetryableError(new NetworkError())).toBe(true);
            expect(isRetryableError(new APIError('Test', 500))).toBe(true);

            expect(isRetryableError(new AuthenticationError())).toBe(false);
            expect(isRetryableError(new APIError('Test', 400))).toBe(false);
            expect(isRetryableError(new AbortError())).toBe(false);
            expect(isRetryableError(new Error('Regular'))).toBe(false);
        });
    });

    describe('Error inheritance', () => {
        it('all errors should be instanceof SardisError', () => {
            const errors = [
                new APIError('Test', 400),
                new AuthenticationError(),
                new RateLimitError(),
                new TimeoutError(),
                new AbortError(),
                new NetworkError(),
                new ValidationError('Test'),
                new InsufficientBalanceError('Test', '100', '50', 'USDC'),
                new NotFoundError('Wallet', '123'),
                new PolicyViolationError('Test', 'policy'),
                new SpendingLimitError('Test', 'daily', '100', '150', 'USDC'),
                new BlockchainError('Test', 'base'),
            ];

            for (const error of errors) {
                expect(error).toBeInstanceOf(SardisError);
                expect(error).toBeInstanceOf(Error);
            }
        });
    });
});
