/**
 * Core HTTP types for the Sardis SDK.
 *
 * These are the *low-level* HTTP plumbing types. Domain types
 * (Wallet, Payment, Mandate, ...) live in their respective resource
 * files and subpath façades.
 */

export type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

export interface SardisClientOptions {
  apiKey: string;
  baseURL?: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
  maxRetryDelay?: number;
  retryOn?: number[];
  retryOnNetworkError?: boolean;
  defaultHeaders?: Record<string, string>;
  fetch?: typeof globalThis.fetch;
  tokenRefresh?: TokenRefreshConfig;
  telemetry?: TelemetryConfig | boolean;
}

export interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  maxRetryDelay: number;
  retryOn: number[];
  retryOnNetworkError: boolean;
}

export interface TokenRefreshConfig {
  refreshToken: () => Promise<string>;
}

export interface TelemetryConfig {
  enabled?: boolean;
  endpoint?: string;
  agentId?: string;
  sessionId?: string;
  flushIntervalSeconds?: number;
  heartbeatIntervalSeconds?: number;
}

export interface RequestOptions {
  signal?: AbortSignal;
  timeout?: number;
  idempotencyKey?: string;
  headers?: Record<string, string>;
  params?: Record<string, unknown>;
  data?: unknown;
  maxRetries?: number;
}

export interface SardisResponse<T> {
  data: T;
  status: number;
  headers: Record<string, string>;
  requestId?: string;
}

export interface PaginationParams {
  cursor?: string;
  limit?: number;
  [key: string]: unknown;
}

export interface PaginatedResponse<T> {
  data: T[];
  hasMore: boolean;
  nextCursor?: string;
}

export interface RequestInterceptor {
  onRequest?: (
    init: NormalizedRequest
  ) => NormalizedRequest | Promise<NormalizedRequest>;
  onError?: (error: Error) => void | Promise<void>;
}

export interface ResponseInterceptor {
  onResponse?: <T>(
    response: SardisResponse<T>
  ) => SardisResponse<T> | Promise<SardisResponse<T>>;
  onError?: (error: Error) => void | Promise<void>;
}

/** Normalized request the Engine actually dispatches. */
export interface NormalizedRequest {
  method: HTTPMethod;
  url: string;
  headers: Record<string, string>;
  body?: string;
  signal?: AbortSignal;
  timeout: number;
  /** @internal — used by retry tracking */
  _retryCount?: number;
}
