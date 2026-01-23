/**
 * Agents resource
 *
 * Agents are the core identity entities in Sardis. They can:
 * - Own wallets
 * - Issue mandates
 * - Be subject to spending policies
 */

import { BaseResource } from './base.js';
import type {
  Agent,
  CreateAgentInput,
  UpdateAgentInput,
  ListAgentsOptions,
} from '../types.js';

export class AgentsResource extends BaseResource {
  /**
   * Create a new agent
   *
   * @example
   * ```typescript
   * const agent = await client.agents.create({
   *   name: 'Shopping Agent',
   *   description: 'Agent for e-commerce purchases',
   *   spending_limits: {
   *     per_transaction: '100.00',
   *     daily: '500.00',
   *   },
   * });
   * ```
   */
  async create(input: CreateAgentInput): Promise<Agent> {
    return this._post<Agent>('/api/v2/agents', input);
  }

  /**
   * Get an agent by ID
   *
   * @example
   * ```typescript
   * const agent = await client.agents.get('agent_abc123');
   * console.log(agent.name, agent.is_active);
   * ```
   */
  async get(agentId: string): Promise<Agent> {
    return this._get<Agent>(`/api/v2/agents/${agentId}`);
  }

  /**
   * List all agents
   *
   * @example
   * ```typescript
   * // List all agents
   * const agents = await client.agents.list();
   *
   * // List with pagination
   * const page = await client.agents.list({ limit: 10, offset: 20 });
   *
   * // List only active agents
   * const active = await client.agents.list({ is_active: true });
   * ```
   */
  async list(options?: ListAgentsOptions): Promise<Agent[]> {
    const params: Record<string, unknown> = {};

    if (options?.limit !== undefined) {
      params.limit = options.limit;
    }
    if (options?.offset !== undefined) {
      params.offset = options.offset;
    }
    if (options?.is_active !== undefined) {
      params.is_active = options.is_active;
    }

    const response = await this._get<{ agents: Agent[] } | Agent[]>(
      '/api/v2/agents',
      Object.keys(params).length > 0 ? params : undefined
    );

    // Handle both array and object response formats
    if (Array.isArray(response)) {
      return response;
    }
    return response.agents || [];
  }

  /**
   * Update an agent
   *
   * @example
   * ```typescript
   * const updated = await client.agents.update('agent_abc123', {
   *   name: 'Updated Name',
   *   is_active: false,
   * });
   * ```
   */
  async update(agentId: string, input: UpdateAgentInput): Promise<Agent> {
    return this._patch<Agent>(`/api/v2/agents/${agentId}`, input);
  }

  /**
   * Delete an agent
   *
   * Note: This is a soft delete - the agent is deactivated, not removed.
   *
   * @example
   * ```typescript
   * await client.agents.delete('agent_abc123');
   * ```
   */
  async delete(agentId: string): Promise<void> {
    await this._delete(`/api/v2/agents/${agentId}`);
  }

  /**
   * Get an agent's associated wallet
   *
   * @example
   * ```typescript
   * const wallet = await client.agents.getWallet('agent_abc123');
   * console.log(wallet.addresses);
   * ```
   */
  async getWallet(agentId: string): Promise<{ wallet_id: string; addresses: Record<string, string> }> {
    return this._get(`/api/v2/agents/${agentId}/wallet`);
  }

  /**
   * Create a wallet for an agent
   *
   * @example
   * ```typescript
   * const wallet = await client.agents.createWallet('agent_abc123', {
   *   currency: 'USDC',
   *   limit_per_tx: '100.00',
   * });
   * ```
   */
  async createWallet(
    agentId: string,
    options?: {
      currency?: string;
      limit_per_tx?: string;
      limit_total?: string;
    }
  ): Promise<{ wallet_id: string; addresses: Record<string, string> }> {
    return this._post(`/api/v2/agents/${agentId}/wallet`, options || {});
  }
}
