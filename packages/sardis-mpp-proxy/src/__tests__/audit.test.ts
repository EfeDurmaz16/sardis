import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  generateEventId,
  createAuditEntry,
  logAuditEvent,
  type AuditEntry,
} from '../audit.js';

describe('generateEventId', () => {
  it('produces unique IDs', () => {
    const ids = new Set(Array.from({ length: 100 }, () => generateEventId()));
    expect(ids.size).toBe(100);
  });

  it('starts with evt_mpp_ prefix', () => {
    expect(generateEventId()).toMatch(/^evt_mpp_/);
  });
});

describe('createAuditEntry', () => {
  it('adds eventId and timestamp', () => {
    const entry = createAuditEntry({
      eventType: 'mpp_proxy.payment_completed',
      amount: '0.01',
      payerAddress: '0xabc',
      recipientAddress: '0xdef',
      paymentMethod: 'tempo',
      route: '/v1/data',
      merchant: 'api.example.com',
      httpMethod: 'GET',
      responseStatus: 200,
    });

    expect(entry.eventId).toMatch(/^evt_mpp_/);
    expect(entry.timestamp).toBeTruthy();
    expect(new Date(entry.timestamp).getTime()).not.toBeNaN();
    expect(entry.amount).toBe('0.01');
  });
});

describe('logAuditEvent', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockEntry: AuditEntry = {
    eventId: 'evt_mpp_test',
    timestamp: new Date().toISOString(),
    eventType: 'mpp_proxy.payment_completed',
    amount: '0.05',
    payerAddress: '0xpayer',
    recipientAddress: '0xrecipient',
    paymentMethod: 'tempo',
    route: '/v1/data/query',
    merchant: 'api.example.com',
    httpMethod: 'POST',
    responseStatus: 200,
  };

  it('skips logging when no API key is provided', async () => {
    global.fetch = vi.fn();
    await logAuditEvent(mockEntry, 'https://api.sardis.sh', '');
    expect(fetch).not.toHaveBeenCalled();
  });

  it('sends POST to /api/v2/events/ingest', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true });

    await logAuditEvent(
      mockEntry,
      'https://api.sardis.sh',
      'testkey_audit_123',
    );

    expect(fetch).toHaveBeenCalledWith(
      'https://api.sardis.sh/api/v2/events/ingest',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'X-API-Key': 'testkey_audit_123',
          'Content-Type': 'application/json',
        }),
      }),
    );
  });

  it('does not throw on fetch failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
    // Should not throw
    await logAuditEvent(
      mockEntry,
      'https://api.sardis.sh',
      'testkey_audit_123',
    );
  });

  it('does not throw on non-ok response', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 });
    await logAuditEvent(
      mockEntry,
      'https://api.sardis.sh',
      'testkey_audit_123',
    );
  });
});
