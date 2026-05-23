/**
 * Facility Gate resource — programmable facility access for agents.
 *
 * Ported to TS to close the parity gap with
 * `packages/sardis-sdk-python/src/sardis_sdk/resources/facility_gate.py`.
 */

import { BaseResource } from '../core/base-resource.js';
import type { RequestOptions } from '../types.js';

export interface FacilityRequestPayload {
  [key: string]: unknown;
}

export interface FacilityEvidenceItem {
  [key: string]: unknown;
}

export interface ExportEventsParams {
  occurred_from?: string | Date;
  occurred_to?: string | Date;
  event_type?: string;
  limit?: number;
}

function toIsoString(value: string | Date | undefined): string | undefined {
  if (value === undefined) return undefined;
  if (value instanceof Date) return value.toISOString();
  return value;
}

function buildExportParams(input: ExportEventsParams): Record<string, unknown> {
  const params: Record<string, unknown> = { limit: input.limit ?? 500 };
  const from = toIsoString(input.occurred_from);
  const to = toIsoString(input.occurred_to);
  if (from) params['occurred_from'] = from;
  if (to) params['occurred_to'] = to;
  if (input.event_type) params['event_type'] = input.event_type;
  return params;
}

export class FacilityGateResource extends BaseResource {
  /** Create a Facility Gate spend request. */
  createRequest(payload: FacilityRequestPayload, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._post<Record<string, unknown>>('/api/v2/facility-requests', payload, options);
  }

  /** Attach evidence references to a facility request. */
  attachEvidence(
    requestId: string,
    evidence: FacilityEvidenceItem[],
    opts: { idempotencyKey?: string; options?: RequestOptions } = {},
  ): Promise<Record<string, unknown>> {
    const body: Record<string, unknown> = { evidence };
    if (opts.idempotencyKey) body['idempotency_key'] = opts.idempotencyKey;
    return this._post<Record<string, unknown>>(
      `/api/v2/facility-requests/${requestId}/evidence`,
      body,
      opts.options,
    );
  }

  /** Evaluate and record a facility authorization decision. */
  authorize(requestId: string, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._post<Record<string, unknown>>(`/api/v2/facility-requests/${requestId}/authorize`, undefined, options);
  }

  /** Execute an approved authorization through the configured adapter. */
  execute(requestId: string, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._post<Record<string, unknown>>(`/api/v2/facility-requests/${requestId}/execute`, undefined, options);
  }

  /** Audit reconstruction for a facility request. */
  audit(requestId: string, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>(`/api/v2/facility-requests/${requestId}/audit`, undefined, options);
  }

  /** Export a request-level audit packet. */
  exportAudit(requestId: string, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>(`/api/v2/facility-requests/${requestId}/audit/export`, undefined, options);
  }

  /** Export organization-level Facility Gate events and decision packets. */
  exportEvents(params: ExportEventsParams = {}, options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>('/api/v2/facility-requests/audit/exports', buildExportParams(params), options);
  }

  /** List Facility Gate request states. */
  async list(params: { limit?: number } = {}, options?: RequestOptions): Promise<Record<string, unknown>[]> {
    const data = await this._get<{ requests?: Record<string, unknown>[]; items?: Record<string, unknown>[] }>(
      '/api/v2/facility-requests',
      { limit: params.limit ?? 50 },
      options,
    );
    return data.requests ?? data.items ?? [];
  }

  /** List requests waiting for human review. */
  manualReview(options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>('/api/v2/facility-requests/manual-review', undefined, options);
  }

  /** Record a Facility Gate approval outcome. */
  recordApproval(
    requestId: string,
    input: { approved: boolean; reviewedBy: string; reason?: string; idempotencyKey?: string },
    options?: RequestOptions,
  ): Promise<Record<string, unknown>> {
    const body: Record<string, unknown> = { approved: input.approved, reviewed_by: input.reviewedBy };
    if (input.reason) body['reason'] = input.reason;
    if (input.idempotencyKey) body['idempotency_key'] = input.idempotencyKey;
    return this._post<Record<string, unknown>>(`/api/v2/facility-requests/${requestId}/approval`, body, options);
  }

  /** Create a facility revocation event. */
  revoke(
    input: { scope: string; targetId: string; reason: string; idempotencyKey?: string },
    options?: RequestOptions,
  ): Promise<Record<string, unknown>> {
    const body: Record<string, unknown> = {
      scope: input.scope,
      target_id: input.targetId,
      reason: input.reason,
    };
    if (input.idempotencyKey) body['idempotency_key'] = input.idempotencyKey;
    return this._post<Record<string, unknown>>('/api/v2/facility-requests/revocations', body, options);
  }

  /** List Facility Gate exception events. */
  exceptions(options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>('/api/v2/facility-requests/exceptions', undefined, options);
  }

  /** Append an auditable exception resolution event. */
  resolveException(
    input: { eventId: string; resolvedBy: string; resolution: string },
    options?: RequestOptions,
  ): Promise<Record<string, unknown>> {
    return this._post<Record<string, unknown>>(
      '/api/v2/facility-requests/exceptions/resolve',
      { event_id: input.eventId, resolved_by: input.resolvedBy, resolution: input.resolution },
      options,
    );
  }

  /** Get Facility Gate limiter summary. */
  limits(options?: RequestOptions): Promise<Record<string, unknown>> {
    return this._get<Record<string, unknown>>('/api/v2/facility-requests/limits', undefined, options);
  }
}
