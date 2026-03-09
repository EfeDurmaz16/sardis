/**
 * Sardis MCP Server - ERC-8183 Agentic Commerce Job Tools
 *
 * Three-party job primitive: Client creates, Provider delivers, Evaluator judges.
 * Tools:
 * - sardis_create_job: Create a new job as client
 * - sardis_fund_job: Fund a job
 * - sardis_submit_deliverable: Submit work as provider
 * - sardis_evaluate_job: Evaluate work as evaluator
 * - sardis_get_job: Get job details
 * - sardis_list_jobs: List jobs by role/state
 * - sardis_dispute_job: Raise dispute
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';

// Zod schemas
const CreateJobSchema = z.object({
  provider_agent_id: z.string().describe('Agent ID of the service provider'),
  evaluator_agent_id: z.string().describe('Agent ID of the independent evaluator'),
  amount: z.string().describe('Payment amount as a decimal string (e.g., "50.00")'),
  token: z.string().optional().default('USDC').describe('Payment token (default: USDC)'),
  chain: z.string().optional().default('base').describe('Blockchain network (default: base)'),
  deadline_hours: z.number().optional().default(72).describe('Hours until job expires (default: 72)'),
  description: z.string().optional().default('').describe('Job description'),
});

const FundJobSchema = z.object({
  job_id: z.string().describe('Job ID to fund'),
  tx_hash: z.string().optional().default('').describe('On-chain funding transaction hash'),
});

const SubmitDeliverableSchema = z.object({
  job_id: z.string().describe('Job ID to submit deliverable for'),
  deliverable_uri: z.string().describe('URI of the deliverable (IPFS, HTTPS, etc.)'),
  deliverable_hash: z.string().optional().default('').describe('SHA-256 hash of deliverable content'),
});

const EvaluateJobSchema = z.object({
  job_id: z.string().describe('Job ID to evaluate'),
  approved: z.boolean().describe('Whether to approve (true) or reject (false) the deliverable'),
  reason: z.string().optional().default('').describe('Evaluation reason or feedback'),
});

const GetJobSchema = z.object({
  job_id: z.string().describe('Job ID to retrieve'),
});

const ListJobsSchema = z.object({
  role: z.string().optional().describe('Filter by role: client, provider, evaluator'),
  state: z.string().optional().describe('Filter by state: open, funded, submitted, completed, rejected, expired, disputed'),
  limit: z.number().optional().default(20).describe('Maximum results to return'),
  offset: z.number().optional().default(0).describe('Pagination offset'),
});

const DisputeJobSchema = z.object({
  job_id: z.string().describe('Job ID to dispute'),
  reason: z.string().describe('Reason for raising the dispute'),
});

// Tool definitions
export const jobToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_job',
    description:
      'Create a new ERC-8183 agentic commerce job. You act as the client, specifying a provider ' +
      'agent to do the work and an independent evaluator agent to judge the result. Funds are ' +
      'escrowed until the evaluator approves the deliverable.',
    inputSchema: {
      type: 'object',
      properties: {
        provider_agent_id: {
          type: 'string',
          description: 'Agent ID of the service provider',
        },
        evaluator_agent_id: {
          type: 'string',
          description: 'Agent ID of the independent evaluator',
        },
        amount: {
          type: 'string',
          description: 'Payment amount as a decimal string (e.g., "50.00")',
        },
        token: {
          type: 'string',
          description: 'Payment token (default: USDC)',
        },
        chain: {
          type: 'string',
          description: 'Blockchain network (default: base)',
        },
        deadline_hours: {
          type: 'number',
          description: 'Hours until job expires (default: 72)',
        },
        description: {
          type: 'string',
          description: 'Job description',
        },
      },
      required: ['provider_agent_id', 'evaluator_agent_id', 'amount'],
    },
  },
  {
    name: 'sardis_fund_job',
    description:
      'Fund an ERC-8183 job. Transitions the job from "open" to "funded", escrowing the payment ' +
      'amount. Only the client agent who created the job can fund it.',
    inputSchema: {
      type: 'object',
      properties: {
        job_id: {
          type: 'string',
          description: 'Job ID to fund',
        },
        tx_hash: {
          type: 'string',
          description: 'On-chain funding transaction hash (optional)',
        },
      },
      required: ['job_id'],
    },
  },
  {
    name: 'sardis_submit_deliverable',
    description:
      'Submit a deliverable for an ERC-8183 job. Only the provider agent can submit. ' +
      'Transitions the job from "funded" to "submitted" for evaluator review.',
    inputSchema: {
      type: 'object',
      properties: {
        job_id: {
          type: 'string',
          description: 'Job ID to submit deliverable for',
        },
        deliverable_uri: {
          type: 'string',
          description: 'URI of the deliverable (IPFS hash, HTTPS URL, etc.)',
        },
        deliverable_hash: {
          type: 'string',
          description: 'SHA-256 hash of deliverable content for verification',
        },
      },
      required: ['job_id', 'deliverable_uri'],
    },
  },
  {
    name: 'sardis_evaluate_job',
    description:
      'Evaluate a submitted deliverable for an ERC-8183 job. Only the evaluator agent can ' +
      'evaluate. Approving releases payment to the provider; rejecting returns funds to the client.',
    inputSchema: {
      type: 'object',
      properties: {
        job_id: {
          type: 'string',
          description: 'Job ID to evaluate',
        },
        approved: {
          type: 'boolean',
          description: 'Whether to approve (true) or reject (false)',
        },
        reason: {
          type: 'string',
          description: 'Evaluation reason or feedback',
        },
      },
      required: ['job_id', 'approved'],
    },
  },
  {
    name: 'sardis_get_job',
    description:
      'Get details of an ERC-8183 job including its current state, participants, amounts, ' +
      'deliverable, and evaluation results.',
    inputSchema: {
      type: 'object',
      properties: {
        job_id: {
          type: 'string',
          description: 'Job ID to retrieve',
        },
      },
      required: ['job_id'],
    },
  },
  {
    name: 'sardis_list_jobs',
    description:
      'List ERC-8183 jobs. Filter by your role (client, provider, evaluator) and/or job state.',
    inputSchema: {
      type: 'object',
      properties: {
        role: {
          type: 'string',
          enum: ['client', 'provider', 'evaluator'],
          description: 'Filter by your role in the job',
        },
        state: {
          type: 'string',
          enum: ['open', 'funded', 'submitted', 'completed', 'rejected', 'expired', 'disputed'],
          description: 'Filter by job state',
        },
        limit: {
          type: 'number',
          description: 'Maximum results to return (default: 20)',
        },
        offset: {
          type: 'number',
          description: 'Pagination offset (default: 0)',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_dispute_job',
    description:
      'Raise a dispute on an ERC-8183 job. Only the client or provider can dispute. ' +
      'Transitions funded or submitted jobs to "disputed" state for resolution.',
    inputSchema: {
      type: 'object',
      properties: {
        job_id: {
          type: 'string',
          description: 'Job ID to dispute',
        },
        reason: {
          type: 'string',
          description: 'Reason for raising the dispute',
        },
      },
      required: ['job_id', 'reason'],
    },
  },
];

// Tool handlers
export const jobToolHandlers: Record<string, ToolHandler> = {
  sardis_create_job: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateJobSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { provider_agent_id, evaluator_agent_id, amount, token, chain, deadline_hours, description } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simId = `job_sim_${Date.now().toString(36)}`;
      const deadline = new Date(Date.now() + deadline_hours * 3600_000).toISOString();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                job_id: simId,
                state: 'open',
                created_at: new Date().toISOString(),
                deadline,
                message: `Job created: ${amount} ${token} for provider ${provider_agent_id}, evaluated by ${evaluator_agent_id}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<{ job_id: string; state: string; created_at: string; deadline: string }>(
        'POST',
        '/api/v2/erc8183/jobs',
        {
          provider_agent_id,
          evaluator_agent_id,
          amount,
          token,
          chain,
          deadline_hours,
          description,
        },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                ...result,
                message: `Job ${result.job_id} created (${amount} ${token}), deadline: ${result.deadline}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to create job' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_fund_job: async (args: unknown): Promise<ToolResult> => {
    const parsed = FundJobSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { job_id, tx_hash } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                job_id,
                state: 'funded',
                funded_at: new Date().toISOString(),
                message: `Job ${job_id} funded successfully`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/erc8183/jobs/${job_id}/fund`,
        { tx_hash },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Job ${job_id} funded` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to fund job' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_submit_deliverable: async (args: unknown): Promise<ToolResult> => {
    const parsed = SubmitDeliverableSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { job_id, deliverable_uri, deliverable_hash } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                job_id,
                state: 'submitted',
                deliverable_uri,
                submitted_at: new Date().toISOString(),
                message: `Deliverable submitted for job ${job_id}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/erc8183/jobs/${job_id}/submit`,
        { deliverable_uri, deliverable_hash },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Deliverable submitted for job ${job_id}` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to submit deliverable' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_evaluate_job: async (args: unknown): Promise<ToolResult> => {
    const parsed = EvaluateJobSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { job_id, approved, reason } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const result = approved ? 'approved' : 'rejected';
      const state = approved ? 'completed' : 'rejected';
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                job_id,
                state,
                evaluation_result: result,
                evaluated_at: new Date().toISOString(),
                message: `Job ${job_id} ${result}${reason ? `: ${reason}` : ''}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/erc8183/jobs/${job_id}/evaluate`,
        { approved, reason },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                ...result,
                message: `Job ${job_id} ${approved ? 'approved' : 'rejected'}${reason ? `: ${reason}` : ''}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to evaluate job' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_get_job: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetJobSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { job_id } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                id: job_id,
                client_agent_id: config.agentId || 'agent_sim_client',
                provider_agent_id: 'agent_sim_provider',
                evaluator_agent_id: 'agent_sim_evaluator',
                amount: '50.00',
                token: 'USDC',
                chain: config.chain,
                state: 'open',
                description: 'Simulated ERC-8183 job',
                created_at: new Date().toISOString(),
                deadline: new Date(Date.now() + 72 * 3600_000).toISOString(),
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'GET',
        `/api/v2/erc8183/jobs/${job_id}`,
      );

      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to get job' }, null, 2) },
        ],
        isError: true,
      };
    }
  },

  sardis_list_jobs: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListJobsSchema.safeParse(args);
    const { role, state, limit, offset } = parsed.success
      ? parsed.data
      : { role: undefined, state: undefined, limit: 20, offset: 0 };

    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simTime = new Date().toISOString();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                jobs: [
                  {
                    id: `job_sim_${Date.now().toString(36)}`,
                    client_agent_id: config.agentId || 'agent_sim_client',
                    provider_agent_id: 'agent_sim_provider',
                    evaluator_agent_id: 'agent_sim_evaluator',
                    amount: '50.00',
                    token: 'USDC',
                    chain: config.chain,
                    state: state || 'open',
                    description: 'Simulated job',
                    created_at: simTime,
                    deadline: new Date(Date.now() + 72 * 3600_000).toISOString(),
                  },
                ],
                total: 1,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });
      if (role) params.append('role', role);
      if (state) params.append('state', state);

      const result = await apiRequest<{ jobs: Record<string, unknown>[]; total: number }>(
        'GET',
        `/api/v2/erc8183/jobs?${params}`,
      );

      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: `Failed to list jobs: ${error instanceof Error ? error.message : 'Unknown error'}` },
        ],
        isError: true,
      };
    }
  },

  sardis_dispute_job: async (args: unknown): Promise<ToolResult> => {
    const parsed = DisputeJobSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const { job_id, reason } = parsed.data;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: true,
                job_id,
                state: 'disputed',
                message: `Dispute raised on job ${job_id}: ${reason}`,
              },
              null,
              2,
            ),
          },
        ],
      };
    }

    try {
      const result = await apiRequest<Record<string, unknown>>(
        'POST',
        `/api/v2/erc8183/jobs/${job_id}/dispute`,
        { reason },
      );

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              { success: true, ...result, message: `Dispute raised on job ${job_id}` },
              null,
              2,
            ),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          { type: 'text', text: JSON.stringify({ success: false, error: error instanceof Error ? error.message : 'Failed to dispute job' }, null, 2) },
        ],
        isError: true,
      };
    }
  },
};
