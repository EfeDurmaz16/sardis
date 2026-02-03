/**
 * Comprehensive tests for AgentsResource
 *
 * Tests cover:
 * - Agent creation with various configurations
 * - Agent retrieval and listing
 * - Agent updates
 * - Agent deletion
 * - Agent wallet management
 * - Spending limits and policies
 * - Error scenarios
 * - Edge cases
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';
import { APIError } from '../src/errors.js';

describe('AgentsResource Comprehensive Tests', () => {
    let client: SardisClient;

    const mockAgent = {
        id: 'agent_comprehensive_001',
        name: 'Test Agent',
        description: 'A comprehensive test agent',
        organization_id: 'org_test_001',
        wallet_id: 'wallet_agent_001',
        public_key: '0x04abc123...',
        key_algorithm: 'ed25519',
        spending_limits: {
            per_transaction: '1000.00',
            daily: '5000.00',
            monthly: '50000.00',
        },
        policy: {
            allowed_categories: ['software', 'cloud_services', 'api'],
            blocked_merchants: ['blocked_merchant_001'],
            max_transaction_amount: '2000.00',
            approval_threshold: '1500.00',
        },
        is_active: true,
        metadata: {
            environment: 'production',
            team: 'engineering',
            purpose: 'API integrations',
        },
        created_at: '2025-01-20T00:00:00Z',
        updated_at: '2025-01-20T12:00:00Z',
    };

    const mockAgentWallet = {
        wallet_id: 'wallet_agent_001',
        addresses: {
            base: '0x1234567890abcdef1234567890abcdef12345678',
            polygon: '0xabcdef1234567890abcdef1234567890abcdef12',
            ethereum: '0x9876543210fedcba9876543210fedcba98765432',
        },
    };

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-api-key' });
    });

    describe('create', () => {
        it('should create agent with minimal parameters', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json(mockAgent);
                })
            );

            const result = await client.agents.create({
                name: 'Minimal Agent',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('agent_comprehensive_001');
            expect(result.name).toBe('Test Agent');
        });

        it('should create agent with all parameters', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAgent);
                })
            );

            await client.agents.create({
                name: 'Full Agent',
                description: 'Agent with all parameters',
                organization_id: 'org_123',
                public_key: '0x04abc...',
                key_algorithm: 'ed25519',
                spending_limits: {
                    per_transaction: '500.00',
                    daily: '2500.00',
                    monthly: '25000.00',
                },
                policy: {
                    allowed_categories: ['software'],
                    max_transaction_amount: '1000.00',
                },
                metadata: {
                    team: 'devops',
                    environment: 'staging',
                },
            });

            expect(receivedBody.name).toBe('Full Agent');
            expect(receivedBody.description).toBe('Agent with all parameters');
            expect(receivedBody.spending_limits.per_transaction).toBe('500.00');
            expect(receivedBody.policy.allowed_categories).toContain('software');
            expect(receivedBody.metadata.team).toBe('devops');
        });

        it('should handle duplicate name error', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Agent with this name already exists',
                                code: 'SARDIS_3409',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(
                client.agents.create({ name: 'Duplicate Agent' })
            ).rejects.toThrow();
        });

        it('should handle invalid key algorithm', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Invalid key algorithm',
                                code: 'SARDIS_5000',
                                details: { field: 'key_algorithm', allowed: ['ed25519', 'ecdsa-p256'] },
                            },
                        },
                        { status: 422 }
                    );
                })
            );

            await expect(
                client.agents.create({
                    name: 'Invalid Agent',
                    key_algorithm: 'invalid' as any,
                })
            ).rejects.toThrow();
        });

        it('should create agent with different key algorithms', async () => {
            const algorithms = ['ed25519', 'ecdsa-p256'] as const;

            for (const algorithm of algorithms) {
                let receivedAlgorithm: string;
                server.use(
                    http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                        const body = await request.json() as { key_algorithm: string };
                        receivedAlgorithm = body.key_algorithm;
                        return HttpResponse.json({ ...mockAgent, key_algorithm: algorithm });
                    })
                );

                const result = await client.agents.create({
                    name: `Agent ${algorithm}`,
                    key_algorithm: algorithm,
                });

                expect(result.key_algorithm).toBe(algorithm);
            }
        });
    });

    describe('get', () => {
        it('should retrieve agent by ID', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', ({ params }) => {
                    return HttpResponse.json({ ...mockAgent, id: params.id as string });
                })
            );

            const result = await client.agents.get('agent_test_123');

            expect(result.id).toBe('agent_test_123');
            expect(result.name).toBe('Test Agent');
            expect(result.is_active).toBe(true);
        });

        it('should handle agent not found', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', () => {
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

            await expect(client.agents.get('nonexistent_agent')).rejects.toThrow();
        });

        it('should return all agent fields', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json(mockAgent);
                })
            );

            const result = await client.agents.get('agent_comprehensive_001');

            expect(result.id).toBe('agent_comprehensive_001');
            expect(result.name).toBe('Test Agent');
            expect(result.description).toBe('A comprehensive test agent');
            expect(result.organization_id).toBe('org_test_001');
            expect(result.wallet_id).toBe('wallet_agent_001');
            expect(result.key_algorithm).toBe('ed25519');
            expect(result.spending_limits).toBeDefined();
            expect(result.spending_limits?.per_transaction).toBe('1000.00');
            expect(result.policy).toBeDefined();
            expect(result.policy?.allowed_categories).toContain('software');
            expect(result.is_active).toBe(true);
            expect(result.metadata.environment).toBe('production');
            expect(result.created_at).toBeDefined();
            expect(result.updated_at).toBeDefined();
        });
    });

    describe('list', () => {
        it('should list all agents', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json([
                        mockAgent,
                        { ...mockAgent, id: 'agent_002', name: 'Agent 2' },
                        { ...mockAgent, id: 'agent_003', name: 'Agent 3' },
                    ]);
                })
            );

            const result = await client.agents.list();

            expect(result).toHaveLength(3);
            expect(result[0].id).toBe('agent_comprehensive_001');
            expect(result[1].id).toBe('agent_002');
        });

        it('should list agents with limit', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', ({ request }) => {
                    const url = new URL(request.url);
                    const limit = parseInt(url.searchParams.get('limit') || '100');
                    const agents = Array.from({ length: limit }, (_, i) => ({
                        ...mockAgent,
                        id: `agent_${i}`,
                        name: `Agent ${i}`,
                    }));
                    return HttpResponse.json(agents);
                })
            );

            const result = await client.agents.list({ limit: 5 });

            expect(result).toHaveLength(5);
        });

        it('should list agents with offset', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', ({ request }) => {
                    const url = new URL(request.url);
                    const offset = parseInt(url.searchParams.get('offset') || '0');
                    return HttpResponse.json([
                        { ...mockAgent, id: `agent_${offset}` },
                        { ...mockAgent, id: `agent_${offset + 1}` },
                    ]);
                })
            );

            const result = await client.agents.list({ offset: 10 });

            expect(result[0].id).toBe('agent_10');
            expect(result[1].id).toBe('agent_11');
        });

        it('should filter agents by active status', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', ({ request }) => {
                    const url = new URL(request.url);
                    const isActive = url.searchParams.get('is_active') === 'true';
                    return HttpResponse.json([
                        { ...mockAgent, is_active: isActive },
                    ]);
                })
            );

            const activeAgents = await client.agents.list({ is_active: true });
            expect(activeAgents[0].is_active).toBe(true);

            const inactiveAgents = await client.agents.list({ is_active: false });
            expect(inactiveAgents[0].is_active).toBe(false);
        });

        it('should return empty array when no agents exist', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json([]);
                })
            );

            const result = await client.agents.list();

            expect(result).toEqual([]);
            expect(result).toHaveLength(0);
        });
    });

    describe('update', () => {
        it('should update agent name', async () => {
            let receivedBody: any;
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({ ...mockAgent, ...receivedBody });
                })
            );

            const result = await client.agents.update('agent_comprehensive_001', {
                name: 'Updated Agent Name',
            });

            expect(receivedBody.name).toBe('Updated Agent Name');
            expect(result.name).toBe('Updated Agent Name');
        });

        it('should update agent spending limits', async () => {
            let receivedBody: any;
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({
                        ...mockAgent,
                        spending_limits: receivedBody.spending_limits,
                    });
                })
            );

            const newLimits = {
                per_transaction: '2000.00',
                daily: '10000.00',
                monthly: '100000.00',
            };

            const result = await client.agents.update('agent_comprehensive_001', {
                spending_limits: newLimits,
            });

            expect(receivedBody.spending_limits).toEqual(newLimits);
            expect(result.spending_limits).toEqual(newLimits);
        });

        it('should update agent policy', async () => {
            let receivedBody: any;
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({
                        ...mockAgent,
                        policy: receivedBody.policy,
                    });
                })
            );

            const newPolicy = {
                allowed_categories: ['software', 'cloud_services'],
                blocked_merchants: ['merchant_blocked_001', 'merchant_blocked_002'],
                max_transaction_amount: '5000.00',
            };

            const result = await client.agents.update('agent_comprehensive_001', {
                policy: newPolicy,
            });

            expect(receivedBody.policy).toEqual(newPolicy);
        });

        it('should deactivate agent', async () => {
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json({ ...mockAgent, is_active: false });
                })
            );

            const result = await client.agents.update('agent_comprehensive_001', {
                is_active: false,
            });

            expect(result.is_active).toBe(false);
        });

        it('should reactivate agent', async () => {
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json({ ...mockAgent, is_active: true });
                })
            );

            const result = await client.agents.update('agent_inactive', {
                is_active: true,
            });

            expect(result.is_active).toBe(true);
        });

        it('should merge metadata', async () => {
            let receivedBody: any;
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({
                        ...mockAgent,
                        metadata: { ...mockAgent.metadata, ...receivedBody.metadata },
                    });
                })
            );

            const result = await client.agents.update('agent_comprehensive_001', {
                metadata: { newKey: 'newValue' },
            });

            expect(receivedBody.metadata.newKey).toBe('newValue');
            expect(result.metadata.environment).toBe('production'); // Original
            expect(result.metadata.newKey).toBe('newValue'); // New
        });

        it('should handle agent not found', async () => {
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', () => {
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
                client.agents.update('nonexistent_agent', { name: 'New Name' })
            ).rejects.toThrow();
        });
    });

    describe('delete', () => {
        it('should delete agent', async () => {
            let deletedId: string;
            server.use(
                http.delete('https://api.sardis.network/api/v2/agents/:id', ({ params }) => {
                    deletedId = params.id as string;
                    return new HttpResponse(null, { status: 204 });
                })
            );

            await client.agents.delete('agent_to_delete');

            expect(deletedId).toBe('agent_to_delete');
        });

        it('should handle agent not found', async () => {
            server.use(
                http.delete('https://api.sardis.network/api/v2/agents/:id', () => {
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

            await expect(client.agents.delete('nonexistent_agent')).rejects.toThrow();
        });

        it('should handle deletion of agent with active holds', async () => {
            server.use(
                http.delete('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Cannot delete agent with active holds',
                                code: 'SARDIS_3409',
                            },
                        },
                        { status: 409 }
                    );
                })
            );

            await expect(client.agents.delete('agent_with_holds')).rejects.toThrow();
        });
    });

    describe('getWallet', () => {
        it('should get agent wallet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
                    return HttpResponse.json(mockAgentWallet);
                })
            );

            const result = await client.agents.getWallet('agent_comprehensive_001');

            expect(result.wallet_id).toBe('wallet_agent_001');
            expect(result.addresses.base).toBeDefined();
            expect(result.addresses.polygon).toBeDefined();
        });

        it('should handle agent without wallet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
                    return HttpResponse.json(
                        {
                            error: {
                                message: 'Agent does not have a wallet',
                                code: 'SARDIS_3404',
                            },
                        },
                        { status: 404 }
                    );
                })
            );

            await expect(client.agents.getWallet('agent_no_wallet')).rejects.toThrow();
        });
    });

    describe('createWallet', () => {
        it('should create wallet for agent', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
                    return HttpResponse.json(mockAgentWallet);
                })
            );

            const result = await client.agents.createWallet('agent_without_wallet');

            expect(result.wallet_id).toBeDefined();
            expect(result.addresses).toBeDefined();
        });

        it('should handle agent already has wallet', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
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
                client.agents.createWallet('agent_with_wallet')
            ).rejects.toThrow();
        });
    });

    describe('error handling', () => {
        it('should handle rate limiting', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', () => {
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

            await expect(rateLimitedClient.agents.list()).rejects.toThrow();
        });

        it('should retry on server errors', async () => {
            let attempts = 0;
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', () => {
                    attempts++;
                    if (attempts < 3) {
                        return HttpResponse.json(
                            { error: 'Internal server error' },
                            { status: 500 }
                        );
                    }
                    return HttpResponse.json(mockAgent);
                })
            );

            const retryClient = new SardisClient({
                apiKey: 'test-key',
                maxRetries: 5,
                retryDelay: 10,
            });

            const result = await retryClient.agents.get('agent_test');

            expect(result).toBeDefined();
            expect(attempts).toBe(3);
        });
    });

    describe('edge cases', () => {
        it('should handle very long agent name', async () => {
            const longName = 'Agent ' + 'x'.repeat(500);
            let receivedName: string;

            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    const body = await request.json() as { name: string };
                    receivedName = body.name;
                    return HttpResponse.json({ ...mockAgent, name: receivedName });
                })
            );

            const result = await client.agents.create({ name: longName });

            expect(receivedName).toBe(longName);
        });

        it('should handle special characters in name and description', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAgent);
                })
            );

            await client.agents.create({
                name: 'Agent "Special" & <More>',
                description: 'Description with emoji 🤖💰 and symbols @#$%',
            });

            expect(receivedBody.name).toBe('Agent "Special" & <More>');
            expect(receivedBody.description).toContain('🤖💰');
        });

        it('should handle empty metadata', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({ ...mockAgent, metadata: {} });
                })
            );

            const result = await client.agents.create({
                name: 'Agent No Metadata',
                metadata: {},
            });

            expect(receivedBody.metadata).toEqual({});
        });

        it('should handle zero spending limits', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json({
                        ...mockAgent,
                        spending_limits: receivedBody.spending_limits,
                    });
                })
            );

            await client.agents.create({
                name: 'Agent Zero Limits',
                spending_limits: {
                    per_transaction: '0.00',
                    daily: '0.00',
                    monthly: '0.00',
                },
            });

            expect(receivedBody.spending_limits.per_transaction).toBe('0.00');
        });

        it('should handle very large spending limits', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAgent);
                })
            );

            await client.agents.create({
                name: 'Agent Large Limits',
                spending_limits: {
                    per_transaction: '1000000000.00',
                    daily: '10000000000.00',
                    monthly: '100000000000.00',
                },
            });

            expect(receivedBody.spending_limits.per_transaction).toBe('1000000000.00');
        });

        it('should handle agent with all blocked merchants', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAgent);
                })
            );

            const blockedMerchants = Array.from({ length: 100 }, (_, i) => `merchant_${i}`);

            await client.agents.create({
                name: 'Agent Many Blocked',
                policy: {
                    blocked_merchants: blockedMerchants,
                },
            });

            expect(receivedBody.policy.blocked_merchants).toHaveLength(100);
        });

        it('should handle concurrent agent operations', async () => {
            let requestCount = 0;
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', async ({ params }) => {
                    requestCount++;
                    await new Promise((resolve) => setTimeout(resolve, 50));
                    return HttpResponse.json({ ...mockAgent, id: params.id as string });
                })
            );

            const agentIds = ['agent_1', 'agent_2', 'agent_3', 'agent_4', 'agent_5'];
            const results = await Promise.all(agentIds.map((id) => client.agents.get(id)));

            expect(results).toHaveLength(5);
            expect(requestCount).toBe(5);
        });

        it('should handle nested metadata objects', async () => {
            let receivedBody: any;
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    receivedBody = await request.json();
                    return HttpResponse.json(mockAgent);
                })
            );

            const complexMetadata = {
                level1: {
                    level2: {
                        level3: {
                            value: 'deep',
                        },
                    },
                },
                array: [1, 2, { nested: true }],
                mixed: {
                    string: 'text',
                    number: 42,
                    boolean: true,
                    null: null,
                },
            };

            await client.agents.create({
                name: 'Agent Complex Metadata',
                metadata: complexMetadata,
            });

            expect(receivedBody.metadata).toEqual(complexMetadata);
        });
    });

    describe('request cancellation', () => {
        it('should support AbortController', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', async () => {
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    return HttpResponse.json(mockAgent);
                })
            );

            const controller = new AbortController();
            setTimeout(() => controller.abort(), 50);

            await expect(client.agents.get('agent_test', { signal: controller.signal })).rejects.toThrow();
        });
    });
});
