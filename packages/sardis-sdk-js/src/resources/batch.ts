/**
 * Batch Payments Resource
 *
 * Execute multiple payment transfers in a single atomic operation.
 * Supports cross-chain batching with optional mandate enforcement.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface BatchTransfer {
  to: string;
  amount: string;
  token: string;
  memo?: string;
}

export interface BatchExecuteParams {
  transfers: BatchTransfer[];
  chain?: string;
  mandate_id?: string;
}

export interface BatchExecuteResponse {
  batch_id: string;
  status: string;
  results: Array<{
    transfer_index: number;
    tx_hash: string | null;
    status: string;
    error?: string;
  }>;
}

export class BatchResource extends BaseResource {
  /**
   * Execute a batch of payment transfers.
   *
   * Submits multiple transfers for atomic execution. All transfers
   * are validated against the spending mandate (if provided) before
   * any are executed.
   *
   * @param params - Batch execution parameters
   * @param options - Request options (signal, timeout)
   * @returns The batch execution result with per-transfer statuses
   */
  async execute(params: BatchExecuteParams, options?: RequestOptions): Promise<BatchExecuteResponse> {
    return this._post<BatchExecuteResponse>('/api/v2/payments/batch', params, options);
  }
}
