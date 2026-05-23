/**
 * `sardis/protocol` — AP2 / TAP mandate builders + signature helpers.
 *
 * The AP2 specification (Google/PayPal/Mastercard/Visa) defines a 3-step
 * mandate chain: Intent → Cart → Payment. This module ships small
 * builders that construct each step with the correct snake_case wire
 * format while exposing a camelCase TS API.
 */

export { MandateDelegationResource } from '../resources/mandate-delegation.js';
export { PaymentObjectsResource } from '../resources/payment-objects.js';

import type { Chain, Token } from '../types.js';

export interface IntentMandateInput {
  /** Agent or wallet ID submitting the intent. */
  subjectId: string;
  /** Free-form intent string (the "why"). */
  description: string;
  /** Maximum amount the agent is authorized to spend on this intent. */
  maxAmount: string;
  /** Token symbol. */
  token?: Token;
  /** ISO 8601 expiration. */
  expiresAt?: string | Date;
  /** Domain context (e.g. "aws.amazon.com"). */
  domain?: string;
  /** Arbitrary metadata. */
  metadata?: Record<string, unknown>;
}

export interface CartMandateInput {
  /** Intent mandate id this cart binds to. */
  intentId: string;
  /** Itemized cart. */
  items: Array<{ name: string; amount: string; quantity?: number; sku?: string }>;
  /** Merchant identifier. */
  merchantId: string;
  /** Token symbol. */
  token?: Token;
  /** Chain. */
  chain?: Chain;
  metadata?: Record<string, unknown>;
}

export interface PaymentMandateInput {
  /** Cart mandate id this payment binds to. */
  cartId: string;
  /** Total to charge. */
  amount: string;
  /** Destination — merchant wallet, account, or address. */
  destination: string;
  /** Token symbol. */
  token?: Token;
  /** Chain. */
  chain?: Chain;
  metadata?: Record<string, unknown>;
}

function toIso(value: string | Date | undefined): string | undefined {
  if (value === undefined) return undefined;
  return value instanceof Date ? value.toISOString() : value;
}

/**
 * AP2 mandate builders. The TS API uses camelCase; the wire shape uses
 * snake_case to match the AP2 specification.
 */
export const Mandate = {
  intent(input: IntentMandateInput): Record<string, unknown> {
    return {
      type: 'intent',
      subject_id: input.subjectId,
      description: input.description,
      max_amount: input.maxAmount,
      token: input.token ?? 'USDC',
      ...(toIso(input.expiresAt) ? { expires_at: toIso(input.expiresAt) } : {}),
      ...(input.domain ? { domain: input.domain } : {}),
      ...(input.metadata ? { metadata: input.metadata } : {}),
    };
  },

  cart(input: CartMandateInput): Record<string, unknown> {
    return {
      type: 'cart',
      intent_id: input.intentId,
      merchant_id: input.merchantId,
      items: input.items.map((i) => ({
        name: i.name,
        amount: i.amount,
        quantity: i.quantity ?? 1,
        ...(i.sku ? { sku: i.sku } : {}),
      })),
      token: input.token ?? 'USDC',
      ...(input.chain ? { chain: input.chain } : {}),
      ...(input.metadata ? { metadata: input.metadata } : {}),
    };
  },

  payment(input: PaymentMandateInput): Record<string, unknown> {
    return {
      type: 'payment',
      cart_id: input.cartId,
      amount: input.amount,
      destination: input.destination,
      token: input.token ?? 'USDC',
      ...(input.chain ? { chain: input.chain } : {}),
      ...(input.metadata ? { metadata: input.metadata } : {}),
    };
  },
};
