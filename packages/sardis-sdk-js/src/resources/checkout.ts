/**
 * Checkout resource for Pay with Sardis merchant checkout sessions.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface CreateCheckoutSessionParams {
  merchant_id: string;
  amount: string;
  currency?: string;
  description?: string;
  success_url?: string;
  cancel_url?: string;
  metadata?: Record<string, unknown>;
}

export interface CheckoutSession {
  session_id: string;
  merchant_id: string;
  amount: string;
  currency: string;
  description?: string;
  status: string;
  payment_method?: string;
  tx_hash?: string;
  redirect_url: string;
  expires_at?: string;
  created_at: string;
}

export interface CheckoutSessionDetails {
  session_id: string;
  merchant_name: string;
  merchant_logo_url?: string;
  amount: string;
  currency: string;
  description?: string;
  status: string;
  expires_at?: string;
}

export class CheckoutResource extends BaseResource {
  /**
   * Create a new checkout session.
   */
  async createSession(
    params: CreateCheckoutSessionParams,
    options?: RequestOptions,
  ): Promise<CheckoutSession> {
    return this._post<CheckoutSession>(
      '/api/v2/merchant-checkout/sessions',
      params,
      options,
    );
  }

  /**
   * Get a checkout session by ID (merchant-side, authenticated).
   */
  async getSession(
    sessionId: string,
    options?: RequestOptions,
  ): Promise<CheckoutSession> {
    return this._get<CheckoutSession>(
      `/api/v2/merchant-checkout/sessions/${sessionId}`,
      undefined,
      options,
    );
  }

  /**
   * Get public session details (for checkout page rendering).
   */
  async getSessionDetails(
    sessionId: string,
    options?: RequestOptions,
  ): Promise<CheckoutSessionDetails> {
    return this._get<CheckoutSessionDetails>(
      `/api/v2/merchant-checkout/sessions/${sessionId}/details`,
      undefined,
      options,
    );
  }
}
