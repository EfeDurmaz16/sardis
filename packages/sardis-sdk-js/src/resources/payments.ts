/**
 * Payments resource
 */

import { BaseResource } from './base.js';
import type { ExecutePaymentResponse, ExecuteAP2Response } from '../types.js';

export class PaymentsResource extends BaseResource {
  /**
   * Execute a single payment mandate
   */
  async executeMandate(mandate: Record<string, unknown>): Promise<ExecutePaymentResponse> {
    return this._post<ExecutePaymentResponse>('/api/v2/mandates/execute', { mandate });
  }

  /**
   * Execute a full AP2 payment bundle (Intent → Cart → Payment)
   */
  async executeAP2(
    intent: Record<string, unknown>,
    cart: Record<string, unknown>,
    payment: Record<string, unknown>
  ): Promise<ExecuteAP2Response> {
    return this._post<ExecuteAP2Response>('/api/v2/ap2/payments/execute', {
      intent,
      cart,
      payment,
    });
  }

  /**
   * Execute a pre-built AP2 bundle
   */
  async executeAP2Bundle(bundle: {
    intent: Record<string, unknown>;
    cart: Record<string, unknown>;
    payment: Record<string, unknown>;
  }): Promise<ExecuteAP2Response> {
    return this.executeAP2(bundle.intent, bundle.cart, bundle.payment);
  }
}
