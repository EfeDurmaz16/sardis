/**
 * Sardis MPP Proxy — Cloudflare Worker entry point
 *
 * A payment-gating reverse proxy that lets any API accept payments
 * from AI agents without code changes. Uses the Machine Payments
 * Protocol (HTTP 402) via the mppx SDK.
 *
 * Flow:
 *   1. Request arrives at the Worker
 *   2. Check if the route is protected (config.ts)
 *   3. If protected and no payment credential:
 *      → Return 402 with WWW-Authenticate: Payment header
 *   4. If protected and has Authorization: Payment header:
 *      → Verify payment via mppx
 *      → Check Sardis policy (spending mandate, vendor allowlist)
 *      → Forward to origin API
 *      → Log payment to Sardis audit trail (fire-and-forget)
 *      → Return response with Payment-Receipt header
 *   5. If not protected: pass through to origin
 *
 * @see https://mpp.dev
 * @see https://sardis.sh
 */

import { Hono } from 'hono';
import * as Mppx from 'mppx/server';
import type { Env } from './config.js';
import { buildConfig, findProtectedRoute } from './config.js';
import { checkPolicy } from './sardis-policy.js';
import { logAuditEvent, createAuditEntry } from './audit.js';

type HonoEnv = { Bindings: Env };

const app = new Hono<HonoEnv>();

// ---------------------------------------------------------------------------
// Health & introspection endpoints (never gated)
// ---------------------------------------------------------------------------

app.get('/__mpp/health', (c) =>
  c.json({
    status: 'ok',
    proxy: 'sardis-mpp-proxy',
    version: '0.1.0',
    timestamp: new Date().toISOString(),
  }),
);

app.get('/__mpp/config', (c) => {
  const config = buildConfig(c.env);
  return c.json({
    origin: config.origin ? '***' : '(not set)',
    protectedRoutes: config.protectedRoutes.map((r) => ({
      path: r.path,
      priceUsd: r.priceUsd,
      description: r.description,
    })),
    paymentMethods: config.paymentMethods,
    sardisPolicy: config.sardisApiKey ? 'enabled' : 'disabled',
    recipientAddress: config.recipientAddress
      ? config.recipientAddress.slice(0, 6) + '...' + config.recipientAddress.slice(-4)
      : '(not set)',
  });
});

// ---------------------------------------------------------------------------
// Main proxy middleware — all other requests
// ---------------------------------------------------------------------------

app.all('*', async (c) => {
  const config = buildConfig(c.env);
  const url = new URL(c.req.url);
  const path = url.pathname;

  // Find matching protected route
  const routeConfig = findProtectedRoute(path, config.protectedRoutes);

  // ── Pass-through: route is not protected ──────────────────────────
  if (!routeConfig) {
    return proxyToOrigin(c.req.raw, config.origin, c.env);
  }

  // ── Validate environment ──────────────────────────────────────────
  if (!config.mppSecretKey) {
    return c.json(
      { error: 'MPP_SECRET_KEY not configured' },
      { status: 500 },
    );
  }
  if (!config.recipientAddress) {
    return c.json(
      { error: 'PAY_TO not configured' },
      { status: 500 },
    );
  }

  // ── Build the mppx payment handler ────────────────────────────────
  const mppx = Mppx.create({
    methods: [
      Mppx.tempo({
        address: config.recipientAddress as `0x${string}`,
        asset: config.paymentCurrency as `0x${string}`,
      }),
    ],
    secretKey: config.mppSecretKey,
    realm: url.hostname,
  });

  // Create the charge handler for this route's price
  const chargeHandler = mppx.charge({
    amount: routeConfig.priceUsd,
    description: routeConfig.description,
  });

  // Execute the mppx charge/verify flow against the incoming request
  const paymentResult = await chargeHandler(c.req.raw);

  // ── 402: Payment required ─────────────────────────────────────────
  if (paymentResult.status === 402) {
    const challengeResponse = new Response(
      JSON.stringify({
        error: 'Payment Required',
        description: routeConfig.description,
        price: routeConfig.priceUsd,
        currency: 'USD',
        methods: config.paymentMethods,
        recipient: config.recipientAddress,
        sardisPolicy: config.sardisApiKey ? 'enabled' : 'disabled',
      }),
      {
        status: 402,
        headers: { 'Content-Type': 'application/json' },
      },
    );

    // Merge the WWW-Authenticate headers from mppx
    const challenge = paymentResult.challenge;
    if (challenge && typeof challenge === 'object' && 'headers' in challenge) {
      const challengeHeaders = challenge as { headers: Headers };
      challengeHeaders.headers.forEach((value: string, key: string) => {
        challengeResponse.headers.set(key, value);
      });
    }

    return challengeResponse;
  }

  // ── Payment verified — extract payer info ─────────────────────────
  const payerAddress = extractPayerAddress(c.req.raw) || 'unknown';

  // ── Sardis policy check ───────────────────────────────────────────
  const policyResult = await checkPolicy(
    {
      amount: routeConfig.priceUsd,
      payerAddress,
      route: path,
      merchant: config.origin ? new URL(config.origin).hostname : url.hostname,
      paymentMethod: 'tempo',
    },
    config.sardisApiUrl,
    config.sardisApiKey,
  );

  if (!policyResult.allowed) {
    // Log the blocked attempt
    const ctx = (c.executionCtx as ExecutionContext | undefined);
    if (ctx?.waitUntil) {
      ctx.waitUntil(
        logAuditEvent(
          createAuditEntry({
            eventType: 'mpp_proxy.policy_blocked',
            amount: routeConfig.priceUsd,
            payerAddress,
            recipientAddress: config.recipientAddress,
            paymentMethod: 'tempo',
            route: path,
            merchant: config.origin ? new URL(config.origin).hostname : url.hostname,
            httpMethod: c.req.method,
            responseStatus: 403,
            policyReason: policyResult.reason,
            mandateId: policyResult.mandateId,
          }),
          config.sardisApiUrl,
          config.sardisApiKey,
        ),
      );
    }

    return c.json(
      {
        error: 'Payment rejected by Sardis policy',
        reason: policyResult.reason,
        mandateId: policyResult.mandateId,
        remainingBudget: policyResult.remainingBudget,
      },
      { status: 403 },
    );
  }

  // ── Forward to origin API ─────────────────────────────────────────
  const originResponse = await proxyToOrigin(c.req.raw, config.origin, c.env);

  // ── Attach Payment-Receipt header ─────────────────────────────────
  const finalResponse = new Response(originResponse.body, {
    status: originResponse.status,
    statusText: originResponse.statusText,
    headers: new Headers(originResponse.headers),
  });

  // Merge receipt headers from mppx
  if (paymentResult.status === 200 && paymentResult.withReceipt) {
    try {
      const receiptResponse = paymentResult.withReceipt(finalResponse);
      if (receiptResponse instanceof Response) {
        return receiptResponse;
      }
    } catch {
      // If withReceipt fails, return the response without receipt
    }
  }

  // ── Fire-and-forget audit log ─────────────────────────────────────
  const ctx = (c.executionCtx as ExecutionContext | undefined);
  if (ctx?.waitUntil) {
    ctx.waitUntil(
      logAuditEvent(
        createAuditEntry({
          eventType: 'mpp_proxy.payment_completed',
          amount: routeConfig.priceUsd,
          payerAddress,
          recipientAddress: config.recipientAddress,
          paymentMethod: 'tempo',
          route: path,
          merchant: config.origin ? new URL(config.origin).hostname : url.hostname,
          httpMethod: c.req.method,
          responseStatus: finalResponse.status,
          policyReason: policyResult.reason,
          mandateId: policyResult.mandateId,
        }),
        config.sardisApiUrl,
        config.sardisApiKey,
      ),
    );
  }

  return finalResponse;
});

// ---------------------------------------------------------------------------
// Origin proxy helper
// ---------------------------------------------------------------------------

/**
 * Forward a request to the origin API.
 *
 * Supports three modes:
 *   1. Service binding (ORIGIN_SERVICE) — Worker-to-Worker
 *   2. External URL (ORIGIN_URL) — standard HTTP proxy
 *   3. DNS passthrough — when neither is configured
 */
async function proxyToOrigin(
  request: Request,
  originUrl: string,
  env: Env,
): Promise<Response> {
  // Service binding takes priority
  if (env.ORIGIN_SERVICE) {
    return env.ORIGIN_SERVICE.fetch(request.clone());
  }

  // Rewrite URL to point to origin
  if (originUrl) {
    const url = new URL(request.url);
    const origin = new URL(originUrl);
    url.hostname = origin.hostname;
    url.protocol = origin.protocol;
    url.port = origin.port;

    const proxyRequest = new Request(url.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'manual',
    });

    return fetch(proxyRequest);
  }

  // DNS passthrough — no origin rewriting
  return fetch(request.clone());
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extract the payer wallet address from MPP Authorization header.
 *
 * The Authorization: Payment header contains a base64-encoded
 * credential with the payer's address. We do a best-effort extraction.
 */
function extractPayerAddress(request: Request): string | undefined {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Payment ')) return undefined;

  try {
    const credential = authHeader.slice('Payment '.length);
    const decoded = atob(credential);
    // The payer address is typically in the credential payload
    const match = decoded.match(/0x[a-fA-F0-9]{40}/);
    return match?.[0];
  } catch {
    return undefined;
  }
}

// ---------------------------------------------------------------------------
// Export for Cloudflare Workers
// ---------------------------------------------------------------------------

export default app;
