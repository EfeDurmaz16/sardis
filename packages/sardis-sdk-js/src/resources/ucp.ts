/**
 * UCP (Universal Commerce Protocol) resource
 *
 * Provides checkout session management for structured commerce:
 * - Create checkout sessions with cart items
 * - Update sessions (add/remove items, discounts)
 * - Complete checkout and generate payment mandates
 */

import { BaseResource } from './base.js';

// ============ Types ============

export interface UCPLineItem {
  item_id: string;
  name: string;
  description: string;
  quantity: number;
  unit_price_minor: number;
  currency?: string;
  sku?: string;
  category?: string;
  image_url?: string;
  taxable?: boolean;
  tax_rate?: string;
  metadata?: Record<string, unknown>;
}

export interface UCPDiscount {
  discount_id: string;
  name: string;
  discount_type: 'percentage' | 'fixed' | 'coupon';
  value: string;
  code?: string;
  applied_to?: string[];
  min_purchase_minor?: number;
}

export interface CreateCheckoutInput {
  merchant_id: string;
  merchant_name: string;
  merchant_domain: string;
  customer_id: string;
  line_items: UCPLineItem[];
  currency?: string;
  tax_rate?: string;
  shipping_minor?: number;
  metadata?: Record<string, unknown>;
}

export interface UpdateCheckoutInput {
  add_items?: UCPLineItem[];
  remove_item_ids?: string[];
  add_discounts?: UCPDiscount[];
  remove_discount_ids?: string[];
  shipping_minor?: number;
  metadata?: Record<string, unknown>;
}

export interface CompleteCheckoutInput {
  chain: string;
  token: string;
  destination: string;
  subject: string;
  issuer: string;
  execute_payment?: boolean;
}

export interface CheckoutSession {
  session_id: string;
  merchant_id: string;
  merchant_name: string;
  merchant_domain: string;
  customer_id: string;
  status: 'open' | 'pending_payment' | 'completed' | 'expired' | 'cancelled';
  currency: string;
  line_items: UCPLineItem[];
  discounts: UCPDiscount[];
  subtotal_minor: number;
  taxes_minor: number;
  shipping_minor: number;
  total_minor: number;
  cart_mandate?: Record<string, unknown>;
  checkout_mandate?: Record<string, unknown>;
  payment_mandate?: Record<string, unknown>;
  order_id?: string;
  chain_tx_hash?: string;
  created_at: string;
  updated_at: string;
  expires_at: number;
  metadata?: Record<string, unknown>;
}

export interface CheckoutResult {
  success: boolean;
  session_id: string;
  order_id?: string;
  payment_mandate?: Record<string, unknown>;
  chain_tx_hash?: string;
  error?: string;
  error_code?: string;
}

export interface UCPOrder {
  order_id: string;
  checkout_session_id: string;
  merchant_id: string;
  customer_id: string;
  status: string;
  line_items: UCPLineItem[];
  currency: string;
  subtotal_minor: number;
  taxes_minor: number;
  shipping_minor: number;
  discount_minor: number;
  total_minor: number;
  payment_mandate_id?: string;
  chain_tx_hash?: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

// ============ Resource ============

export class UCPResource extends BaseResource {
  /**
   * Create a new checkout session
   *
   * @example
   * ```typescript
   * const session = await client.ucp.createCheckout({
   *   merchant_id: 'merchant_123',
   *   merchant_name: 'Example Store',
   *   merchant_domain: 'store.example.com',
   *   customer_id: 'agent_abc',
   *   line_items: [{
   *     item_id: 'item_1',
   *     name: 'Widget',
   *     description: 'A useful widget',
   *     quantity: 2,
   *     unit_price_minor: 1000,
   *   }],
   * });
   * ```
   */
  async createCheckout(input: CreateCheckoutInput): Promise<CheckoutSession> {
    return this._post<CheckoutSession>('/api/v2/ucp/checkout', input);
  }

  /**
   * Get a checkout session
   *
   * @example
   * ```typescript
   * const session = await client.ucp.getCheckout('cs_abc123');
   * console.log(session.status, session.total_minor);
   * ```
   */
  async getCheckout(sessionId: string): Promise<CheckoutSession> {
    return this._get<CheckoutSession>(`/api/v2/ucp/checkout/${sessionId}`);
  }

  /**
   * Update a checkout session
   *
   * @example
   * ```typescript
   * const updated = await client.ucp.updateCheckout('cs_abc123', {
   *   add_items: [{ item_id: 'item_2', name: 'Extra', quantity: 1, unit_price_minor: 500 }],
   *   add_discounts: [{
   *     discount_id: 'disc_1',
   *     name: '10% Off',
   *     discount_type: 'percentage',
   *     value: '10',
   *   }],
   * });
   * ```
   */
  async updateCheckout(sessionId: string, input: UpdateCheckoutInput): Promise<CheckoutSession> {
    return this._patch<CheckoutSession>(`/api/v2/ucp/checkout/${sessionId}`, input);
  }

  /**
   * Complete a checkout session and generate payment mandate
   *
   * @example
   * ```typescript
   * const result = await client.ucp.completeCheckout('cs_abc123', {
   *   chain: 'base',
   *   token: 'USDC',
   *   destination: '0x...',
   *   subject: 'agent_abc',
   *   issuer: 'sardis.sh',
   * });
   *
   * if (result.success) {
   *   console.log('Payment tx:', result.chain_tx_hash);
   * }
   * ```
   */
  async completeCheckout(sessionId: string, input: CompleteCheckoutInput): Promise<CheckoutResult> {
    return this._post<CheckoutResult>(`/api/v2/ucp/checkout/${sessionId}/complete`, input);
  }

  /**
   * Cancel a checkout session
   *
   * @example
   * ```typescript
   * await client.ucp.cancelCheckout('cs_abc123');
   * ```
   */
  async cancelCheckout(sessionId: string): Promise<CheckoutSession> {
    return this._post<CheckoutSession>(`/api/v2/ucp/checkout/${sessionId}/cancel`, {});
  }

  /**
   * Get an order by ID
   *
   * @example
   * ```typescript
   * const order = await client.ucp.getOrder('ord_abc123');
   * console.log(order.status, order.chain_tx_hash);
   * ```
   */
  async getOrder(orderId: string): Promise<UCPOrder> {
    return this._get<UCPOrder>(`/api/v2/ucp/orders/${orderId}`);
  }

  /**
   * List orders
   *
   * @example
   * ```typescript
   * const orders = await client.ucp.listOrders({
   *   customer_id: 'agent_abc',
   *   status: 'completed',
   * });
   * ```
   */
  async listOrders(options?: {
    customer_id?: string;
    merchant_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<UCPOrder[]> {
    const response = await this._get<{ orders: UCPOrder[] } | UCPOrder[]>(
      '/api/v2/ucp/orders',
      options
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.orders || [];
  }
}
