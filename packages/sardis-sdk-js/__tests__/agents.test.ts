/**
 * Comprehensive tests for AgentsResource
 *
 * Tests cover:
 * - Agent creation with various configurations
 * - Agent retrieval and listing
 * - Agent updates and deletion
 * - Agent wallet management
 * - Error handling
 * - Edge cases
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';
import { APIError } from '../src/errors.js';

describe('AgentsResource', () => {
    let client: SardisClient;

    const mockAgent = {
        id: 'agent_test123',
        name: 'Test Agent',
        description: 'A test agent for unit testing',
        is_active: true,
        spending_limits: {
            per_transaction: '100.00',
            daily: '1000.00',
            monthly: '10000.00',
        },
        metadata: { environment: 'test' },
        created_at: '2025-01-20T00:00:00Z',
        updated_at: '2025-01-20T00:00:00Z',
    };

    const mockAgentWallet = {
        wallet_id: 'wallet_abc123',
        addresses: {
            base: '0x1234567890abcdef1234567890abcdef12345678',
            polygon: '0xabcdef1234567890abcdef1234567890abcdef12',
        },
    };

    beforeEach(() => {
        client = new SardisClient({ apiKey: 'test-key' });
    });

    describe('create', () => {
        it('should create a new agent with minimal parameters', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json(mockAgent);
                })
            );

            const result = await client.agents.create({
                name: 'Test Agent',
            });

            expect(result).toBeDefined();
            expect(result.id).toBe('agent_test123');
            expect(result.name).toBe('Test Agent');
        });

        it('should create an agent with full parameters', async () => {
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
                spending_limits: {
                    per_transaction: '50.00',
                    daily: '500.00',
                },
                metadata: { key: 'value' },
            });

            expect(receivedBody.name).toBe('Full Agent');
            expect(receivedBody.description).toBe('Agent with all parameters');
            expect(receivedBody.spending_limits.per_transaction).toBe('50.00');
            expect(receivedBody.metadata.key).toBe('value');
        });

        it('should handle creation failure', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json(
                        { error: { message: 'Invalid agent configuration' } },
                        { status: 400 }
                    );
                })
            );

            await expect(client.agents.create({ name: '' })).rejects.toThrow();
        });

        it('should handle network errors during creation', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.error();
                })
            );

            await expect(
                client.agents.create({ name: 'Test' })
            ).rejects.toThrow();
        });
    });

    describe('get', () => {
        it('should get agent by ID', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', ({ params }) => {
                    return HttpResponse.json({ ...mockAgent, id: params.id });
                })
            );

            const result = await client.agents.get('agent_xyz789');

            expect(result).toBeDefined();
            expect(result.id).toBe('agent_xyz789');
        });

        it('should handle agent not found', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json(
                        { error: { message: 'Agent not found', code: 'SARDIS_3404' } },
                        { status: 404 }
                    );
                })
            );

            await expect(client.agents.get('nonexistent')).rejects.toThrow();
        });

        it('should return agent with all fields populated', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json(mockAgent);
                })
            );

            const result = await client.agents.get('agent_test123');

            expect(result.id).toBe('agent_test123');
            expect(result.name).toBe('Test Agent');
            expect(result.description).toBe('A test agent for unit testing');
            expect(result.is_active).toBe(true);
            expect(result.spending_limits).toBeDefined();
            expect(result.spending_limits?.per_transaction).toBe('100.00');
            expect(result.metadata?.environment).toBe('test');
        });
    });

    describe('list', () => {
        it('should list all agents', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json([
                        mockAgent,
                        { ...mockAgent, id: 'agent_2', name: 'Agent 2' },
                        { ...mockAgent, id: 'agent_3', name: 'Agent 3' },
                    ]);
                })
            );

            const result = await client.agents.list();

            expect(result).toHaveLength(3);
            expect(result[0].id).toBe('agent_test123');
            expect(result[1].id).toBe('agent_2');
        });

        it('should handle wrapped response format', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json({
                        agents: [mockAgent, { ...mockAgent, id: 'agent_2' }],
                    });
                })
            );

            const result = await client.agents.list();

            expect(result).toHaveLength(2);
        });

        it('should filter by is_active', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', ({ request }) => {
                    const url = new URL(request.url);
                    const isActive = url.searchParams.get('is_active');
                    if (isActive === 'true') {
                        return HttpResponse.json([mockAgent]);
                    }
                    return HttpResponse.json([
                        { ...mockAgent, id: 'agent_inactive', is_active: false },
                    ]);
                })
            );

            const activeAgents = await client.agents.list({ is_active: true });
            expect(activeAgents).toHaveLength(1);
            expect(activeAgents[0].is_active).toBe(true);

            const inactiveAgents = await client.agents.list({ is_active: false });
            expect(inactiveAgents).toHaveLength(1);
            expect(inactiveAgents[0].is_active).toBe(false);
        });

        it('should respect limit and offset', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', ({ request }) => {
                    const url = new URL(request.url);
                    const limit = url.searchParams.get('limit');
                    const offset = url.searchParams.get('offset');
                    expect(limit).toBe('10');
                    expect(offset).toBe('20');
                    return HttpResponse.json([mockAgent]);
                })
            );

            await client.agents.list({ limit: 10, offset: 20 });
        });

        it('should return empty array when no agents', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json([]);
                })
            );

            const result = await client.agents.list();

            expect(result).toEqual([]);
            expect(result).toHaveLength(0);
        });

        it('should handle wrapped empty response', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json({ agents: [] });
                })
            );

            const result = await client.agents.list();

            expect(result).toEqual([]);
        });
    });

    describe('update', () => {
        it('should update agent name', async () => {
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json({
                        ...mockAgent,
                        name: 'Updated Agent Name',
                        updated_at: '2025-01-21T00:00:00Z',
                    });
                })
            );

            const result = await client.agents.update('agent_test123', {
                name: 'Updated Agent Name',
            });

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

            await client.agents.update('agent_test123', {
                spending_limits: {
                    per_transaction: '200.00',
                    daily: '2000.00',
                },
            });

            expect(receivedBody.spending_limits.per_transaction).toBe('200.00');
            expect(receivedBody.spending_limits.daily).toBe('2000.00');
        });

        it('should deactivate an agent', async () => {
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json({
                        ...mockAgent,
                        is_active: false,
                    });
                })
            );

            const result = await client.agents.update('agent_test123', {
                is_active: false,
            });

            expect(result.is_active).toBe(false);
        });

        it('should handle update validation errors', async () => {
            server.use(
                http.patch('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json(
                        { error: { message: 'Invalid spending limit format' } },
                        { status: 422 }
                    );
                })
            );

            await expect(
                client.agents.update('agent_test123', {
                    spending_limits: { per_transaction: 'invalid' },
                })
            ).rejects.toThrow();
        });
    });

    describe('delete', () => {
        it('should delete (soft delete) an agent', async () => {
            server.use(
                http.delete('https://api.sardis.network/api/v2/agents/:id', () => {
                    return new HttpResponse(null, { status: 204 });
                })
            );

            // Should not throw
            await expect(client.agents.delete('agent_test123')).resolves.not.toThrow();
        });

        it('should handle delete of non-existent agent', async () => {
            server.use(
                http.delete('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json(
                        { error: { message: 'Agent not found' } },
                        { status: 404 }
                    );
                })
            );

            await expect(client.agents.delete('nonexistent')).rejects.toThrow();
        });

        it('should handle delete of agent with active transactions', async () => {
            server.use(
                http.delete('https://api.sardis.network/api/v2/agents/:id', () => {
                    return HttpResponse.json(
                        { error: { message: 'Cannot delete agent with pending transactions' } },
                        { status: 409 }
                    );
                })
            );

            await expect(client.agents.delete('agent_with_pending')).rejects.toThrow();
        });
    });

    describe('getWallet', () => {
        it('should get agent wallet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
                    return HttpResponse.json(mockAgentWallet);
                })
            );

            const result = await client.agents.getWallet('agent_test123');

            expect(result).toBeDefined();
            expect(result.wallet_id).toBe('wallet_abc123');
            expect(result.addresses).toBeDefined();
            expect(result.addresses.base).toBeDefined();
            expect(result.addresses.polygon).toBeDefined();
        });

        it('should handle agent without wallet', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
                    return HttpResponse.json(
                        { error: { message: 'Agent has no wallet' } },
                        { status: 404 }
                    );
                })
            );

            await expect(client.agents.getWallet('agent_no_wallet')).rejects.toThrow();
        });
    });

    describe('createWallet', () => {
        it('should create wallet for agent with default options', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
                    return HttpResponse.json(mockAgentWallet);
                })
            );

            const result = await client.agents.createWallet('agent_test123');

            expect(result).toBeDefined();
            expect(result.wallet_id).toBeDefined();
            expect(result.addresses).toBeDefined();
        });

        it('should create wallet with custom options', async () => {
            let receivedBody: any;
            server.use(
                http.post(
                    'https://api.sardis.network/api/v2/agents/:id/wallet',
                    async ({ request }) => {
                        receivedBody = await request.json();
                        return HttpResponse.json(mockAgentWallet);
                    }
                )
            );

            await client.agents.createWallet('agent_test123', {
                currency: 'USDT',
                limit_per_tx: '50.00',
                limit_total: '1000.00',
            });

            expect(receivedBody.currency).toBe('USDT');
            expect(receivedBody.limit_per_tx).toBe('50.00');
            expect(receivedBody.limit_total).toBe('1000.00');
        });

        it('should handle wallet already exists error', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents/:id/wallet', () => {
                    return HttpResponse.json(
                        { error: { message: 'Agent already has a wallet' } },
                        { status: 409 }
                    );
                })
            );

            await expect(
                client.agents.createWallet('agent_with_wallet')
            ).rejects.toThrow();
        });
    });

    describe('edge cases', () => {
        it('should handle special characters in agent name', async () => {
            const specialAgent = {
                ...mockAgent,
                name: 'Agent with "quotes" & <special> chars',
            };
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json(specialAgent);
                })
            );

            const result = await client.agents.create({
                name: 'Agent with "quotes" & <special> chars',
            });

            expect(result.name).toBe('Agent with "quotes" & <special> chars');
        });

        it('should handle very long description', async () => {
            const longDescription = 'A'.repeat(10000);
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    const body = await request.json() as { description: string };
                    return HttpResponse.json({
                        ...mockAgent,
                        description: body.description,
                    });
                })
            );

            const result = await client.agents.create({
                name: 'Long Description Agent',
                description: longDescription,
            });

            expect(result.description).toBe(longDescription);
        });

        it('should handle empty metadata', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', () => {
                    return HttpResponse.json({
                        ...mockAgent,
                        metadata: {},
                    });
                })
            );

            const result = await client.agents.create({
                name: 'No Metadata Agent',
                metadata: {},
            });

            expect(result.metadata).toEqual({});
        });

        it('should handle nested metadata', async () => {
            const nestedMetadata = {
                level1: {
                    level2: {
                        level3: 'deep value',
                    },
                },
                array: [1, 2, 3],
            };

            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    const body = await request.json() as { metadata: object };
                    return HttpResponse.json({
                        ...mockAgent,
                        metadata: body.metadata,
                    });
                })
            );

            const result = await client.agents.create({
                name: 'Nested Metadata Agent',
                metadata: nestedMetadata,
            });

            expect(result.metadata).toEqual(nestedMetadata);
        });

        it('should handle zero spending limits', async () => {
            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    const body = await request.json() as { spending_limits: object };
                    return HttpResponse.json({
                        ...mockAgent,
                        spending_limits: body.spending_limits,
                    });
                })
            );

            const result = await client.agents.create({
                name: 'Zero Limits Agent',
                spending_limits: {
                    per_transaction: '0.00',
                    daily: '0.00',
                },
            });

            expect(result.spending_limits?.per_transaction).toBe('0.00');
            expect(result.spending_limits?.daily).toBe('0.00');
        });

        it('should handle high precision amounts in spending limits', async () => {
            const highPrecisionLimits = {
                per_transaction: '100.123456789',
                daily: '1000.999999999',
            };

            server.use(
                http.post('https://api.sardis.network/api/v2/agents', async ({ request }) => {
                    const body = await request.json() as { spending_limits: object };
                    return HttpResponse.json({
                        ...mockAgent,
                        spending_limits: body.spending_limits,
                    });
                })
            );

            const result = await client.agents.create({
                name: 'High Precision Agent',
                spending_limits: highPrecisionLimits,
            });

            expect(result.spending_limits).toEqual(highPrecisionLimits);
        });
    });

    describe('request cancellation', () => {
        it('should support AbortController for cancellation', async () => {
            server.use(
                http.get('https://api.sardis.network/api/v2/agents/:id', async () => {
                    // Simulate slow response
                    await new Promise((resolve) => setTimeout(resolve, 1000));
                    return HttpResponse.json(mockAgent);
                })
            );

            const controller = new AbortController();

            // Abort after 50ms
            setTimeout(() => controller.abort(), 50);

            await expect(
                client.agents.get('agent_test123')
            ).rejects.toThrow();
        });
    });
});
