/**
 * Agent group management tools for MCP server
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type {
  ToolDefinition,
  ToolHandler,
  ToolResult,
} from './types.js';

// Zod schemas
const CreateGroupSchema = z.object({
  name: z.string().describe('Group display name'),
  budget_daily: z.string().optional().describe('Daily budget limit (e.g. "5000.00")'),
  budget_monthly: z.string().optional().describe('Monthly budget limit'),
});

const GetGroupSchema = z.object({
  group_id: z.string().describe('Group ID to retrieve'),
});

const ListGroupsSchema = z.object({
  limit: z.number().optional().default(50),
  offset: z.number().optional().default(0),
});

const AddAgentToGroupSchema = z.object({
  group_id: z.string().describe('Group ID'),
  agent_id: z.string().describe('Agent ID to add'),
});

const RemoveAgentFromGroupSchema = z.object({
  group_id: z.string().describe('Group ID'),
  agent_id: z.string().describe('Agent ID to remove'),
});

const GetGroupSpendingSchema = z.object({
  group_id: z.string().describe('Group ID'),
});

// Tool definitions
export const groupToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_group',
    description: 'Create a new agent group with shared budget and policies. Groups enable multi-agent governance.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Display name for the group' },
        budget_daily: { type: 'string', description: 'Daily budget limit (e.g. "5000.00")' },
        budget_monthly: { type: 'string', description: 'Monthly budget limit' },
      },
      required: ['name'],
    },
  },
  {
    name: 'sardis_get_group',
    description: 'Get details of a specific agent group including members and budget.',
    inputSchema: {
      type: 'object',
      properties: {
        group_id: { type: 'string', description: 'Group ID to retrieve' },
      },
      required: ['group_id'],
    },
  },
  {
    name: 'sardis_list_groups',
    description: 'List all agent groups in the organization.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Maximum number of groups to return' },
        offset: { type: 'number', description: 'Pagination offset' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_add_agent_to_group',
    description: 'Add an agent to a group. The agent will be subject to the group\'s shared budget.',
    inputSchema: {
      type: 'object',
      properties: {
        group_id: { type: 'string', description: 'Group ID' },
        agent_id: { type: 'string', description: 'Agent ID to add to the group' },
      },
      required: ['group_id', 'agent_id'],
    },
  },
  {
    name: 'sardis_remove_agent_from_group',
    description: 'Remove an agent from a group.',
    inputSchema: {
      type: 'object',
      properties: {
        group_id: { type: 'string', description: 'Group ID' },
        agent_id: { type: 'string', description: 'Agent ID to remove' },
      },
      required: ['group_id', 'agent_id'],
    },
  },
  {
    name: 'sardis_get_group_spending',
    description: 'Get current spending summary for an agent group.',
    inputSchema: {
      type: 'object',
      properties: {
        group_id: { type: 'string', description: 'Group ID' },
      },
      required: ['group_id'],
    },
  },
];

// Tool handlers
export const groupToolHandlers: Record<string, ToolHandler> = {
  sardis_create_group: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateGroupSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      const groupId = `grp_${Date.now().toString(36)}`;
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            group_id: groupId,
            name: parsed.data.name,
            budget: {
              daily: parsed.data.budget_daily || '5000.00',
              monthly: parsed.data.budget_monthly || '50000.00',
            },
            agent_ids: [],
            created_at: new Date().toISOString(),
            message: `Group "${parsed.data.name}" created successfully`,
          }, null, 2),
        }],
      };
    }

    try {
      const body: Record<string, unknown> = { name: parsed.data.name };
      if (parsed.data.budget_daily || parsed.data.budget_monthly) {
        body.budget = {
          daily: parsed.data.budget_daily,
          monthly: parsed.data.budget_monthly,
        };
      }
      const result = await apiRequest('POST', '/api/v2/groups', body);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return {
        content: [{ type: 'text', text: `Failed to create group: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        isError: true,
      };
    }
  },

  sardis_get_group: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetGroupSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            group_id: parsed.data.group_id,
            name: 'Simulated Group',
            budget: { per_transaction: '500.00', daily: '5000.00', monthly: '50000.00', total: '500000.00' },
            agent_ids: [],
            created_at: new Date().toISOString(),
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest('GET', `/api/v2/groups/${parsed.data.group_id}`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return {
        content: [{ type: 'text', text: `Failed to get group: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        isError: true,
      };
    }
  },

  sardis_list_groups: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListGroupsSchema.safeParse(args);
    const limit = parsed.success ? parsed.data.limit : 50;
    const offset = parsed.success ? parsed.data.offset : 0;

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify([], null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest('GET', `/api/v2/groups?limit=${limit}&offset=${offset}`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return {
        content: [{ type: 'text', text: `Failed to list groups: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        isError: true,
      };
    }
  },

  sardis_add_agent_to_group: async (args: unknown): Promise<ToolResult> => {
    const parsed = AddAgentToGroupSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            group_id: parsed.data.group_id,
            agent_ids: [parsed.data.agent_id],
            message: `Agent ${parsed.data.agent_id} added to group ${parsed.data.group_id}`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest('POST', `/api/v2/groups/${parsed.data.group_id}/agents`, {
        agent_id: parsed.data.agent_id,
      });
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return {
        content: [{ type: 'text', text: `Failed to add agent to group: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        isError: true,
      };
    }
  },

  sardis_remove_agent_from_group: async (args: unknown): Promise<ToolResult> => {
    const parsed = RemoveAgentFromGroupSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            group_id: parsed.data.group_id,
            agent_ids: [],
            message: `Agent ${parsed.data.agent_id} removed from group ${parsed.data.group_id}`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest('DELETE', `/api/v2/groups/${parsed.data.group_id}/agents/${parsed.data.agent_id}`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return {
        content: [{ type: 'text', text: `Failed to remove agent from group: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        isError: true,
      };
    }
  },

  sardis_get_group_spending: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetGroupSpendingSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            group_id: parsed.data.group_id,
            name: 'Simulated Group',
            budget: { per_transaction: '500.00', daily: '5000.00', monthly: '50000.00', total: '500000.00' },
            agent_count: 0,
            agent_ids: [],
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest('GET', `/api/v2/groups/${parsed.data.group_id}/spending`);
      return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
    } catch (error) {
      return {
        content: [{ type: 'text', text: `Failed to get group spending: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        isError: true,
      };
    }
  },
};
