/**
 * Simulation Resource
 *
 * Dry-run payment execution to preview policy decisions without on-chain effects.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface SimulationInput {
  agent_id: string;
  amount: string;
  currency?: string;
  merchant_id?: string;
  merchant_category?: string;
  mcc_code?: string;
  chain?: string;
  token?: string;
}

export interface SimulationResult {
  allowed: boolean;
  reason: string;
  policy_checks: Array<{
    check: string;
    passed: boolean;
    detail?: string;
  }>;
  estimated_fee?: string;
  confidence?: number;
}

export class SimulationResource extends BaseResource {
  async run(input: SimulationInput, options?: RequestOptions): Promise<SimulationResult> {
    return this._post<SimulationResult>('/api/v2/simulate', input, options);
  }
}
