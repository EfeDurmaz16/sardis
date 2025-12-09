/**
 * Sardis TypeScript SDK Client
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import { APIError, AuthenticationError, RateLimitError } from './errors.js';
import { PaymentsResource } from './resources/payments.js';
import { HoldsResource } from './resources/holds.js';
import { WebhooksResource } from './resources/webhooks.js';
import { MarketplaceResource } from './resources/marketplace.js';
import { TransactionsResource } from './resources/transactions.js';
import { LedgerResource } from './resources/ledger.js';
import type { SardisClientOptions } from './types.js';

const DEFAULT_BASE_URL = 'https://api.sardis.network';
const DEFAULT_TIMEOUT = 30000;
const DEFAULT_MAX_RETRIES = 3;

/**
 * Sardis API Client
 *
 * Provides access to all Sardis API resources:
 * - payments: Execute mandates and AP2 payment bundles
 * - holds: Create, capture, and void pre-authorization holds
 * - webhooks: Manage webhook subscriptions
 * - marketplace: A2A service discovery and offers
 * - transactions: Gas estimation and transaction status
 * - ledger: Query ledger entries
 *
 * @example
 * ```typescript
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
 */
export class SardisClient {
  private http: AxiosInstance;
  private maxRetries: number;

  /** Payment operations */
  public readonly payments: PaymentsResource;
  /** Hold (pre-authorization) operations */
  public readonly holds: HoldsResource;
  /** Webhook subscription operations */
  public readonly webhooks: WebhooksResource;
  /** A2A marketplace operations */
  public readonly marketplace: MarketplaceResource;
  /** Transaction and gas operations */
  public readonly transactions: TransactionsResource;
  /** Ledger query operations */
  public readonly ledger: LedgerResource;

  constructor(options: SardisClientOptions) {
    if (!options.apiKey) {
      throw new Error('API key is required');
    }

    this.maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;

    this.http = axios.create({
      baseURL: (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, ''),
      timeout: options.timeout ?? DEFAULT_TIMEOUT,
      headers: {
        'X-API-Key': options.apiKey,
        'Content-Type': 'application/json',
        'User-Agent': '@sardis/sdk/0.1.0',
      },
    });

    // Initialize resources
    this.payments = new PaymentsResource(this);
    this.holds = new HoldsResource(this);
    this.webhooks = new WebhooksResource(this);
    this.marketplace = new MarketplaceResource(this);
    this.transactions = new TransactionsResource(this);
    this.ledger = new LedgerResource(this);
  }

  /**
   * Make an HTTP request with retry logic
   */
  async request<T>(
    method: string,
    path: string,
    options?: { params?: Record<string, unknown>; data?: unknown }
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const response = await this.http.request<T>({
          method,
          url: path,
          params: options?.params,
          data: options?.data,
        });

        return response.data;
      } catch (error) {
        if (axios.isAxiosError(error)) {
          const axiosError = error as AxiosError<Record<string, unknown>>;

          // Handle rate limiting
          if (axiosError.response?.status === 429) {
            const retryAfter = parseInt(
              axiosError.response.headers['retry-after'] as string || '5',
              10
            );
            if (attempt < this.maxRetries - 1) {
              await this.sleep(retryAfter * 1000);
              continue;
            }
            throw new RateLimitError('Rate limit exceeded', retryAfter);
          }

          // Handle authentication errors
          if (axiosError.response?.status === 401) {
            throw new AuthenticationError();
          }

          // Handle other API errors
          if (axiosError.response?.status && axiosError.response.status >= 400) {
            throw APIError.fromResponse(
              axiosError.response.status,
              axiosError.response.data || {}
            );
          }

          // Handle network errors with retry
          if (axiosError.code === 'ECONNABORTED' || !axiosError.response) {
            lastError = error as Error;
            if (attempt < this.maxRetries - 1) {
              await this.sleep(Math.pow(2, attempt) * 1000);
              continue;
            }
          }
        }

        throw error;
      }
    }

    if (lastError) {
      throw lastError;
    }

    throw new Error('Unexpected error in request retry loop');
  }

  /**
   * Check API health status
   */
  async health(): Promise<{ status: string; version?: string }> {
    return this.request<{ status: string; version?: string }>('GET', '/health');
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
