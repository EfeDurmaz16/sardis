/**
 * Canonical JSON — byte-for-byte mirror of Python
 * `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True)`.
 *
 * This is the exact serializer used by `AuthorityProof._canonical_bytes`,
 * `DelegationEvidence._canonical_decision`, and `RevocationProof._canonical_decision`
 * (with `default=str` applied by callers before serialization). The signing /
 * verification contract depends on this matching Python's output exactly.
 *
 * Properties matched:
 *   - object keys sorted lexicographically (by UTF-16 code unit, which equals
 *     Python's code-point sort for the ASCII/BMP keys used in claims);
 *   - separators `(",", ":")` — no whitespace;
 *   - `ensure_ascii=True` — every non-ASCII char is `\uXXXX`-escaped;
 *   - string escaping matches Python's json (`"`, `\`, control chars, etc.);
 *   - integers serialized as bare decimal digits;
 *   - `bigint` serialized as its decimal digits (claims carry `amount_minor` as
 *     an int — callers convert bigint → the int form before hashing, but bigint
 *     is supported here for safety);
 *   - booleans `true`/`false`, `null` for null/undefined;
 *   - floats are REJECTED (the authority-proof paths forbid floats).
 */

/** A JSON value that the canonical serializer accepts (no floats). */
export type CanonicalValue =
  | string
  | number // integer only — non-integers throw
  | bigint
  | boolean
  | null
  | undefined
  | CanonicalValue[]
  | { [key: string]: CanonicalValue };

function escapeString(s: string): string {
  let out = '"';
  for (let i = 0; i < s.length; i++) {
    const code = s.charCodeAt(i);
    const ch = s[i]!;
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
        if (code < 0x20 || code > 0x7e) {
          // Control chars and all non-ASCII → \uXXXX (ensure_ascii=True).
          out += '\\u' + code.toString(16).padStart(4, '0');
        } else {
          out += ch;
        }
    }
  }
  return out + '"';
}

export function canonicalize(value: CanonicalValue): string {
  if (value === null || value === undefined) {
    return 'null';
  }
  const t = typeof value;
  if (t === 'string') {
    return escapeString(value as string);
  }
  if (t === 'boolean') {
    return value ? 'true' : 'false';
  }
  if (t === 'bigint') {
    return (value as bigint).toString();
  }
  if (t === 'number') {
    const n = value as number;
    if (!Number.isFinite(n)) {
      throw new TypeError(`non-finite number is not canonicalizable: ${n}`);
    }
    if (!Number.isInteger(n)) {
      // Mirrors the Python authority-proof paths, which forbid floats.
      throw new TypeError(`float values are forbidden in canonical JSON: ${n}`);
    }
    return n.toString();
  }
  if (Array.isArray(value)) {
    return '[' + value.map((v) => canonicalize(v)).join(',') + ']';
  }
  // plain object
  const obj = value as { [key: string]: CanonicalValue };
  const keys = Object.keys(obj).sort();
  const parts: string[] = [];
  for (const k of keys) {
    parts.push(escapeString(k) + ':' + canonicalize(obj[k]));
  }
  return '{' + parts.join(',') + '}';
}

const ENCODER = new TextEncoder();

export function canonicalBytes(value: CanonicalValue): Uint8Array {
  return ENCODER.encode(canonicalize(value));
}
