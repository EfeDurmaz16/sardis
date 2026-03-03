import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SardisAPI, APIError } from '../api.js';
import type { CLIConfig } from '../config.js';

const mockConfig: CLIConfig = {
  api_key: 'testkey_123',
  api_base_url: 'https://api.sardis.sh',
  default_chain: 'base',
  default_token: 'USDC',
  mode: 'live',
  agent_id: '',
  wallet_id: '',
};

describe('SardisAPI', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sends GET request with correct headers', async () => {
    const mockResponse = { wallet_id: 'wal_123', balance: '100.00' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const api = new SardisAPI(mockConfig);
    const result = await api.get('/api/v2/wallets/wal_123');

    expect(fetch).toHaveBeenCalledWith(
      'https://api.sardis.sh/api/v2/wallets/wal_123',
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'X-API-Key': 'testkey_123',
          'Content-Type': 'application/json',
        }),
      }),
    );
    expect(result).toEqual(mockResponse);
  });

  it('sends POST request with body', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ hold_id: 'hold_123' }),
    });

    const api = new SardisAPI(mockConfig);
    const body = { wallet_id: 'wal_123', amount: '100.00' };
    await api.post('/api/v2/holds', body);

    expect(fetch).toHaveBeenCalledWith(
      'https://api.sardis.sh/api/v2/holds',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(body),
      }),
    );
  });

  it('appends query params for GET', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ wallets: [] }),
    });

    const api = new SardisAPI(mockConfig);
    await api.get('/api/v2/wallets', { agent_id: 'agent_123' });

    expect(fetch).toHaveBeenCalledWith(
      'https://api.sardis.sh/api/v2/wallets?agent_id=agent_123',
      expect.any(Object),
    );
  });

  it('throws APIError on non-ok response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve('Unauthorized'),
    });

    const api = new SardisAPI(mockConfig);
    await expect(api.get('/api/v2/wallets')).rejects.toThrow(APIError);
    await expect(api.get('/api/v2/wallets')).rejects.toThrow('401');
  });

  it('detects sandbox mode', () => {
    const sandboxApi = new SardisAPI({ ...mockConfig, api_key: '' });
    expect(sandboxApi.isSandbox()).toBe(true);

    const liveApi = new SardisAPI(mockConfig);
    expect(liveApi.isSandbox()).toBe(false);
  });

  it('normalizes path with leading slash', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });

    const api = new SardisAPI(mockConfig);
    await api.get('api/v2/wallets');

    expect(fetch).toHaveBeenCalledWith(
      'https://api.sardis.sh/api/v2/wallets',
      expect.any(Object),
    );
  });
});

describe('APIError', () => {
  it('contains status and body', () => {
    const err = new APIError(404, 'Not found');
    expect(err.status).toBe(404);
    expect(err.body).toBe('Not found');
    expect(err.message).toContain('404');
    expect(err.name).toBe('APIError');
  });
});
