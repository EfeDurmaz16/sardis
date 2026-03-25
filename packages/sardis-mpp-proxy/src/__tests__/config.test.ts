import { describe, it, expect } from 'vitest';
import {
  pathMatchesPattern,
  findProtectedRoute,
  buildConfig,
  type Env,
  type ProtectedRoute,
} from '../config.js';

// ---------------------------------------------------------------------------
// pathMatchesPattern
// ---------------------------------------------------------------------------

describe('pathMatchesPattern', () => {
  it('matches exact path', () => {
    expect(pathMatchesPattern('/v1/data', '/v1/data')).toBe(true);
  });

  it('rejects non-matching exact path', () => {
    expect(pathMatchesPattern('/v1/data', '/v1/compute')).toBe(false);
  });

  it('matches wildcard suffix', () => {
    expect(pathMatchesPattern('/v1/data/query', '/v1/data/*')).toBe(true);
    expect(pathMatchesPattern('/v1/data/query/nested', '/v1/data/*')).toBe(true);
  });

  it('matches wildcard prefix without trailing slash', () => {
    expect(pathMatchesPattern('/v1/data', '/v1/data/*')).toBe(true);
  });

  it('rejects partial prefix match', () => {
    expect(pathMatchesPattern('/v1/database', '/v1/data/*')).toBe(false);
  });

  it('matches catch-all', () => {
    expect(pathMatchesPattern('/anything', '/*')).toBe(true);
    expect(pathMatchesPattern('/nested/path', '/*')).toBe(true);
  });

  it('matches root with catch-all', () => {
    expect(pathMatchesPattern('/', '/*')).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// findProtectedRoute
// ---------------------------------------------------------------------------

describe('findProtectedRoute', () => {
  const routes: ProtectedRoute[] = [
    { path: '/v1/data/*', priceUsd: '0.01', description: 'Data query' },
    { path: '/v1/compute/*', priceUsd: '0.10', description: 'Compute job' },
    { path: '/v1/status', priceUsd: '0.00', description: 'Status check' },
  ];

  it('returns matching route config', () => {
    const result = findProtectedRoute('/v1/data/users', routes);
    expect(result).toBeDefined();
    expect(result!.priceUsd).toBe('0.01');
    expect(result!.description).toBe('Data query');
  });

  it('returns first matching route', () => {
    const result = findProtectedRoute('/v1/compute/train', routes);
    expect(result).toBeDefined();
    expect(result!.priceUsd).toBe('0.10');
  });

  it('returns exact match', () => {
    const result = findProtectedRoute('/v1/status', routes);
    expect(result).toBeDefined();
    expect(result!.description).toBe('Status check');
  });

  it('returns undefined for unprotected paths', () => {
    const result = findProtectedRoute('/v1/public', routes);
    expect(result).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// buildConfig
// ---------------------------------------------------------------------------

describe('buildConfig', () => {
  const minimalEnv: Env = {
    MPP_SECRET_KEY: 'test_secret',
    PAY_TO: '0x1234567890abcdef1234567890abcdef12345678',
    SARDIS_API_KEY: 'testkey_config_123',
  };

  it('builds config from minimal env', () => {
    const config = buildConfig(minimalEnv);
    expect(config.mppSecretKey).toBe('test_secret');
    expect(config.recipientAddress).toBe('0x1234567890abcdef1234567890abcdef12345678');
    expect(config.sardisApiKey).toBe('testkey_config_123');
    expect(config.sardisApiUrl).toBe('https://api.sardis.sh');
    expect(config.paymentMethods).toEqual(['tempo']);
  });

  it('uses default catch-all route when no PROTECTED_ROUTES set', () => {
    const config = buildConfig(minimalEnv);
    expect(config.protectedRoutes).toHaveLength(1);
    expect(config.protectedRoutes[0]!.path).toBe('/*');
    expect(config.protectedRoutes[0]!.priceUsd).toBe('0.01');
  });

  it('parses PROTECTED_ROUTES JSON', () => {
    const env: Env = {
      ...minimalEnv,
      PROTECTED_ROUTES: JSON.stringify([
        { path: '/api/*', priceUsd: '0.05', description: 'API call' },
      ]),
    };
    const config = buildConfig(env);
    expect(config.protectedRoutes).toHaveLength(1);
    expect(config.protectedRoutes[0]!.priceUsd).toBe('0.05');
  });

  it('falls back on invalid PROTECTED_ROUTES JSON', () => {
    const env: Env = { ...minimalEnv, PROTECTED_ROUTES: 'invalid json' };
    const config = buildConfig(env);
    expect(config.protectedRoutes).toHaveLength(1);
    expect(config.protectedRoutes[0]!.path).toBe('/*');
  });

  it('strips trailing slash from SARDIS_API_URL', () => {
    const env: Env = {
      ...minimalEnv,
      SARDIS_API_URL: 'https://api.sardis.sh/',
    };
    const config = buildConfig(env);
    expect(config.sardisApiUrl).toBe('https://api.sardis.sh');
  });

  it('parses PAYMENT_METHODS JSON', () => {
    const env: Env = {
      ...minimalEnv,
      PAYMENT_METHODS: '["tempo", "stripe"]',
    };
    const config = buildConfig(env);
    expect(config.paymentMethods).toEqual(['tempo', 'stripe']);
  });
});
