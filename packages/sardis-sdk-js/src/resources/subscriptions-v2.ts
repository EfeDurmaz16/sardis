/**
 * Subscriptions V2 Resource
 *
 * Manages recurring on-chain subscriptions with support for
 * fixed-amount and usage-based billing models.
 */

import { BaseResource } from './base.js';
import type {
  Subscription,
  CreateSubscriptionInput,
  ListSubscriptionsParams,
  AmendSubscriptionInput,
  ReportUsageInput,
  ReportUsageResponse,
  RequestOptions,
} from '../types.js';

export class SubscriptionsV2Resource extends BaseResource {
  /**
   * Create a new subscription.
   *
   * Sets up a recurring billing relationship between a subscriber
   * and a provider with the specified plan and interval.
   *
   * @param params - Subscription creation parameters
   * @param options - Request options (signal, timeout)
   * @returns The created subscription
   */
  async create(params: CreateSubscriptionInput, options?: RequestOptions): Promise<Subscription> {
    return this._post<Subscription>('/api/v2/subscriptions', params, options);
  }

  /**
   * Get a subscription by ID.
   *
   * @param id - Subscription ID
   * @param options - Request options (signal, timeout)
   * @returns The subscription
   */
  async get(id: string, options?: RequestOptions): Promise<Subscription> {
    return this._get<Subscription>(`/api/v2/subscriptions/${id}`, undefined, options);
  }

  /**
   * List subscriptions.
   *
   * @param params - Optional filter and pagination parameters
   * @param options - Request options (signal, timeout)
   * @returns List of subscriptions
   */
  async list(params?: ListSubscriptionsParams, options?: RequestOptions): Promise<Subscription[]> {
    const response = await this._get<{ subscriptions: Subscription[] } | Subscription[]>(
      '/api/v2/subscriptions',
      params as Record<string, unknown>,
      options
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.subscriptions || [];
  }

  /**
   * Cancel a subscription.
   *
   * Cancels the subscription effective at the end of the current billing period.
   *
   * @param id - Subscription ID
   * @param options - Request options (signal, timeout)
   * @returns The cancelled subscription
   */
  async cancel(id: string, options?: RequestOptions): Promise<Subscription> {
    return this._post<Subscription>(`/api/v2/subscriptions/${id}/cancel`, {}, options);
  }

  /**
   * Amend a subscription.
   *
   * Updates subscription parameters such as amount, interval, or plan.
   * Changes take effect at the next billing cycle.
   *
   * @param id - Subscription ID
   * @param params - Amendment parameters
   * @param options - Request options (signal, timeout)
   * @returns The updated subscription
   */
  async amend(
    id: string,
    params: AmendSubscriptionInput,
    options?: RequestOptions
  ): Promise<Subscription> {
    return this._patch<Subscription>(`/api/v2/subscriptions/${id}`, params, options);
  }

  /**
   * Report usage for a usage-based subscription.
   *
   * Records usage events that will be included in the next billing cycle.
   * Use the idempotency_key to prevent double-counting.
   *
   * @param id - Subscription ID
   * @param params - Usage report parameters
   * @param options - Request options (signal, timeout)
   * @returns Updated usage summary
   */
  async reportUsage(
    id: string,
    params: ReportUsageInput,
    options?: RequestOptions
  ): Promise<ReportUsageResponse> {
    return this._post<ReportUsageResponse>(
      `/api/v2/subscriptions/${id}/usage`,
      params,
      options
    );
  }
}
