/**
 * Edge-runtime-safe crypto shims using the Web Crypto API.
 *
 * Use this on Cloudflare Workers, Vercel Edge, Deno, Bun, or any
 * environment exposing `globalThis.crypto.subtle`.
 */

function utf8(input: string): Uint8Array {
  return new TextEncoder().encode(input);
}

function hex(bytes: ArrayBuffer): string {
  const view = new Uint8Array(bytes);
  let out = '';
  for (let i = 0; i < view.length; i++) {
    const b = view[i]!;
    out += b.toString(16).padStart(2, '0');
  }
  return out;
}

export async function hmacSha256Hex(secret: string, payload: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error('Web Crypto SubtleCrypto is not available in this runtime');
  }
  const key = await subtle.importKey(
    'raw',
    utf8(secret) as BufferSource,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await subtle.sign('HMAC', key, utf8(payload) as BufferSource);
  return hex(sig);
}

/**
 * Constant-time string comparison. Both inputs must be hex strings of equal length.
 */
export function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

export function randomId(prefix: string = 'sardis'): string {
  const bytes = new Uint8Array(16);
  globalThis.crypto.getRandomValues(bytes);
  let out = `${prefix}_`;
  for (let i = 0; i < bytes.length; i++) {
    out += bytes[i]!.toString(16).padStart(2, '0');
  }
  return out;
}
