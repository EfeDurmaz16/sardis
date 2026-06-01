/**
 * Decimal-string amount helpers — no floats on the money-comparison path.
 *
 * The threshold gate compares token-major amount strings (e.g. "49.99" vs
 * "50"). We compare them as fixed-point decimals (integer + fractional parts)
 * instead of `parseFloat`, to stay faithful to the Sardis no-float money rule
 * and avoid binary-float rounding at the boundary.
 */

function coerceAmount(a: unknown): string | null {
  if (typeof a === 'string' && a.trim() !== '') return a.trim();
  if (typeof a === 'number' && Number.isFinite(a)) return String(a);
  if (typeof a === 'bigint') return a.toString();
  return null;
}

/**
 * Pull an `amount` token-major string out of arbitrary tool args, if present.
 * For mandate-bearing verbs (pay-invoice), the authoritative amount lives on
 * the mandate, so we fall back to `mandate.amount` when there is no top-level
 * `amount`.
 */
export function extractAmount(args: unknown): string | null {
  if (args && typeof args === 'object') {
    const obj = args as Record<string, unknown>;
    const top = coerceAmount(obj.amount);
    if (top != null) return top;
    const mandate = obj.mandate;
    if (mandate && typeof mandate === 'object') {
      return coerceAmount((mandate as Record<string, unknown>).amount);
    }
  }
  return null;
}

/** Normalize a decimal string into `[integerDigits, fractionDigits]`. */
function split(value: string): [string, string] {
  const s = value.replace(/^\+/, '').trim();
  const [intPart = '0', fracPart = ''] = s.split('.');
  // strip a leading sign for magnitude compare; negatives are not expected for
  // amounts, but handle defensively by treating them as 0.
  const cleanInt = intPart.replace(/^-/, '').replace(/^0+(?=\d)/, '') || '0';
  const cleanFrac = fracPart.replace(/0+$/, '');
  return [cleanInt, cleanFrac];
}

/**
 * Compare two non-negative decimal strings.
 * Returns -1 if a < b, 0 if equal, 1 if a > b.
 */
export function compareDecimalStrings(a: string, b: string): number {
  const [ai, af] = split(a);
  const [bi, bf] = split(b);

  // Compare integer parts by length then lexicographically.
  if (ai.length !== bi.length) return ai.length < bi.length ? -1 : 1;
  if (ai !== bi) return ai < bi ? -1 : 1;

  // Equal integer parts -> compare fractional parts digit by digit.
  const len = Math.max(af.length, bf.length);
  for (let i = 0; i < len; i++) {
    const da = af.charCodeAt(i) || 48; // missing digit == '0'
    const db = bf.charCodeAt(i) || 48;
    if (da !== db) return da < db ? -1 : 1;
  }
  return 0;
}
