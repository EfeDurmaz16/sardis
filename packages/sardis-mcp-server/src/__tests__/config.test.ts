/**
 * Config Test Suite
 *
 * Covers the trust-critical gating: live mode without an API key must
 * hard-error, and simulated mode is an explicit opt-in.
 */

import { describe, it, expect } from 'vitest';
import {
  shouldSimulate,
  LiveModeMisconfiguredError,
  loadConfig,
} from '../config.js';

describe('shouldSimulate', () => {
  it('simulates when mode is simulated (no key required)', () => {
    expect(shouldSimulate({ apiKey: '', mode: 'simulated' })).toBe(true);
    expect(shouldSimulate({ apiKey: 'test-key', mode: 'simulated' })).toBe(true);
  });

  it('does NOT simulate when live with an API key', () => {
    expect(shouldSimulate({ apiKey: 'test-key', mode: 'live' })).toBe(false);
  });

  it('HARD-ERRORS when live with no API key (never fakes a result)', () => {
    expect(() => shouldSimulate({ apiKey: '', mode: 'live' })).toThrow(
      LiveModeMisconfiguredError
    );
  });

  it('includes the operation name in the error message', () => {
    expect(() => shouldSimulate({ apiKey: '', mode: 'live' }, 'sardis_pay')).toThrow(
      /sardis_pay/
    );
  });
});

describe('loadConfig defaults', () => {
  it('defaults mode to live so simulated is an explicit opt-in', () => {
    const prevMode = process.env.SARDIS_MODE;
    const prevKey = process.env.SARDIS_API_KEY;
    delete process.env.SARDIS_MODE;
    delete process.env.SARDIS_API_KEY;
    try {
      const cfg = loadConfig();
      expect(cfg.mode).toBe('live');
      // Live default + empty key means tools hard-error rather than fake.
      expect(() => shouldSimulate(cfg)).toThrow(LiveModeMisconfiguredError);
    } finally {
      if (prevMode === undefined) delete process.env.SARDIS_MODE;
      else process.env.SARDIS_MODE = prevMode;
      if (prevKey === undefined) delete process.env.SARDIS_API_KEY;
      else process.env.SARDIS_API_KEY = prevKey;
    }
  });

  it('respects SARDIS_MODE=simulated opt-in', () => {
    const prev = process.env.SARDIS_MODE;
    process.env.SARDIS_MODE = 'simulated';
    try {
      expect(loadConfig().mode).toBe('simulated');
    } finally {
      if (prev === undefined) delete process.env.SARDIS_MODE;
      else process.env.SARDIS_MODE = prev;
    }
  });
});
