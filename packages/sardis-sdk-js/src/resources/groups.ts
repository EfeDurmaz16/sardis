/**
 * Groups resource
 *
 * Agent groups enable multi-agent governance with shared budgets
 * and merchant policies across multiple agents.
 */

import { BaseResource } from './base.js';
import type {
  AgentGroup,
  CreateGroupInput,
  UpdateGroupInput,
  GroupSpending,
  RequestOptions,
} from '../types.js';

export class GroupsResource extends BaseResource {
  /**
   * Create a new agent group
   *
   * @example
   * ```typescript
   * const group = await client.groups.create({
   *   name: 'Engineering Team',
   *   budget: { daily: '5000.00', monthly: '50000.00' },
   * });
   * ```
   */
  async create(input: CreateGroupInput, options?: RequestOptions): Promise<AgentGroup> {
    return this._post<AgentGroup>('/api/v2/groups', input, options);
  }

  /**
   * Get a group by ID
   *
   * @example
   * ```typescript
   * const group = await client.groups.get('grp_abc123');
   * console.log(group.name, group.agent_ids);
   * ```
   */
  async get(groupId: string, options?: RequestOptions): Promise<AgentGroup> {
    return this._get<AgentGroup>(`/api/v2/groups/${groupId}`, undefined, options);
  }

  /**
   * List all agent groups
   *
   * @example
   * ```typescript
   * const groups = await client.groups.list();
   * const limited = await client.groups.list({ limit: 10 });
   * ```
   */
  async list(options?: { limit?: number; offset?: number }): Promise<AgentGroup[]> {
    const params: Record<string, unknown> = {};
    if (options?.limit !== undefined) params.limit = options.limit;
    if (options?.offset !== undefined) params.offset = options.offset;

    const response = await this._get<AgentGroup[] | { groups: AgentGroup[] }>(
      '/api/v2/groups',
      Object.keys(params).length > 0 ? params : undefined
    );

    if (Array.isArray(response)) return response;
    return response.groups || [];
  }

  /**
   * Update a group
   *
   * @example
   * ```typescript
   * const updated = await client.groups.update('grp_abc123', {
   *   name: 'Updated Name',
   *   budget: { daily: '10000.00' },
   * });
   * ```
   */
  async update(groupId: string, input: UpdateGroupInput): Promise<AgentGroup> {
    return this._patch<AgentGroup>(`/api/v2/groups/${groupId}`, input);
  }

  /**
   * Delete a group
   *
   * @example
   * ```typescript
   * await client.groups.delete('grp_abc123');
   * ```
   */
  async delete(groupId: string): Promise<void> {
    await this._delete(`/api/v2/groups/${groupId}`);
  }

  /**
   * Add an agent to a group
   *
   * @example
   * ```typescript
   * const group = await client.groups.addAgent('grp_abc123', 'agent_def456');
   * ```
   */
  async addAgent(groupId: string, agentId: string): Promise<AgentGroup> {
    return this._post<AgentGroup>(`/api/v2/groups/${groupId}/agents`, { agent_id: agentId });
  }

  /**
   * Remove an agent from a group
   *
   * @example
   * ```typescript
   * const group = await client.groups.removeAgent('grp_abc123', 'agent_def456');
   * ```
   */
  async removeAgent(groupId: string, agentId: string): Promise<AgentGroup> {
    return this._delete<AgentGroup>(`/api/v2/groups/${groupId}/agents/${agentId}`);
  }

  /**
   * Get current spending for a group
   *
   * @example
   * ```typescript
   * const spending = await client.groups.getSpending('grp_abc123');
   * console.log(spending.budget, spending.agent_count);
   * ```
   */
  async getSpending(groupId: string): Promise<GroupSpending> {
    return this._get<GroupSpending>(`/api/v2/groups/${groupId}/spending`);
  }
}
