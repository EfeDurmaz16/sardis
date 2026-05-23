import { describe, expect, it, vi } from 'vitest';
import {
  Engine,
  APIError,
  AuthenticationError,
  RateLimitError,
  AbortError,
} from '../src/index.js';
import { hmacSha256Hex as hmacWeb, timingSafeEqual as eqWeb } from '../src/shims/web.js';
import { hmacSha256Hex as hmacNode, timingSafeEqual as eqNode } from '../src/shims/node.js';

function fakeFetch(responses: Array<Partial<Response> | (() => Partial<Response>)>) {
  let i = 0;
  return vi.fn(async () => {
    const next = responses[i++];
    const r = typeof next === 'function' ? next() : next;
    const baseHeaders = (r?.headers ?? {}) as Record<string, string>;
    const headers = new Headers({ 'content-type': 'application/json', ...baseHeaders });
    return {
      ok: ((r?.status ?? 200) >= 200 && (r?.status ?? 200) < 300),
      status: r?.status ?? 200,
      headers,
      text: async () => '',
      json: async () => (r as { _json?: unknown })?._json ?? {},
    } as unknown as Response;
  });
}

describe('Engine — fetch core', () => {
  it('builds URL and sends API key header', async () => {
    const fetch = fakeFetch([{ status: 200, _json: { ok: true } } as never]);
    const engine = new Engine({ apiKey: 'sk_test', fetch: fetch as unknown as typeof globalThis.fetch });
    const result = await engine.request<{ ok: boolean }>('GET', '/health');
    expect(result).toEqual({ ok: true });
    const call = fetch.mock.calls[0]!;
    expect(call[0]).toBe('https://api.sardis.sh/health');
    const init = call[1] as RequestInit;
    expect((init.headers as Record<string, string>)['X-API-Key']).toBe('sk_test');
  });

  it('retries on 503 with exponential backoff', async () => {
    const fetch = fakeFetch([
      { status: 503, _json: {} } as never,
      { status: 503, _json: {} } as never,
      { status: 200, _json: { ok: true } } as never,
    ]);
    const engine = new Engine({
      apiKey: 'sk_test',
      fetch: fetch as unknown as typeof globalThis.fetch,
      retryDelay: 1,
      maxRetryDelay: 5,
    });
    const result = await engine.request<{ ok: boolean }>('GET', '/x');
    expect(result.ok).toBe(true);
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it('throws RateLimitError after max retries on 429', async () => {
    const fetch = fakeFetch(
      Array(5).fill({ status: 429, headers: { 'retry-after': '0', 'x-ratelimit-limit': '100' }, _json: {} }) as never
    );
    const engine = new Engine({
      apiKey: 'sk_test',
      fetch: fetch as unknown as typeof globalThis.fetch,
      maxRetries: 2,
      retryDelay: 1,
    });
    await expect(engine.request('GET', '/x')).rejects.toBeInstanceOf(RateLimitError);
  });

  it('throws AuthenticationError on 401 without refresh', async () => {
    const fetch = fakeFetch([{ status: 401, _json: { error: 'unauthorized' } } as never]);
    const engine = new Engine({ apiKey: 'sk_test', fetch: fetch as unknown as typeof globalThis.fetch });
    await expect(engine.request('GET', '/x')).rejects.toBeInstanceOf(AuthenticationError);
  });

  it('refreshes token on 401 once', async () => {
    const fetch = fakeFetch([
      { status: 401, _json: {} } as never,
      { status: 200, _json: { ok: true } } as never,
    ]);
    const refreshToken = vi.fn(async () => 'sk_new');
    const engine = new Engine({
      apiKey: 'sk_old',
      fetch: fetch as unknown as typeof globalThis.fetch,
      tokenRefresh: { refreshToken },
    });
    const result = await engine.request<{ ok: boolean }>('GET', '/x');
    expect(result.ok).toBe(true);
    expect(refreshToken).toHaveBeenCalledOnce();
    expect(engine.getApiKey()).toBe('sk_new');
  });

  it('maps 4xx to APIError', async () => {
    const fetch = fakeFetch([{ status: 422, _json: { error: 'bad', code: 'validation' } } as never]);
    const engine = new Engine({ apiKey: 'sk_test', fetch: fetch as unknown as typeof globalThis.fetch });
    await expect(engine.request('POST', '/x', { data: {} })).rejects.toBeInstanceOf(APIError);
  });

  it('respects AbortSignal', async () => {
    const fetch = vi.fn(async (_url: string, init: RequestInit) => {
      return await new Promise<Response>((_resolve, reject) => {
        init.signal?.addEventListener('abort', () => reject(Object.assign(new Error('aborted'), { name: 'AbortError' })));
      });
    });
    const engine = new Engine({ apiKey: 'sk_test', fetch: fetch as unknown as typeof globalThis.fetch });
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 5);
    await expect(engine.request('GET', '/slow', { signal: ctrl.signal })).rejects.toBeInstanceOf(AbortError);
  });

  it('normalizes x402 WWW-Authenticate into x-payment-challenge', async () => {
    const fetch = fakeFetch([
      {
        status: 402,
        headers: { 'www-authenticate': 'x402 scheme="evm", asset="USDC", amount="1000"' },
        _json: {},
      } as never,
    ]);
    const engine = new Engine({ apiKey: 'sk_test', fetch: fetch as unknown as typeof globalThis.fetch });
    try {
      await engine.request('GET', '/paid');
      throw new Error('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(APIError);
      const headers = (err as APIError).headers ?? {};
      expect(headers['x-payment-challenge']).toContain('USDC');
    }
  });
});

describe('shims/web HMAC', () => {
  it('hmacSha256Hex matches known vector', async () => {
    // RFC 4231 — test case 1: key="key", data="The quick brown fox jumps over the lazy dog"
    const sig = await hmacWeb('key', 'The quick brown fox jumps over the lazy dog');
    expect(sig).toBe('f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8');
  });
  it('timingSafeEqual short-circuits on length', () => {
    expect(eqWeb('abc', 'abcd')).toBe(false);
    expect(eqWeb('abcd', 'abcd')).toBe(true);
    expect(eqWeb('abcd', 'abce')).toBe(false);
  });
});

describe('shims/node HMAC', () => {
  it('hmacSha256Hex matches known vector', async () => {
    const sig = await hmacNode('key', 'The quick brown fox jumps over the lazy dog');
    expect(sig).toBe('f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8');
  });
  it('timingSafeEqual short-circuits on length', () => {
    expect(eqNode('abc', 'abcd')).toBe(false);
    expect(eqNode('abcd', 'abcd')).toBe(true);
  });
});
