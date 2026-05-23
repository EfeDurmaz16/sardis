/**
 * Sardis HTTP engine — native `fetch`, edge-runtime safe, zero deps.
 *
 * Ported from `packages/sardis-sdk-js/src/client.ts:1-1112` (axios) to
 * `fetch` + `AbortController`. Behavior preserved:
 *   - Exponential backoff with jitter
 *   - 429 / 401 / 5xx / network retry
 *   - 401 token refresh hook (one-shot per request)
 *   - x402 header normalization (`WWW-Authenticate: x402 ...` → `x-payment-challenge`)
 *   - Case-insensitive header lookup
 *   - Request / response interceptors
 *   - `signal: AbortSignal` cancellation
 */

import {
  APIError,
  AuthenticationError,
  RateLimitError,
  TimeoutError,
  AbortError,
  NetworkError,
  SardisErrorCode,
} from './errors.js';
import type {
  SardisClientOptions,
  RequestOptions,
  RetryConfig,
  RequestInterceptor,
  ResponseInterceptor,
  TokenRefreshConfig,
  NormalizedRequest,
  HTTPMethod,
  SardisResponse,
  PaginationParams,
  PaginatedResponse,
} from './types.js';

const DEFAULT_BASE_URL = 'https://api.sardis.sh';
const DEFAULT_TIMEOUT = 30_000;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_RETRY_DELAY = 1_000;
const DEFAULT_MAX_RETRY_DELAY = 30_000;
const SDK_VERSION = '2.0.0-rc.0';

/**
 * Low-level HTTP engine. Resource classes call `engine.request(...)`.
 *
 * One engine instance per `Sardis` client. Resources are thin wrappers
 * that build paths + bodies and hand off here.
 */
export class Engine {
  private readonly baseURL: string;
  private apiKey: string;
  private readonly defaultHeaders: Record<string, string>;
  private readonly timeout: number;
  private readonly retryConfig: RetryConfig;
  private readonly tokenRefreshConfig?: TokenRefreshConfig;
  private readonly fetchImpl: typeof globalThis.fetch;
  private readonly requestInterceptors: RequestInterceptor[] = [];
  private readonly responseInterceptors: ResponseInterceptor[] = [];

  constructor(options: SardisClientOptions) {
    if (!options.apiKey) {
      throw new Error('API key is required');
    }
    this.apiKey = options.apiKey;
    this.baseURL = (options.baseURL ?? DEFAULT_BASE_URL).replace(/\/$/, '');
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT;
    this.defaultHeaders = options.defaultHeaders ?? {};
    this.retryConfig = {
      maxRetries: options.maxRetries ?? DEFAULT_MAX_RETRIES,
      retryDelay: options.retryDelay ?? DEFAULT_RETRY_DELAY,
      maxRetryDelay: options.maxRetryDelay ?? DEFAULT_MAX_RETRY_DELAY,
      retryOn: options.retryOn ?? [408, 429, 500, 502, 503, 504],
      retryOnNetworkError: options.retryOnNetworkError ?? true,
    };
    this.tokenRefreshConfig = options.tokenRefresh;
    // `globalThis.fetch` is available on Node 18+, Edge runtimes, Bun, Deno.
    const f = options.fetch ?? globalThis.fetch;
    if (!f) {
      throw new Error(
        'No global `fetch` available. Pass `fetch` in options or upgrade to Node 18+.'
      );
    }
    this.fetchImpl = f.bind(globalThis);
  }

  // ───────────────────────────────────────────────────────── auth

  setApiKey(apiKey: string): void {
    this.apiKey = apiKey;
  }

  getApiKey(): string {
    return this.apiKey;
  }

  // ───────────────────────────────────────────────────────── interceptors

  addRequestInterceptor(interceptor: RequestInterceptor): () => void {
    this.requestInterceptors.push(interceptor);
    return () => {
      const i = this.requestInterceptors.indexOf(interceptor);
      if (i !== -1) this.requestInterceptors.splice(i, 1);
    };
  }

  addResponseInterceptor(interceptor: ResponseInterceptor): () => void {
    this.responseInterceptors.push(interceptor);
    return () => {
      const i = this.responseInterceptors.indexOf(interceptor);
      if (i !== -1) this.responseInterceptors.splice(i, 1);
    };
  }

  // ───────────────────────────────────────────────────────── request

  async request<T>(method: HTTPMethod, path: string, options: RequestOptions = {}): Promise<T> {
    const url = this.buildUrl(path, options.params);
    const headers: Record<string, string> = {
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json',
      'User-Agent': `sardis-js/${SDK_VERSION}`,
      Accept: 'application/json',
      ...this.defaultHeaders,
      ...(options.headers ?? {}),
    };
    if (options.idempotencyKey) {
      headers['Idempotency-Key'] = options.idempotencyKey;
    }

    let req: NormalizedRequest = {
      method,
      url,
      headers,
      body:
        options.data !== undefined && method !== 'GET' && method !== 'HEAD'
          ? JSON.stringify(options.data)
          : undefined,
      signal: options.signal,
      timeout: options.timeout ?? this.timeout,
      _retryCount: 0,
    };

    for (const interceptor of this.requestInterceptors) {
      if (!interceptor.onRequest) continue;
      try {
        req = await interceptor.onRequest(req);
      } catch (err) {
        if (interceptor.onError) await interceptor.onError(err as Error);
        throw err;
      }
    }

    return this.executeWithRetry<T>(req, options.maxRetries ?? this.retryConfig.maxRetries);
  }

  /** Returns full response envelope (status, headers, data). */
  async requestRaw<T>(
    method: HTTPMethod,
    path: string,
    options: RequestOptions = {}
  ): Promise<SardisResponse<T>> {
    // Stash result on a side-channel via response interceptor.
    let captured: SardisResponse<unknown> | undefined;
    const remove = this.addResponseInterceptor({
      onResponse: (response) => {
        captured = response;
        return response;
      },
    });
    try {
      const data = await this.request<T>(method, path, options);
      return (captured as SardisResponse<T> | undefined) ?? { data, status: 200, headers: {} };
    } finally {
      remove();
    }
  }

  // ───────────────────────────────────────────────────────── execute + retry

  private async executeWithRetry<T>(req: NormalizedRequest, maxRetries: number): Promise<T> {
    const retryCount = req._retryCount ?? 0;

    if (req.signal?.aborted) throw new AbortError();

    // Timeout via AbortController, composed with user-supplied signal.
    const timeoutCtrl = new AbortController();
    const timeoutId = setTimeout(() => timeoutCtrl.abort(new Error('timeout')), req.timeout);
    const signal = this.composeSignals(req.signal, timeoutCtrl.signal);

    let res: Response;
    try {
      res = await this.fetchImpl(req.url, {
        method: req.method,
        headers: req.headers,
        body: req.body,
        signal,
      });
    } catch (err) {
      clearTimeout(timeoutId);

      // Distinguish: user abort vs. timeout vs. network error.
      if (req.signal?.aborted) throw new AbortError();
      if (timeoutCtrl.signal.aborted) {
        if (retryCount < maxRetries) {
          await this.sleep(this.calculateRetryDelay(retryCount));
          return this.executeWithRetry<T>(
            { ...req, _retryCount: retryCount + 1 },
            maxRetries
          );
        }
        throw new TimeoutError('Request timed out', req.timeout);
      }

      // Generic network failure.
      if (this.retryConfig.retryOnNetworkError && retryCount < maxRetries) {
        await this.sleep(this.calculateRetryDelay(retryCount));
        return this.executeWithRetry<T>(
          { ...req, _retryCount: retryCount + 1 },
          maxRetries
        );
      }
      throw new NetworkError(
        (err as Error)?.message ?? 'Network error occurred',
        err as Error,
        SardisErrorCode.NETWORK_ERROR
      );
    }
    clearTimeout(timeoutId);

    const headers = this.normalizeResponseHeaders(res.headers);
    const status = res.status;

    // 429 — rate limit (with optional Retry-After)
    if (status === 429) {
      const retryAfter = this.parseRetryAfter(headers);
      if (retryCount < maxRetries) {
        const delay = retryAfter ? retryAfter * 1000 : this.calculateRetryDelay(retryCount);
        await this.sleep(delay);
        return this.executeWithRetry<T>(
          { ...req, _retryCount: retryCount + 1 },
          maxRetries
        );
      }
      const limit = headers['x-ratelimit-limit'] ? Number(headers['x-ratelimit-limit']) : undefined;
      const remaining = headers['x-ratelimit-remaining']
        ? Number(headers['x-ratelimit-remaining'])
        : undefined;
      const resetAt = headers['x-ratelimit-reset']
        ? new Date(Number(headers['x-ratelimit-reset']) * 1000)
        : undefined;
      throw new RateLimitError('Rate limit exceeded', retryAfter, limit, remaining, resetAt);
    }

    // 401 — auth (with one-shot token refresh)
    if (status === 401) {
      if (this.tokenRefreshConfig && retryCount === 0) {
        try {
          const newToken = await this.tokenRefreshConfig.refreshToken();
          this.setApiKey(newToken);
          return this.executeWithRetry<T>(
            {
              ...req,
              headers: { ...req.headers, 'X-API-Key': newToken },
              _retryCount: retryCount + 1,
            },
            maxRetries
          );
        } catch {
          throw new AuthenticationError(
            'Token refresh failed',
            SardisErrorCode.TOKEN_REFRESH_FAILED
          );
        }
      }
      throw new AuthenticationError();
    }

    // 4xx / 5xx
    if (status >= 400) {
      if (this.retryConfig.retryOn.includes(status) && retryCount < maxRetries) {
        await this.sleep(this.calculateRetryDelay(retryCount));
        return this.executeWithRetry<T>(
          { ...req, _retryCount: retryCount + 1 },
          maxRetries
        );
      }
      const body = await this.readJsonSafe(res);
      throw APIError.fromResponse(status, (body ?? {}) as Record<string, unknown>, headers);
    }

    // 2xx — success
    const data = (await this.readJsonSafe(res)) as T;
    let envelope: SardisResponse<T> = {
      data,
      status,
      headers,
      requestId: headers['x-request-id'] ?? headers['x-sardis-request-id'],
    };
    for (const interceptor of this.responseInterceptors) {
      if (!interceptor.onResponse) continue;
      try {
        envelope = await interceptor.onResponse(envelope);
      } catch (err) {
        if (interceptor.onError) await interceptor.onError(err as Error);
        throw err;
      }
    }
    return envelope.data;
  }

  // ───────────────────────────────────────────────────────── pagination

  async *paginate<T>(
    fetchPage: (params: PaginationParams) => Promise<PaginatedResponse<T>>,
    options: PaginationParams = {}
  ): AsyncIterableIterator<T> {
    let cursor = options.cursor;
    let hasMore = true;
    const limit = options.limit ?? 100;
    while (hasMore) {
      const response = await fetchPage({ ...options, limit, cursor });
      for (const item of response.data) yield item;
      hasMore = response.hasMore;
      cursor = response.nextCursor;
      if (!cursor) hasMore = false;
    }
  }

  async paginateAll<T>(
    fetchPage: (params: PaginationParams) => Promise<PaginatedResponse<T>>,
    options: PaginationParams = {}
  ): Promise<T[]> {
    const out: T[] = [];
    for await (const item of this.paginate(fetchPage, options)) out.push(item);
    return out;
  }

  // ───────────────────────────────────────────────────────── helpers

  private buildUrl(path: string, params?: Record<string, unknown>): string {
    const url = new URL(path, this.baseURL + '/');
    // Preserve full path (URL collapses "/" if baseURL has no path).
    const full = path.startsWith('http') ? path : `${this.baseURL}${path.startsWith('/') ? '' : '/'}${path}`;
    const u = new URL(full);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v === undefined || v === null) continue;
        if (Array.isArray(v)) {
          for (const item of v) u.searchParams.append(k, String(item));
        } else {
          u.searchParams.set(k, String(v));
        }
      }
    }
    // `url` is intentionally unused — left for static analysis.
    void url;
    return u.toString();
  }

  private composeSignals(
    a: AbortSignal | undefined,
    b: AbortSignal
  ): AbortSignal {
    if (!a) return b;
    if (typeof (AbortSignal as unknown as { any?: unknown }).any === 'function') {
      // AbortSignal.any is available on Node 20.3+, Bun, Deno, and modern browsers.
      return (AbortSignal as unknown as { any: (signals: AbortSignal[]) => AbortSignal }).any([a, b]);
    }
    const ctrl = new AbortController();
    const onAbort = (signal: AbortSignal) => () => ctrl.abort(signal.reason);
    if (a.aborted) ctrl.abort(a.reason);
    else a.addEventListener('abort', onAbort(a), { once: true });
    if (b.aborted) ctrl.abort(b.reason);
    else b.addEventListener('abort', onAbort(b), { once: true });
    return ctrl.signal;
  }

  private async readJsonSafe(res: Response): Promise<unknown> {
    const ct = res.headers.get('content-type') ?? '';
    if (res.status === 204 || res.headers.get('content-length') === '0') return undefined;
    if (!ct.includes('json')) {
      const text = await res.text().catch(() => '');
      return text || undefined;
    }
    try {
      return await res.json();
    } catch {
      return undefined;
    }
  }

  private normalizeResponseHeaders(h: Headers): Record<string, string> {
    const out: Record<string, string> = {};
    h.forEach((value, key) => {
      out[key] = value;
      out[key.toLowerCase()] = value;
    });
    // x402 PaymentRequired / x-payment-challenge normalization
    const paymentRequired = out['paymentrequired'] ?? out['x-payment-challenge'];
    if (paymentRequired) {
      out['PaymentRequired'] = paymentRequired;
      out['paymentrequired'] = paymentRequired;
      out['x-payment-challenge'] = paymentRequired;
    }
    const wwwAuthenticate = out['www-authenticate'];
    if (wwwAuthenticate && !out['x-payment-challenge']) {
      const parsed = this.parseX402WwwAuthenticate(wwwAuthenticate);
      if (parsed) {
        const challenge = JSON.stringify(parsed);
        out['x-payment-challenge'] = challenge;
        out['PaymentRequired'] = challenge;
        out['paymentrequired'] = challenge;
      }
    }
    return out;
  }

  private parseRetryAfter(headers: Record<string, string>): number | undefined {
    const v = headers['retry-after'];
    if (!v) return undefined;
    const seconds = Number(v);
    if (!Number.isNaN(seconds)) return seconds;
    const date = Date.parse(v);
    if (!Number.isNaN(date)) return Math.max(0, Math.ceil((date - Date.now()) / 1000));
    return undefined;
  }

  private parseX402WwwAuthenticate(value: string): Record<string, string> | undefined {
    if (!value.toLowerCase().startsWith('x402')) return undefined;
    const out: Record<string, string> = {};
    const matcher = /([a-zA-Z0-9_-]+)\s*=\s*"([^"]*)"/g;
    for (const m of value.matchAll(matcher)) {
      const k = m[1];
      const v = m[2];
      if (k && v !== undefined) out[k] = v;
    }
    return Object.keys(out).length > 0 ? out : undefined;
  }

  private calculateRetryDelay(retryCount: number): number {
    const exp = this.retryConfig.retryDelay * Math.pow(2, retryCount);
    const jitter = Math.random() * 0.3 * exp;
    return Math.min(exp + jitter, this.retryConfig.maxRetryDelay);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
