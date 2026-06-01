/**
 * Money — minor-unit `bigint`, never a float.
 *
 * The Python decision engine uses `Decimal` token-major units. To stay exact
 * and deterministic in TS we represent money as integer minor units
 * (`bigint`) plus a `currency` tag. Decimal token-major strings appear only as
 * display fields (mirroring `AuthorityProof.amount`).
 */

export type Currency = string; // "USDC" | "EURC" | "USD" | ...

export interface Money {
  /** Integer minor units (e.g. cents, or 6-decimal USDC base units). Never a float. */
  minor: bigint;
  currency: Currency;
}

/** Construct a Money value from minor units. */
export function money(minor: bigint, currency: Currency): Money {
  return { minor, currency };
}

/** Zero in a given currency. */
export function zero(currency: Currency): Money {
  return { minor: 0n, currency };
}

/**
 * Parse an exact token-major decimal string ("12.34") into minor-unit bigint,
 * given the token's decimal precision. No floats — string parsing only.
 *
 * Throws on malformed input or more fractional digits than `decimals`.
 */
export function toMinor(major: string, decimals: number): bigint {
  if (!Number.isInteger(decimals) || decimals < 0) {
    throw new RangeError(`decimals must be a non-negative integer, got ${decimals}`);
  }
  const trimmed = major.trim();
  const m = /^(-)?(\d+)(?:\.(\d+))?$/.exec(trimmed);
  if (!m) {
    throw new RangeError(`invalid decimal string: ${JSON.stringify(major)}`);
  }
  const sign = m[1] === '-' ? -1n : 1n;
  const intPart = m[2] ?? '0';
  const fracPart = m[3] ?? '';
  if (fracPart.length > decimals) {
    throw new RangeError(
      `too many fractional digits: ${fracPart.length} > ${decimals} for ${JSON.stringify(major)}`,
    );
  }
  const fracPadded = (fracPart + '0'.repeat(decimals)).slice(0, decimals);
  const combined = intPart + fracPadded;
  return sign * BigInt(combined === '' ? '0' : combined);
}

/** Format a Money value as a token-major decimal string. Display only. */
export function fmtMajor(m: Money, decimals: number): string {
  if (!Number.isInteger(decimals) || decimals < 0) {
    throw new RangeError(`decimals must be a non-negative integer, got ${decimals}`);
  }
  const neg = m.minor < 0n;
  const abs = neg ? -m.minor : m.minor;
  if (decimals === 0) {
    return `${neg ? '-' : ''}${abs.toString()}`;
  }
  const s = abs.toString().padStart(decimals + 1, '0');
  const intPart = s.slice(0, s.length - decimals);
  const fracPart = s.slice(s.length - decimals);
  return `${neg ? '-' : ''}${intPart}.${fracPart}`;
}

/** Guard: assert two Money values share a currency before comparing/adding. */
export function assertSameCurrency(a: Money, b: Money): void {
  if (a.currency !== b.currency) {
    throw new TypeError(`currency mismatch: ${a.currency} vs ${b.currency}`);
  }
}

/** Add two same-currency Money values. */
export function add(a: Money, b: Money): Money {
  assertSameCurrency(a, b);
  return { minor: a.minor + b.minor, currency: a.currency };
}

/** a > b (same currency). */
export function gt(a: Money, b: Money): boolean {
  assertSameCurrency(a, b);
  return a.minor > b.minor;
}

/** a >= b (same currency). */
export function gte(a: Money, b: Money): boolean {
  assertSameCurrency(a, b);
  return a.minor >= b.minor;
}
