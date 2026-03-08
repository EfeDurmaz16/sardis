/**
 * Evidence Resource
 *
 * Retrieve tamper-evident receipts, policy decision traces, and audit proofs.
 */

import { BaseResource } from './base.js';
import type { RequestOptions } from '../types.js';

export interface TransactionEvidence {
  transaction_id: string;
  receipt: Record<string, unknown>;
  policy_decision: Record<string, unknown>;
  compliance_result?: Record<string, unknown>;
  ledger_entries: Record<string, unknown>[];
  blockchain_anchor?: Record<string, unknown>;
}

export interface EvidenceVerification {
  valid: boolean;
  receipt_valid: boolean;
  merkle_proof_valid?: boolean;
  blockchain_anchor_valid?: boolean;
  errors?: string[];
}

export class EvidenceResource extends BaseResource {
  async get(txId: string, options?: RequestOptions): Promise<TransactionEvidence> {
    return this._get<TransactionEvidence>(`/api/v2/evidence/${txId}`, undefined, options);
  }

  async verify(txId: string, options?: RequestOptions): Promise<EvidenceVerification> {
    return this._get<EvidenceVerification>(`/api/v2/evidence/${txId}/verify`, undefined, options);
  }

  async listPolicyDecisions(
    params?: { agent_id?: string; limit?: number },
    options?: RequestOptions,
  ): Promise<Record<string, unknown>[]> {
    return this._get<Record<string, unknown>[]>(
      '/api/v2/evidence/policy-decisions',
      params as Record<string, unknown>,
      options,
    );
  }

  async getPolicyDecision(
    decisionId: string,
    options?: RequestOptions,
  ): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>(
      `/api/v2/evidence/policy-decisions/${decisionId}`,
      undefined,
      options,
    );
  }
}
