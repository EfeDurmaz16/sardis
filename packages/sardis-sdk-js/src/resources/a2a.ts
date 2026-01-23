/**
 * A2A (Agent-to-Agent) resource
 *
 * Provides inter-agent communication capabilities:
 * - Discover other agents via agent cards
 * - Send payment requests
 * - Verify credentials
 */

import { BaseResource } from './base.js';

// ============ Types ============

export interface AgentCapability {
  capability_type: string;
  version?: string;
  enabled?: boolean;
  endpoint?: string;
}

export interface PaymentCapability {
  supported_tokens: string[];
  supported_chains: string[];
  min_amount_minor?: number;
  max_amount_minor?: number;
  ap2_compliant?: boolean;
  x402_compliant?: boolean;
  ucp_compliant?: boolean;
}

export interface ServiceEndpoint {
  url: string;
  protocol?: string;
  auth_required?: boolean;
  auth_type?: string;
}

export interface AgentCard {
  agent_id: string;
  name: string;
  version?: string;
  description?: string;
  operator?: {
    name?: string;
    url?: string;
    contact?: string;
  };
  capabilities: string[];
  payment?: PaymentCapability;
  endpoints?: {
    api?: ServiceEndpoint;
    mcp?: string;
    webhook?: ServiceEndpoint;
    a2a?: ServiceEndpoint;
  };
  signing?: {
    key_id?: string;
    public_key?: string;
    algorithm?: string;
  };
  created_at?: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
}

export interface DiscoveredAgent {
  agent_id: string;
  agent_name: string;
  agent_url: string;
  card?: AgentCard;
  available: boolean;
  last_error?: string;
  discovered_at: string;
  last_verified_at: string;
}

export interface PaymentRequestInput {
  recipient_agent_url: string;
  amount_minor: number;
  token: string;
  chain: string;
  destination: string;
  purpose?: string;
  reference?: string;
  callback_url?: string;
  metadata?: Record<string, unknown>;
}

export interface PaymentResponse {
  response_id: string;
  request_id: string;
  success: boolean;
  status: string;
  tx_hash?: string;
  chain?: string;
  block_number?: number;
  error?: string;
  error_code?: string;
}

export interface CredentialVerifyInput {
  recipient_agent_url: string;
  credential_type: string;
  credential_data: Record<string, unknown>;
  verify_signature?: boolean;
  verify_expiration?: boolean;
  verify_chain?: boolean;
}

export interface CredentialResponse {
  response_id: string;
  request_id: string;
  valid: boolean;
  verified_at: string;
  signature_valid?: boolean;
  not_expired?: boolean;
  chain_valid?: boolean;
  error?: string;
  error_code?: string;
  verification_details?: Record<string, unknown>;
}

export interface A2AMessage {
  message_id: string;
  message_type: string;
  sender_id: string;
  recipient_id: string;
  timestamp: string;
  expires_at?: string;
  correlation_id?: string;
  in_reply_to?: string;
  payload: Record<string, unknown>;
  signature?: string;
  status: string;
  error?: string;
  error_code?: string;
}

// ============ Resource ============

export class A2AResource extends BaseResource {
  /**
   * Discover an agent by URL
   *
   * Fetches the agent card from /.well-known/agent-card.json
   *
   * @example
   * ```typescript
   * const agent = await client.a2a.discoverAgent('https://agent.example.com');
   * console.log(agent.card?.capabilities);
   * ```
   */
  async discoverAgent(agentUrl: string, forceRefresh?: boolean): Promise<DiscoveredAgent> {
    return this._post<DiscoveredAgent>('/api/v2/a2a/discover', {
      agent_url: agentUrl,
      force_refresh: forceRefresh,
    });
  }

  /**
   * Get our own agent card
   *
   * @example
   * ```typescript
   * const myCard = await client.a2a.getAgentCard();
   * console.log(myCard.capabilities);
   * ```
   */
  async getAgentCard(): Promise<AgentCard> {
    return this._get<AgentCard>('/api/v2/a2a/agent-card');
  }

  /**
   * List all discovered agents
   *
   * @example
   * ```typescript
   * const agents = await client.a2a.listAgents({
   *   capability: 'payment.execute',
   *   available_only: true,
   * });
   * ```
   */
  async listAgents(options?: {
    capability?: string;
    token?: string;
    chain?: string;
    available_only?: boolean;
  }): Promise<DiscoveredAgent[]> {
    const response = await this._get<{ agents: DiscoveredAgent[] } | DiscoveredAgent[]>(
      '/api/v2/a2a/agents',
      options
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.agents || [];
  }

  /**
   * Send a payment request to another agent
   *
   * @example
   * ```typescript
   * const response = await client.a2a.sendPaymentRequest({
   *   recipient_agent_url: 'https://merchant.example.com',
   *   amount_minor: 5000,
   *   token: 'USDC',
   *   chain: 'base',
   *   destination: '0x...',
   *   purpose: 'Order #12345',
   * });
   *
   * if (response.success) {
   *   console.log('Payment tx:', response.tx_hash);
   * }
   * ```
   */
  async sendPaymentRequest(input: PaymentRequestInput): Promise<PaymentResponse> {
    return this._post<PaymentResponse>('/api/v2/a2a/payment-request', input);
  }

  /**
   * Request credential verification from another agent
   *
   * @example
   * ```typescript
   * const response = await client.a2a.verifyCredential({
   *   recipient_agent_url: 'https://verifier.example.com',
   *   credential_type: 'mandate',
   *   credential_data: mandate,
   * });
   *
   * if (response.valid) {
   *   console.log('Credential verified!');
   * }
   * ```
   */
  async verifyCredential(input: CredentialVerifyInput): Promise<CredentialResponse> {
    return this._post<CredentialResponse>('/api/v2/a2a/verify-credential', input);
  }

  /**
   * Send a raw A2A message to another agent
   *
   * @example
   * ```typescript
   * const response = await client.a2a.sendMessage(
   *   'https://agent.example.com',
   *   {
   *     message_type: 'custom',
   *     payload: { action: 'notify', data: {...} },
   *   }
   * );
   * ```
   */
  async sendMessage(
    recipientUrl: string,
    message: Partial<A2AMessage>
  ): Promise<A2AMessage> {
    return this._post<A2AMessage>('/api/v2/a2a/messages', {
      recipient_url: recipientUrl,
      ...message,
    });
  }

  /**
   * List recent A2A messages
   *
   * @example
   * ```typescript
   * const messages = await client.a2a.listMessages({
   *   direction: 'inbound',
   *   message_type: 'payment_request',
   * });
   * ```
   */
  async listMessages(options?: {
    direction?: 'inbound' | 'outbound' | 'all';
    message_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<A2AMessage[]> {
    const response = await this._get<{ messages: A2AMessage[] } | A2AMessage[]>(
      '/api/v2/a2a/messages',
      options
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.messages || [];
  }

  /**
   * Register an agent for discovery
   *
   * @example
   * ```typescript
   * await client.a2a.registerAgent({
   *   agent_id: 'my_agent',
   *   agent_name: 'My Agent',
   *   agent_url: 'https://my-agent.example.com',
   * });
   * ```
   */
  async registerAgent(input: {
    agent_id: string;
    agent_name: string;
    agent_url: string;
    card?: AgentCard;
  }): Promise<DiscoveredAgent> {
    return this._post<DiscoveredAgent>('/api/v2/a2a/agents/register', input);
  }
}
