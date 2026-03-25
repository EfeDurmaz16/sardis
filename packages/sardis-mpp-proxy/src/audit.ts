/**
 * Sardis MPP Proxy — Audit trail
 *
 * Every payment that flows through the proxy is logged to the
 * Sardis audit API. This provides a complete, immutable record
 * of agent spending for compliance and analytics.
 *
 * Audit logging is fire-and-forget: it MUST NOT block or slow
 * the proxied response. We use waitUntil() in the Worker to
 * ensure the log is delivered without holding up the client.
 */

export interface AuditEntry {
  /** Unique event ID */
  eventId: string;
  /** ISO timestamp */
  timestamp: string;
  /** Event type */
  eventType: 'mpp_proxy.payment_completed' | 'mpp_proxy.payment_rejected' | 'mpp_proxy.policy_blocked';
  /** Amount in USD */
  amount: string;
  /** Payer wallet address */
  payerAddress: string;
  /** Recipient wallet address */
  recipientAddress: string;
  /** Payment method (e.g. "tempo") */
  paymentMethod: string;
  /** The proxied API route */
  route: string;
  /** Origin API host */
  merchant: string;
  /** HTTP method of the original request */
  httpMethod: string;
  /** HTTP status code returned to client */
  responseStatus: number;
  /** Policy decision reason (if checked) */
  policyReason?: string;
  /** Mandate ID (if policy was checked) */
  mandateId?: string;
  /** Additional metadata */
  metadata?: Record<string, string>;
}

/**
 * Generate a unique event ID for audit entries.
 */
export function generateEventId(): string {
  return `evt_mpp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Log a payment event to the Sardis audit trail.
 *
 * This function is designed to be called inside waitUntil()
 * so it does not block the response to the client.
 *
 * On failure, errors are logged to the console but never thrown.
 */
export async function logAuditEvent(
  entry: AuditEntry,
  sardisApiUrl: string,
  sardisApiKey: string,
): Promise<void> {
  if (!sardisApiKey) {
    console.log('[audit] No SARDIS_API_KEY — skipping audit log');
    return;
  }

  try {
    const response = await fetch(
      `${sardisApiUrl}/api/v2/events/ingest`,
      {
        method: 'POST',
        headers: {
          'X-API-Key': sardisApiKey,
          'Content-Type': 'application/json',
          'User-Agent': 'sardis-mpp-proxy/0.1.0',
        },
        body: JSON.stringify({
          event_id: entry.eventId,
          event_type: entry.eventType,
          timestamp: entry.timestamp,
          payload: {
            amount: entry.amount,
            payer_address: entry.payerAddress,
            recipient_address: entry.recipientAddress,
            payment_method: entry.paymentMethod,
            route: entry.route,
            merchant: entry.merchant,
            http_method: entry.httpMethod,
            response_status: entry.responseStatus,
            policy_reason: entry.policyReason,
            mandate_id: entry.mandateId,
            ...entry.metadata,
          },
        }),
      },
    );

    if (!response.ok) {
      console.error(
        `[audit] Failed to log event ${entry.eventId}: ${response.status}`,
      );
    }
  } catch (error) {
    console.error('[audit] Failed to send audit event:', error);
  }
}

/**
 * Create an audit entry from payment context.
 * Convenience builder so the main handler stays clean.
 */
export function createAuditEntry(
  params: Omit<AuditEntry, 'eventId' | 'timestamp'>,
): AuditEntry {
  return {
    eventId: generateEventId(),
    timestamp: new Date().toISOString(),
    ...params,
  };
}
