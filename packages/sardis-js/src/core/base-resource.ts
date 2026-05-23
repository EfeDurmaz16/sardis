import type { Engine } from './engine.js';
import type { RequestOptions } from './types.js';

/**
 * Base class for resource modules. All resources operate against a shared
 * `Engine` provided by the umbrella `Sardis` client.
 */
export abstract class BaseResource {
  protected engine: Engine;

  constructor(engine: Engine) {
    this.engine = engine;
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
