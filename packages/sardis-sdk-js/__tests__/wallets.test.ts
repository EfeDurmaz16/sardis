/**
 * Tests for WalletsResource
 */
import { describe, it, expect } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

describe('WalletsResource', () => {
    const client = new SardisClient({ apiKey: 'test-key' });

    const mockWallet = {
        id: 'wallet_test123',
        address: '0x1234567890abcdef1234567890abcdef12345678',
        status: 'active',
        chain: 'base_sepolia',
        agent_id: 'agent_001',
        created_at: '2025-01-20T00:00:00Z',
    };

    describe('create', () => {
        it('should create a new wallet', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/wallets', () => {
                    return HttpResponse.json(mockWallet);
                })
            );

            const result = await client.wallets.create({
                agent_id: 'agent_001',
                chain: 'base_sepolia',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('wallet_test123');
            expect(result.agent_id).toBe('agent_001');
        });

        it('should send correct creation parameters', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.sh/api/v2/wallets', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockWallet);
                })
            );

            await client.wallets.create({
                agent_id: 'my-agent',
                chain: 'polygon',
                metadata: { purpose: 'test wallet' },
            });

            expect(receivedBody.agent_id).toBe('my-agent');
            expect(receivedBody.chain).toBe('polygon');
            expect(receivedBody.metadata).toEqual({ purpose: 'test wallet' });
        });
    });

    describe('get', () => {
        it('should get wallet by ID', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets/:id', ({ params }) => {
                    return HttpResponse.json({ ...mockWallet, id: params.id });
                })
            );

            const result = await client.wallets.get('wallet_xyz789');

            expect(result).toBeDefined();
            expect(result.id).toBe('wallet_xyz789');
        });

        it('should handle wallet not found', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets/:id', () => {
                    return HttpResponse.json(
                        { error: 'Wallet not found' },
                        { status: 404 }
                    );
                })
            );

            await expect(client.wallets.get('nonexistent')).rejects.toThrow();
        });
    });

    describe('list', () => {
        it('should list all wallets', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets', () => {
                    return HttpResponse.json([mockWallet, { ...mockWallet, id: 'wallet_2' }]);
                })
            );

            const result = await client.wallets.list();

            expect(result).toHaveLength(2);
            expect(result[0].id).toBe('wallet_test123');
        });

        it('should filter by agent ID', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets', ({ request }) => {
                    const url = new URL(request.url);
                    const agentId = url.searchParams.get('agent_id');
                    if (agentId === 'agent_001') {
                        return HttpResponse.json([mockWallet]);
                    }
                    return HttpResponse.json([]);
                })
            );

            const result = await client.wallets.list('agent_001');

            expect(result).toHaveLength(1);
            expect(result[0].agent_id).toBe('agent_001');
        });

        it('should respect limit parameter', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets', ({ request }) => {
                    const url = new URL(request.url);
                    const limit = url.searchParams.get('limit');
                    expect(limit).toBe('50');
                    return HttpResponse.json([mockWallet]);
                })
            );

            await client.wallets.list(undefined, 50);
        });
    });

    describe('getBalance', () => {
        it('should get wallet balance', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets/:id/balance', () => {
                    return HttpResponse.json({
                        wallet_id: 'wallet_test123',
                        chain: 'base',
                        token: 'USDC',
                        balance: '1000.00',
                        balance_minor: 1000000000,
                    });
                })
            );

            const result = await client.wallets.getBalance('wallet_test123');

            expect(result).toBeDefined();
            expect(result.balance).toBe('1000.00');
            expect(result.balance_minor).toBe(1000000000);
        });

        it('should specify chain and token', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    const chain = url.searchParams.get('chain');
                    const token = url.searchParams.get('token');
                    return HttpResponse.json({
                        wallet_id: 'wallet_test123',
                        chain,
                        token,
                        balance: '500.00',
                        balance_minor: 500000000,
                    });
                })
            );

            const result = await client.wallets.getBalance(
                'wallet_test123',
                'polygon',
                'USDT'
            );

            expect(result.chain).toBe('polygon');
            expect(result.token).toBe('USDT');
        });

        it('should use default chain and token', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    const chain = url.searchParams.get('chain');
                    const token = url.searchParams.get('token');
                    expect(chain).toBe('base');
                    expect(token).toBe('USDC');
                    return HttpResponse.json({
                        wallet_id: 'wallet_test123',
                        chain: 'base',
                        token: 'USDC',
                        balance: '1000.00',
                        balance_minor: 1000000000,
                    });
                })
            );

            await client.wallets.getBalance('wallet_test123');
        });
    });

    describe('getAddresses', () => {
        it('should get all wallet addresses', async () => {
            server.use(
                http.get('https://api.sardis.sh/api/v2/wallets/:id/addresses', () => {
                    return HttpResponse.json({
                        base: '0x1234567890abcdef1234567890abcdef12345678',
                        polygon: '0xabcdef1234567890abcdef1234567890abcdef12',
                        ethereum: '0x9876543210fedcba9876543210fedcba98765432',
                    });
                })
            );

            const result = await client.wallets.getAddresses('wallet_test123');

            expect(result).toBeDefined();
            expect(result.base).toBeDefined();
            expect(result.polygon).toBeDefined();
            expect(result.ethereum).toBeDefined();
        });
    });

    describe('setAddress', () => {
        it('should set wallet address', async () => {
            server.use(
                http.post('https://api.sardis.sh/api/v2/wallets/:id/addresses', () => {
                    return HttpResponse.json({
                        ...mockWallet,
                        address: '0xnewaddress1234567890abcdef1234567890abcd',
                    });
                })
            );

            const result = await client.wallets.setAddress('wallet_test123', {
                chain: 'arbitrum',
                address: '0xnewaddress1234567890abcdef1234567890abcd',
            });

            expect(result.address).toBe('0xnewaddress1234567890abcdef1234567890abcd');
        });

        it('should send correct address input', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.sh/api/v2/wallets/:id/addresses',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json(mockWallet);
                    }
                )
            );

            await client.wallets.setAddress('wallet_test123', {
                chain: 'optimism',
                address: '0xaddr123',
            });

            expect(receivedBody.chain).toBe('optimism');
            expect(receivedBody.address).toBe('0xaddr123');
        });
    });
});
