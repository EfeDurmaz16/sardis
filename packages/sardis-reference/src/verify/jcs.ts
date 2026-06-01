/**
 * JCS — RFC 8785 JSON Canonicalization, mirroring the Python
 * `MandateVerifier._jcs_canonicalize`:
 *
 *   json.dumps(sorted_recursive(obj), separators=(",",":"),
 *              ensure_ascii=False, sort_keys=True)
 *
 * Note `ensure_ascii=False` (unlike the authority-proof canonical JSON). Keys
 * are sorted recursively. Only the structural subset used by the AP2 payload
 * builders is supported (strings, integers, booleans, null, arrays, objects).
 */
import type { CanonicalValue } from './canonical-json.js';

function escapeStringUnicode(s: string): string {
  let out = '"';
  for (let i = 0; i < s.length; i++) {
    const ch = s[i]!;
    const code = s.charCodeAt(i);
    switch (ch) {
      case '"':
        out += '\\"';
        break;
      case '\\':
        out += '\\\\';
        break;
      case '\n':
        out += '\\n';
        break;
      case '\r':
        out += '\\r';
        break;
      case '\t':
        out += '\\t';
        break;
      case '\b':
        out += '\\b';
        break;
      case '\f':
        out += '\\f';
        break;
      default:
        if (code < 0x20) {
          out += '\\u' + code.toString(16).padStart(4, '0');
        } else {
          // ensure_ascii=False: emit the character as-is.
          out += ch;
        }
    }
  }
  return out + '"';
}

export function jcsCanonicalize(value: CanonicalValue): string {
  if (value === null || value === undefined) {
    return 'null';
  }
  const t = typeof value;
  if (t === 'string') {
    return escapeStringUnicode(value as string);
  }
  if (t === 'boolean') {
    return value ? 'true' : 'false';
  }
  if (t === 'bigint') {
    return (value as bigint).toString();
  }
  if (t === 'number') {
    const n = value as number;
    if (!Number.isInteger(n)) {
      throw new TypeError(`non-integer numbers are not supported by this JCS subset: ${n}`);
    }
    return n.toString();
  }
  if (Array.isArray(value)) {
    return '[' + value.map((v) => jcsCanonicalize(v)).join(',') + ']';
  }
  const obj = value as { [key: string]: CanonicalValue };
  const keys = Object.keys(obj).sort();
  const parts: string[] = [];
  for (const k of keys) {
    parts.push(escapeStringUnicode(k) + ':' + jcsCanonicalize(obj[k]));
  }
  return '{' + parts.join(',') + '}';
}

const ENCODER = new TextEncoder();

export function jcsBytes(value: CanonicalValue): Uint8Array {
  return ENCODER.encode(jcsCanonicalize(value));
}
