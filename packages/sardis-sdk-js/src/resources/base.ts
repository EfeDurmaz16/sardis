/**
 * Base resource class for all API resources.
 *
 * Provides common HTTP methods with support for:
 * - Request options (params, data, signal, timeout)
 * - Request cancellation via AbortController
 * - Consistent error handling
 *
 * @packageDocumentation
 */

import type { SardisClient } from '../client.js';
import type { RequestOptions } from '../types.js';

/**
 * Abstract base class for API resources.
 *
 * All resource classes extend this class to gain access to
 * HTTP methods that integrate with the SardisClient.
 *
 * @example
 * ```typescript
 * class MyResource extends BaseResource {
 *   async getItem(id: string, options?: RequestOptions) {
 *     return this._get<Item>(`/api/v2/items/${id}`, undefined, options);
 *   }
 * }
 * ```
 */
export abstract class BaseResource {
  /**
   * The SardisClient instance used for HTTP requests.
   * @internal
   */
  protected client: SardisClient;

  /**
   * Creates a new BaseResource instance.
   *
   * @param client - The SardisClient instance
   */
  constructor(client: SardisClient) {
    this.client = client;
  }

  /**
   * Performs a GET request.
   *
   * @typeParam T - The expected response type
   * @param path - API path
   * @param params - Query parameters
   * @param options - Request options (signal, timeout)
   * @returns The response data
   *
   * @example
   * ```typescript
   * const result = await this._get<Item[]>('/api/v2/items', { limit: 10 });
   * ```
   */
  protected async _get<T>(
    path: string,
    params?: Record<string, unknown>,
    options?: RequestOptions
  ): Promise<T> {
    return this.client.request<T>('GET', path, { ...options, params: params ?? options?.params });
  }

  /**
   * Performs a POST request.
   *
   * @typeParam T - The expected response type
   * @param path - API path
   * @param data - Request body
   * @param options - Request options (signal, timeout)
   * @returns The response data
   *
   * @example
   * ```typescript
   * const result = await this._post<Item>('/api/v2/items', { name: 'New Item' });
   * ```
   */
  protected async _post<T>(
    path: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.client.request<T>('POST', path, { ...options, data: data ?? options?.data });
  }

  /**
   * Performs a PATCH request.
   *
   * @typeParam T - The expected response type
   * @param path - API path
   * @param data - Request body with partial updates
   * @param options - Request options (signal, timeout)
   * @returns The response data
   *
   * @example
   * ```typescript
   * const result = await this._patch<Item>('/api/v2/items/123', { name: 'Updated' });
   * ```
   */
  protected async _patch<T>(
    path: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.client.request<T>('PATCH', path, { ...options, data: data ?? options?.data });
  }

  /**
   * Performs a PUT request.
   *
   * @typeParam T - The expected response type
   * @param path - API path
   * @param data - Request body
   * @param options - Request options (signal, timeout)
   * @returns The response data
   *
   * @example
   * ```typescript
   * const result = await this._put<Item>('/api/v2/items/123', { name: 'Replaced' });
   * ```
   */
  protected async _put<T>(
    path: string,
    data?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    return this.client.request<T>('PUT', path, { ...options, data: data ?? options?.data });
  }

  /**
   * Performs a DELETE request.
   *
   * @typeParam T - The expected response type
   * @param path - API path
   * @param options - Request options (signal, timeout)
   * @returns The response data (if any)
   *
   * @example
   * ```typescript
   * await this._delete('/api/v2/items/123');
   * ```
   */
  protected async _delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.client.request<T>('DELETE', path, options);
  }
}
