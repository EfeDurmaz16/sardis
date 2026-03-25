/**
 * Sardis MCP Server — Paid API Proxy Tools
 *
 * Tools for calling MPP-enabled APIs with automatic 402 payment handling.
 * When an API returns HTTP 402, the tool automatically:
 *   1. Reads the payment challenge (price, recipient, method)
 *   2. Checks Sardis spending policy (mandate budget, vendor allowlist)
 *   3. Executes payment via the Sardis MPP session
 *   4. Retries the request with the payment credential
 *   5. Returns the API response
 */

import { z } from 'zod';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';
import { apiRequest } from '../api.js';
import { getConfig } from '../config.js';

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const CallPaidApiSchema = z.object({
  url: z.string().url().describe('URL of the MPP-enabled API endpoint'),
  method: z.enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']).optional().default('GET'),
  body: z.string().optional().describe('Request body (JSON string)'),
  headers: z.record(z.string()).optional().describe('Additional request headers'),
  session_id: z.string().optional().describe('MPP session ID to charge against (creates one-time session if omitted)'),
  max_price_usd: z.number().positive().optional().default(1.0).describe('Maximum price willing to pay in USD (safety cap)'),
});

const PreviewCostSchema = z.object({
  url: z.string().url().describe('URL to check for MPP pricing'),
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function serialize(result: unknown): ToolResult {
  return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
}

function errorResult(message: string): ToolResult {
  return { content: [{ type: 'text', text: message }], isError: true };
}

/**
 * Parse a 402 response to extract the payment challenge.
 */
function parsePaymentChallenge(headers: Headers, body: string): {
  price?: string;
  recipient?: string;
  methods?: string[];
  description?: string;
  challenge?: string;
} | null {
  // Try parsing WWW-Authenticate header
  const wwwAuth = headers.get('WWW-Authenticate');

  // Also try parsing the JSON body for challenge info
  let bodyData: Record<string, unknown> = {};
  try {
    bodyData = JSON.parse(body) as Record<string, unknown>;
  } catch { /* not JSON */ }

  return {
    price: bodyData['price'] as string | undefined,
    recipient: bodyData['recipient'] as string | undefined,
    methods: bodyData['methods'] as string[] | undefined,
    description: bodyData['description'] as string | undefined,
    challenge: wwwAuth || undefined,
  };
}

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

export const proxyToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_call_paid_api',
    description:
      'Call any MPP-enabled API with automatic payment handling. ' +
      'If the API returns HTTP 402 (Payment Required), Sardis automatically ' +
      'verifies the price against your spending policy, executes the payment, ' +
      'and retries the request. Returns the API response after successful payment.',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'URL of the MPP-enabled API endpoint',
        },
        method: {
          type: 'string',
          enum: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
          description: 'HTTP method (default: GET)',
        },
        body: {
          type: 'string',
          description: 'Request body as JSON string',
        },
        headers: {
          type: 'object',
          description: 'Additional request headers as key-value pairs',
        },
        session_id: {
          type: 'string',
          description:
            'MPP session ID to charge against. If omitted, creates a one-time session.',
        },
        max_price_usd: {
          type: 'number',
          description:
            'Maximum price willing to pay in USD. Rejects if API charges more. Default: $1.00',
        },
      },
      required: ['url'],
    },
  },
  {
    name: 'sardis_preview_paid_api',
    description:
      'Preview the cost of calling an MPP-enabled API without actually paying. ' +
      'Sends a request to discover the price and payment methods.',
    inputSchema: {
      type: 'object',
      properties: {
        url: {
          type: 'string',
          description: 'URL to check for MPP pricing',
        },
      },
      required: ['url'],
    },
  },
];

// ---------------------------------------------------------------------------
// Tool handlers
// ---------------------------------------------------------------------------

export const proxyToolHandlers: Record<string, ToolHandler> = {
  sardis_call_paid_api: async (args: unknown): Promise<ToolResult> => {
    const parsed = CallPaidApiSchema.safeParse(args);
    if (!parsed.success)
      return errorResult(`Invalid request: ${parsed.error.message}`);

    const config = getConfig();
    const { url, method, body, headers, session_id, max_price_usd } = parsed.data;

    // ── Step 1: Make the initial request ─────────────────────────────
    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'sardis-mcp-server/1.0.0',
          ...headers,
        },
        body: body || undefined,
      });
    } catch (error) {
      return errorResult(
        `Failed to reach API: ${error instanceof Error ? error.message : 'Network error'}`,
      );
    }

    // ── Not 402? Return the response directly ────────────────────────
    if (response.status !== 402) {
      const responseBody = await response.text();
      let responseData: unknown;
      try {
        responseData = JSON.parse(responseBody);
      } catch {
        responseData = responseBody;
      }

      return serialize({
        status: response.status,
        payment_required: false,
        data: responseData,
      });
    }

    // ── Step 2: Parse the 402 challenge ──────────────────────────────
    const challengeBody = await response.text();
    const challenge = parsePaymentChallenge(response.headers, challengeBody);

    if (!challenge) {
      return errorResult(
        'API returned 402 but no valid payment challenge was found',
      );
    }

    // ── Step 3: Price safety check ───────────────────────────────────
    const price = parseFloat(challenge.price || '0');
    if (price > max_price_usd) {
      return serialize({
        status: 402,
        payment_required: true,
        blocked: true,
        reason: `Price $${price} exceeds max_price_usd cap of $${max_price_usd}`,
        challenge,
      });
    }

    // ── Step 4: Sardis policy check ──────────────────────────────────
    if (config.apiKey && config.mode !== 'simulated') {
      try {
        const policyResult = await apiRequest<{
          allowed: boolean;
          reason?: string;
        }>('POST', '/api/v2/mpp/evaluate', {
          amount: price,
          merchant: new URL(url).hostname,
          payment_type: 'mpp_tempo',
          currency: 'USDC',
          network: 'tempo',
        });

        if (!policyResult.allowed) {
          return serialize({
            status: 402,
            payment_required: true,
            blocked: true,
            reason: `Sardis policy: ${policyResult.reason || 'BLOCKED'}`,
            challenge,
            prevention: 'Financial Hallucination PREVENTED',
          });
        }
      } catch (error) {
        // Fail-open on policy check errors
        console.error('Policy check failed:', error);
      }
    }

    // ── Step 5: Execute payment via Sardis MPP ───────────────────────
    if (!config.apiKey || config.mode === 'simulated') {
      // Simulated mode — show what would happen
      return serialize({
        status: 402,
        payment_required: true,
        simulated: true,
        message:
          'Payment would be executed in live mode. Configure SARDIS_API_KEY and SARDIS_MODE=live.',
        challenge,
        price: challenge.price,
        recipient: challenge.recipient,
      });
    }

    try {
      // Create or use existing MPP session
      const sessionId = session_id || await createOneTimeSession(price);

      // Execute the MPP payment
      const paymentResult = await apiRequest<{
        payment_id: string;
        credential?: string;
        tx_hash?: string;
        status: string;
      }>('POST', `/api/v2/mpp/sessions/${sessionId}/execute`, {
        amount: price,
        merchant: new URL(url).hostname,
        merchant_url: url,
        memo: `MPP auto-payment for ${method} ${url}`,
      });

      if (paymentResult.status !== 'completed') {
        return errorResult(
          `Payment failed: ${paymentResult.status}`,
        );
      }

      // ── Step 6: Retry with payment credential ──────────────────────
      const retryResponse = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'sardis-mcp-server/1.0.0',
          ...(paymentResult.credential
            ? { Authorization: `Payment ${paymentResult.credential}` }
            : {}),
          ...headers,
        },
        body: body || undefined,
      });

      const retryBody = await retryResponse.text();
      let retryData: unknown;
      try {
        retryData = JSON.parse(retryBody);
      } catch {
        retryData = retryBody;
      }

      return serialize({
        status: retryResponse.status,
        payment_required: true,
        paid: true,
        payment: {
          payment_id: paymentResult.payment_id,
          amount: challenge.price,
          tx_hash: paymentResult.tx_hash,
          session_id: sessionId,
        },
        data: retryData,
      });
    } catch (error) {
      return errorResult(
        `Payment execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      );
    }
  },

  sardis_preview_paid_api: async (args: unknown): Promise<ToolResult> => {
    const parsed = PreviewCostSchema.safeParse(args);
    if (!parsed.success)
      return errorResult(`Invalid request: ${parsed.error.message}`);

    try {
      const response = await fetch(parsed.data.url, {
        method: 'HEAD',
        headers: {
          'User-Agent': 'sardis-mcp-server/1.0.0',
        },
      });

      if (response.status !== 402) {
        return serialize({
          url: parsed.data.url,
          payment_required: false,
          status: response.status,
          message: 'This endpoint does not require payment',
        });
      }

      // Try GET for the full challenge body
      const getResponse = await fetch(parsed.data.url, {
        method: 'GET',
        headers: {
          'User-Agent': 'sardis-mcp-server/1.0.0',
        },
      });

      const body = await getResponse.text();
      const challenge = parsePaymentChallenge(getResponse.headers, body);

      return serialize({
        url: parsed.data.url,
        payment_required: true,
        price: challenge?.price || 'unknown',
        methods: challenge?.methods || ['unknown'],
        recipient: challenge?.recipient || 'unknown',
        description: challenge?.description || 'N/A',
      });
    } catch (error) {
      return errorResult(
        `Failed to preview: ${error instanceof Error ? error.message : 'Network error'}`,
      );
    }
  },
};

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Create a one-time MPP session for a single payment.
 */
async function createOneTimeSession(amount: number): Promise<string> {
  const result = await apiRequest<{ session_id: string }>(
    'POST',
    '/api/v2/mpp/sessions',
    {
      spending_limit: amount * 1.1, // 10% buffer for fees
      method: 'tempo',
      chain: 'tempo',
      currency: 'USDC',
      expires_in_seconds: 300, // 5-minute session
    },
  );
  return result.session_id;
}
