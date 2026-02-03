/**
 * Policies Resource
 *
 * Natural language policy parsing + deterministic enforcement helpers.
 */

import { BaseResource } from './base.js';
import type {
  ParsedPolicy,
  PolicyPreviewResponse,
  ApplyPolicyFromNLResponse,
  PolicyCheckResponse,
  RequestOptions,
} from '../types.js';

export class PoliciesResource extends BaseResource {
  async parse(
    natural_language: string,
    agent_id?: string,
    options?: RequestOptions
  ): Promise<ParsedPolicy> {
    return this._post<ParsedPolicy>(
      '/api/v2/policies/parse',
      { natural_language, agent_id },
      options
    );
  }

  async preview(
    natural_language: string,
    agent_id: string,
    options?: RequestOptions
  ): Promise<PolicyPreviewResponse> {
    return this._post<PolicyPreviewResponse>(
      '/api/v2/policies/preview',
      { natural_language, agent_id, confirm: false },
      options
    );
  }

  async apply(
    natural_language: string,
    agent_id: string,
    options?: RequestOptions
  ): Promise<ApplyPolicyFromNLResponse> {
    return this._post<ApplyPolicyFromNLResponse>(
      '/api/v2/policies/apply',
      { natural_language, agent_id, confirm: true },
      options
    );
  }

  async get(agent_id: string, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>(`/api/v2/policies/${agent_id}`, undefined, options);
  }

  async check(
    input: {
      agent_id: string;
      amount: string;
      currency?: string;
      merchant_id?: string | null;
      merchant_category?: string | null;
      mcc_code?: string | null;
    },
    options?: RequestOptions
  ): Promise<PolicyCheckResponse> {
    return this._post<PolicyCheckResponse>('/api/v2/policies/check', input, options);
  }

  async examples(options?: RequestOptions): Promise<Record<string, unknown>[]> {
    return this._get<Record<string, unknown>[]>('/api/v2/policies/examples', undefined, options);
  }
}

