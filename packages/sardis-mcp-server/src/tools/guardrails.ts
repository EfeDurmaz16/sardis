/**
 * Guardrails tools for MCP server
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
const CheckCircuitBreakerSchema = z.object({
  wallet_id: z.string().optional(),
});

const ActivateKillSwitchSchema = z.object({
  wallet_id: z.string().optional(),
  reason: z.string(),
});

const DeactivateKillSwitchSchema = z.object({
  wallet_id: z.string().optional(),
});

const CheckRateLimitsSchema = z.object({
  wallet_id: z.string().optional(),
});

const GetBehavioralAlertsSchema = z.object({
  wallet_id: z.string().optional(),
  severity: z.enum(['low', 'medium', 'high', 'critical']).optional(),
  limit: z.number().min(1).max(100).optional(),
  since: z.string().optional(),
});

// Response types
interface CircuitBreakerStatus {
  active: boolean;
  reason: string | null;
  triggered_at: string | null;
  auto_recovery: boolean;
}

interface KillSwitchStatus {
  active: boolean;
  activated_by: string | null;
  activated_at: string | null;
  requires_manual_reset: boolean;
}

interface RateLimit {
  limit: number;
  current: number;
  percentage_used: number;
  breached: boolean;
}

interface GuardrailsStatus {
  wallet_id: string;
  circuit_breaker: CircuitBreakerStatus;
  kill_switch: KillSwitchStatus;
  rate_limits: {
    tx_per_minute: RateLimit;
    tx_per_hour: RateLimit;
    spend_per_hour_usd: RateLimit;
  };
  status: 'operational' | 'halted';
  last_checked: string;
}

interface BehavioralAlert {
  alert_id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  type: string;
  message: string;
  details: Record<string, unknown>;
  timestamp: string;
  auto_blocked: boolean;
  requires_review: boolean;
}

interface BehavioralAlertsResponse {
  wallet_id: string;
  alerts: BehavioralAlert[];
  total: number;
  has_critical: boolean;
}

// Tool definitions
export const guardrailsToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_check_circuit_breaker',
    description: 'Check circuit breaker and kill switch status for a wallet. Returns operational status and any active safety controls.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: {
          type: 'string',
          description: 'Wallet ID to check. Uses default wallet if not specified.',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_activate_kill_switch',
    description: 'EMERGENCY: Activate kill switch to halt ALL transactions for a wallet. Use only in security emergencies.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: {
          type: 'string',
          description: 'Wallet ID to halt. Uses default wallet if not specified.',
        },
        reason: {
          type: 'string',
          description: 'Reason for activating kill switch (required for audit trail)',
        },
      },
      required: ['reason'],
    },
  },
  {
    name: 'sardis_deactivate_kill_switch',
    description: 'Deactivate kill switch to resume normal wallet operations. Use after security issue is resolved.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: {
          type: 'string',
          description: 'Wallet ID to resume. Uses default wallet if not specified.',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_check_rate_limits',
    description: 'Check transaction rate limits and spending velocity. Monitor for approaching thresholds.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: {
          type: 'string',
          description: 'Wallet ID to check. Uses default wallet if not specified.',
        },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_behavioral_alerts',
    description: 'Get behavioral anomaly alerts for a wallet. Identifies unusual spending patterns and security threats.',
    inputSchema: {
      type: 'object',
      properties: {
        wallet_id: {
          type: 'string',
          description: 'Wallet ID to check. Uses default wallet if not specified.',
        },
        severity: {
          type: 'string',
          enum: ['low', 'medium', 'high', 'critical'],
          description: 'Filter by alert severity',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of alerts to return (1-100)',
        },
        since: {
          type: 'string',
          description: 'ISO 8601 timestamp - only return alerts after this time',
        },
      },
      required: [],
    },
  },
];

// Tool handlers
export const guardrailsToolHandlers: Record<string, ToolHandler> = {
  sardis_check_circuit_breaker: async (args: unknown): Promise<ToolResult> => {
    const parsed = CheckCircuitBreakerSchema.safeParse(args);
    const config = getConfig();
    const walletId = parsed.success && parsed.data.wallet_id
      ? parsed.data.wallet_id
      : config.walletId || 'wallet_default';

    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated response
      const mockStatus: GuardrailsStatus = {
        wallet_id: walletId,
        circuit_breaker: {
          active: false,
          reason: null,
          triggered_at: null,
          auto_recovery: true,
        },
        kill_switch: {
          active: false,
          activated_by: null,
          activated_at: null,
          requires_manual_reset: true,
        },
        rate_limits: {
          tx_per_minute: {
            limit: 5,
            current: 1.2,
            percentage_used: 24.0,
            breached: false,
          },
          tx_per_hour: {
            limit: 100,
            current: 23,
            percentage_used: 23.0,
            breached: false,
          },
          spend_per_hour_usd: {
            limit: 1000.0,
            current: 125.5,
            percentage_used: 12.55,
            breached: false,
          },
        },
        status: 'operational',
        last_checked: new Date().toISOString(),
      };

      return {
        content: [{ type: 'text', text: JSON.stringify(mockStatus, null, 2) }],
      };
    }

    try {
      const status = await apiRequest<GuardrailsStatus>(
        'GET',
        '/api/v2/guardrails/status',
        undefined,
        { 'X-Wallet-ID': walletId }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(status, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to check circuit breaker: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_activate_kill_switch: async (args: unknown): Promise<ToolResult> => {
    const parsed = ActivateKillSwitchSchema.safeParse(args);
    if (!parsed.success) {
      return {
        content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }],
        isError: true,
      };
    }

    const config = getConfig();
    const walletId = parsed.data.wallet_id || config.walletId || 'wallet_default';

    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated response
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: walletId,
            kill_switch_active: true,
            activated_by: 'simulated_user',
            activated_at: new Date().toISOString(),
            reason: parsed.data.reason,
            message: '⚠️ KILL SWITCH ACTIVATED - All transactions halted',
            status: 'halted',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<{
        wallet_id: string;
        kill_switch_active: boolean;
        activated_at: string;
        reason: string;
        message: string;
      }>(
        'POST',
        '/api/v2/guardrails/kill-switch/activate',
        {
          wallet_id: walletId,
          reason: parsed.data.reason,
        }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to activate kill switch: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_deactivate_kill_switch: async (args: unknown): Promise<ToolResult> => {
    const parsed = DeactivateKillSwitchSchema.safeParse(args);
    const config = getConfig();
    const walletId = parsed.success && parsed.data.wallet_id
      ? parsed.data.wallet_id
      : config.walletId || 'wallet_default';

    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated response
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            wallet_id: walletId,
            kill_switch_active: false,
            deactivated_at: new Date().toISOString(),
            message: '✓ Kill switch deactivated - Wallet operational',
            status: 'operational',
          }, null, 2),
        }],
      };
    }

    try {
      const result = await apiRequest<{
        wallet_id: string;
        kill_switch_active: boolean;
        deactivated_at: string;
        message: string;
      }>(
        'POST',
        '/api/v2/guardrails/kill-switch/deactivate',
        { wallet_id: walletId }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to deactivate kill switch: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_check_rate_limits: async (args: unknown): Promise<ToolResult> => {
    const parsed = CheckRateLimitsSchema.safeParse(args);
    const config = getConfig();
    const walletId = parsed.success && parsed.data.wallet_id
      ? parsed.data.wallet_id
      : config.walletId || 'wallet_default';

    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated response
      const mockLimits = {
        wallet_id: walletId,
        limits: {
          tx_per_minute: {
            limit: 5,
            current: 1.2,
            percentage_used: 24.0,
            breached: false,
          },
          tx_per_hour: {
            limit: 100,
            current: 23,
            percentage_used: 23.0,
            breached: false,
          },
          spend_per_hour_usd: {
            limit: '1000.00',
            current: '125.50',
            percentage_used: 12.55,
            breached: false,
          },
        },
        status: 'healthy',
        last_checked: new Date().toISOString(),
      };

      return {
        content: [{ type: 'text', text: JSON.stringify(mockLimits, null, 2) }],
      };
    }

    try {
      const limits = await apiRequest(
        'GET',
        '/api/v2/guardrails/rate-limits',
        undefined,
        { 'X-Wallet-ID': walletId }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(limits, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to check rate limits: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },

  sardis_get_behavioral_alerts: async (args: unknown): Promise<ToolResult> => {
    const parsed = GetBehavioralAlertsSchema.safeParse(args);
    const config = getConfig();
    const walletId = parsed.success && parsed.data.wallet_id
      ? parsed.data.wallet_id
      : config.walletId || 'wallet_default';

    const queryParams = new URLSearchParams();
    if (parsed.success) {
      if (parsed.data.severity) queryParams.set('severity', parsed.data.severity);
      if (parsed.data.limit) queryParams.set('limit', parsed.data.limit.toString());
      if (parsed.data.since) queryParams.set('since', parsed.data.since);
    }

    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated response
      const mockAlerts: BehavioralAlertsResponse = {
        wallet_id: walletId,
        alerts: [
          {
            alert_id: 'alert_sim1',
            severity: 'medium',
            type: 'velocity_increase',
            message: 'Transaction rate slightly elevated',
            details: {
              normal_rate: '2.5 tx/min',
              current_rate: '3.2 tx/min',
              duration: '10 minutes',
            },
            timestamp: new Date(Date.now() - 600000).toISOString(),
            auto_blocked: false,
            requires_review: false,
          },
        ],
        total: 1,
        has_critical: false,
      };

      return {
        content: [{ type: 'text', text: JSON.stringify(mockAlerts, null, 2) }],
      };
    }

    try {
      const alerts = await apiRequest<BehavioralAlertsResponse>(
        'GET',
        `/api/v2/guardrails/alerts?${queryParams.toString()}`,
        undefined,
        { 'X-Wallet-ID': walletId }
      );
      return {
        content: [{ type: 'text', text: JSON.stringify(alerts, null, 2) }],
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `Failed to get behavioral alerts: ${error instanceof Error ? error.message : 'Unknown error'}`,
        }],
        isError: true,
      };
    }
  },
};
