/**
 * Facility Gate tools for MCP server.
 *
 * Agent-facing programmable facility access tools. These create and inspect
 * facility requests, but intentionally do not expose admin approval or
 * revocation controls.
 */

import { z } from 'zod';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

const MerchantSchema = z.object({
  name: z.string().describe('Merchant or vendor name'),
  category: z.string().optional().describe('Merchant category, such as cloud, api, saas, or developer_tooling'),
  merchant_id: z.string().optional().describe('Known merchant identifier, if available'),
});

const FacilityRequestSchema = z.object({
  organization_id: z.string().optional().describe('Organization ID. Defaults to server-side auth context when omitted.'),
  agent_id: z.string().describe('Agent requesting delegated facility access'),
  facility_id: z.string().describe('Facility ID to draw against'),
  mandate_id: z.string().describe('Mandate granting explicit facility draw authority'),
  amount: z.union([z.string(), z.number()]).describe('Requested spend amount'),
  currency: z.string().optional().default('USD').describe('Currency code'),
  merchant: MerchantSchema,
  purpose: z.string().describe('Business purpose for the request'),
  category: z.string().optional().describe('Spend category'),
  idempotency_key: z.string().optional().describe('Idempotency key for request creation'),
  metadata: z.record(z.unknown()).optional().describe('Additional request metadata'),
});

const FacilityEvidenceSchema = z.object({
  request_id: z.string().describe('Facility request ID'),
  evidence: z.array(z.record(z.unknown())).min(1).describe('Evidence references and hashes to attach'),
  idempotency_key: z.string().optional().describe('Idempotency key for evidence attachment'),
});

const FacilityRequestIdSchema = z.object({
  request_id: z.string().describe('Facility request ID'),
});

const FacilityListSchema = z.object({
  limit: z.number().int().positive().max(100).optional().default(50),
});

function jsonResult(payload: unknown): ToolResult {
  return {
    content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }],
  };
}

function validationError(error: z.ZodError): ToolResult {
  return {
    content: [{ type: 'text', text: `Invalid request: ${error.message}` }],
    isError: true,
  };
}

function errorResult(prefix: string, error: unknown): ToolResult {
  return {
    content: [{ type: 'text', text: `${prefix}: ${error instanceof Error ? error.message : 'Unknown error'}` }],
    isError: true,
  };
}

function simulatedId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}`;
}

export const facilityGateToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_facility_request',
    description:
      'Create a Sardis Facility Gate request for delegated, mandate-aware facility access. ' +
      'Use this when an agent needs authority to spend through a partner-backed facility instead of a prefunded balance.',
    inputSchema: {
      type: 'object',
      properties: {
        organization_id: { type: 'string', description: 'Organization ID. Defaults to server-side auth context when omitted.' },
        agent_id: { type: 'string', description: 'Agent requesting delegated facility access' },
        facility_id: { type: 'string', description: 'Facility ID to draw against' },
        mandate_id: { type: 'string', description: 'Mandate granting explicit facility draw authority' },
        amount: { type: ['string', 'number'], description: 'Requested spend amount' },
        currency: { type: 'string', description: 'Currency code. Default: USD' },
        merchant: {
          type: 'object',
          description: 'Merchant identity and category',
          properties: {
            name: { type: 'string', description: 'Merchant or vendor name' },
            category: { type: 'string', description: 'Merchant category' },
            merchant_id: { type: 'string', description: 'Known merchant identifier' },
          },
          required: ['name'],
        },
        purpose: { type: 'string', description: 'Business purpose for the request' },
        category: { type: 'string', description: 'Spend category' },
        idempotency_key: { type: 'string', description: 'Idempotency key for request creation' },
        metadata: { type: 'object', description: 'Additional request metadata' },
      },
      required: ['agent_id', 'facility_id', 'mandate_id', 'amount', 'merchant', 'purpose'],
    },
  },
  {
    name: 'sardis_facility_attach_evidence',
    description: 'Attach evidence references and hashes to a Facility Gate request before or during authorization.',
    inputSchema: {
      type: 'object',
      properties: {
        request_id: { type: 'string', description: 'Facility request ID' },
        evidence: { type: 'array', items: { type: 'object' }, description: 'Evidence references and hashes' },
        idempotency_key: { type: 'string', description: 'Idempotency key for evidence attachment' },
      },
      required: ['request_id', 'evidence'],
    },
  },
  {
    name: 'sardis_facility_authorize',
    description: 'Evaluate mandate, policy, risk, evidence, and revocation state for a Facility Gate request.',
    inputSchema: {
      type: 'object',
      properties: {
        request_id: { type: 'string', description: 'Facility request ID' },
      },
      required: ['request_id'],
    },
  },
  {
    name: 'sardis_facility_execute',
    description: 'Execute an already approved Facility Gate authorization through the configured adapter.',
    inputSchema: {
      type: 'object',
      properties: {
        request_id: { type: 'string', description: 'Facility request ID' },
      },
      required: ['request_id'],
    },
  },
  {
    name: 'sardis_facility_audit',
    description: 'Fetch audit reconstruction for a Facility Gate request, including decision basis and liability chain.',
    inputSchema: {
      type: 'object',
      properties: {
        request_id: { type: 'string', description: 'Facility request ID' },
      },
      required: ['request_id'],
    },
  },
  {
    name: 'sardis_facility_export_audit',
    description: 'Export the immutable request-level Facility Gate audit packet.',
    inputSchema: {
      type: 'object',
      properties: {
        request_id: { type: 'string', description: 'Facility request ID' },
      },
      required: ['request_id'],
    },
  },
  {
    name: 'sardis_facility_list_requests',
    description: 'List Facility Gate requests visible to the configured Sardis identity.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Maximum number of requests to return. Default: 50, max: 100' },
      },
      required: [],
    },
  },
];

export const facilityGateToolHandlers: Record<string, ToolHandler> = {
  sardis_facility_request: async (args: unknown): Promise<ToolResult> => {
    const parsed = FacilityRequestSchema.safeParse(args);
    if (!parsed.success) return validationError(parsed.error);

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      const requestId = simulatedId('fg_req_sim');
      return jsonResult({
        _simulated: true,
        _warning: 'This is simulated data. Configure SARDIS_API_KEY for real Facility Gate requests.',
        request_id: requestId,
        state: 'created',
        verdict: 'pending_authorization',
        agent_id: parsed.data.agent_id,
        facility_id: parsed.data.facility_id,
        mandate_id: parsed.data.mandate_id,
        amount: String(parsed.data.amount),
        currency: parsed.data.currency,
        merchant: parsed.data.merchant,
        purpose: parsed.data.purpose,
        next_steps: [
          'Attach evidence with sardis_facility_attach_evidence if required.',
          'Authorize with sardis_facility_authorize.',
          'Execute only after the decision is approved.',
        ],
      });
    }

    try {
      const result = await apiRequest<Record<string, unknown>>('POST', '/api/v2/facility-requests', parsed.data);
      return jsonResult(result);
    } catch (error) {
      return errorResult('Failed to create Facility Gate request', error);
    }
  },

  sardis_facility_attach_evidence: async (args: unknown): Promise<ToolResult> => {
    const parsed = FacilityEvidenceSchema.safeParse(args);
    if (!parsed.success) return validationError(parsed.error);

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return jsonResult({
        _simulated: true,
        request_id: parsed.data.request_id,
        evidence_count: parsed.data.evidence.length,
        state: 'evidence_attached',
      });
    }

    try {
      const { request_id, ...body } = parsed.data;
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/facility-requests/${request_id}/evidence`,
        body,
      );
      return jsonResult(result);
    } catch (error) {
      return errorResult('Failed to attach Facility Gate evidence', error);
    }
  },

  sardis_facility_authorize: async (args: unknown): Promise<ToolResult> => {
    const parsed = FacilityRequestIdSchema.safeParse(args);
    if (!parsed.success) return validationError(parsed.error);

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return jsonResult({
        _simulated: true,
        request_id: parsed.data.request_id,
        decision_id: simulatedId('fg_decision_sim'),
        verdict: 'approved',
        reason_codes: ['simulated_low_risk_facility_request'],
        adapter_execution_allowed: true,
      });
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/facility-requests/${parsed.data.request_id}/authorize`,
      );
      return jsonResult(result);
    } catch (error) {
      return errorResult('Failed to authorize Facility Gate request', error);
    }
  },

  sardis_facility_execute: async (args: unknown): Promise<ToolResult> => {
    const parsed = FacilityRequestIdSchema.safeParse(args);
    if (!parsed.success) return validationError(parsed.error);

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return jsonResult({
        _simulated: true,
        request_id: parsed.data.request_id,
        execution_id: simulatedId('fg_exec_sim'),
        adapter: 'simulated_virtual_card',
        status: 'executed',
        credential: {
          type: 'simulated_virtual_card',
          last4: '4242',
          merchant_bound: true,
        },
      });
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/facility-requests/${parsed.data.request_id}/execute`,
      );
      return jsonResult(result);
    } catch (error) {
      return errorResult('Failed to execute Facility Gate authorization', error);
    }
  },

  sardis_facility_audit: async (args: unknown): Promise<ToolResult> => {
    const parsed = FacilityRequestIdSchema.safeParse(args);
    if (!parsed.success) return validationError(parsed.error);

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return jsonResult({
        _simulated: true,
        request_id: parsed.data.request_id,
        timeline: [
          'facility.request.created',
          'facility.authorization.approved',
          'facility.execution.simulated',
        ],
        liability_assignment: {
          obligor: 'simulated_sponsor',
          loss_owner: 'simulated_sponsor',
        },
      });
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'GET',
        `/api/v2/facility-requests/${parsed.data.request_id}/audit`,
      );
      return jsonResult(result);
    } catch (error) {
      return errorResult('Failed to fetch Facility Gate audit', error);
    }
  },

  sardis_facility_export_audit: async (args: unknown): Promise<ToolResult> => {
    const parsed = FacilityRequestIdSchema.safeParse(args);
    if (!parsed.success) return validationError(parsed.error);

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return jsonResult({
        _simulated: true,
        request_id: parsed.data.request_id,
        decision_packet: {
          schema_version: 'facility.decision_packet.v1',
          decision_packet_hash: 'simulated',
          mandate_version_id: 'simulated',
          facility_version_id: 'simulated',
          policy_version_id: 'simulated',
          risk_model_version: 'facility-risk-rules-v0',
        },
      });
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'GET',
        `/api/v2/facility-requests/${parsed.data.request_id}/audit/export`,
      );
      return jsonResult(result);
    } catch (error) {
      return errorResult('Failed to export Facility Gate audit', error);
    }
  },

  sardis_facility_list_requests: async (args: unknown): Promise<ToolResult> => {
    const parsed = FacilityListSchema.safeParse(args);
    if (!parsed.success) return validationError(parsed.error);

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return jsonResult({
        _simulated: true,
        requests: [
          {
            request_id: 'fg_req_sim_example',
            state: 'approved',
            amount: '2400.00',
            currency: 'USD',
            merchant: { name: 'Example Cloud', category: 'cloud' },
          },
        ],
      });
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'GET',
        `/api/v2/facility-requests?limit=${parsed.data.limit}`,
      );
      return jsonResult(result);
    } catch (error) {
      return errorResult('Failed to list Facility Gate requests', error);
    }
  },
};
