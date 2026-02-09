/**
 * Sardis TypeScript SDK Client
 *
 * Production-grade client for the Sardis stablecoin execution layer API.
 * Features include:
 * - Request cancellation via AbortController
 * - Request/response interceptors
 * - Automatic retry with exponential backoff
 * - Automatic token refresh
 * - Configurable timeouts
 * - Comprehensive error handling
 *
 * @packageDocumentation
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import {
  APIError,
  AuthenticationError,
  RateLimitError,
  TimeoutError,
  AbortError,
  NetworkError,
  SardisErrorCode,
} from './errors.js';
import { PaymentsResource } from './resources/payments.js';
import { HoldsResource } from './resources/holds.js';
import { WebhooksResource } from './resources/webhooks.js';
import { MarketplaceResource } from './resources/marketplace.js';
import { TransactionsResource } from './resources/transactions.js';
import { LedgerResource } from './resources/ledger.js';
import { WalletsResource } from './resources/wallets.js';
import { AgentsResource } from './resources/agents.js';
import { CardsResource } from './resources/cards.js';
import { PoliciesResource } from './resources/policies.js';
import { UCPResource } from './resources/ucp.js';
import { A2AResource } from './resources/a2a.js';
import type {
  SardisClientOptions,
  RequestOptions,
  RequestInterceptor,
  ResponseInterceptor,
  RetryConfig,
  PaginatedResponse,
  PaginationParams,
  TokenRefreshConfig,
} from './types.js';

/** Default API base URL */
const DEFAULT_BASE_URL = 'https://api.sardis.sh';

/** Default request timeout in milliseconds */
const DEFAULT_TIMEOUT = 30000;

/** Default connection timeout in milliseconds */
const DEFAULT_CONNECT_TIMEOUT = 10000;

/** Default maximum retry attempts */
const DEFAULT_MAX_RETRIES = 3;

/** Default retry delay in milliseconds */
const DEFAULT_RETRY_DELAY = 1000;

/** SDK version for User-Agent header */
const SDK_VERSION = '0.2.0';

/**
 * Internal request configuration with retry tracking
 * @internal
 */
interface InternalRequestConfig extends AxiosRequestConfig {
  _retryCount?: number;
  _startTime?: number;
}

/**
 * Sardis API Client
 *
 * The main entry point for interacting with the Sardis API. Provides access
 * to all API resources through typed methods and handles authentication,
 * retries, and error handling.
 *
 * @example Basic usage
 * ```typescript
 * import { SardisClient } from '@sardis/sdk';
 *
 * const client = new SardisClient({
 *   apiKey: 'your-api-key',
 * });
 *
 * // Execute a payment
 * const result = await client.payments.executeMandate(mandate);
 *
 * // Create a hold
 * const hold = await client.holds.create({
 *   wallet_id: 'wallet_123',
 *   amount: '100.00',
 * });
 * ```
 *
 * @example With request cancellation
 * ```typescript
 * const controller = new AbortController();
 *
 * // Cancel after 5 seconds
 * setTimeout(() => controller.abort(), 5000);
 *
 * try {
 *   const result = await client.payments.executeMandate(mandate, {
 *     signal: controller.signal,
 *   });
 * } catch (error) {
 *   if (error instanceof AbortError) {
 *     console.log('Request was cancelled');
 *   }
 * }
 * ```
 *
 * @example With interceptors
 * ```typescript
 * const client = new SardisClient({ apiKey: 'your-api-key' });
 *
 * // Add request logging
 * client.addRequestInterceptor({
 *   onRequest: (config) => {
 *     console.log(`Requesting ${config.method} ${config.url}`);
 *     return config;
 *   },
 * });
 *
 * // Add response logging
 * client.addResponseInterceptor({
 *   onResponse: (response) => {
 *     console.log(`Response: ${response.status}`);
 *     return response;
 *   },
 * });
 * ```
 */
export class SardisClient {
  /** @internal HTTP client instance */
  private http: AxiosInstance;

  /** @internal Retry configuration */
  private retryConfig: Required<RetryConfig>;

  /** @internal Token refresh configuration */
  private tokenRefreshConfig?: TokenRefreshConfig;

  /** @internal Current API key */
  private apiKey: string;

  /** @internal Request interceptors */
  private requestInterceptors: RequestInterceptor[] = [];

  /** @internal Response interceptors */
  private responseInterceptors: ResponseInterceptor[] = [];

  /** @internal Base URL for API requests */
  private baseUrl: string;

  /** @internal Connection timeout in milliseconds */
  private connectTimeout: number;

  /** @internal Request timeout in milliseconds */
  private timeout: number;

  /**
   * Payment operations - execute mandates and AP2 payment bundles.
   * @see {@link PaymentsResource}
   */
  public readonly payments: PaymentsResource;

  /**
   * Hold operations - create, capture, and void pre-authorization holds.
   * @see {@link HoldsResource}
   */
  public readonly holds: HoldsResource;

  /**
   * Virtual card operations - issue cards and record/simulate purchases.
   * @see {@link CardsResource}
   */
  public readonly cards: CardsResource;

  /**
   * Policy operations - parse/apply natural language policies.
   * @see {@link PoliciesResource}
   */
  public readonly policies: PoliciesResource;

  /**
   * Webhook subscription operations - manage webhook endpoints.
   * @see {@link WebhooksResource}
   */
  public readonly webhooks: WebhooksResource;

  /**
   * Marketplace operations - A2A service discovery and offers.
   * @see {@link MarketplaceResource}
   */
  public readonly marketplace: MarketplaceResource;

  /**
   * Transaction operations - gas estimation and transaction status.
   * @see {@link TransactionsResource}
   */
  public readonly transactions: TransactionsResource;

  /**
   * Ledger operations - query ledger entries.
   * @see {@link LedgerResource}
   */
  public readonly ledger: LedgerResource;

  /**
   * Wallet operations - manage non-custodial wallets.
   * @see {@link WalletsResource}
   */
  public readonly wallets: WalletsResource;

  /**
   * Agent operations - create and manage agents.
   * @see {@link AgentsResource}
   */
  public readonly agents: AgentsResource;

  /**
   * UCP (Universal Commerce Protocol) checkout operations.
   * @see {@link UCPResource}
   */
  public readonly ucp: UCPResource;

  /**
   * A2A (Agent-to-Agent) communication operations.
   * @see {@link A2AResource}
   */
  public readonly a2a: A2AResource;

  /**
   * Creates a new SardisClient instance.
   *
   * @param options - Client configuration options
   * @throws {Error} If API key is not provided
   *
   * @example
   * ```typescript
   * const client = new SardisClient({
   *   apiKey: process.env.SARDIS_API_KEY,
   *   timeout: 60000, // 60 second timeout
   *   maxRetries: 5,
   *   retryDelay: 2000,
   * });
   * ```
   */
  constructor(options: SardisClientOptions) {
    if (!options.apiKey) {
      throw new Error('API key is required');
    }

    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, '');
    this.timeout = options.timeout ?? DEFAULT_TIMEOUT;
    this.connectTimeout = options.connectTimeout ?? DEFAULT_CONNECT_TIMEOUT;

    // Configure retry settings
    this.retryConfig = {
      maxRetries: options.maxRetries ?? DEFAULT_MAX_RETRIES,
      retryDelay: options.retryDelay ?? DEFAULT_RETRY_DELAY,
      maxRetryDelay: options.maxRetryDelay ?? 30000,
      retryOn: options.retryOn ?? [408, 429, 500, 502, 503, 504],
      retryOnNetworkError: options.retryOnNetworkError ?? true,
    };

    // Configure token refresh
    this.tokenRefreshConfig = options.tokenRefresh;

    // Create axios instance
    this.http = axios.create({
      baseURL: this.baseUrl,
      timeout: this.timeout,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json',
        'User-Agent': `@sardis/sdk/${SDK_VERSION}`,
      },
    });

    // Initialize resources
    this.payments = new PaymentsResource(this);
    this.holds = new HoldsResource(this);
    this.cards = new CardsResource(this);
    this.policies = new PoliciesResource(this);
    this.webhooks = new WebhooksResource(this);
    this.marketplace = new MarketplaceResource(this);
    this.transactions = new TransactionsResource(this);
    this.ledger = new LedgerResource(this);
    this.wallets = new WalletsResource(this);
    this.agents = new AgentsResource(this);
    this.ucp = new UCPResource(this);
    this.a2a = new A2AResource(this);
  }

  /**
   * Adds a request interceptor.
   *
   * Request interceptors are called before each request is sent and can
   * modify the request configuration or throw an error to cancel the request.
   *
   * @param interceptor - The interceptor to add
   * @returns A function to remove the interceptor
   *
   * @example
   * ```typescript
   * const removeInterceptor = client.addRequestInterceptor({
   *   onRequest: (config) => {
   *     config.headers['X-Custom-Header'] = 'value';
   *     return config;
   *   },
   *   onError: (error) => {
   *     console.error('Request interceptor error:', error);
   *     throw error;
   *   },
   * });
   *
   * // Later, remove the interceptor
   * removeInterceptor();
   * ```
   */
  addRequestInterceptor(interceptor: RequestInterceptor): () => void {
    this.requestInterceptors.push(interceptor);
    return () => {
      const index = this.requestInterceptors.indexOf(interceptor);
      if (index !== -1) {
        this.requestInterceptors.splice(index, 1);
      }
    };
  }

  /**
   * Adds a response interceptor.
   *
   * Response interceptors are called after each response is received and can
   * modify the response or throw an error.
   *
   * @param interceptor - The interceptor to add
   * @returns A function to remove the interceptor
   *
   * @example
   * ```typescript
   * const removeInterceptor = client.addResponseInterceptor({
   *   onResponse: (response) => {
   *     // Log all responses
   *     console.log(`${response.config.method} ${response.config.url}: ${response.status}`);
   *     return response;
   *   },
   *   onError: (error) => {
   *     // Transform errors
   *     if (error.response?.status === 404) {
   *       throw new NotFoundError('Resource', 'unknown');
   *     }
   *     throw error;
   *   },
   * });
   * ```
   */
  addResponseInterceptor(interceptor: ResponseInterceptor): () => void {
    this.responseInterceptors.push(interceptor);
    return () => {
      const index = this.responseInterceptors.indexOf(interceptor);
      if (index !== -1) {
        this.responseInterceptors.splice(index, 1);
      }
    };
  }

  /**
   * Updates the API key used for authentication.
   *
   * @param apiKey - The new API key
   *
   * @example
   * ```typescript
   * // Update API key after token refresh
   * client.setApiKey(newApiKey);
   * ```
   */
  setApiKey(apiKey: string): void {
    this.apiKey = apiKey;
    // Update the default headers on the axios instance
    this.http.defaults.headers['X-API-Key'] = apiKey;
  }

  /**
   * Gets the current API key.
   *
   * @returns The current API key
   */
  getApiKey(): string {
    return this.apiKey;
  }

  /**
   * Makes an HTTP request with retry logic, interceptors, and cancellation support.
   *
   * @typeParam T - The expected response type
   * @param method - HTTP method
   * @param path - API path
   * @param options - Request options including params, data, and signal
   * @returns The response data
   *
   * @throws {AuthenticationError} If authentication fails
   * @throws {RateLimitError} If rate limit is exceeded
   * @throws {TimeoutError} If request times out
   * @throws {AbortError} If request is cancelled
   * @throws {NetworkError} If network error occurs
   * @throws {APIError} If API returns an error response
   *
   * @example
   * ```typescript
   * const result = await client.request<PaymentResponse>('POST', '/payments', {
   *   data: paymentData,
   *   signal: abortController.signal,
   * });
   * ```
   */
  async request<T>(
    method: string,
    path: string,
    options?: RequestOptions
  ): Promise<T> {
    const config: InternalRequestConfig = {
      method,
      url: path,
      params: options?.params,
      data: options?.data,
      signal: options?.signal,
      timeout: options?.timeout ?? this.timeout,
      headers: {
        'X-API-Key': this.apiKey,
      },
      _retryCount: 0,
      _startTime: Date.now(),
    };

    // Apply request interceptors
    let processedConfig = config;
    for (const interceptor of this.requestInterceptors) {
      try {
        if (interceptor.onRequest) {
          processedConfig = await interceptor.onRequest(processedConfig);
        }
      } catch (error) {
        if (interceptor.onError) {
          await interceptor.onError(error as Error);
        }
        throw error;
      }
    }

    return this.executeWithRetry<T>(processedConfig);
  }

  /**
   * Executes a request with retry logic.
   * @internal
   */
  private async executeWithRetry<T>(config: InternalRequestConfig): Promise<T> {
    const retryCount = config._retryCount ?? 0;

    try {
      // Check for abort signal
      if (config.signal?.aborted) {
        throw new AbortError();
      }

      const response = await this.http.request<T>(config);

      // Apply response interceptors
      let processedResponse = response;
      for (const interceptor of this.responseInterceptors) {
        try {
          if (interceptor.onResponse) {
            processedResponse = await interceptor.onResponse(processedResponse);
          }
        } catch (error) {
          if (interceptor.onError) {
            await interceptor.onError(error as Error);
          }
          throw error;
        }
      }

      return processedResponse.data;
    } catch (error) {
      // Handle abort
      if (axios.isCancel(error) || (error as Error).name === 'AbortError') {
        throw new AbortError();
      }

      // Check if signal was aborted during request
      if (config.signal?.aborted) {
        throw new AbortError();
      }

      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<Record<string, unknown>>;

        // Handle rate limiting
        if (axiosError.response?.status === 429) {
          const retryAfter = this.parseRetryAfter(axiosError.response.headers);
          const resetAt = axiosError.response.headers['x-ratelimit-reset']
            ? new Date(parseInt(axiosError.response.headers['x-ratelimit-reset'] as string) * 1000)
            : undefined;

          if (retryCount < this.retryConfig.maxRetries) {
            const delay = retryAfter ? retryAfter * 1000 : this.calculateRetryDelay(retryCount);
            await this.sleep(delay);
            return this.executeWithRetry<T>({
              ...config,
              _retryCount: retryCount + 1,
            });
          }

          throw new RateLimitError(
            'Rate limit exceeded',
            retryAfter,
            parseInt(axiosError.response.headers['x-ratelimit-limit'] as string),
            parseInt(axiosError.response.headers['x-ratelimit-remaining'] as string),
            resetAt
          );
        }

        // Handle authentication errors
        if (axiosError.response?.status === 401) {
          // Try token refresh if configured
          if (this.tokenRefreshConfig && retryCount === 0) {
            try {
              const newToken = await this.tokenRefreshConfig.refreshToken();
              this.setApiKey(newToken);
              // Update the request config headers with the new token
              const updatedConfig = {
                ...config,
                headers: {
                  ...config.headers,
                  'X-API-Key': newToken,
                },
                _retryCount: retryCount + 1,
              };
              return this.executeWithRetry<T>(updatedConfig);
            } catch {
              throw new AuthenticationError('Token refresh failed', SardisErrorCode.TOKEN_REFRESH_FAILED);
            }
          }
          throw new AuthenticationError();
        }

        // Handle timeout
        if (axiosError.code === 'ECONNABORTED' || axiosError.code === 'ETIMEDOUT') {
          if (retryCount < this.retryConfig.maxRetries) {
            const delay = this.calculateRetryDelay(retryCount);
            await this.sleep(delay);
            return this.executeWithRetry<T>({
              ...config,
              _retryCount: retryCount + 1,
            });
          }
          throw new TimeoutError('Request timed out', config.timeout as number);
        }

        // Handle other API errors
        if (axiosError.response?.status && axiosError.response.status >= 400) {
          // Check if should retry
          if (
            this.retryConfig.retryOn.includes(axiosError.response.status) &&
            retryCount < this.retryConfig.maxRetries
          ) {
            const delay = this.calculateRetryDelay(retryCount);
            await this.sleep(delay);
            return this.executeWithRetry<T>({
              ...config,
              _retryCount: retryCount + 1,
            });
          }

          const headers: Record<string, string> = {};
          Object.entries(axiosError.response.headers).forEach(([key, value]) => {
            if (typeof value === 'string') {
              headers[key] = value;
            }
          });

          throw APIError.fromResponse(
            axiosError.response.status,
            axiosError.response.data || {},
            headers
          );
        }

        // Handle network errors
        if (!axiosError.response) {
          if (this.retryConfig.retryOnNetworkError && retryCount < this.retryConfig.maxRetries) {
            const delay = this.calculateRetryDelay(retryCount);
            await this.sleep(delay);
            return this.executeWithRetry<T>({
              ...config,
              _retryCount: retryCount + 1,
            });
          }
          throw new NetworkError(
            axiosError.message || 'Network error occurred',
            axiosError,
            SardisErrorCode.NETWORK_ERROR
          );
        }
      }

      throw error;
    }
  }

  /**
   * Parses the Retry-After header value.
   * @internal
   */
  private parseRetryAfter(headers: Record<string, unknown>): number | undefined {
    const retryAfter = headers['retry-after'] as string | undefined;
    if (!retryAfter) return undefined;

    // Check if it's a number (seconds)
    const seconds = parseInt(retryAfter, 10);
    if (!isNaN(seconds)) {
      return seconds;
    }

    // Check if it's an HTTP date
    const date = Date.parse(retryAfter);
    if (!isNaN(date)) {
      return Math.max(0, Math.ceil((date - Date.now()) / 1000));
    }

    return undefined;
  }

  /**
   * Calculates retry delay with exponential backoff and jitter.
   * @internal
   */
  private calculateRetryDelay(retryCount: number): number {
    // Exponential backoff with jitter
    const exponentialDelay = this.retryConfig.retryDelay * Math.pow(2, retryCount);
    const jitter = Math.random() * 0.3 * exponentialDelay;
    const delay = exponentialDelay + jitter;
    return Math.min(delay, this.retryConfig.maxRetryDelay);
  }

  /**
   * Creates an async iterator for paginated responses.
   *
   * @typeParam T - The item type in the paginated response
   * @param fetchPage - Function to fetch a page of results
   * @param options - Pagination options
   * @returns An async iterator that yields items from all pages
   *
   * @example
   * ```typescript
   * const iterator = client.paginate<Agent>(
   *   async (params) => {
   *     const response = await client.agents.list(params);
   *     return {
   *       data: response,
   *       hasMore: response.length === params.limit,
   *       nextCursor: response[response.length - 1]?.id,
   *     };
   *   },
   *   { limit: 100 }
   * );
   *
   * for await (const agent of iterator) {
   *   console.log(agent.name);
   * }
   * ```
   */
  async *paginate<T>(
    fetchPage: (params: PaginationParams) => Promise<PaginatedResponse<T>>,
    options: PaginationParams = {}
  ): AsyncIterableIterator<T> {
    let cursor = options.cursor;
    let hasMore = true;
    const limit = options.limit ?? 100;

    while (hasMore) {
      const response = await fetchPage({ ...options, limit, cursor });

      for (const item of response.data) {
        yield item;
      }

      hasMore = response.hasMore;
      cursor = response.nextCursor;

      if (!cursor) {
        hasMore = false;
      }
    }
  }

  /**
   * Creates an async iterator that collects all paginated results into an array.
   *
   * @typeParam T - The item type in the paginated response
   * @param fetchPage - Function to fetch a page of results
   * @param options - Pagination options
   * @returns Promise that resolves to an array of all items
   *
   * @example
   * ```typescript
   * const allAgents = await client.paginateAll<Agent>(
   *   async (params) => {
   *     const response = await client.agents.list(params);
   *     return {
   *       data: response,
   *       hasMore: response.length === params.limit,
   *       nextCursor: response[response.length - 1]?.id,
   *     };
   *   }
   * );
   * console.log(`Found ${allAgents.length} agents`);
   * ```
   */
  async paginateAll<T>(
    fetchPage: (params: PaginationParams) => Promise<PaginatedResponse<T>>,
    options: PaginationParams = {}
  ): Promise<T[]> {
    const results: T[] = [];
    for await (const item of this.paginate(fetchPage, options)) {
      results.push(item);
    }
    return results;
  }

  /**
   * Checks API health status.
   *
   * @param options - Request options
   * @returns Health status response
   *
   * @example
   * ```typescript
   * const health = await client.health();
   * console.log(`API status: ${health.status}, version: ${health.version}`);
   * ```
   */
  async health(options?: RequestOptions): Promise<{ status: string; version?: string }> {
    return this.request<{ status: string; version?: string }>('GET', '/health', options);
  }

  /**
   * Executes multiple operations in a batch.
   *
   * @typeParam T - The response type for each operation
   * @param operations - Array of operations to execute
   * @param options - Batch options
   * @returns Array of results (either success or error for each operation)
   *
   * @example
   * ```typescript
   * const results = await client.batch([
   *   { method: 'GET', path: '/api/v2/wallets/wallet_1' },
   *   { method: 'GET', path: '/api/v2/wallets/wallet_2' },
   *   { method: 'GET', path: '/api/v2/wallets/wallet_3' },
   * ], { concurrency: 3 });
   *
   * results.forEach((result, i) => {
   *   if (result.success) {
   *     console.log(`Operation ${i}: ${result.data}`);
   *   } else {
   *     console.error(`Operation ${i} failed: ${result.error}`);
   *   }
   * });
   * ```
   */
  async batch<T>(
    operations: Array<{
      method: string;
      path: string;
      params?: Record<string, unknown>;
      data?: unknown;
    }>,
    options?: {
      /** Maximum number of concurrent requests (default: 5) */
      concurrency?: number;
      /** Whether to stop on first error (default: false) */
      stopOnError?: boolean;
      /** AbortSignal for cancellation */
      signal?: AbortSignal;
    }
  ): Promise<Array<{ success: true; data: T } | { success: false; error: Error }>> {
    const concurrency = options?.concurrency ?? 5;
    const stopOnError = options?.stopOnError ?? false;
    const signal = options?.signal;

    const results: Array<{ success: true; data: T } | { success: false; error: Error }> = [];
    let stopped = false;

    // Process in chunks
    for (let i = 0; i < operations.length && !stopped; i += concurrency) {
      if (signal?.aborted) {
        throw new AbortError();
      }

      const chunk = operations.slice(i, i + concurrency);
      const chunkResults = await Promise.all(
        chunk.map(async (op) => {
          if (stopped) {
            return { success: false as const, error: new AbortError('Batch stopped') };
          }

          try {
            const data = await this.request<T>(op.method, op.path, {
              params: op.params,
              data: op.data,
              signal,
            });
            return { success: true as const, data };
          } catch (error) {
            // If any request was aborted due to signal, throw immediately
            if (error instanceof AbortError && signal?.aborted) {
              throw error;
            }
            if (stopOnError) {
              stopped = true;
            }
            return { success: false as const, error: error as Error };
          }
        })
      );

      results.push(...chunkResults);
    }

    return results;
  }

  /**
   * Sleep utility for retry delays.
   * @internal
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
