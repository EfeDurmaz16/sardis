/**
 * base64url (no padding) — mirrors Python `_b64url_encode` / `_b64url_decode`.
 */

export function b64urlEncode(data: Uint8Array): string {
  let bin = '';
  for (let i = 0; i < data.length; i++) {
    bin += String.fromCharCode(data[i]!);
  }
  // btoa is available on Node 16+ and all browsers/edge runtimes.
  const b64 = typeof btoa === 'function' ? btoa(bin) : Buffer.from(data).toString('base64');
  return b64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function b64urlDecode(value: string): Uint8Array {
  const padLen = (4 - (value.length % 4)) % 4;
  const b64 = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat(padLen);
  if (typeof atob === 'function') {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) {
      out[i] = bin.charCodeAt(i);
    }
    return out;
  }
  return new Uint8Array(Buffer.from(b64, 'base64'));
}
