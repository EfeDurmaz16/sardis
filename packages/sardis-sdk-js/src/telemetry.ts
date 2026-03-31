/**
 * Sardis SDK Telemetry Module
 *
 * Provides automatic agent registration, heartbeat, event tracking,
 * and header injection for agent-to-dashboard sync.
 *
 * All telemetry operations are wrapped in try/catch — telemetry
 * never crashes or blocks the SDK.
 *
 * @packageDocumentation
 */

import type { TelemetryConfig, TelemetryEvent } from './types.js';

/** Max events to buffer before dropping oldest */
const MAX_BUFFER_SIZE = 1000;

/** Default heartbeat interval in seconds */
const DEFAULT_HEARTBEAT_INTERVAL = 60;

/** Default batch flush interval in seconds */
const DEFAULT_BATCH_INTERVAL = 10;

/** Default batch size (events per flush) */
const DEFAULT_BATCH_SIZE = 10;

/** Generate a random session ID */
function generateSessionId(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = 'sess_';
  for (let i = 0; i < 24; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/** Generate a random agent ID if none provided */
function generateAgentId(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let result = 'ag_';
  for (let i = 0; i < 16; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Read an environment variable if available (Node.js or compatible runtimes).
 * Returns undefined in browser environments.
 */
function getEnv(key: string): string | undefined {
  try {
    if (typeof process !== 'undefined' && process.env) {
      return process.env[key];
    }
  } catch {
    // Browser or restricted environment
  }
  return undefined;
}

/**
 * SardisTelemetry handles agent auto-registration, heartbeat,
 * event batching, and correlation header injection.
 *
 * @example
 * ```typescript
 * const telemetry = new SardisTelemetry({
 *   agentId: 'my-agent',
 *   agentName: 'My Trading Agent',
 * });
 *
 * // Called internally by SardisClient
 * await telemetry.ensureRegistered(requestFn);
 * telemetry.startHeartbeat(requestFn);
 * telemetry.track('tool_call', { tool: 'get_balance' });
 * ```
 */
export class SardisTelemetry {
  private agentId: string;
  private agentName: string;
  private sessionId: string;
  private framework: string;
  private enabled: boolean;
  private heartbeatInterval: number;
  private batchInterval: number;
  private batchSize: number;

  private registered = false;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private buffer: TelemetryEvent[] = [];
  private shuttingDown = false;

  constructor(config?: TelemetryConfig) {
    const envEnabled = getEnv('SARDIS_TELEMETRY_ENABLED');
    this.enabled = config?.enabled ?? (envEnabled !== 'false');
    this.agentId = config?.agentId ?? getEnv('SARDIS_AGENT_ID') ?? generateAgentId();
    this.agentName = config?.agentName ?? getEnv('SARDIS_AGENT_NAME') ?? 'unnamed-agent';
    this.sessionId = generateSessionId();
    this.framework = config?.framework ?? '';

    const envHeartbeat = getEnv('SARDIS_HEARTBEAT_INTERVAL');
    this.heartbeatInterval = config?.heartbeatInterval
      ?? (envHeartbeat ? parseInt(envHeartbeat, 10) : DEFAULT_HEARTBEAT_INTERVAL);

    const envBatchInterval = getEnv('SARDIS_BATCH_INTERVAL');
    this.batchInterval = config?.batchInterval
      ?? (envBatchInterval ? parseInt(envBatchInterval, 10) : DEFAULT_BATCH_INTERVAL);

    const envBatchSize = getEnv('SARDIS_BATCH_SIZE');
    this.batchSize = config?.batchSize
      ?? (envBatchSize ? parseInt(envBatchSize, 10) : DEFAULT_BATCH_SIZE);
  }

  /**
   * Auto-register the agent with the server. Idempotent — safe to call multiple times.
   *
   * @param requestFn - The client's request function for making API calls
   */
  async ensureRegistered(
    requestFn: <T>(method: string, path: string, options?: { data?: unknown }) => Promise<T>
  ): Promise<void> {
    if (!this.enabled || this.registered) return;

    try {
      await requestFn('POST', '/api/v2/agents/auto-register', {
        data: {
          agent_id: this.agentId,
          name: this.agentName,
          session_id: this.sessionId,
          sdk_version: '1.0.0',
          framework: this.framework || undefined,
        },
      });
      this.registered = true;
    } catch {
      // Telemetry failure never propagates
    }
  }

  /**
   * Start periodic heartbeat to keep the agent marked as "online".
   * Also starts the event flush timer.
   *
   * @param requestFn - The client's request function for making API calls
   */
  startHeartbeat(
    requestFn: <T>(method: string, path: string, options?: { data?: unknown }) => Promise<T>
  ): void {
    if (!this.enabled) return;

    // Heartbeat with jitter to avoid thundering herd
    const sendHeartbeat = async () => {
      try {
        await requestFn('POST', '/api/v2/agents/heartbeat', {
          data: {
            agent_id: this.agentId,
            session_id: this.sessionId,
          },
        });
      } catch {
        // Silently ignore heartbeat failures
      }
    };

    // Jittered interval: interval * (0.8 + 0.4 * random())
    const jitteredMs = this.heartbeatInterval * 1000 * (0.8 + 0.4 * Math.random());
    this.heartbeatTimer = setInterval(sendHeartbeat, jitteredMs);

    // Unref the timer so it doesn't keep the process alive (Node.js)
    if (this.heartbeatTimer && typeof this.heartbeatTimer === 'object' && 'unref' in this.heartbeatTimer) {
      (this.heartbeatTimer as NodeJS.Timeout).unref();
    }

    // Start flush timer
    this.startFlushTimer(requestFn);
  }

  /**
   * Track an event. Events are buffered and flushed periodically.
   *
   * @param eventType - The type of event (e.g., 'tool_call', 'payment', 'error')
   * @param data - Arbitrary event data
   */
  track(eventType: string, data?: Record<string, unknown>): void {
    if (!this.enabled) return;

    try {
      const event: TelemetryEvent = {
        event_type: eventType,
        event_data: data ?? {},
        sdk_timestamp: new Date().toISOString(),
      };

      this.buffer.push(event);

      // Drop oldest events if buffer exceeds max
      while (this.buffer.length > MAX_BUFFER_SIZE) {
        this.buffer.shift();
      }
    } catch {
      // Never crash on tracking
    }
  }

  /**
   * Flush buffered events to the server.
   *
   * @param requestFn - The client's request function for making API calls
   */
  async flush(
    requestFn: <T>(method: string, path: string, options?: { data?: unknown }) => Promise<T>
  ): Promise<void> {
    if (!this.enabled || this.buffer.length === 0) return;

    try {
      // Take up to batchSize events
      const batch = this.buffer.splice(0, this.batchSize);

      await requestFn('POST', `/api/v2/agents/${this.agentId}/events/batch`, {
        data: {
          events: batch,
          session_id: this.sessionId,
        },
      });
    } catch {
      // Silently ignore flush failures — events are already removed from buffer
      // to avoid infinite retry loops
    }
  }

  /**
   * Stop heartbeat, flush remaining events, and clean up timers.
   *
   * @param requestFn - The client's request function for making API calls
   */
  async shutdown(
    requestFn: <T>(method: string, path: string, options?: { data?: unknown }) => Promise<T>
  ): Promise<void> {
    if (this.shuttingDown) return;
    this.shuttingDown = true;

    try {
      // Stop timers
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer);
        this.heartbeatTimer = null;
      }
      if (this.flushTimer) {
        clearInterval(this.flushTimer);
        this.flushTimer = null;
      }

      // Final flush of remaining events
      while (this.buffer.length > 0) {
        await this.flush(requestFn);
      }
    } catch {
      // Never crash on shutdown
    }
  }

  /**
   * Returns correlation headers to merge into every API request.
   */
  getHeaders(): Record<string, string> {
    if (!this.enabled) return {};

    return {
      'X-Sardis-Agent-Id': this.agentId,
      'X-Sardis-Session-Id': this.sessionId,
    };
  }

  /**
   * Whether telemetry is enabled.
   */
  isEnabled(): boolean {
    return this.enabled;
  }

  /**
   * Start the periodic flush timer.
   */
  private startFlushTimer(
    requestFn: <T>(method: string, path: string, options?: { data?: unknown }) => Promise<T>
  ): void {
    this.flushTimer = setInterval(async () => {
      try {
        await this.flush(requestFn);
      } catch {
        // Silently ignore
      }
    }, this.batchInterval * 1000);

    // Unref so it doesn't keep the process alive
    if (this.flushTimer && typeof this.flushTimer === 'object' && 'unref' in this.flushTimer) {
      (this.flushTimer as NodeJS.Timeout).unref();
    }
  }
}
