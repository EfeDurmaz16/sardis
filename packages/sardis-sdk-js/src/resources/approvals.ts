/**
 * Approvals Resource
 *
 * Manage approval requests for payments that exceed policy thresholds.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface Approval {
  id: string;
  agent_id: string;
  transaction_id?: string;
  amount: string;
  currency: string;
  merchant_id?: string;
  reason: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  approved_by?: string;
  rejected_by?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export class ApprovalsResource extends BaseResource {
  async listPending(options?: RequestOptions): Promise<Approval[]> {
    return this._get<Approval[]>('/api/v2/approvals/pending', undefined, options);
  }

  async list(
    params?: { status?: string; limit?: number },
    options?: RequestOptions,
  ): Promise<Approval[]> {
    return this._get<Approval[]>('/api/v2/approvals', params as Record<string, unknown>, options);
  }

  async get(approvalId: string, options?: RequestOptions): Promise<Approval> {
    return this._get<Approval>(`/api/v2/approvals/${approvalId}`, undefined, options);
  }

  async approve(
    approvalId: string,
    data?: { notes?: string },
    options?: RequestOptions,
  ): Promise<Approval> {
    return this._post<Approval>(`/api/v2/approvals/${approvalId}/approve`, data ?? {}, options);
  }

  async deny(
    approvalId: string,
    data?: { reason?: string },
    options?: RequestOptions,
  ): Promise<Approval> {
    return this._post<Approval>(`/api/v2/approvals/${approvalId}/reject`, data ?? {}, options);
  }
}
