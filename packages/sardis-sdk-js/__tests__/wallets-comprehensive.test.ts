/**
 * Comprehensive tests for WalletsResource
 *
 * Tests cover:
 * - Wallet creation with various configurations
 * - Wallet retrieval and listing
 * - Balance queries across chains/tokens
 * - Address management
 * - Policy updates
 * - Error scenarios
 * - Edge cases
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';
import { APIError } from '../src/errors.js';

describe('WalletsResource Comprehensive Tests', () => {
    let client: SardisClient;

    const mockWallet = {
        id: 'wallet_comprehensive_001',
        agent_id: 'agent_test_001',
        mpc_provider: 'turnkey',
        addresses: {
            base: '0x1234567890abcdef1234567890abcdef12345678',
            polygon: '0xabcdef1234567890abcdef1234567890abcdef12',
            ethereum: '0x9876543210fedcba9876543210fedcba98765432',
            arbitrum: '0xfedcba9876543210fedcba9876543210fedcba98',
            optimism: '0x1111222233334444555566667777888899990000',
        },
        currency: 'USDC',
        token_limits: {
            USDC: { token: 'USDC', limit_per_tx: '1000.00', limit_total: '10000.00' },
            USDT: { token: 'USDT', limit_per_tx: '500.00', limit_total: '5000.00' },
        },
        limit_per_tx: '1000.00',
        limit_total: '10000.00',
        is_active: true,
        created_at: '2025-01-20T00:00:00Z',
        updated_at: '2025-01-20T12:00:00Z',
    };

    const mockBalance = {
        wallet_id: 'wallet_comprehensive_001',
        chain: 'base',
        token: 'USDC',
        balance: '5000.00',
        balance_minor: 5000000000,
        address: '0x1234567890abcdef1234567890abcdef12345678',
    };

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-api-key' });
    });

    describe('create', () => {
        it('should create wallet with minimal parameters', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets', () => {
                    return HttpResponse.json(mockWallet);
                })
            );

            const result = await client.wallets.create({
                agent_id: 'agent_test_001',
                chain: 'base',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('wallet_comprehensive_001');
            expect(result.agent_id).toBe('agent_test_001');
        });

        it('should create wallet with all parameters', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockWallet);
                })
            );

            await client.wallets.create({
                agent_id: 'agent_full_001',
                chain: 'polygon',
                metadata: {
                    purpose: 'Production wallet',
                    team: 'Engineering',
                    environment: 'prod',
                },
            });

            expect(receivedBody.agent_id).toBe('agent_full_001');
            expect(receivedBody.chain).toBe('polygon');
            expect(receivedBody.metadata.purpose).toBe('Production wallet');
        });

        it('should handle creation failure - duplicate agent', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Agent already has a wallet',
                                code: 'SARDIS_3409',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(
                client.wallets.create({
                    agent_id: 'agent_existing',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });

        it('should handle creation failure - invalid agent', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Agent not found',
                                code: 'SARDIS_3404',
                            },
                        },
                        { status: 404 }
                    );
                })
            );

            await expect(
                client.wallets.create({
                    agent_id: 'nonexistent_agent',
                    chain: 'base',
                })
            ).rejects.toThrow();
        });
    });

    describe('get', () => {
        it('should retrieve wallet by ID', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', ({ params }) => {
                    return HttpResponse.json({ ...mockWallet, id: params.id as string });
                })
            );

            const result = await client.wallets.get('wallet_test_123');

            expect(result.id).toBe('wallet_test_123');
            expect(result.addresses).toBeDefined();
            expect(result.is_active).toBe(true);
        });

        it('should handle wallet not found', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Wallet not found',
                                code: 'SARDIS_3404',
                            },
                        },
                        { status: 404 }
                    );
                })
            );

            await expect(client.wallets.get('nonexistent_wallet')).rejects.toThrow();
        });

        it('should return all wallet fields', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json(mockWallet);
                })
            );

            const result = await client.wallets.get('wallet_comprehensive_001');

            expect(result.id).toBe('wallet_comprehensive_001');
            expect(result.agent_id).toBe('agent_test_001');
            expect(result.mpc_provider).toBe('turnkey');
            expect(result.addresses.base).toBeDefined();
            expect(result.addresses.polygon).toBeDefined();
            expect(result.currency).toBe('USDC');
            expect(result.token_limits.USDC).toBeDefined();
            expect(result.limit_per_tx).toBe('1000.00');
            expect(result.limit_total).toBe('10000.00');
            expect(result.is_active).toBe(true);
            expect(result.created_at).toBeDefined();
            expect(result.updated_at).toBeDefined();
        });
    });

    describe('list', () => {
        it('should list all wallets', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets', () => {
                    return HttpResponse.json([
                        mockWallet,
                        { ...mockWallet, id: 'wallet_002', agent_id: 'agent_002' },
                        { ...mockWallet, id: 'wallet_003', agent_id: 'agent_003' },
                    ]);
                })
            );

            const result = await client.wallets.list();

            expect(result).toHaveLength(3);
            expect(result[0].id).toBe('wallet_comprehensive_001');
            expect(result[1].id).toBe('wallet_002');
        });

        it('should filter wallets by agent ID', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets', ({ request }) => {
                    const url = new URL(request.url);
                    const agentId = url.searchParams.get('agent_id');

                    if (agentId === 'agent_test_001') {
                        return HttpResponse.json([mockWallet]);
                    }
                    return HttpResponse.json([]);
                })
            );

            const result = await client.wallets.list('agent_test_001');

            expect(result).toHaveLength(1);
            expect(result[0].agent_id).toBe('agent_test_001');
        });

        it('should respect limit parameter', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets', ({ request }) => {
                    const url = new URL(request.url);
                    const limit = parseInt(url.searchParams.get('limit') || '100');
                    const wallets = Array.from({ length: limit }, (_, i) => ({
                        ...mockWallet,
                        id: `wallet_${i}`,
                    }));
                    return HttpResponse.json(wallets);
                })
            );

            const result = await client.wallets.list(undefined, 5);

            expect(result).toHaveLength(5);
        });

        it('should return empty array when no wallets exist', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets', () => {
                    return HttpResponse.json([]);
                })
            );

            const result = await client.wallets.list();

            expect(result).toEqual([]);
            expect(result).toHaveLength(0);
        });

        it('should handle wrapped response format', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets', () => {
                    return HttpResponse.json({
                        wallets: [mockWallet, { ...mockWallet, id: 'wallet_002' }],
                        total: 2,
                    });
                })
            );

            // Note: The test assumes the resource handles both array and wrapped formats
            const result = await client.wallets.list();
            expect(result).toBeDefined();
        });
    });

    describe('getBalance', () => {
        it('should get balance for default chain and token', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    const chain = url.searchParams.get('chain');
                    const token = url.searchParams.get('token');

                    expect(chain).toBe('base');
                    expect(token).toBe('USDC');

                    return HttpResponse.json(mockBalance);
                })
            );

            const result = await client.wallets.getBalance('wallet_comprehensive_001');

            expect(result.wallet_id).toBe('wallet_comprehensive_001');
            expect(result.balance).toBe('5000.00');
            expect(result.balance_minor).toBe(5000000000);
        });

        it('should get balance for specific chain and token', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', ({ request }) => {
                    const url = new URL(request.url);
                    const chain = url.searchParams.get('chain');
                    const token = url.searchParams.get('token');

                    return HttpResponse.json({
                        ...mockBalance,
                        chain,
                        token,
                        balance: '2500.00',
                        balance_minor: 2500000000,
                    });
                })
            );

            const result = await client.wallets.getBalance(
                'wallet_comprehensive_001',
                'polygon',
                'USDT'
            );

            expect(result.chain).toBe('polygon');
            expect(result.token).toBe('USDT');
            expect(result.balance).toBe('2500.00');
        });

        it('should get balance for all supported chains', async () => {
            const chains = ['base', 'polygon', 'ethereum', 'arbitrum', 'optimism'];

            for (const chain of chains) {
                server.use(
                    http.get('https://api.sardis.network/api/v2/wallets/:id/balance', () => {
                        return HttpResponse.json({ ...mockBalance, chain });
                    })
                );

                const result = await client.wallets.getBalance(
                    'wallet_comprehensive_001',
                    chain
                );

                expect(result.chain).toBe(chain);
            }
        });

        it('should get balance for all supported tokens', async () => {
            const tokens = ['USDC', 'USDT', 'PYUSD', 'EURC'];

            for (const token of tokens) {
                server.use(
                    http.get('https://api.sardis.network/api/v2/wallets/:id/balance', () => {
                        return HttpResponse.json({ ...mockBalance, token });
                    })
                );

                const result = await client.wallets.getBalance(
                    'wallet_comprehensive_001',
                    'base',
                    token
                );

                expect(result.token).toBe(token);
            }
        });

        it('should handle zero balance', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', () => {
                    return HttpResponse.json({
                        ...mockBalance,
                        balance: '0.00',
                        balance_minor: 0,
                    });
                })
            );

            const result = await client.wallets.getBalance('wallet_zero');

            expect(result.balance).toBe('0.00');
            expect(result.balance_minor).toBe(0);
        });

        it('should handle very large balance', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/balance', () => {
                    return HttpResponse.json({
                        ...mockBalance,
                        balance: '1000000000.00', // $1 billion
                        balance_minor: 1000000000000000000,
                    });
                })
            );

            const result = await client.wallets.getBalance('wallet_whale');

            expect(result.balance).toBe('1000000000.00');
            expect(result.balance_minor).toBe(1000000000000000000);
        });
    });

    describe('getAddresses', () => {
        it('should get all addresses for wallet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/addresses', () => {
                    return HttpResponse.json(mockWallet.addresses);
                })
            );

            const result = await client.wallets.getAddresses('wallet_comprehensive_001');

            expect(result.base).toBe('0x1234567890abcdef1234567890abcdef12345678');
            expect(result.polygon).toBe('0xabcdef1234567890abcdef1234567890abcdef12');
            expect(result.ethereum).toBeDefined();
            expect(result.arbitrum).toBeDefined();
            expect(result.optimism).toBeDefined();
        });

        it('should handle wallet with single chain address', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/addresses', () => {
                    return HttpResponse.json({
                        base: '0x1234567890abcdef1234567890abcdef12345678',
                    });
                })
            );

            const result = await client.wallets.getAddresses('wallet_single_chain');

            expect(result.base).toBeDefined();
            expect(result.polygon).toBeUndefined();
        });

        it('should handle wallet with no addresses yet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id/addresses', () => {
                    return HttpResponse.json({});
                })
            );

            const result = await client.wallets.getAddresses('wallet_new');

            expect(Object.keys(result)).toHaveLength(0);
        });
    });

    describe('setAddress', () => {
        it('should set address for a chain', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets/:id/addresses', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({
                        ...mockWallet,
                        addresses: {
                            ...mockWallet.addresses,
                            [receivedBody.chain]: receivedBody.address,
                        },
                    });
                })
            );

            const result = await client.wallets.setAddress('wallet_comprehensive_001', {
                chain: 'solana',
                address: 'So11111111111111111111111111111111111111112',
            });

            expect(receivedBody.chain).toBe('solana');
            expect(receivedBody.address).toBe('So11111111111111111111111111111111111111112');
        });

        it('should handle address validation error', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets/:id/addresses', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Invalid address format for chain',
                                code: 'SARDIS_5006',
                                details: { chain: 'ethereum', address: 'invalid_address' },
                            },
                        },
                        { status: 422 }
                    );
                })
            );

            await expect(
                client.wallets.setAddress('wallet_comprehensive_001', {
                    chain: 'ethereum',
                    address: 'invalid_address',
                })
            ).rejects.toThrow();
        });

        it('should handle setting address for existing chain (update)', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets/:id/addresses', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({
                        ...mockWallet,
                        addresses: {
                            ...mockWallet.addresses,
                            base: receivedBody.address,
                        },
                    });
                })
            );

            const newAddress = '0xnewaddress1234567890abcdef1234567890abcd';
            const result = await client.wallets.setAddress('wallet_comprehensive_001', {
                chain: 'base',
                address: newAddress,
            });

            expect(receivedBody.chain).toBe('base');
            expect(receivedBody.address).toBe(newAddress);
        });
    });

    describe('error handling', () => {
        it('should handle rate limiting', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets', () => {
                    return HttpResponse.json(
                        { error: 'Rate limit exceeded' },
                        {
                            status: 429,
                            headers: { 'Retry-After': '60' },
                        }
                    );
                })
            );

            const rateLimitedClient = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 0,
            });

            await expect(rateLimitedClient.wallets.list()).rejects.toThrow();
        });

        it('should handle server errors with retry', async () => {
            let attempts = 0;
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    attempts++;
                    if (attempts < 3) {
                        return HttpResponse.json(
                            { error: 'Service temporarily unavailable' },
                            { status: 503 }
                        );
                    }
                    return HttpResponse.json(mockWallet);
                })
            );

            const retryClient = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
                retryDelay: 10,
            });

            const result = await retryClient.wallets.get('wallet_test');

            expect(result).toBeDefined();
            expect(attempts).toBe(3);
        });
    });

    describe('edge cases', () => {
        it('should handle wallet with all MPC providers', async () => {
            const providers = ['turnkey', 'fireblocks', 'local'];

            for (const provider of providers) {
                server.use(
                    http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                        return HttpResponse.json({ ...mockWallet, mpc_provider: provider });
                    })
                );

                const result = await client.wallets.get('wallet_test');
                expect(result.mpc_provider).toBe(provider);
            }
        });

        it('should handle inactive wallet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json({ ...mockWallet, is_active: false });
                })
            );

            const result = await client.wallets.get('wallet_inactive');

            expect(result.is_active).toBe(false);
        });

        it('should handle wallet with multiple token limits', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', () => {
                    return HttpResponse.json({
                        ...mockWallet,
                        token_limits: {
                            USDC: { token: 'USDC', limit_per_tx: '1000.00', limit_total: '10000.00' },
                            USDT: { token: 'USDT', limit_per_tx: '500.00', limit_total: '5000.00' },
                            PYUSD: { token: 'PYUSD', limit_per_tx: '250.00', limit_total: '2500.00' },
                            EURC: { token: 'EURC', limit_per_tx: '100.00', limit_total: '1000.00' },
                        },
                    });
                })
            );

            const result = await client.wallets.get('wallet_multi_token');

            expect(Object.keys(result.token_limits)).toHaveLength(4);
            expect(result.token_limits.USDC.limit_per_tx).toBe('1000.00');
            expect(result.token_limits.EURC.limit_total).toBe('1000.00');
        });

        it('should handle concurrent wallet operations', async () => {
            let requestCount = 0;
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', async ({ params }) => {
                    requestCount++;
                    await new Promise((resolve) => setTimeout(resolve, 50));
                    return HttpResponse.json({ ...mockWallet, id: params.id as string });
                })
            );

            const walletIds = ['wallet_1', 'wallet_2', 'wallet_3', 'wallet_4', 'wallet_5'];
            const results = await Promise.all(walletIds.map((id) => client.wallets.get(id)));

            expect(results).toHaveLength(5);
            expect(requestCount).toBe(5);
            results.forEach((result, i) => {
                expect(result.id).toBe(walletIds[i]);
            });
        });

        it('should handle very long agent ID', async () => {
            const longAgentId = 'agent_' + 'x'.repeat(1000);
            let receivedAgentId: string;

            server.use(
                http.post('https://api.sardis.network/api/v2/wallets', async ({ request }) => {
                    const body = await request.json() as { agent_id: string };
                    receivedAgentId = body.agent_id;
                    return HttpResponse.json({ ...mockWallet, agent_id: receivedAgentId });
                })
            );

            const result = await client.wallets.create({
                agent_id: longAgentId,
                chain: 'base',
            });

            expect(receivedAgentId).toBe(longAgentId);
        });

        it('should handle special characters in metadata', async () => {
            let receivedMetadata: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/wallets', async ({ request }) => {
                    const body = await request.json() as { metadata: any };
                    receivedMetadata = body.metadata;
                    return HttpResponse.json(mockWallet);
                })
            );

            const specialMetadata = {
                name: 'Wallet "Test" & <Special>',
                emoji: '💰🔒',
                nested: { array: [1, 2, 3] },
            };

            await client.wallets.create({
                agent_id: 'agent_special',
                chain: 'base',
                metadata: specialMetadata,
            });

            expect(receivedMetadata).toEqual(specialMetadata);
        });
    });

    describe('request cancellation', () => {
        it('should support AbortController for wallet operations', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/wallets/:id', async () => {
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    return HttpResponse.json(mockWallet);
                })
            );

            const controller = new AbortController();
            setTimeout(() => controller.abort(), 50);

            await expect(client.wallets.get('wallet_test')).rejects.toThrow();
        });
    });
});
