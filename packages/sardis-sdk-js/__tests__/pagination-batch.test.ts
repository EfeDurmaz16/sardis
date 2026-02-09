/**
 * Tests for SardisClient pagination and batch operations
 *
 * Tests cover:
 * - Async pagination with paginate()
 * - Collecting all paginated results with paginateAll()
 * - Batch operations with concurrency control
 * - Batch operations with stopOnError
 * - Batch cancellation via AbortSignal
 */
import { describe, it, expect, vi } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';
import { AbortError } from '../src/errors.js';

describe('SardisClient Pagination', () => {
    const client = new SardisClient({
        apiKey: 'test-key',
        retryDelay: 10, // Short delay for testing
    });

    describe('paginate', () => {
        it('should iterate through single page', async () => {
            const fetchPage = vi.fn().mockResolvedValue({
                data: [{ id: '1' }, { id: '2' }],
                hasMore: false,
                nextCursor: undefined,
            });

            const items: { id: string }[] = [];
            for await (const item of client.paginate(fetchPage)) {
                items.push(item);
            }

            expect(items).toHaveLength(2);
            expect(fetchPage).toHaveBeenCalledTimes(1);
        });

        it('should iterate through multiple pages', async () => {
            let callCount = 0;
            const fetchPage = vi.fn().mockImplementation(async (params) => {
                callCount++;
                if (callCount === 1) {
                    return {
                        data: [{ id: '1' }, { id: '2' }],
                        hasMore: true,
                        nextCursor: 'cursor_page2',
                    };
                } else if (callCount === 2) {
                    return {
                        data: [{ id: '3' }, { id: '4' }],
                        hasMore: true,
                        nextCursor: 'cursor_page3',
                    };
                } else {
                    return {
                        data: [{ id: '5' }],
                        hasMore: false,
                        nextCursor: undefined,
                    };
                }
            });

            const items: { id: string }[] = [];
            for await (const item of client.paginate(fetchPage)) {
                items.push(item);
            }

            expect(items).toHaveLength(5);
            expect(fetchPage).toHaveBeenCalledTimes(3);
        });

        it('should handle empty first page', async () => {
            const fetchPage = vi.fn().mockResolvedValue({
                data: [],
                hasMore: false,
                nextCursor: undefined,
            });

            const items: { id: string }[] = [];
            for await (const item of client.paginate(fetchPage)) {
                items.push(item);
            }

            expect(items).toHaveLength(0);
            expect(fetchPage).toHaveBeenCalledTimes(1);
        });

        it('should pass cursor to subsequent pages', async () => {
            let callCount = 0;
            const fetchPage = vi.fn().mockImplementation(async (params) => {
                callCount++;
                if (callCount === 1) {
                    expect(params.cursor).toBeUndefined();
                    return {
                        data: [{ id: '1' }],
                        hasMore: true,
                        nextCursor: 'cursor_abc',
                    };
                } else {
                    expect(params.cursor).toBe('cursor_abc');
                    return {
                        data: [{ id: '2' }],
                        hasMore: false,
                        nextCursor: undefined,
                    };
                }
            });

            const items: { id: string }[] = [];
            for await (const item of client.paginate(fetchPage)) {
                items.push(item);
            }

            expect(items).toHaveLength(2);
        });

        it('should respect custom limit', async () => {
            const fetchPage = vi.fn().mockImplementation(async (params) => {
                expect(params.limit).toBe(50);
                return {
                    data: [{ id: '1' }],
                    hasMore: false,
                    nextCursor: undefined,
                };
            });

            const items: { id: string }[] = [];
            for await (const item of client.paginate(fetchPage, { limit: 50 })) {
                items.push(item);
            }

            expect(items).toHaveLength(1);
        });

        it('should use default limit of 100', async () => {
            const fetchPage = vi.fn().mockImplementation(async (params) => {
                expect(params.limit).toBe(100);
                return {
                    data: [],
                    hasMore: false,
                    nextCursor: undefined,
                };
            });

            for await (const _item of client.paginate(fetchPage)) {
                // Just iterate
            }

            expect(fetchPage).toHaveBeenCalledWith(
                expect.objectContaining({ limit: 100 })
            );
        });

        it('should stop when hasMore is false even with cursor', async () => {
            const fetchPage = vi.fn().mockResolvedValue({
                data: [{ id: '1' }],
                hasMore: false,
                nextCursor: 'should_be_ignored',
            });

            const items: { id: string }[] = [];
            for await (const item of client.paginate(fetchPage)) {
                items.push(item);
            }

            expect(items).toHaveLength(1);
            expect(fetchPage).toHaveBeenCalledTimes(1);
        });

        it('should stop when cursor is null', async () => {
            let callCount = 0;
            const fetchPage = vi.fn().mockImplementation(async () => {
                callCount++;
                if (callCount === 1) {
                    return {
                        data: [{ id: '1' }],
                        hasMore: true,
                        nextCursor: null, // null cursor should stop
                    };
                }
                return {
                    data: [{ id: '2' }],
                    hasMore: false,
                    nextCursor: undefined,
                };
            });

            const items: { id: string }[] = [];
            for await (const item of client.paginate(fetchPage)) {
                items.push(item);
            }

            expect(items).toHaveLength(1);
            expect(fetchPage).toHaveBeenCalledTimes(1);
        });
    });

    describe('paginateAll', () => {
        it('should collect all items into array', async () => {
            let callCount = 0;
            const fetchPage = vi.fn().mockImplementation(async () => {
                callCount++;
                if (callCount === 1) {
                    return {
                        data: [{ id: '1' }, { id: '2' }],
                        hasMore: true,
                        nextCursor: 'cursor_2',
                    };
                }
                return {
                    data: [{ id: '3' }],
                    hasMore: false,
                    nextCursor: undefined,
                };
            });

            const results = await client.paginateAll(fetchPage);

            expect(results).toHaveLength(3);
            expect(results[0].id).toBe('1');
            expect(results[2].id).toBe('3');
        });

        it('should return empty array for empty results', async () => {
            const fetchPage = vi.fn().mockResolvedValue({
                data: [],
                hasMore: false,
                nextCursor: undefined,
            });

            const results = await client.paginateAll(fetchPage);

            expect(results).toEqual([]);
        });

        it('should propagate errors from fetchPage', async () => {
            const fetchPage = vi.fn().mockRejectedValue(new Error('Network error'));

            await expect(client.paginateAll(fetchPage)).rejects.toThrow('Network error');
        });

        it('should handle large number of pages', async () => {
            let callCount = 0;
            const totalPages = 50;
            const fetchPage = vi.fn().mockImplementation(async () => {
                callCount++;
                const hasMore = callCount < totalPages;
                return {
                    data: [{ id: `item_${callCount}` }],
                    hasMore,
                    nextCursor: hasMore ? `cursor_${callCount + 1}` : undefined,
                };
            });

            const results = await client.paginateAll(fetchPage);

            expect(results).toHaveLength(totalPages);
            expect(fetchPage).toHaveBeenCalledTimes(totalPages);
        });
    });
});

describe('SardisClient Batch Operations', () => {
    const client = new SardisClient({
        apiKey: 'test-key',
        retryDelay: 10, // Short delay for testing
    });

    describe('batch', () => {
        it('should execute batch of operations', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/items/:id', ({ params }) => {
                    return HttpResponse.json({ id: params.id, name: `Item ${params.id}` });
                })
            );

            const results = await client.batch([
                { method: 'GET', path: '/api/v2/items/1' },
                { method: 'GET', path: '/api/v2/items/2' },
                { method: 'GET', path: '/api/v2/items/3' },
            ]);

            expect(results).toHaveLength(3);
            expect(results.every((r) => r.success)).toBe(true);
            expect((results[0] as any).data.id).toBe('1');
            expect((results[1] as any).data.id).toBe('2');
            expect((results[2] as any).data.id).toBe('3');
        });

        it('should handle mixed success and failure', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/items/:id', ({ params }) => {
                    if (params.id === '2') {
                        return HttpResponse.json(
                            { error: 'Not found' },
                            { status: 404 }
                        );
                    }
                    return HttpResponse.json({ id: params.id });
                })
            );

            const results = await client.batch([
                { method: 'GET', path: '/api/v2/items/1' },
                { method: 'GET', path: '/api/v2/items/2' },
                { method: 'GET', path: '/api/v2/items/3' },
            ]);

            expect(results[0].success).toBe(true);
            expect(results[1].success).toBe(false);
            expect(results[2].success).toBe(true);
        });

        it('should respect concurrency limit', async () => {
            let activeRequests = 0;
            let maxActiveRequests = 0;

            server.use(
                http.get('https://api.sardis.sh/api/v2/slow/:id', async ({ params }) => {
                    activeRequests++;
                    maxActiveRequests = Math.max(maxActiveRequests, activeRequests);
                    await new Promise((resolve) => setTimeout(resolve, 50));
                    activeRequests--;
                    return HttpResponse.json({ id: params.id });
                })
            );

            const operations = Array.from({ length: 10 }, (_, i) => ({
                method: 'GET',
                path: `/api/v2/slow/${i}`,
            }));

            await client.batch(operations, { concurrency: 3 });

            expect(maxActiveRequests).toBeLessThanOrEqual(3);
        });

        it('should use default concurrency of 5', async () => {
            let activeRequests = 0;
            let maxActiveRequests = 0;

            server.use(
                http.get('https://api.sardis.sh/api/v2/slow/:id', async ({ params }) => {
                    activeRequests++;
                    maxActiveRequests = Math.max(maxActiveRequests, activeRequests);
                    await new Promise((resolve) => setTimeout(resolve, 50));
                    activeRequests--;
                    return HttpResponse.json({ id: params.id });
                })
            );

            const operations = Array.from({ length: 20 }, (_, i) => ({
                method: 'GET',
                path: `/api/v2/slow/${i}`,
            }));

            await client.batch(operations);

            expect(maxActiveRequests).toBeLessThanOrEqual(5);
        });

        it('should stop on first error when stopOnError is true', async () => {
            let requestCount = 0;

            server.use(
                http.get('https://api.sardis.sh/api/v2/items/:id', async ({ params }) => {
                    requestCount++;
                    if (params.id === '2') {
                        return HttpResponse.json({ error: 'Failed' }, { status: 500 });
                    }
                    return HttpResponse.json({ id: params.id });
                })
            );

            const results = await client.batch(
                [
                    { method: 'GET', path: '/api/v2/items/1' },
                    { method: 'GET', path: '/api/v2/items/2' },
                    { method: 'GET', path: '/api/v2/items/3' },
                    { method: 'GET', path: '/api/v2/items/4' },
                    { method: 'GET', path: '/api/v2/items/5' },
                ],
                { stopOnError: true, concurrency: 1 }
            );

            // Should have stopped after first failure
            const successCount = results.filter((r) => r.success).length;
            expect(successCount).toBeLessThanOrEqual(2); // Only items before failure
        });

        it('should continue on error when stopOnError is false (default)', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/items/:id', ({ params }) => {
                    if (params.id === '2') {
                        return HttpResponse.json({ error: 'Failed' }, { status: 500 });
                    }
                    return HttpResponse.json({ id: params.id });
                })
            );

            const results = await client.batch([
                { method: 'GET', path: '/api/v2/items/1' },
                { method: 'GET', path: '/api/v2/items/2' },
                { method: 'GET', path: '/api/v2/items/3' },
            ]);

            expect(results).toHaveLength(3);
            expect(results[0].success).toBe(true);
            expect(results[1].success).toBe(false);
            expect(results[2].success).toBe(true);
        });

        it('should support AbortSignal for cancellation', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/slow/:id', async ({ params }) => {
                    await new Promise((resolve) => setTimeout(resolve, 200));
                    return HttpResponse.json({ id: params.id });
                })
            );

            const controller = new AbortController();
            setTimeout(() => controller.abort(), 50);

            await expect(
                client.batch(
                    [
                        { method: 'GET', path: '/api/v2/slow/1' },
                        { method: 'GET', path: '/api/v2/slow/2' },
                    ],
                    { signal: controller.signal }
                )
            ).rejects.toThrow(AbortError);
        });

        it('should handle empty operations array', async () => {
            const results = await client.batch([]);

            expect(results).toEqual([]);
        });

        it('should support POST operations with data', async () => {
            let receivedBodies: any[] = [];

            server.use(
                http.post('https://api.sardis.sh/api/v2/items', async ({ request }) => {
                    const body = await request.json();
                    receivedBodies.push(body);
                    return HttpResponse.json({ id: 'new_item', ...(body as object) });
                })
            );

            const results = await client.batch([
                { method: 'POST', path: '/api/v2/items', data: { name: 'Item 1' } },
                { method: 'POST', path: '/api/v2/items', data: { name: 'Item 2' } },
            ]);

            expect(results).toHaveLength(2);
            expect(results.every((r) => r.success)).toBe(true);
            expect(receivedBodies).toHaveLength(2);
            expect(receivedBodies[0].name).toBe('Item 1');
            expect(receivedBodies[1].name).toBe('Item 2');
        });

        it('should support operations with query params', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/search', ({ request }) => {
                    const url = new URL(request.url);
                    const query = url.searchParams.get('q');
                    return HttpResponse.json({ results: [{ query }] });
                })
            );

            const results = await client.batch([
                { method: 'GET', path: '/api/v2/search', params: { q: 'test1' } },
                { method: 'GET', path: '/api/v2/search', params: { q: 'test2' } },
            ]);

            expect(results).toHaveLength(2);
            expect(results.every((r) => r.success)).toBe(true);
        });
    });
});

describe('SardisClient Interceptors', () => {
    describe('request interceptors', () => {
        it('should call request interceptor before each request', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            const interceptorCalls: any[] = [];

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            client.addRequestInterceptor({
                onRequest: (config) => {
                    interceptorCalls.push(config);
                    return config;
                },
            });

            await client.request('GET', '/api/v2/test');

            expect(interceptorCalls).toHaveLength(1);
            expect(interceptorCalls[0].method).toBe('GET');
            expect(interceptorCalls[0].url).toBe('/api/v2/test');
        });

        it('should allow modifying request config', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            let receivedHeaders: any;

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', ({ request }) => {
                    receivedHeaders = Object.fromEntries(request.headers);
                    return HttpResponse.json({ success: true });
                })
            );

            client.addRequestInterceptor({
                onRequest: (config) => {
                    config.headers = {
                        ...config.headers,
                        'X-Custom-Header': 'custom-value',
                    };
                    return config;
                },
            });

            await client.request('GET', '/api/v2/test');

            expect(receivedHeaders['x-custom-header']).toBe('custom-value');
        });

        it('should chain multiple request interceptors', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            const executionOrder: number[] = [];

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            client.addRequestInterceptor({
                onRequest: (config) => {
                    executionOrder.push(1);
                    return config;
                },
            });

            client.addRequestInterceptor({
                onRequest: (config) => {
                    executionOrder.push(2);
                    return config;
                },
            });

            client.addRequestInterceptor({
                onRequest: (config) => {
                    executionOrder.push(3);
                    return config;
                },
            });

            await client.request('GET', '/api/v2/test');

            expect(executionOrder).toEqual([1, 2, 3]);
        });

        it('should remove interceptor when dispose function is called', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            let interceptorCalled = false;

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            const removeInterceptor = client.addRequestInterceptor({
                onRequest: (config) => {
                    interceptorCalled = true;
                    return config;
                },
            });

            removeInterceptor();

            await client.request('GET', '/api/v2/test');

            expect(interceptorCalled).toBe(false);
        });

        it('should call onError when interceptor throws', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            let errorHandled = false;

            client.addRequestInterceptor({
                onRequest: () => {
                    throw new Error('Interceptor error');
                },
                onError: (error) => {
                    errorHandled = true;
                    throw error;
                },
            });

            await expect(client.request('GET', '/api/v2/test')).rejects.toThrow(
                'Interceptor error'
            );
            expect(errorHandled).toBe(true);
        });
    });

    describe('response interceptors', () => {
        it('should call response interceptor after each response', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            const interceptorCalls: any[] = [];

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', () => {
                    return HttpResponse.json({ data: 'test' });
                })
            );

            client.addResponseInterceptor({
                onResponse: (response) => {
                    interceptorCalls.push(response.data);
                    return response;
                },
            });

            await client.request('GET', '/api/v2/test');

            expect(interceptorCalls).toHaveLength(1);
            expect(interceptorCalls[0]).toEqual({ data: 'test' });
        });

        it('should allow modifying response', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', () => {
                    return HttpResponse.json({ original: true });
                })
            );

            client.addResponseInterceptor({
                onResponse: (response) => {
                    response.data = { ...response.data, modified: true };
                    return response;
                },
            });

            const result = await client.request<any>('GET', '/api/v2/test');

            expect(result.original).toBe(true);
            expect(result.modified).toBe(true);
        });

        it('should chain multiple response interceptors', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            const executionOrder: number[] = [];

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            client.addResponseInterceptor({
                onResponse: (response) => {
                    executionOrder.push(1);
                    return response;
                },
            });

            client.addResponseInterceptor({
                onResponse: (response) => {
                    executionOrder.push(2);
                    return response;
                },
            });

            await client.request('GET', '/api/v2/test');

            expect(executionOrder).toEqual([1, 2]);
        });

        it('should remove response interceptor when dispose function is called', async () => {
            const client = new SardisClient({ apiKey: 'test-key' });
            let interceptorCalled = false;

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            const removeInterceptor = client.addResponseInterceptor({
                onResponse: (response) => {
                    interceptorCalled = true;
                    return response;
                },
            });

            removeInterceptor();

            await client.request('GET', '/api/v2/test');

            expect(interceptorCalled).toBe(false);
        });
    });

    describe('API key management', () => {
        it('should update API key with setApiKey', async () => {
            const client = new SardisClient({ apiKey: 'initial-key' });

            expect(client.getApiKey()).toBe('initial-key');

            client.setApiKey('new-key');

            expect(client.getApiKey()).toBe('new-key');
        });

        it('should use updated API key in subsequent requests', async () => {
            const client = new SardisClient({ apiKey: 'initial-key' });
            let receivedApiKey: string | null = null;

            server.use(
                http.get('https://api.sardis.sh/api/v2/test', ({ request }) => {
                    receivedApiKey = request.headers.get('X-API-Key');
                    return HttpResponse.json({ success: true });
                })
            );

            client.setApiKey('updated-key');
            await client.request('GET', '/api/v2/test');

            expect(receivedApiKey).toBe('updated-key');
        });
    });
});
