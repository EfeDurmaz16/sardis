/**
 * Transactions resource
 */

import { BaseResource } from './base.js';
import type { GasEstimate, TransactionStatus, ChainInfo, Token } from '../types.js';

export class TransactionsResource extends BaseResource {
  /**
   * List supported blockchain networks
   */
  async listChains(): Promise<ChainInfo[]> {
    const response = await this._get<{ chains: ChainInfo[] }>('/api/v2/transactions/chains');
    return response.chains || [];
  }

  /**
   * Estimate gas for a transaction
   */
  async estimateGas(options: {
    chain: string;
    to_address: string;
    amount: string;
    token?: Token;
  }): Promise<GasEstimate> {
    return this._post<GasEstimate>('/api/v2/transactions/estimate-gas', options);
  }

  /**
   * Get the status of a transaction
   */
  async getStatus(txHash: string, chain: string): Promise<TransactionStatus> {
    return this._get<TransactionStatus>(`/api/v2/transactions/status/${txHash}`, { chain });
  }

  /**
   * List supported tokens on a chain
   */
  async listTokens(chain: string): Promise<Array<{ symbol: string; address: string }>> {
    const response = await this._get<{ tokens: Array<{ symbol: string; address: string }> }>(
      `/api/v2/transactions/tokens/${chain}`
    );
    return response.tokens || [];
  }
}
