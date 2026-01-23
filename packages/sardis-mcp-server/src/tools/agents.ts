/**
 * Agent management tools for MCP server
 */

import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type {
  ToolDefinition,
  ToolHandler,
  ToolResult,
  Agent,
} from './types.js';
import {
  CreateAgentSchema,
  GetAgentSchema,
  ListAgentsSchema,
  UpdateAgentSchema,
} from './types.js';

// Tool definitions
export const agentToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_create_agent',
    description: 'Create a new AI agent with Sardis. Agents can own wallets and execute payments.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Display name for the agent' },
        description: { type: 'string', description: 'Optional description of the agent' },
      },
      required: ['name'],
    },
  },
  {
    name: 'sardis_get_agent',
    description: 'Get details of a specific agent.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: { type: 'string', description: 'Agent ID to retrieve' },
      },
      required: ['agent_id'],
    },
  },
  {
    name: 'sardis_list_agents',
    description: 'List all agents in the organization.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Maximum number of agents to return' },
        offset: { type: 'number', description: 'Pagination offset' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_update_agent',
    description: 'Update an agent\'s configuration.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: { type: 'string', description: 'Agent ID to update' },
        name: { type: 'string', description: 'New display name' },
        is_active: { type: 'boolean', description: 'Enable or disable the agent' },
      },
      required: ['agent_id'],
    },
  },
];

// Tool handlers
export const agentToolHandlers: Record<string, ToolHandler> = {
  sardis_create_agent: async (args: unknown): Promise<ToolResult> => {
    const parsed = CreateAgentSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      const agentId = `agent_${Date.now().toString(36)}`;
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: agentId,
            name: parsed.data.name,
            description: parsed.data.description,
            is_active: true,
            created_at: new Date().toISOString(),
            message: `Agent "${parsed.data.name}" created successfully`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Agent>('POST', '/api/v2/agents', parsed.data);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to create agent: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_agent: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetAgentSchema.safeParse(args);
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
            id: parsed.data.agent_id,
            name: 'Simulated Agent',
            description: 'A simulated agent for testing',
            is_active: true,
            created_at: new Date().toISOString(),
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<Agent>('GET', `/api/v2/agents/${parsed.data.agent_id}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get agent: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_list_agents: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListAgentsSchema.safeParse(args);
    const limit = parsed.success ? parsed.data.limit : 100;
    const offset = parsed.success ? parsed.data.offset : 0;

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            agents: [{
              id: 'agent_simulated',
              name: 'Simulated Agent',
              is_active: true,
              created_at: new Date().toISOString(),
            }],
            total: 1,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<{ agents: Agent[] }>(
        'GET',
        `/api/v2/agents?limit=${limit}&offset=${offset}`
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list agents: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_update_agent: async (args: unknown): Promise<ToolResult> => {
    const parsed = UpdateAgentSchema.safeParse(args);
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
            id: parsed.data.agent_id,
            name: parsed.data.name || 'Updated Agent',
            is_active: parsed.data.is_active ?? true,
            updated_at: new Date().toISOString(),
            message: 'Agent updated successfully',
          }, null, 2),
        }],
      };
    }

    try {
      const { agent_id, ...updateData } = parsed.data;
      const result = await apiRequest<Agent>('PATCH', `/api/v2/agents/${agent_id}`, updateData);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to update agent: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
