import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { DiscoverServicesSchema, ProvisionServiceSchema, ListProvisionedSchema } from './types.js';

export const projectToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_discover_services',
    description:
      'Discover available services that can be provisioned through Sardis Projects. ' +
      'Returns providers with tiers and pricing. Use before provisioning to see options.',
    inputSchema: {
      type: 'object',
      properties: {
        category: {
          type: 'string',
          description: 'Filter by category (e.g., "database", "hosting", "auth")',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_provision_service',
    description:
      'Provision a service (e.g., database, hosting) for your project. ' +
      'Creates the resource, handles escrow for paid tiers, and returns credentials. ' +
      'Use sardis_discover_services first to see available options.',
    inputSchema: {
      type: 'object',
      properties: {
        service: {
          type: 'string',
          description: 'Service ID from discovery (e.g., "supabase/postgres")',
        },
        tier: {
          type: 'string',
          description: 'Tier ID (e.g., "free", "pro")',
        },
        project_name: {
          type: 'string',
          description: 'Name for this project',
        },
        region: {
          type: 'string',
          description: 'Preferred region (e.g., "us-east-1")',
        },
      },
      required: ['service', 'tier', 'project_name'],
    },
  },
  {
    name: 'sardis_list_provisioned',
    description:
      'List all services currently provisioned through Sardis Projects. ' +
      'Shows status, tier, and provider for each resource.',
    inputSchema: {
      type: 'object',
      properties: {
        project_name: {
          type: 'string',
          description: 'Filter by project name',
        },
      },
      required: [],
    },
  },
];

export const projectToolHandlers: Record<string, ToolHandler> = {
  sardis_discover_services: async (args: unknown): Promise<ToolResult> => {
    const parsed = DiscoverServicesSchema.safeParse(args);
    const category = parsed.success ? parsed.data.category : undefined;

    try {
      const params = category ? `?category=${encodeURIComponent(category)}` : '';
      const services = await apiRequest<unknown[]>('GET', `/api/v2/projects/discover${params}`);

      if (!services || services.length === 0) {
        return {
          content: [{
            type: 'text',
            text: 'No services found. Available categories: database, hosting, auth, analytics.',
          }],
        };
      }

      return {
        content: [{ type: 'text', text: JSON.stringify(services, null, 2) }],
      };
    } catch (error) {
      const fallbackCatalog = [
        {
          manifest_id: 'mf_supabase_001',
          merchant_id: 'supabase.com',
          offerings: [
            {
              offering_id: 'supabase/postgres',
              name: 'Managed PostgreSQL',
              tiers: [
                { tier_id: 'free', name: 'Free', price: '0', currency: 'USD' },
                { tier_id: 'pro', name: 'Pro', price: '25', currency: 'USD', interval: 'P1M' },
              ],
            },
          ],
        },
      ];

      return {
        content: [{
          type: 'text',
          text: '(Showing cached catalog — API unreachable)\n\n' + JSON.stringify(fallbackCatalog, null, 2),
        }],
      };
    }
  },

  sardis_provision_service: async (args: unknown): Promise<ToolResult> => {
    const parsed = ProvisionServiceSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{
          type: 'text',
          text: `Invalid request: ${parsed.error.message}. Required: service, tier, project_name.`,
        }],
        isError: true,
      };
    }

    const { service, tier, project_name, region } = parsed.data;

    try {
      const result = await apiRequest<{
        success: boolean;
        resource_id: string | null;
        status: string;
        credentials: Record<string, string> | null;
        hold_id: string | null;
        error: string | null;
      }>('POST', '/api/v2/projects/provision', {
        service,
        tier,
        project_name,
        region,
      });

      if (!result.success) {
        return {
          content: [{
            type: 'text',
            text: JSON.stringify({ success: false, error: result.error || 'Provisioning failed', service, tier }, null, 2),
          }],
          isError: true,
        };
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            service,
            tier,
            project_name,
            resource_id: result.resource_id,
            status: result.status,
            credentials: result.credentials,
            hold_id: result.hold_id,
            message: `✓ ${service} provisioned on ${tier} tier. Credentials ready.`,
          }, null, 2),
        }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Provisioning failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_list_provisioned: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListProvisionedSchema.safeParse(args);
    const projectName = parsed.success ? parsed.data.project_name : undefined;

    try {
      const params = projectName ? `?project_name=${encodeURIComponent(projectName)}` : '';
      const services = await apiRequest<unknown[]>('GET', `/api/v2/projects/services${params}`);

      if (!services || services.length === 0) {
        return {
          content: [{
            type: 'text',
            text: 'No provisioned services. Use sardis_provision_service to provision one.',
          }],
        };
      }

      return {
        content: [{ type: 'text', text: JSON.stringify(services, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to list services: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
