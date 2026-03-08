/**
 * Kill Switch Resource
 *
 * Emergency controls to halt payment processing by scope.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface KillSwitchStatus {
  global: Record<string, unknown> | null;
  organizations: Record<string, unknown>;
  agents: Record<string, unknown>;
  rails: Record<string, unknown>;
  chains: Record<string, unknown>;
}

export interface ActivateParams {
  reason: string;
  notes?: string;
  auto_reactivate_after_seconds?: number;
}

export class KillSwitchResource extends BaseResource {
  async status(options?: RequestOptions): Promise<KillSwitchStatus> {
    return this._get<KillSwitchStatus>('/api/v2/admin/kill-switch/status', undefined, options);
  }

  async activateRail(
    rail: string,
    data: ActivateParams,
    options?: RequestOptions,
  ): Promise<Record<string, unknown>> {
    return this._post(`/api/v2/admin/kill-switch/rail/${rail}/activate`, data, options);
  }

  async deactivateRail(rail: string, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._post(`/api/v2/admin/kill-switch/rail/${rail}/deactivate`, {}, options);
  }

  async activateChain(
    chain: string,
    data: ActivateParams,
    options?: RequestOptions,
  ): Promise<Record<string, unknown>> {
    return this._post(`/api/v2/admin/kill-switch/chain/${chain}/activate`, data, options);
  }

  async deactivateChain(chain: string, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._post(`/api/v2/admin/kill-switch/chain/${chain}/deactivate`, {}, options);
  }
}
