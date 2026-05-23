/**
 * Usage Metering Resource
 *
 * Report and query usage meters for consumption-based billing.
 * Meters track agent resource usage and feed into invoicing pipelines.
 */

import { BaseResource } from '../core/base-resource.js';
import type { RequestOptions } from '../types.js';

export interface UsageReportParams {
  meter_id: string;
  quantity: number;
  timestamp?: string;
  idempotency_key?: string;
  metadata?: Record<string, unknown>;
}

export interface UsageReportResponse {
  event_id: string;
  meter_id: string;
  quantity: number;
  recorded_at: string;
}

export interface UsageMeter {
  meter_id: string;
  name: string;
  unit: string;
  total_usage: number;
  current_period_usage: number;
  period_start: string;
  period_end: string;
  created_at: string;
}

export interface UsageMeterListParams {
  limit?: number;
  offset?: number;
  agent_id?: string;
}

export interface UsageMeterListResponse {
  meters: UsageMeter[];
  total: number;
  has_more: boolean;
}

export class UsageResource extends BaseResource {
  /**
   * Report a usage event.
   *
   * Records a metered usage event against a specific meter. Supports
   * idempotency keys for safe retry behavior.
   *
   * @param params - Usage report parameters
   * @param options - Request options (signal, timeout)
   * @returns The recorded usage event
   */
  async report(params: UsageReportParams, options?: RequestOptions): Promise<UsageReportResponse> {
    return this._post<UsageReportResponse>('/api/v2/usage/report', params, options);
  }

  /**
   * Get a specific usage meter.
   *
   * Returns the current state of a meter including total and
   * current-period usage.
   *
   * @param meterId - The meter ID to retrieve
   * @param options - Request options (signal, timeout)
   * @returns The usage meter details
   */
  async getMeter(meterId: string, options?: RequestOptions): Promise<UsageMeter> {
    return this._get<UsageMeter>(`/api/v2/usage/meters/${meterId}`, undefined, options);
  }

  /**
   * List usage meters.
   *
   * Returns a paginated list of meters, optionally filtered by agent.
   *
   * @param params - Optional filter and pagination parameters
   * @param options - Request options (signal, timeout)
   * @returns Paginated list of usage meters
   */
  async listMeters(
    params?: UsageMeterListParams,
    options?: RequestOptions
  ): Promise<UsageMeterListResponse> {
    return this._get<UsageMeterListResponse>('/api/v2/usage/meters', params as Record<string, unknown>, options);
  }
}
