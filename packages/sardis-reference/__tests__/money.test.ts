import { describe, it, expect } from 'vitest';
import { toMinor, fmtMajor, add, gt, gte } from '../src/types/money.js';

describe('Money — exact minor-unit parsing (no floats)', () => {
  it('parses token-major strings at given precision', () => {
    expect(toMinor('5.00', 2)).toBe(500n);
    expect(toMinor('5', 2)).toBe(500n);
    expect(toMinor('0.01', 2)).toBe(1n);
    expect(toMinor('1234.56', 2)).toBe(123456n);
    expect(toMinor('1.000000', 6)).toBe(1_000_000n);
    expect(toMinor('-2.50', 2)).toBe(-250n);
  });

  it('rejects too many fractional digits', () => {
    expect(() => toMinor('5.001', 2)).toThrow();
  });

  it('rejects malformed input', () => {
    expect(() => toMinor('abc', 2)).toThrow();
    expect(() => toMinor('', 2)).toThrow();
  });

  it('formats minor units back to a major string (display only)', () => {
    expect(fmtMajor({ minor: 500n, currency: 'USDC' }, 2)).toBe('5.00');
    expect(fmtMajor({ minor: 1n, currency: 'USDC' }, 2)).toBe('0.01');
    expect(fmtMajor({ minor: -250n, currency: 'USDC' }, 2)).toBe('-2.50');
    expect(fmtMajor({ minor: 1_000_000n, currency: 'USDC' }, 6)).toBe('1.000000');
  });

  it('add / gt / gte enforce currency match', () => {
    const a = { minor: 100n, currency: 'USDC' };
    const b = { minor: 50n, currency: 'USDC' };
    expect(add(a, b).minor).toBe(150n);
    expect(gt(a, b)).toBe(true);
    expect(gte(a, a)).toBe(true);
    expect(() => add(a, { minor: 1n, currency: 'EURC' })).toThrow();
  });
});
