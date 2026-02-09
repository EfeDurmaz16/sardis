/**
 * Tests for A2AResource
 */
import { describe, it, expect } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

describe('A2AResource', () => {
  const client = new SardisClient({ apiKey: 'test-key' });

  const mockAgentCard = {
    agent_id: 'agent_test',
    name: 'Test Agent',
    version: '1.0.0',
    description: 'A test agent for A2A communication',
    operator: {
      name: 'Sardis',
      url: 'https://sardis.sh',
    },
    capabilities: [
      'payment.execute',
      'payment.verify',
      'checkout.create',
    ],
    payment: {
      supported_tokens: ['USDC', 'USDT'],
      supported_chains: ['base', 'polygon'],
      min_amount_minor: 100,
      max_amount_minor: 100_000_00,
      ap2_compliant: true,
      x402_compliant: true,
      ucp_compliant: true,
    },
    endpoints: {
      api: {
        url: 'https://api.test.com/v2',
        protocol: 'https',
        auth_required: true,
        auth_type: 'bearer',
      },
      a2a: {
        url: 'https://api.test.com/v2/a2a',
        protocol: 'https',
        auth_required: true,
        auth_type: 'signature',
      },
    },
    signing: {
      key_id: 'key_123',
      public_key: 'base64_public_key',
      algorithm: 'Ed25519',
    },
    created_at: '2025-01-20T00:00:00Z',
    updated_at: '2025-01-20T00:00:00Z',
  };

  const mockDiscoveredAgent = {
    agent_id: 'agent_test',
    agent_name: 'Test Agent',
    agent_url: 'https://agent.test.com',
    card: mockAgentCard,
    available: true,
    discovered_at: '2025-01-20T00:00:00Z',
    last_verified_at: '2025-01-20T00:00:00Z',
  };

  const mockPaymentResponse = {
    response_id: 'resp_abc123',
    request_id: 'req_xyz789',
    success: true,
    status: 'confirmed',
    tx_hash: '0xabcdef1234567890',
    chain: 'base',
    block_number: 12345,
  };

  const mockCredentialResponse = {
    response_id: 'resp_cred_123',
    request_id: 'req_cred_456',
    valid: true,
    verified_at: '2025-01-20T10:00:00Z',
    signature_valid: true,
    not_expired: true,
    chain_valid: true,
    verification_details: {
      verified_fields: ['issuer', 'subject', 'amount'],
    },
  };

  const mockA2AMessage = {
    message_id: 'msg_abc123',
    message_type: 'ack',
    sender_id: 'agent_recipient',
    recipient_id: 'agent_sender',
    timestamp: '2025-01-20T00:00:00Z',
    payload: { received: true },
    status: 'completed',
  };

  describe('discoverAgent', () => {
    it('should discover an agent', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/discover', () => {
          return HttpResponse.json(mockDiscoveredAgent);
        })
      );

      const agent = await client.a2a.discoverAgent('https://agent.test.com');

      expect(agent).toBeDefined();
      expect(agent.agent_id).toBe('agent_test');
      expect(agent.agent_name).toBe('Test Agent');
      expect(agent.available).toBe(true);
      expect(agent.card).toBeDefined();
      expect(agent.card?.capabilities).toContain('payment.execute');
    });

    it('should send force_refresh flag', async () => {
      let receivedBody: any;
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/discover', async ({ request }) => {
          receivedBody = await request.json();
          return HttpResponse.json(mockDiscoveredAgent);
        })
      );

      await client.a2a.discoverAgent('https://agent.test.com', true);

      expect(receivedBody.agent_url).toBe('https://agent.test.com');
      expect(receivedBody.force_refresh).toBe(true);
    });

    it('should handle unavailable agent', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/discover', () => {
          return HttpResponse.json({
            ...mockDiscoveredAgent,
            available: false,
            last_error: 'Connection refused',
          });
        })
      );

      const agent = await client.a2a.discoverAgent('https://offline.test.com');

      expect(agent.available).toBe(false);
      expect(agent.last_error).toBe('Connection refused');
    });
  });

  describe('getAgentCard', () => {
    it('should get our agent card', async () => {
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/agent-card', () => {
          return HttpResponse.json(mockAgentCard);
        })
      );

      const card = await client.a2a.getAgentCard();

      expect(card).toBeDefined();
      expect(card.agent_id).toBe('agent_test');
      expect(card.capabilities).toContain('payment.execute');
      expect(card.payment?.supported_tokens).toContain('USDC');
      expect(card.signing?.algorithm).toBe('Ed25519');
    });
  });

  describe('listAgents', () => {
    it('should list discovered agents', async () => {
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/agents', () => {
          return HttpResponse.json({
            agents: [mockDiscoveredAgent],
          });
        })
      );

      const agents = await client.a2a.listAgents();

      expect(agents).toHaveLength(1);
      expect(agents[0].agent_id).toBe('agent_test');
    });

    it('should filter agents by capability', async () => {
      let receivedParams: URLSearchParams | null = null;
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/agents', ({ request }) => {
          const url = new URL(request.url);
          receivedParams = url.searchParams;
          return HttpResponse.json({ agents: [] });
        })
      );

      await client.a2a.listAgents({
        capability: 'payment.execute',
        available_only: true,
      });

      expect(receivedParams?.get('capability')).toBe('payment.execute');
      expect(receivedParams?.get('available_only')).toBe('true');
    });

    it('should filter agents by payment support', async () => {
      let receivedParams: URLSearchParams | null = null;
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/agents', ({ request }) => {
          const url = new URL(request.url);
          receivedParams = url.searchParams;
          return HttpResponse.json({ agents: [] });
        })
      );

      await client.a2a.listAgents({
        token: 'USDC',
        chain: 'base',
      });

      expect(receivedParams?.get('token')).toBe('USDC');
      expect(receivedParams?.get('chain')).toBe('base');
    });

    it('should handle array response format', async () => {
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/agents', () => {
          return HttpResponse.json([mockDiscoveredAgent]);
        })
      );

      const agents = await client.a2a.listAgents();

      expect(agents).toHaveLength(1);
    });
  });

  describe('sendPaymentRequest', () => {
    it('should send payment request successfully', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/payment-request', () => {
          return HttpResponse.json(mockPaymentResponse);
        })
      );

      const response = await client.a2a.sendPaymentRequest({
        recipient_agent_url: 'https://merchant.test.com',
        amount_minor: 5000,
        token: 'USDC',
        chain: 'base',
        destination: '0x1234567890abcdef1234567890abcdef12345678',
        purpose: 'Order #12345',
      });

      expect(response.success).toBe(true);
      expect(response.status).toBe('confirmed');
      expect(response.tx_hash).toBe('0xabcdef1234567890');
      expect(response.chain).toBe('base');
      expect(response.block_number).toBe(12345);
    });

    it('should handle payment failure', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/payment-request', () => {
          return HttpResponse.json({
            response_id: 'resp_fail',
            request_id: 'req_fail',
            success: false,
            status: 'failed',
            error: 'Insufficient balance',
            error_code: 'insufficient_balance',
          });
        })
      );

      const response = await client.a2a.sendPaymentRequest({
        recipient_agent_url: 'https://merchant.test.com',
        amount_minor: 10_000_000_00,
        token: 'USDC',
        chain: 'base',
        destination: '0x1234',
      });

      expect(response.success).toBe(false);
      expect(response.error).toBe('Insufficient balance');
      expect(response.error_code).toBe('insufficient_balance');
    });

    it('should include all request fields', async () => {
      let receivedBody: any;
      server.use(
        http.post(
          'https://api.sardis.sh/api/v2/a2a/payment-request',
          async ({ request }) => {
            receivedBody = await request.json();
            return HttpResponse.json(mockPaymentResponse);
          }
        )
      );

      await client.a2a.sendPaymentRequest({
        recipient_agent_url: 'https://merchant.test.com',
        amount_minor: 5000,
        token: 'USDC',
        chain: 'base',
        destination: '0x1234',
        purpose: 'Test payment',
        reference: 'order_123',
        callback_url: 'https://callback.test.com/payments',
        metadata: { order_id: '123' },
      });

      expect(receivedBody.recipient_agent_url).toBe('https://merchant.test.com');
      expect(receivedBody.amount_minor).toBe(5000);
      expect(receivedBody.purpose).toBe('Test payment');
      expect(receivedBody.reference).toBe('order_123');
      expect(receivedBody.callback_url).toBe('https://callback.test.com/payments');
      expect(receivedBody.metadata.order_id).toBe('123');
    });
  });

  describe('verifyCredential', () => {
    it('should verify credential successfully', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/verify-credential', () => {
          return HttpResponse.json(mockCredentialResponse);
        })
      );

      const response = await client.a2a.verifyCredential({
        recipient_agent_url: 'https://verifier.test.com',
        credential_type: 'mandate',
        credential_data: {
          mandate_id: 'mand_123',
          issuer: 'sardis.sh',
          subject: 'agent_abc',
        },
      });

      expect(response.valid).toBe(true);
      expect(response.signature_valid).toBe(true);
      expect(response.not_expired).toBe(true);
      expect(response.chain_valid).toBe(true);
    });

    it('should handle invalid credential', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/verify-credential', () => {
          return HttpResponse.json({
            response_id: 'resp_invalid',
            request_id: 'req_invalid',
            valid: false,
            verified_at: '2025-01-20T10:00:00Z',
            signature_valid: false,
            error: 'Invalid signature',
            error_code: 'invalid_signature',
          });
        })
      );

      const response = await client.a2a.verifyCredential({
        recipient_agent_url: 'https://verifier.test.com',
        credential_type: 'mandate',
        credential_data: { mandate_id: 'mand_invalid' },
      });

      expect(response.valid).toBe(false);
      expect(response.signature_valid).toBe(false);
      expect(response.error).toBe('Invalid signature');
    });

    it('should send verification options', async () => {
      let receivedBody: any;
      server.use(
        http.post(
          'https://api.sardis.sh/api/v2/a2a/verify-credential',
          async ({ request }) => {
            receivedBody = await request.json();
            return HttpResponse.json(mockCredentialResponse);
          }
        )
      );

      await client.a2a.verifyCredential({
        recipient_agent_url: 'https://verifier.test.com',
        credential_type: 'identity',
        credential_data: { did: 'did:web:example.com' },
        verify_signature: true,
        verify_expiration: false,
        verify_chain: false,
      });

      expect(receivedBody.verify_signature).toBe(true);
      expect(receivedBody.verify_expiration).toBe(false);
      expect(receivedBody.verify_chain).toBe(false);
    });
  });

  describe('sendMessage', () => {
    it('should send raw A2A message', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/messages', () => {
          return HttpResponse.json(mockA2AMessage);
        })
      );

      const response = await client.a2a.sendMessage('https://agent.test.com', {
        message_type: 'custom',
        payload: { action: 'notify', data: { event: 'payment_completed' } },
      });

      expect(response.message_type).toBe('ack');
      expect(response.status).toBe('completed');
    });

    it('should include recipient URL in request', async () => {
      let receivedBody: any;
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/messages', async ({ request }) => {
          receivedBody = await request.json();
          return HttpResponse.json(mockA2AMessage);
        })
      );

      await client.a2a.sendMessage('https://agent.test.com', {
        message_type: 'custom',
        payload: { test: true },
      });

      expect(receivedBody.recipient_url).toBe('https://agent.test.com');
      expect(receivedBody.message_type).toBe('custom');
      expect(receivedBody.payload.test).toBe(true);
    });
  });

  describe('listMessages', () => {
    it('should list messages', async () => {
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/messages', () => {
          return HttpResponse.json({
            messages: [mockA2AMessage],
          });
        })
      );

      const messages = await client.a2a.listMessages();

      expect(messages).toHaveLength(1);
      expect(messages[0].message_id).toBe('msg_abc123');
    });

    it('should filter messages', async () => {
      let receivedParams: URLSearchParams | null = null;
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/messages', ({ request }) => {
          const url = new URL(request.url);
          receivedParams = url.searchParams;
          return HttpResponse.json({ messages: [] });
        })
      );

      await client.a2a.listMessages({
        direction: 'inbound',
        message_type: 'payment_request',
        status: 'completed',
        limit: 10,
      });

      expect(receivedParams?.get('direction')).toBe('inbound');
      expect(receivedParams?.get('message_type')).toBe('payment_request');
      expect(receivedParams?.get('status')).toBe('completed');
      expect(receivedParams?.get('limit')).toBe('10');
    });

    it('should handle array response format', async () => {
      server.use(
        http.get('https://api.sardis.sh/api/v2/a2a/messages', () => {
          return HttpResponse.json([mockA2AMessage]);
        })
      );

      const messages = await client.a2a.listMessages();

      expect(messages).toHaveLength(1);
    });
  });

  describe('registerAgent', () => {
    it('should register an agent', async () => {
      server.use(
        http.post('https://api.sardis.sh/api/v2/a2a/agents/register', () => {
          return HttpResponse.json(mockDiscoveredAgent);
        })
      );

      const agent = await client.a2a.registerAgent({
        agent_id: 'my_agent',
        agent_name: 'My Agent',
        agent_url: 'https://my-agent.test.com',
      });

      expect(agent.agent_id).toBe('agent_test');
      expect(agent.available).toBe(true);
    });

    it('should register agent with card', async () => {
      let receivedBody: any;
      server.use(
        http.post(
          'https://api.sardis.sh/api/v2/a2a/agents/register',
          async ({ request }) => {
            receivedBody = await request.json();
            return HttpResponse.json(mockDiscoveredAgent);
          }
        )
      );

      await client.a2a.registerAgent({
        agent_id: 'my_agent',
        agent_name: 'My Agent',
        agent_url: 'https://my-agent.test.com',
        card: mockAgentCard,
      });

      expect(receivedBody.agent_id).toBe('my_agent');
      expect(receivedBody.card).toBeDefined();
      expect(receivedBody.card.capabilities).toContain('payment.execute');
    });
  });
});
