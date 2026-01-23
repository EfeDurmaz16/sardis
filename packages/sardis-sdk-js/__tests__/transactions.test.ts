/**
 * Tests for TransactionsResource
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

const BASE_URL = 'https://api.sardis.network';

describe('TransactionsResource', () => {
  let client: SardisClient;

  beforeEach(() => {
    client = new SardisClient({
      apiKey: 'test-key',
      baseUrl: BASE_URL,
    });
  });

  describe('listChains', () => {
    it('should list supported chains', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/chains`, () => {
          return HttpResponse.json({
            chains: [
              { id: 'base', name: 'Base', rpc_url: 'https://mainnet.base.org' },
              { id: 'base_sepolia', name: 'Base Sepolia', rpc_url: 'https://sepolia.base.org' },
            ],
          });
        })
      );

      const chains = await client.transactions.listChains();
      expect(chains).toHaveLength(2);
      expect(chains[0].id).toBe('base');
    });

    it('should return empty array when no chains configured', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/chains`, () => {
          return HttpResponse.json({ chains: [] });
        })
      );

      const chains = await client.transactions.listChains();
      expect(chains).toHaveLength(0);
    });

    it('should handle missing chains field gracefully', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/chains`, () => {
          return HttpResponse.json({});
        })
      );

      const chains = await client.transactions.listChains();
      expect(chains).toHaveLength(0);
    });
  });

  describe('estimateGas', () => {
    it('should estimate gas for a transaction', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/transactions/estimate-gas`, async ({ request }) => {
          const body = await request.json() as any;
          expect(body.chain).toBe('base_sepolia');
          expect(body.to_address).toBe('0x123');
          expect(body.amount).toBe('100');
          return HttpResponse.json({
            gas_limit: '21000',
            gas_price: '1000000000',
            total_cost: '0.000021',
            chain: 'base_sepolia',
          });
        })
      );

      const estimate = await client.transactions.estimateGas({
        chain: 'base_sepolia',
        to_address: '0x123',
        amount: '100',
      });
      expect(estimate.gas_limit).toBe('21000');
      expect(estimate.chain).toBe('base_sepolia');
    });

    it('should estimate gas with token parameter', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/transactions/estimate-gas`, async ({ request }) => {
          const body = await request.json() as any;
          expect(body.token).toBe('USDC');
          return HttpResponse.json({
            gas_limit: '65000',
            gas_price: '1000000000',
            total_cost: '0.000065',
            chain: 'base',
          });
        })
      );

      const estimate = await client.transactions.estimateGas({
        chain: 'base',
        to_address: '0x456',
        amount: '1000',
        token: 'USDC',
      });
      expect(estimate.gas_limit).toBe('65000');
    });

    it('should handle estimation errors', async () => {
      server.use(
        http.post(`${BASE_URL}/api/v2/transactions/estimate-gas`, () => {
          return HttpResponse.json(
            { error: 'Invalid address format' },
            { status: 400 }
          );
        })
      );

      await expect(
        client.transactions.estimateGas({
          chain: 'base',
          to_address: 'invalid',
          amount: '100',
        })
      ).rejects.toThrow();
    });
  });

  describe('getStatus', () => {
    it('should get transaction status', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/status/:txHash`, ({ params, request }) => {
          expect(params.txHash).toBe('0x123');
          const url = new URL(request.url);
          expect(url.searchParams.get('chain')).toBe('base_sepolia');
          return HttpResponse.json({
            tx_hash: '0x123',
            status: 'confirmed',
            block_number: 12345,
            confirmations: 10,
          });
        })
      );

      const status = await client.transactions.getStatus('0x123', 'base_sepolia');
      expect(status.status).toBe('confirmed');
      expect(status.confirmations).toBe(10);
    });

    it('should return pending status for unconfirmed tx', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/status/:txHash`, () => {
          return HttpResponse.json({
            tx_hash: '0x456',
            status: 'pending',
            block_number: null,
            confirmations: 0,
          });
        })
      );

      const status = await client.transactions.getStatus('0x456', 'base');
      expect(status.status).toBe('pending');
      expect(status.confirmations).toBe(0);
    });

    it('should handle failed transaction status', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/status/:txHash`, () => {
          return HttpResponse.json({
            tx_hash: '0x789',
            status: 'failed',
            block_number: 12340,
            confirmations: 5,
            error: 'Execution reverted',
          });
        })
      );

      const status = await client.transactions.getStatus('0x789', 'base');
      expect(status.status).toBe('failed');
    });

    it('should handle non-existent transaction', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/status/:txHash`, () => {
          return HttpResponse.json(
            { error: 'Transaction not found' },
            { status: 404 }
          );
        })
      );

      await expect(
        client.transactions.getStatus('0xnonexistent', 'base')
      ).rejects.toThrow();
    });
  });

  describe('listTokens', () => {
    it('should list tokens for a chain', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/tokens/:chain`, ({ params }) => {
          expect(params.chain).toBe('base');
          return HttpResponse.json({
            tokens: [
              { symbol: 'USDC', address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' },
              { symbol: 'USDT', address: '0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2' },
            ],
          });
        })
      );

      const tokens = await client.transactions.listTokens('base');
      expect(tokens).toHaveLength(2);
      expect(tokens[0].symbol).toBe('USDC');
    });

    it('should return empty array for chain with no tokens', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/tokens/:chain`, () => {
          return HttpResponse.json({ tokens: [] });
        })
      );

      const tokens = await client.transactions.listTokens('unknown_chain');
      expect(tokens).toHaveLength(0);
    });

    it('should handle missing tokens field gracefully', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/tokens/:chain`, () => {
          return HttpResponse.json({});
        })
      );

      const tokens = await client.transactions.listTokens('base');
      expect(tokens).toHaveLength(0);
    });

    it('should handle unsupported chain error', async () => {
      server.use(
        http.get(`${BASE_URL}/api/v2/transactions/tokens/:chain`, () => {
          return HttpResponse.json(
            { error: 'Chain not supported' },
            { status: 400 }
          );
        })
      );

      await expect(client.transactions.listTokens('invalid_chain')).rejects.toThrow();
    });
  });
});
