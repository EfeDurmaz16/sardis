/**
 * Base resource class
 */

import type { SardisClient } from '../client.js';

export abstract class BaseResource {
  protected client: SardisClient;

  constructor(client: SardisClient) {
    this.client = client;
  }

  protected async _get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    return this.client.request<T>('GET', path, { params });
  }

  protected async _post<T>(path: string, data?: unknown): Promise<T> {
    return this.client.request<T>('POST', path, { data });
  }

  protected async _patch<T>(path: string, data?: unknown): Promise<T> {
    return this.client.request<T>('PATCH', path, { data });
  }

  protected async _delete<T>(path: string): Promise<T> {
    return this.client.request<T>('DELETE', path);
  }
}
