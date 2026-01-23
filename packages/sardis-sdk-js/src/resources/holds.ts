/**
 * Holds resource
 */

import { BaseResource } from './base.js';
import type { Hold, CreateHoldInput, CreateHoldResponse } from '../types.js';

export class HoldsResource extends BaseResource {
  /**
   * Create a hold (pre-authorization) on funds
   */
  async create(input: CreateHoldInput): Promise<CreateHoldResponse> {
    return this._post<CreateHoldResponse>('/api/v2/holds', input);
  }

  /**
   * Get a hold by ID
   *
   * @param holdId - The hold ID
   * @returns The hold object
   */
  async get(holdId: string): Promise<Hold> {
    return this._get<Hold>(`/api/v2/holds/${holdId}`);
  }

  /**
   * Get a hold by ID
   *
   * @deprecated Use `get(holdId)` instead. This method will be removed in v1.0.0.
   * @param holdId - The hold ID
   * @returns The hold object
   */
  async getById(holdId: string): Promise<Hold> {
    return this.get(holdId);
  }

  /**
   * Capture a hold (complete the payment)
   */
  async capture(holdId: string, amount?: string): Promise<Hold> {
    const data = amount ? { amount } : {};
    return this._post<Hold>(`/api/v2/holds/${holdId}/capture`, data);
  }

  /**
   * Void a hold (cancel without payment)
   */
  async void(holdId: string): Promise<Hold> {
    return this._post<Hold>(`/api/v2/holds/${holdId}/void`, {});
  }

  /**
   * List all holds for a wallet
   */
  async listByWallet(walletId: string): Promise<Hold[]> {
    const response = await this._get<{ holds: Hold[] }>(`/api/v2/holds/wallet/${walletId}`);
    return response.holds || [];
  }

  /**
   * List all active holds
   */
  async listActive(): Promise<Hold[]> {
    const response = await this._get<{ holds: Hold[] }>('/api/v2/holds');
    return response.holds || [];
  }
}
