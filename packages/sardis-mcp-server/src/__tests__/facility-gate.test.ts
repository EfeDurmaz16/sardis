/**
 * Facility Gate MCP tools test suite.
 */

import { describe, expect, it, vi } from 'vitest';
import { facilityGateToolDefinitions, facilityGateToolHandlers } from '../tools/facility-gate.js';

vi.mock('../config.js', () => ({
  getConfig: vi.fn(() => ({
    walletId: 'wallet_test_123',
    agentId: 'agent_test_123',
    apiKey: '',
    apiUrl: 'https://api.sardis.sh',
    chain: 'base_sepolia',
    mode: 'simulated',
  })),
}));

function parseResult(result: Awaited<ReturnType<(typeof facilityGateToolHandlers)[string]>>) {
  return JSON.parse(result.content[0].text);
}

describe('Facility Gate tools', () => {
  it('defines the agent-facing facility gate tools', () => {
    const names = facilityGateToolDefinitions.map((tool) => tool.name);

    expect(names).toContain('sardis_facility_request');
    expect(names).toContain('sardis_facility_attach_evidence');
    expect(names).toContain('sardis_facility_authorize');
    expect(names).toContain('sardis_facility_execute');
    expect(names).toContain('sardis_facility_audit');
    expect(names).toContain('sardis_facility_export_audit');
    expect(names).toContain('sardis_facility_list_requests');
  });

  it('creates a simulated facility request', async () => {
    const result = await facilityGateToolHandlers.sardis_facility_request({
      agent_id: 'agent_123',
      facility_id: 'fac_123',
      mandate_id: 'mandate_123',
      amount: '2400.00',
      currency: 'USD',
      merchant: { name: 'Example Cloud', category: 'cloud' },
      purpose: 'cloud infrastructure expansion',
    });

    expect(result.isError).toBeFalsy();
    const parsed = parseResult(result);
    expect(parsed._simulated).toBe(true);
    expect(parsed.request_id).toMatch(/^fg_req_sim_/);
    expect(parsed.verdict).toBe('pending_authorization');
  });

  it('attaches evidence and authorizes a simulated request', async () => {
    const evidenceResult = await facilityGateToolHandlers.sardis_facility_attach_evidence({
      request_id: 'fg_req_123',
      evidence: [{ evidence_id: 'ev_123', evidence_type: 'task_log', hash: 'sha256:abc' }],
      idempotency_key: 'idem_evidence_123',
    });
    const authorizationResult = await facilityGateToolHandlers.sardis_facility_authorize({
      request_id: 'fg_req_123',
    });

    expect(evidenceResult.isError).toBeFalsy();
    expect(authorizationResult.isError).toBeFalsy();
    expect(parseResult(evidenceResult).evidence_count).toBe(1);
    expect(parseResult(authorizationResult).verdict).toBe('approved');
  });

  it('executes and exports audit for a simulated approved request', async () => {
    const executeResult = await facilityGateToolHandlers.sardis_facility_execute({
      request_id: 'fg_req_123',
    });
    const auditResult = await facilityGateToolHandlers.sardis_facility_export_audit({
      request_id: 'fg_req_123',
    });

    expect(executeResult.isError).toBeFalsy();
    expect(auditResult.isError).toBeFalsy();
    expect(parseResult(executeResult).adapter).toBe('simulated_virtual_card');
    expect(parseResult(auditResult).decision_packet.schema_version).toBe('facility.decision_packet.v1');
  });

  it('rejects invalid facility requests', async () => {
    const result = await facilityGateToolHandlers.sardis_facility_request({
      agent_id: 'agent_123',
    });

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain('Invalid request');
  });

  it('lists simulated requests', async () => {
    const result = await facilityGateToolHandlers.sardis_facility_list_requests({ limit: 10 });

    expect(result.isError).toBeFalsy();
    expect(parseResult(result).requests[0].request_id).toBe('fg_req_sim_example');
  });
});
