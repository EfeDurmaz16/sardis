/**
 * Tests for LedgerResource
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

const BASE_URL = 'https://api.sardis.network';

describe('LedgerResource', () => {
  let client: SardisClient;

  beforeEach(() => {
    client = new SardisClient({
      apiKey: 'test-key',
      baseUrl: BASE_URL,
    });
  });

  describe('listEntries', () => {
    it('should list ledger entries', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries`, () => {
          return HttpResponse.json({
            entries: [
              {
                id: 'ltx_123',
                wallet_id: 'wallet_abc',
                amount: '100.00',
                token: 'USDC',
                type: 'debit',
                created_at: '2025-01-20T00:00:00Z',
              },
            ],
          });
        })
      );

      const entries = await client.ledger.listEntries();
      expect(entries).toHaveLength(1);
      expect(entries[0].id).toBe('ltx_123');
    });

    it('should list entries with filters', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries`, ({ request }) => {
          const url = new URL(request.url);
          expect(url.searchParams.get('wallet_id')).toBe('wallet_abc');
          expect(url.searchParams.get('limit')).toBe('10');
          expect(url.searchParams.get('offset')).toBe('0');
          return HttpResponse.json({
            entries: [
              {
                id: 'ltx_123',
                wallet_id: 'wallet_abc',
                amount: '100.00',
                token: 'USDC',
                type: 'debit',
                created_at: '2025-01-20T00:00:00Z',
              },
            ],
          });
        })
      );

      const entries = await client.ledger.listEntries({
        wallet_id: 'wallet_abc',
        limit: 10,
        offset: 0,
      });
      expect(entries).toHaveLength(1);
    });

    it('should return empty array when no entries', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries`, () => {
          return HttpResponse.json({ entries: [] });
        })
      );

      const entries = await client.ledger.listEntries();
      expect(entries).toHaveLength(0);
    });

    it('should handle missing entries field gracefully', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries`, () => {
          return HttpResponse.json({});
        })
      );

      const entries = await client.ledger.listEntries();
      expect(entries).toHaveLength(0);
    });
  });

  describe('getEntry', () => {
    it('should get a ledger entry by ID', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries/:txId`, ({ params }) => {
          return HttpResponse.json({
            id: params.txId,
            wallet_id: 'wallet_abc',
            amount: '100.00',
            token: 'USDC',
            type: 'debit',
            created_at: '2025-01-20T00:00:00Z',
          });
        })
      );

      const entry = await client.ledger.getEntry('ltx_456');
      expect(entry.id).toBe('ltx_456');
      expect(entry.wallet_id).toBe('wallet_abc');
    });

    it('should handle 404 for non-existent entry', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries/:txId`, () => {
          return HttpResponse.json(
            { error: 'Entry not found' },
            { status: 404 }
          );
        })
      );

      await expect(client.ledger.getEntry('non_existent')).rejects.toThrow();
    });
  });

  describe('verifyEntry', () => {
    it('should verify a valid ledger entry', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries/:txId/verify`, () => {
          return HttpResponse.json({
            valid: true,
            anchor: 'merkle::abc123',
          });
        })
      );

      const result = await client.ledger.verifyEntry('ltx_789');
      expect(result.valid).toBe(true);
      expect(result.anchor).toBe('merkle::abc123');
    });

    it('should handle invalid entry verification', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/ledger/entries/:txId/verify`, () => {
          return HttpResponse.json({
            valid: false,
            anchor: null,
          });
        })
      );

      const result = await client.ledger.verifyEntry('ltx_tampered');
      expect(result.valid).toBe(false);
    });
  });
});
