/**
 * Mandate Delegation Resource
 *
 * Delegate spending mandates to sub-agents with scoped authority.
 * Supports hierarchical delegation trees for multi-agent workflows.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface DelegateParams {
  delegate_agent_id: string;
  max_amount?: string;
  allowed_tokens?: string[];
  allowed_chains?: string[];
  expires_at?: string;
  metadata?: Record<string, unknown>;
}

export interface DelegateResponse {
  delegation_id: string;
  parent_mandate_id: string;
  child_mandate_id: string;
  delegate_agent_id: string;
  status: string;
  max_amount: string | null;
  created_at: string;
  expires_at: string | null;
}

export interface DelegationTreeNode {
  mandate_id: string;
  agent_id: string;
  max_amount: string | null;
  consumed: string;
  status: string;
  children: DelegationTreeNode[];
}

export interface DelegationTreeResponse {
  root_mandate_id: string;
  tree: DelegationTreeNode;
}

export class MandateDelegationResource extends BaseResource {
  /**
   * Delegate a mandate to a sub-agent.
   *
   * Creates a child mandate with scoped authority derived from the
   * parent mandate. The child mandate cannot exceed the parent's
   * remaining limits.
   *
   * @param mandateId - Parent mandate ID to delegate from
   * @param params - Delegation parameters
   * @param options - Request options (signal, timeout)
   * @returns The delegation result with child mandate details
   */
  async delegate(
    mandateId: string,
    params: DelegateParams,
    options?: RequestOptions
  ): Promise<DelegateResponse> {
    return this._post<DelegateResponse>(
      `/api/v2/mandates/${mandateId}/delegate`,
      params,
      options
    );
  }

  /**
   * Get the delegation tree for a mandate.
   *
   * Returns the full hierarchy of delegated mandates rooted at
   * the specified mandate, including consumption status at each level.
   *
   * @param mandateId - Root mandate ID
   * @param options - Request options (signal, timeout)
   * @returns The delegation tree
   */
  async getTree(mandateId: string, options?: RequestOptions): Promise<DelegationTreeResponse> {
    return this._get<DelegationTreeResponse>(
      `/api/v2/mandates/${mandateId}/tree`,
      undefined,
      options
    );
  }
}
