/**
 * Trust tools for MCP server — FIDES identity and trust graph queries
 */

import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type {
  ToolDefinition,
  ToolHandler,
  ToolResult,
} from './types.js';
import { z } from 'zod';

// Schemas
const CheckAgentTrustSchema = z.object({
  agent_id: z.string().describe('Agent ID to check trust score for'),
});

const VerifyAgentIdentitySchema = z.object({
  agent_id: z.string().describe('Agent ID to verify'),
  target_did: z.string().optional().describe('Optional target DID to find trust path to'),
});

const ViewPolicyHistorySchema = z.object({
  agent_id: z.string().describe('Agent ID to view policy history for'),
  limit: z.number().min(1).max(100).optional().default(20).describe('Maximum entries to return'),
});

// Tool definitions
export const trustToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_check_agent_trust',
    description:
      'Query an agent\'s trust score including tier, spending limits, and signal breakdown. ' +
      'Returns the overall trust score (0.0-1.0), trust tier (UNTRUSTED/LOW/MEDIUM/HIGH/SOVEREIGN), ' +
      'and individual signal scores (KYA level, transaction history, compliance, reputation, behavioral, transitive trust).',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: { type: 'string', description: 'Agent ID to check trust score for' },
      },
      required: ['agent_id'],
    },
  },
  {
    name: 'sardis_verify_agent_identity',
    description:
      'Verify a counterparty agent\'s FIDES DID and trust level. ' +
      'Checks if the agent has a linked FIDES identity and optionally finds the trust path to a target DID. ' +
      'Use this before accepting payments from unknown agents.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: { type: 'string', description: 'Agent ID to verify' },
        target_did: { type: 'string', description: 'Optional target DID to find trust path to' },
      },
      required: ['agent_id'],
    },
  },
  {
    name: 'sardis_view_policy_history',
    description:
      'View AGIT-signed policy change history for an agent. ' +
      'Shows hash-chained policy commits with signatures, making policy changes auditable and tamper-evident.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: { type: 'string', description: 'Agent ID to view policy history for' },
        limit: { type: 'number', description: 'Maximum entries to return (default 20)' },
      },
      required: ['agent_id'],
    },
  },
];

// Tool handlers
async function handleCheckAgentTrust(args: unknown): Promise<ToolResult> {
  const parsed = CheckAgentTrustSchema.parse(args);
  const config = getConfig();

  try {
    const result = await apiRequest(
      `${config.apiBaseUrl}/api/v2/agents/${parsed.agent_id}/trust-score`,
      { method: 'GET' },
    );

    const data = result as Record<string, unknown>;
    const tier = (data.tier as string) || 'unknown';
    const overall = (data.overall as number) || 0;
    const maxPerTx = (data.max_per_tx as string) || '0';
    const maxPerDay = (data.max_per_day as string) || '0';

    const signals = (data.signals as Array<Record<string, unknown>>) || [];
    const signalLines = signals
      .map((s) => `  - ${s.name}: ${(s.score as number)?.toFixed(4)} (weight: ${s.weight})`)
      .join('\n');

    return {
      content: [
        {
          type: 'text',
          text: [
            `Trust Score for ${parsed.agent_id}:`,
            `  Overall: ${overall.toFixed(4)}`,
            `  Tier: ${tier.toUpperCase()}`,
            `  Max per transaction: $${maxPerTx}`,
            `  Max per day: $${maxPerDay}`,
            '',
            'Signal breakdown:',
            signalLines || '  No signals available',
          ].join('\n'),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Failed to get trust score for ${parsed.agent_id}: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
}

async function handleVerifyAgentIdentity(args: unknown): Promise<ToolResult> {
  const parsed = VerifyAgentIdentitySchema.parse(args);
  const config = getConfig();

  try {
    const identity = await apiRequest(
      `${config.apiBaseUrl}/api/v2/agents/${parsed.agent_id}/fides/identity`,
      { method: 'GET' },
    );

    const data = identity as Record<string, unknown>;
    const lines = [
      `FIDES Identity for ${parsed.agent_id}:`,
      `  FIDES DID: ${data.fides_did || 'Not linked'}`,
      `  Verified: ${data.verified_at ? 'Yes' : 'No'}`,
    ];

    if (parsed.target_did) {
      try {
        const pathResult = await apiRequest(
          `${config.apiBaseUrl}/api/v2/agents/${parsed.agent_id}/trust-path/${encodeURIComponent(parsed.target_did)}`,
          { method: 'GET' },
        );

        const pathData = pathResult as Record<string, unknown>;
        lines.push('');
        lines.push(`Trust path to ${parsed.target_did}:`);
        lines.push(`  Found: ${pathData.found ? 'Yes' : 'No'}`);
        if (pathData.found) {
          lines.push(`  Hops: ${pathData.hops}`);
          lines.push(`  Cumulative trust: ${(pathData.cumulative_trust as number)?.toFixed(4)}`);
        }
      } catch {
        lines.push(`  Trust path lookup failed for ${parsed.target_did}`);
      }
    }

    return {
      content: [{ type: 'text', text: lines.join('\n') }],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Failed to verify identity for ${parsed.agent_id}: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
}

async function handleViewPolicyHistory(args: unknown): Promise<ToolResult> {
  const parsed = ViewPolicyHistorySchema.parse(args);
  const config = getConfig();

  try {
    const result = await apiRequest(
      `${config.apiBaseUrl}/api/v2/agents/${parsed.agent_id}/policy-history?limit=${parsed.limit}`,
      { method: 'GET' },
    );

    const data = result as Record<string, unknown>;
    const commits = (data.commits as Array<Record<string, unknown>>) || [];

    if (commits.length === 0) {
      return {
        content: [
          { type: 'text', text: `No policy history found for ${parsed.agent_id}` },
        ],
      };
    }

    const lines = [`Policy history for ${parsed.agent_id} (${commits.length} commits):`];
    for (const commit of commits) {
      lines.push(`  ${commit.commit_hash} — ${commit.created_at || 'unknown date'}`);
      if (commit.signed) {
        lines.push(`    Signed by: ${commit.signer_did}`);
      }
    }

    return {
      content: [{ type: 'text', text: lines.join('\n') }],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Failed to get policy history for ${parsed.agent_id}: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
}

export const trustToolHandlers: Record<string, ToolHandler> = {
  sardis_check_agent_trust: handleCheckAgentTrust,
  sardis_verify_agent_identity: handleVerifyAgentIdentity,
  sardis_view_policy_history: handleViewPolicyHistory,
};
