/**
 * FX Resource
 *
 * Foreign exchange operations for stablecoin conversions and cross-chain bridging.
 * Supports token-to-token swaps (e.g., USDC to EURC) and cross-chain transfers
 * via Circle CCTP v2.
 */

import { BaseResource } from './base.js';
import type {
  FXQuote,
  FXQuoteInput,
  FXExecuteResponse,
  FXRate,
  FXBridgeInput,
  FXBridgeResponse,
  RequestOptions,
} from '../types.js';

export class FXResource extends BaseResource {
  /**
   * Request an FX quote.
   *
   * Returns a time-limited quote for converting between stablecoin tokens.
   * The quote locks in the exchange rate for a short window.
   *
   * @param params - Quote request parameters
   * @param options - Request options (signal, timeout)
   * @returns The FX quote
   */
  async quote(params: FXQuoteInput, options?: RequestOptions): Promise<FXQuote> {
    return this._post<FXQuote>('/api/v2/fx/quote', params, options);
  }

  /**
   * Execute a previously obtained FX quote.
   *
   * Performs the token conversion at the locked-in rate. The quote
   * must still be active (not expired).
   *
   * @param quoteId - Quote ID to execute
   * @param options - Request options (signal, timeout)
   * @returns The execution result
   */
  async execute(quoteId: string, options?: RequestOptions): Promise<FXExecuteResponse> {
    return this._post<FXExecuteResponse>(`/api/v2/fx/quotes/${quoteId}/execute`, {}, options);
  }

  /**
   * Get current exchange rates for all supported token pairs.
   *
   * @param options - Request options (signal, timeout)
   * @returns Array of current exchange rates
   */
  async rates(options?: RequestOptions): Promise<FXRate[]> {
    return this._get<FXRate[]>('/api/v2/fx/rates', undefined, options);
  }

  /**
   * Bridge tokens across chains.
   *
   * Initiates a cross-chain transfer using Circle CCTP v2 for supported
   * tokens, or a bridge aggregator for other paths.
   *
   * @param params - Bridge parameters
   * @param options - Request options (signal, timeout)
   * @returns The bridge operation details
   */
  async bridge(params: FXBridgeInput, options?: RequestOptions): Promise<FXBridgeResponse> {
    return this._post<FXBridgeResponse>('/api/v2/fx/bridge', params, options);
  }
}
