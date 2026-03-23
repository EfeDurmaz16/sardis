/**
 * Streaming Payments Resource
 *
 * Open, consume, and settle continuous payment streams between agents
 * and services. Supports usage-based billing with real-time settlement.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface StreamOpenParams {
  from_wallet: string;
  to: string;
  token: string;
  max_amount: string;
  rate_per_unit?: string;
  chain?: string;
  mandate_id?: string;
  metadata?: Record<string, unknown>;
}

export interface StreamOpenResponse {
  stream_id: string;
  status: string;
  from_wallet: string;
  to: string;
  token: string;
  max_amount: string;
  consumed: string;
  created_at: string;
}

export interface StreamConsumeParams {
  units: number;
  memo?: string;
}

export interface StreamConsumeResponse {
  stream_id: string;
  units_consumed: number;
  amount_charged: string;
  total_consumed: string;
  remaining: string;
}

export interface StreamSettleResponse {
  stream_id: string;
  status: string;
  total_consumed: string;
  refunded: string;
  tx_hash: string | null;
  settled_at: string;
}

export class StreamingResource extends BaseResource {
  /**
   * Open a new payment stream.
   *
   * Creates a continuous payment channel between a wallet and a recipient.
   * Funds are reserved up to max_amount but only consumed incrementally.
   *
   * @param params - Stream configuration
   * @param options - Request options (signal, timeout)
   * @returns The opened stream details
   */
  async open(params: StreamOpenParams, options?: RequestOptions): Promise<StreamOpenResponse> {
    return this._post<StreamOpenResponse>('/api/v2/payments/stream/open', params, options);
  }

  /**
   * Consume units from an active payment stream.
   *
   * Deducts the specified number of units from the stream at the
   * configured rate per unit. Fails if the stream is exhausted or closed.
   *
   * @param streamId - The stream ID to consume from
   * @param params - Consumption parameters
   * @param options - Request options (signal, timeout)
   * @returns Consumption result with updated balances
   */
  async consume(
    streamId: string,
    params: StreamConsumeParams,
    options?: RequestOptions
  ): Promise<StreamConsumeResponse> {
    return this._post<StreamConsumeResponse>(
      `/api/v2/payments/stream/${streamId}/consume`,
      params,
      options
    );
  }

  /**
   * Settle and close a payment stream.
   *
   * Finalizes the stream, settling any remaining balance. Unconsumed
   * funds are returned to the source wallet.
   *
   * @param streamId - The stream ID to settle
   * @param options - Request options (signal, timeout)
   * @returns Settlement result with final amounts
   */
  async settle(streamId: string, options?: RequestOptions): Promise<StreamSettleResponse> {
    return this._post<StreamSettleResponse>(
      `/api/v2/payments/stream/${streamId}/settle`,
      undefined,
      options
    );
  }
}
