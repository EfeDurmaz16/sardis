import type { Engine } from './engine.js';
import type { RequestOptions } from './types.js';
import { Page } from './pagination.js';
import type { PageParams, PageResponse } from './pagination.js';

/**
 * Base class for resource modules. All resources operate against a shared
 * `Engine` provided by the umbrella `Sardis` client.
 */
export abstract class BaseResource {
  protected engine: Engine;

  constructor(engine: Engine) {
    this.engine = engine;
  }

  /**
   * Build an auto-paginating {@link Page} for a list endpoint.
   *
   * `dataKey` lets us normalize Sardis's named-array envelopes (e.g.
   * `{ agents: [...] }`) into the standard `{ data: [...] }` page shape, while
   * also supporting cursor envelopes (`{ data, has_more, next_cursor }`).
   *
   * @param path - List endpoint path
   * @param dataKey - Envelope key holding the array (e.g. `'agents'`)
   * @param params - Initial query params (limit/offset/cursor/filters)
   * @param options - Per-request options
   */
  protected async _list<Item>(
    path: string,
    dataKey: string,
    params: PageParams = {},
    options?: RequestOptions
  ): Promise<Page<Item>> {
    const fetcher = async (p: PageParams): Promise<PageResponse<Item>> => {
      const cleaned: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(p)) {
        if (v !== undefined && v !== null) cleaned[k] = v;
      }
      const raw = await this.engine.request<unknown>('GET', path, { ...options, params: cleaned });
      return normalizePageResponse<Item>(raw, dataKey);
    };
    const first = await fetcher(params);
    return new Page<Item>(first, fetcher, params);
  }

  protected _get<T>(path: string, params?: Record<string, unknown>, options?: RequestOptions): Promise<T> {
    return this.engine.request<T>('GET', path, { ...options, params: params ?? options?.params });
  }

  protected _post<T>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.engine.request<T>('POST', path, { ...options, data: data ?? options?.data });
  }

  protected _patch<T>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.engine.request<T>('PATCH', path, { ...options, data: data ?? options?.data });
  }

  protected _put<T>(path: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.engine.request<T>('PUT', path, { ...options, data: data ?? options?.data });
  }

  protected _delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.engine.request<T>('DELETE', path, options);
  }
}

/**
 * Normalize a list endpoint's raw body into the standard {@link PageResponse}
 * shape, accepting: a bare array, a `{ data, has_more, next_cursor }` cursor
 * envelope, or a named-array envelope (`{ agents: [...] }`).
 */
export function normalizePageResponse<Item>(raw: unknown, dataKey: string): PageResponse<Item> {
  if (Array.isArray(raw)) {
    return { data: raw as Item[] };
  }
  const obj = (raw ?? {}) as Record<string, unknown>;
  const data = (Array.isArray(obj.data) ? obj.data : (obj[dataKey] as unknown)) as Item[] | undefined;
  return {
    data: Array.isArray(data) ? data : [],
    has_more: typeof obj.has_more === 'boolean' ? obj.has_more : undefined,
    next_cursor: (obj.next_cursor as string | null | undefined) ?? undefined,
    total: typeof obj.total === 'number' ? obj.total : undefined,
  };
}
