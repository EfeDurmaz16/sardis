/**
 * Sardis API Client for CLI
 *
 * Fetch-based HTTP client with error handling and sandbox detection.
 */

import { CLI_VERSION } from './version.js';
import type { CLIConfig } from './config.js';
import { isSandbox } from './config.js';

export class APIError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`API error ${status}: ${body}`);
    this.name = 'APIError';
  }
}

export class SardisAPI {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly sandbox: boolean;

  constructor(config: CLIConfig) {
    this.baseUrl = config.api_base_url;
    this.apiKey = config.api_key;
    this.sandbox = isSandbox(config);
  }

  isSandbox(): boolean {
    return this.sandbox;
  }

  async get<T = Record<string, unknown>>(path: string, params?: Record<string, string>): Promise<T> {
    let url = `${this.baseUrl}${path.startsWith('/') ? path : '/' + path}`;
    if (params) {
      const qs = new URLSearchParams(params).toString();
      if (qs) url += `?${qs}`;
    }
    return this.request<T>('GET', url);
  }

  async post<T = Record<string, unknown>>(path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : '/' + path}`;
    return this.request<T>('POST', url, body);
  }

  async put<T = Record<string, unknown>>(path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : '/' + path}`;
    return this.request<T>('PUT', url, body);
  }

  async delete<T = Record<string, unknown>>(path: string): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith('/') ? path : '/' + path}`;
    return this.request<T>('DELETE', url);
  }

  private async request<T>(method: string, url: string, body?: unknown): Promise<T> {
    const response = await fetch(url, {
      method,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
        'User-Agent': `sardis-cli/${CLI_VERSION}`,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new APIError(response.status, errorBody);
    }

    return response.json() as Promise<T>;
  }
}
