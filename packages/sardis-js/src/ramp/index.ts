/**
 * `sardis/ramp` — on-/off-ramp surface.
 *
 * The ramp REST endpoints are exposed via the umbrella Sardis client
 * (`sardis.engine.request("POST", "/api/v2/ramp/...")`). This subpath
 * provides typed inputs and quote helpers without pulling in the full
 * client when only the ramp surface is needed.
 */

import type { Chain, Token } from '../types.js';

export interface RampQuoteInput {
  /** Fiat currency code (ISO 4217), e.g. "USD". */
  fiatCurrency: string;
  /** Token to receive on-chain. */
  token: Token;
  /** Chain to deliver to. */
  chain: Chain;
  /** Fiat amount being sold (mutually exclusive with cryptoAmount). */
  fiatAmount?: string;
  /** Token amount being requested (mutually exclusive with fiatAmount). */
  cryptoAmount?: string;
  /** Region hint (ISO 3166-1 alpha-2), used to filter eligible providers. */
  countryCode?: string;
}

export interface RampQuoteResponse {
  quote_id: string;
  rate: string;
  fee: string;
  fiat_amount: string;
  crypto_amount: string;
  expires_at: string;
  provider: string;
}

/**
 * Stable sort order for ramp quote providers. Use to pick the
 * best-priced quote when several providers respond.
 */
export function sortQuotesByEffectiveRate(quotes: RampQuoteResponse[]): RampQuoteResponse[] {
  return [...quotes].sort((a, b) => {
    const ra = Number.parseFloat(a.crypto_amount) / Math.max(Number.parseFloat(a.fiat_amount), 1e-9);
    const rb = Number.parseFloat(b.crypto_amount) / Math.max(Number.parseFloat(b.fiat_amount), 1e-9);
    return rb - ra;
  });
}
