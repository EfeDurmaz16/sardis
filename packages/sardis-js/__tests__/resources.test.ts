import { describe, expect, it, vi } from 'vitest';
import {
  Sardis,
  Page,
  APIError,
  BadRequestError,
  AuthenticationError,
  PermissionDeniedError,
  NotFoundError,
  ConflictError,
  UnprocessableEntityError,
  RateLimitError,
  InternalServerError,
} from '../src/index.js';

/**
 * Build a fetch mock that returns scripted responses in order, capturing every
 * request URL + init so tests can assert on headers, methods, and query params.
 */
function scriptedFetch(
  responses: Array<{ status?: number; json?: unknown; headers?: Record<string, string> }>
) {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  let i = 0;
  const fn = vi.fn(async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    const r = responses[Math.min(i, responses.length - 1)];
    i++;
    const status = r?.status ?? 200;
    const headers = new Headers({ 'content-type': 'application/json', ...(r?.headers ?? {}) });
    return {
      ok: status >= 200 && status < 300,
      status,
      headers,
      text: async () => '',
      json: async () => r?.json ?? {},
    } as unknown as Response;
  });
  return { fn: fn as unknown as typeof globalThis.fetch, calls, raw: fn };
}

function client(fetchImpl: typeof globalThis.fetch, overrides = {}) {
  return new Sardis({ apiKey: 'sk_test', fetch: fetchImpl, retryDelay: 1, maxRetryDelay: 5, ...overrides });
}

describe('Sardis — construction', () => {
  it('throws when apiKey is missing', () => {
    // @ts-expect-error — intentionally omitting required apiKey
    expect(() => new Sardis({})).toThrow(/API key is required/);
  });

  it('namespaces every documented resource', () => {
    const s = new Sardis({ apiKey: 'sk_test' });
    for (const ns of [
      'pay',
      'payments',
      'agents',
      'wallets',
      'cards',
      'approvals',
      'evidence',
      'mandateDelegation',
    ] as const) {
      expect((s as Record<string, unknown>)[ns]).toBeDefined();
    }
    expect(typeof s.pay).toBe('function');
  });

  it('honors baseURL + defaultHeaders overrides', async () => {
    const { fn, calls } = scriptedFetch([{ json: { ok: true } }]);
    const s = client(fn, { baseURL: 'https://sandbox.sardis.sh', defaultHeaders: { 'X-Env': 'sandbox' } });
    await s.health();
    expect(calls[0]!.url).toBe('https://sandbox.sardis.sh/health');
    expect((calls[0]!.init.headers as Record<string, string>)['X-Env']).toBe('sandbox');
  });
});

describe('Sardis — auth', () => {
  it('sends the X-API-Key header on every resource call', async () => {
    const { fn, calls } = scriptedFetch([{ json: { agent_id: 'agent_1' } }]);
    await client(fn).agents.get('agent_1');
    expect((calls[0]!.init.headers as Record<string, string>)['X-API-Key']).toBe('sk_test');
  });

  it('setApiKey rotates the key in-place', async () => {
    const { fn, calls } = scriptedFetch([{ json: {} }, { json: {} }]);
    const s = client(fn);
    s.setApiKey('sk_rotated');
    expect(s.getApiKey()).toBe('sk_rotated');
    await s.agents.get('a');
    expect((calls[0]!.init.headers as Record<string, string>)['X-API-Key']).toBe('sk_rotated');
  });
});

describe('Sardis — idempotency on writes', () => {
  it('forwards Idempotency-Key on POST writes', async () => {
    const { fn, calls } = scriptedFetch([{ json: { agent_id: 'agent_1' } }]);
    await client(fn).agents.create({ name: 'A' } as never, { idempotencyKey: 'idem_123' });
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers['Idempotency-Key']).toBe('idem_123');
    expect(calls[0]!.init.method).toBe('POST');
  });

  it('does not attach Idempotency-Key when not provided', async () => {
    const { fn, calls } = scriptedFetch([{ json: {} }]);
    await client(fn).agents.create({ name: 'A' } as never);
    expect((calls[0]!.init.headers as Record<string, string>)['Idempotency-Key']).toBeUndefined();
  });
});

describe('Sardis — retries', () => {
  it('retries a resource call on 503 then succeeds', async () => {
    const { fn, raw } = scriptedFetch([
      { status: 503, json: {} },
      { status: 503, json: {} },
      { status: 200, json: { agent_id: 'agent_1' } },
    ]);
    const agent = await client(fn).agents.get('agent_1');
    expect(agent.agent_id).toBe('agent_1');
    expect(raw).toHaveBeenCalledTimes(3);
  });

  it('per-request maxRetries=0 disables retry on a resource call', async () => {
    const { fn, raw } = scriptedFetch([{ status: 500, json: { error: 'boom' } }]);
    await expect(client(fn).agents.get('a', { maxRetries: 0 })).rejects.toBeInstanceOf(InternalServerError);
    expect(raw).toHaveBeenCalledTimes(1);
  });
});

describe('Sardis — error mapping (Anthropic-style subclasses)', () => {
  const cases: Array<[number, new (...a: never[]) => APIError]> = [
    [400, BadRequestError],
    [401, AuthenticationError],
    [403, PermissionDeniedError],
    [404, NotFoundError],
    [409, ConflictError],
    [422, UnprocessableEntityError],
    [429, RateLimitError],
    [500, InternalServerError],
  ];

  for (const [status, klass] of cases) {
    it(`maps HTTP ${status} -> ${klass.name} (and still instanceof APIError)`, async () => {
      const { fn } = scriptedFetch([
        { status, json: { error: { message: 'nope' } }, headers: { 'retry-after': '0', 'x-request-id': 'req_abc' } },
      ]);
      // maxRetries 0 so 429/5xx surface immediately.
      const err = await client(fn).agents.get('a', { maxRetries: 0 }).catch((e) => e);
      expect(err).toBeInstanceOf(klass);
      expect(err).toBeInstanceOf(APIError);
      expect((err as APIError).statusCode).toBe(status);
      expect((err as APIError).request_id).toBe('req_abc');
    });
  }

  it('surfaces request_id from the request-id header too', async () => {
    const { fn } = scriptedFetch([{ status: 400, json: {}, headers: { 'request-id': 'req_xyz' } }]);
    const err = await client(fn).agents.get('a').catch((e) => e);
    expect((err as APIError).request_id).toBe('req_xyz');
  });
});

describe('Sardis — auto-pagination', () => {
  it('listPage iterates every item across pages (cursor envelope)', async () => {
    const { fn } = scriptedFetch([
      { json: { agents: [{ agent_id: 'a1' }, { agent_id: 'a2' }], has_more: true, next_cursor: 'c2' } },
      { json: { agents: [{ agent_id: 'a3' }], has_more: false } },
    ]);
    const page = await client(fn).agents.listPage({ limit: 2 });
    expect(page).toBeInstanceOf(Page);
    expect(page.data.map((a) => a.agent_id)).toEqual(['a1', 'a2']);
    expect(page.hasNextPage()).toBe(true);

    const all: string[] = [];
    for await (const agent of page) all.push(agent.agent_id);
    expect(all).toEqual(['a1', 'a2', 'a3']);
  });

  it('iterPages walks page objects and follows the cursor', async () => {
    const { fn, calls } = scriptedFetch([
      { json: { agents: [{ agent_id: 'a1' }], has_more: true, next_cursor: 'cursor_2' } },
      { json: { agents: [{ agent_id: 'a2' }], has_more: false } },
    ]);
    const page = await client(fn).agents.listPage({ limit: 1 });
    const pageSizes: number[] = [];
    for await (const p of page.iterPages()) pageSizes.push(p.data.length);
    expect(pageSizes).toEqual([1, 1]);
    // second request must carry the cursor from page one
    expect(calls[1]!.url).toContain('cursor=cursor_2');
  });

  it('normalizes a named-array envelope and offset-paginates when no cursor', async () => {
    const { fn, calls } = scriptedFetch([
      { json: { wallets: [{ wallet_id: 'w1' }, { wallet_id: 'w2' }] } },
      { json: { wallets: [] } },
    ]);
    const page = await client(fn).wallets.listPage({ limit: 2 });
    const ids: string[] = [];
    for await (const w of page) ids.push(w.wallet_id);
    expect(ids).toEqual(['w1', 'w2']);
    // full page (limit met) -> fetch next with offset=2
    expect(calls[1]!.url).toContain('offset=2');
  });
});

describe('Sardis — pay shortcut', () => {
  it('dispatches sardis.pay(...) to wallets.transfer with the from wallet', async () => {
    const { fn, calls } = scriptedFetch([{ json: { transaction_id: 'tx_1' } }]);
    await client(fn).pay({ from: 'wallet_a', to: 'merchant_b', amount: '25.00' });
    expect(calls[0]!.init.method).toBe('POST');
    expect(calls[0]!.url).toContain('/api/v2/wallets/wallet_a/transfer');
    expect(JSON.parse(calls[0]!.init.body as string)).toMatchObject({ destination: 'merchant_b', amount: '25.00' });
  });
});
