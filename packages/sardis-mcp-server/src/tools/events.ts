/**
 * Event and webhook management tools for MCP server
 */

import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type {
  ToolDefinition,
  ToolHandler,
  ToolResult,
} from './types.js';
import {
  SubscribeEventsSchema,
  ListEventTypesSchema,
  GetEventHistorySchema,
  ConfigureWebhookSchema,
} from './types.js';

// Tool definitions
export const eventToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_subscribe_events',
    description: 'Subscribe to event patterns (e.g., "policy.*", "spend.*", "card.*"). Use wildcards to subscribe to multiple event types at once.',
    inputSchema: {
      type: 'object',
      properties: {
        event_pattern: {
          type: 'string',
          description: 'Event pattern to subscribe to. Supports wildcards: "policy.*" for all policy events, "*.created" for all creation events, or "*" for all events',
        },
        webhook_url: {
          type: 'string',
          description: 'Optional webhook URL to forward events to',
        },
      },
      required: ['event_pattern'],
    },
  },
  {
    name: 'sardis_list_event_types',
    description: 'List all available event types organized by category (policy, spend, approval, card, compliance, group, payment, hold, wallet, agent, mandate, risk).',
    inputSchema: {
      type: 'object',
      properties: {
        category: {
          type: 'string',
          description: 'Optional category filter: policy, spend, approval, card, compliance, group, payment, hold, wallet, agent, mandate, risk',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_event_history',
    description: 'Get recent events for an agent or wallet. Useful for debugging and monitoring.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_id: {
          type: 'string',
          description: 'Agent ID to filter events by',
        },
        wallet_id: {
          type: 'string',
          description: 'Wallet ID to filter events by',
        },
        event_type: {
          type: 'string',
          description: 'Optional event type filter (e.g., "policy.violated")',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of events to return (default: 50)',
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
    name: 'sardis_configure_webhook',
    description: 'Set up a webhook URL for event forwarding. Events matching the subscription will be POSTed to this URL with HMAC signature verification.',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'Webhook URL to POST events to',
        },
        events: {
          type: 'array',
          items: { type: 'string' },
          description: 'List of event types to subscribe to. Empty array = all events',
        },
        is_active: {
          type: 'boolean',
          description: 'Enable or disable the webhook (default: true)',
        },
      },
      required: ['url'],
    },
  },
];

// Event type categories
const EVENT_CATEGORIES = {
  policy: [
    'policy.created',
    'policy.updated',
    'policy.violated',
    'policy.check.passed',
  ],
  spend: [
    'spend.threshold.warning',
    'spend.threshold.reached',
    'spend.daily.summary',
  ],
  approval: [
    'approval.requested',
    'approval.granted',
    'approval.denied',
    'approval.expired',
  ],
  card: [
    'card.created',
    'card.activated',
    'card.transaction',
    'card.declined',
    'card.frozen',
  ],
  compliance: [
    'compliance.check.passed',
    'compliance.check.failed',
    'compliance.alert',
  ],
  group: [
    'group.budget.warning',
    'group.budget.exceeded',
  ],
  payment: [
    'payment.initiated',
    'payment.completed',
    'payment.failed',
    'payment.refunded',
  ],
  hold: [
    'hold.created',
    'hold.captured',
    'hold.voided',
    'hold.expired',
  ],
  wallet: [
    'wallet.created',
    'wallet.funded',
    'wallet.updated',
  ],
  agent: [
    'agent.created',
    'agent.updated',
  ],
  mandate: [
    'mandate.verified',
    'mandate.executed',
    'mandate.rejected',
  ],
  risk: [
    'risk.alert',
    'limit.exceeded',
  ],
} as const;

// Tool handlers
export const eventToolHandlers: Record<string, ToolHandler> = {
  sardis_subscribe_events: async (args: unknown): Promise<ToolResult> => {
    const parsed = SubscribeEventsSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated mode - show what would be subscribed
      const matchingEvents: string[] = [];
      const pattern = parsed.data.event_pattern;

      // Find matching events
      for (const [category, events] of Object.entries(EVENT_CATEGORIES)) {
        for (const event of events) {
          if (matchesPattern(event, pattern)) {
            matchingEvents.push(event);
          }
        }
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            subscription_id: `sub_${Date.now().toString(36)}`,
            event_pattern: pattern,
            webhook_url: parsed.data.webhook_url,
            matching_events: matchingEvents,
            status: 'active',
            created_at: new Date().toISOString(),
            message: `Would subscribe to ${matchingEvents.length} event types matching "${pattern}"`,
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<any>('POST', '/api/v2/events/subscriptions', {
        event_pattern: parsed.data.event_pattern,
        webhook_url: parsed.data.webhook_url,
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to subscribe to events: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_list_event_types: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListEventTypesSchema.safeParse(args);
    const category = parsed.success ? parsed.data.category : undefined;

    // Filter by category if specified
    const categories = category && category in EVENT_CATEGORIES
      ? { [category]: EVENT_CATEGORIES[category as keyof typeof EVENT_CATEGORIES] }
      : EVENT_CATEGORIES;

    const summary = Object.entries(categories).map(([cat, events]) => ({
      category: cat,
      count: events.length,
      events: events,
    }));

    const totalEvents = summary.reduce((sum, cat) => sum + cat.count, 0);

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          total_event_types: totalEvents,
          categories: summary,
          usage_examples: [
            'Subscribe to all policy events: sardis_subscribe_events with event_pattern="policy.*"',
            'Subscribe to all creation events: sardis_subscribe_events with event_pattern="*.created"',
            'Subscribe to specific event: sardis_subscribe_events with event_pattern="policy.violated"',
            'Subscribe to all events: sardis_subscribe_events with event_pattern="*"',
          ],
        }, null, 2),
      }],
    };
  },

  sardis_get_event_history: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetEventHistorySchema.safeParse(args);
    const limit = parsed.success && parsed.data.limit ? parsed.data.limit : 50;
    const offset = parsed.success && parsed.data.offset ? parsed.data.offset : 0;

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated mode - generate sample events
      const sampleEvents = [
        {
          event_id: `evt_${Date.now().toString(36)}`,
          event_type: 'policy.check.passed',
          data: {
            policy_id: 'pol_sim123',
            agent_id: parsed.success && parsed.data.agent_id || 'agent_sim',
            vendor: 'openai',
            amount: '50.00',
          },
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          event_id: `evt_${(Date.now() - 1).toString(36)}`,
          event_type: 'payment.completed',
          data: {
            transaction_id: 'tx_sim456',
            agent_id: parsed.success && parsed.data.agent_id || 'agent_sim',
            amount: '50.00',
            vendor: 'openai',
          },
          created_at: new Date(Date.now() - 7200000).toISOString(),
        },
        {
          event_id: `evt_${(Date.now() - 2).toString(36)}`,
          event_type: 'spend.threshold.warning',
          data: {
            agent_id: parsed.success && parsed.data.agent_id || 'agent_sim',
            amount: '800.00',
            limit: '1000.00',
            period: 'daily',
            percentage: 80.0,
          },
          created_at: new Date(Date.now() - 10800000).toISOString(),
        },
      ];

      // Filter by event_type if specified
      const filteredEvents = parsed.success && parsed.data.event_type
        ? sampleEvents.filter(e => e.event_type === parsed.data.event_type)
        : sampleEvents;

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            events: filteredEvents.slice(offset, offset + limit),
            total: filteredEvents.length,
            limit,
            offset,
            filters: {
              agent_id: parsed.success ? parsed.data.agent_id : undefined,
              wallet_id: parsed.success ? parsed.data.wallet_id : undefined,
              event_type: parsed.success ? parsed.data.event_type : undefined,
            },
          }, null, 2),
        }],
      };
    }

    try {
      // Build query params
      const params = new URLSearchParams();
      if (parsed.success) {
        if (parsed.data.agent_id) params.set('agent_id', parsed.data.agent_id);
        if (parsed.data.wallet_id) params.set('wallet_id', parsed.data.wallet_id);
        if (parsed.data.event_type) params.set('event_type', parsed.data.event_type);
      }
      params.set('limit', limit.toString());
      params.set('offset', offset.toString());

      const result = await apiRequest<any>('GET', `/api/v2/events?${params.toString()}`);
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get event history: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_configure_webhook: async (args: unknown): Promise<ToolResult> => {
    const parsed = ConfigureWebhookSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated mode
      const subscriptionId = `whsub_${Date.now().toString(36)}`;
      const secret = `whsec_${Math.random().toString(36).substring(2)}`;

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            subscription_id: subscriptionId,
            url: parsed.data.url,
            events: parsed.data.events || [],
            secret,
            is_active: parsed.data.is_active ?? true,
            created_at: new Date().toISOString(),
            message: 'Webhook configured successfully',
            signature_verification: {
              header: 'X-Sardis-Signature',
              format: 't=<timestamp>,v1=<hmac_sha256>',
              algorithm: 'HMAC-SHA256',
              tolerance: '300 seconds',
            },
            delivery_info: {
              max_retries: 3,
              retry_delays: [1, 5, 30],
              timeout: 10,
            },
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<any>('POST', '/api/v2/webhooks', {
        url: parsed.data.url,
        events: parsed.data.events || [],
        is_active: parsed.data.is_active ?? true,
      });
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to configure webhook: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};

/**
 * Check if event type matches pattern (supports wildcards)
 */
function matchesPattern(eventType: string, pattern: string): boolean {
  if (pattern === '*') return true;
  if (pattern === eventType) return true;

  // Convert glob pattern to regex
  const regexPattern = pattern
    .replace(/\./g, '\\.')
    .replace(/\*/g, '.*');

  return new RegExp(`^${regexPattern}$`).test(eventType);
}
