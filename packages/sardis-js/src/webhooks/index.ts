/**
 * `sardis/webhooks` — webhook signature verification + event types.
 *
 * Intentionally separated from the root umbrella bundle so edge runtimes
 * (Cloudflare Workers, Vercel Edge) can receive webhooks with the
 * smallest possible bundle. Picks the runtime-appropriate HMAC shim at
 * import time.
 */

export { WebhooksResource } from '../resources/webhooks.js';
export type {
  Webhook,
  WebhookDelivery,
  WebhookEventType,
  CreateWebhookInput,
  UpdateWebhookInput,
} from '../types.js';

/**
 * Verify a Sardis webhook signature against a raw body and shared secret.
 *
 * Works on both Node (uses `node:crypto`) and edge runtimes (uses Web
 * Crypto SubtleCrypto via `globalThis.crypto.subtle`). For maximum bundle
 * efficiency, import the runtime-specific shim directly from
 * `sardis/shims/node` or `sardis/shims/web`.
 */
export async function verifyWebhook(opts: {
  secret: string;
  rawBody: string;
  signature: string;
}): Promise<boolean> {
  if (typeof globalThis !== 'undefined' && globalThis.crypto?.subtle) {
    const { hmacSha256Hex, timingSafeEqual } = await import('../shims/web.js');
    const expected = await hmacSha256Hex(opts.secret, opts.rawBody);
    return timingSafeEqual(expected, opts.signature);
  }
  const { hmacSha256Hex, timingSafeEqual } = await import('../shims/node.js');
  const expected = await hmacSha256Hex(opts.secret, opts.rawBody);
  return timingSafeEqual(expected, opts.signature);
}

/**
 * Construct + verify an event from a raw body. Throws if the signature
 * is invalid. Returns the parsed JSON payload otherwise.
 *
 * Mirrors Stripe's `webhooks.constructEvent(...)`.
 */
export async function constructEvent<T = unknown>(
  rawBody: string,
  signature: string,
  secret: string,
): Promise<T> {
  const ok = await verifyWebhook({ secret, rawBody, signature });
  if (!ok) throw new Error('Invalid webhook signature');
  return JSON.parse(rawBody) as T;
}
