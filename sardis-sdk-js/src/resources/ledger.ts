/**
 * Ledger resource
 */

import { BaseResource } from './base.js';
import type { LedgerEntry } from '../types.js';

export class LedgerResource extends BaseResource {
  /**
   * List ledger entries
   */
  async listEntries(options?: {
    wallet_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<LedgerEntry[]> {
    const response = await this._get<{ entries: LedgerEntry[] }>('/api/v2/ledger/entries', options);
    return response.entries || [];
  }

  /**
   * Get a ledger entry by transaction ID
   */
  async getEntry(txId: string): Promise<LedgerEntry> {
    return this._get<LedgerEntry>(`/api/v2/ledger/entries/${txId}`);
  }

  /**
   * Verify a ledger entry's audit anchor
   */
  async verifyEntry(txId: string): Promise<{ valid: boolean; anchor?: string }> {
    return this._get<{ valid: boolean; anchor?: string }>(`/api/v2/ledger/entries/${txId}/verify`);
  }
}
