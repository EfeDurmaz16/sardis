import { describe, it, expect, vi, beforeEach } from 'vitest';
import { checkPolicy, type PolicyCheckRequest } from '../sardis-policy.js';

describe('checkPolicy', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockRequest: PolicyCheckRequest = {
    amount: '0.01',
    payerAddress: '0xpayer123',
    route: '/v1/data/query',
    merchant: 'api.example.com',
    paymentMethod: 'tempo',
  };

  it('skips policy check when no API key is provided', async () => {
    const result = await checkPolicy(
      mockRequest,
      'https://api.sardis.sh',
      '',
    );
    expect(result.allowed).toBe(true);
    expect(result.reason).toContain('not configured');
  });

  it('returns allowed when Sardis API approves', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          allowed: true,
          reason: 'ALLOWED by mandate',
          mandate_id: 'mnd_123',
          remaining_budget: '99.99',
          checks_total: 5,
        }),
    });

    const result = await checkPolicy(
      mockRequest,
      'https://api.sardis.sh',
      'testkey_policy_123',
    );

    expect(result.allowed).toBe(true);
    expect(result.mandateId).toBe('mnd_123');
    expect(result.remainingBudget).toBe('99.99');
    expect(result.checksRun).toBe(5);
  });

  it('returns blocked when Sardis API rejects', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          allowed: false,
          reason: 'BUDGET_EXCEEDED',
        }),
    });

    const result = await checkPolicy(
      mockRequest,
      'https://api.sardis.sh',
      'testkey_policy_123',
    );

    expect(result.allowed).toBe(false);
    expect(result.reason).toBe('BUDGET_EXCEEDED');
  });

  it('fails closed on API error', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal Server Error'),
    });

    const result = await checkPolicy(
      mockRequest,
      'https://api.sardis.sh',
      'testkey_policy_123',
    );

    expect(result.allowed).toBe(false);
    expect(result.reason).toContain('blocked because policy enforcement is unavailable');
  });

  it('fails closed on network error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('DNS resolution failed'));

    const result = await checkPolicy(
      mockRequest,
      'https://api.sardis.sh',
      'testkey_policy_123',
    );

    expect(result.allowed).toBe(false);
    expect(result.reason).toContain('blocked because policy enforcement is unavailable');
  });

  it('sends correct payload to Sardis API', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ allowed: true }),
    });

    await checkPolicy(
      mockRequest,
      'https://api.sardis.sh',
      'testkey_policy_123',
    );

    expect(fetch).toHaveBeenCalledWith(
      'https://api.sardis.sh/api/v2/mpp/evaluate',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'X-API-Key': 'testkey_policy_123',
          'Content-Type': 'application/json',
        }),
        body: expect.stringContaining('"merchant":"api.example.com"'),
      }),
    );
  });
});
