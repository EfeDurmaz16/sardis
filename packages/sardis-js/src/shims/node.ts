/**
 * Node-only crypto shims using `node:crypto`.
 *
 * Used by package consumers that explicitly target a Node runtime
 * (no Edge support required). Web Crypto also works on modern Node
 * 20+, but `node:crypto` is faster and avoids a `subtle` round-trip.
 */

import { createHmac, randomBytes, timingSafeEqual as nodeTimingSafeEqual } from 'node:crypto';

export async function hmacSha256Hex(secret: string, payload: string): Promise<string> {
  return createHmac('sha256', secret).update(payload).digest('hex');
}

export function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  return nodeTimingSafeEqual(Buffer.from(a), Buffer.from(b));
}

export function randomId(prefix: string = 'sardis'): string {
  return `${prefix}_${randomBytes(16).toString('hex')}`;
}
