/**
 * Sardis Connect middleware for Express/Node.js.
 *
 * Adds agent discovery, payment, and verification endpoints.
 */

import type {
  PricedEndpoint,
  ServiceManifest,
  PaySession,
  PaymentResult,
} from "./types";

export interface SardisConnectOptions {
  /** Merchant API key (mch_live_xxx) */
  apiKey: string;
  /** Merchant ID */
  merchantId?: string;
  /** Service name for discovery */
  serviceName?: string;
  /** Service description */
  serviceDescription?: string;
  /** Base URL of this API */
  baseUrl?: string;
  /** Priced endpoints */
  endpoints?: PricedEndpoint[];
  /** Sardis API URL */
  sardisApiUrl?: string;
  /** Webhook secret for verification */
  webhookSecret?: string;
}

interface ConnectInstance {
  /** Express/Connect middleware */
  middleware: () => (req: any, res: any, next: any) => void;
  /** Add a priced endpoint */
  price: (
    path: string,
    amount: string,
    description?: string,
    method?: string
  ) => void;
  /** Get the service manifest */
  manifest: () => ServiceManifest;
}

/**
 * Create a Sardis Connect instance.
 *
 * Usage:
 *   const sardis = sardisConnect({ apiKey: 'mch_live_xxx' });
 *   app.use(sardis.middleware());
 */
export function sardisConnect(options: SardisConnectOptions): ConnectInstance {
  const {
    apiKey,
    merchantId = process.env.SARDIS_MERCHANT_ID || "",
    serviceName = "API Service",
    serviceDescription = "API endpoints available for agent payments",
    baseUrl = process.env.SARDIS_CONNECT_BASE_URL || "",
    endpoints = [],
    sardisApiUrl = process.env.SARDIS_API_URL || "https://api.sardis.sh",
  } = options;

  const pricedEndpoints: PricedEndpoint[] = [...endpoints];

  function price(
    path: string,
    amount: string,
    description = "",
    method = "POST"
  ) {
    pricedEndpoints.push({
      path,
      method,
      price: amount,
      currency: "USD",
      description,
    });
  }

  function manifest(): ServiceManifest {
    return {
      version: "1.0",
      name: serviceName,
      description: serviceDescription,
      baseUrl,
      merchantId,
      accepts: ["sardis", "x402", "mpp"],
      endpoints: pricedEndpoints,
    };
  }

  function middleware() {
    return async (req: any, res: any, next: any) => {
      const url = new URL(req.url || req.originalUrl || "/", "http://localhost");
      const path = url.pathname;

      // Discovery endpoint
      if (path === "/.well-known/sardis.json" && req.method === "GET") {
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify(manifest()));
        return;
      }

      // Payment endpoint
      if (path === "/sardis/pay" && req.method === "POST") {
        try {
          const body = await parseBody(req);
          const endpoint = pricedEndpoints.find(
            (ep) => ep.path === body.endpoint
          );
          if (!endpoint) {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: "Endpoint not found" }));
            return;
          }

          const amount = body.amount || endpoint.price;
          const resp = await fetch(
            `${sardisApiUrl}/api/v2/merchant-checkout/sessions`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${apiKey}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                merchant_id: merchantId,
                amount,
                currency: body.currency || "USD",
                description:
                  endpoint.description || `Payment for ${endpoint.path}`,
                metadata: { endpoint: body.endpoint, ...body.metadata },
              }),
            }
          );

          if (!resp.ok) {
            res.statusCode = 502;
            res.end(JSON.stringify({ error: "Failed to create payment" }));
            return;
          }

          const data = (await resp.json()) as Record<string, any>;
          const result: PaySession = {
            sessionId: data.session_id,
            clientSecret: data.client_secret || "",
            checkoutUrl: data.checkout_url || "",
            amount,
            currency: body.currency || "USD",
            status: "pending",
          };
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(result));
        } catch (e: any) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: e.message }));
        }
        return;
      }

      // Verification endpoint
      if (path === "/sardis/verify" && req.method === "POST") {
        try {
          const body = await parseBody(req);
          const resp = await fetch(
            `${sardisApiUrl}/api/v2/merchant-checkout/sessions/${body.sessionId || body.session_id}`,
            { headers: { Authorization: `Bearer ${apiKey}` } }
          );

          if (!resp.ok) {
            res.setHeader("Content-Type", "application/json");
            res.end(
              JSON.stringify({
                verified: false,
                sessionId: body.sessionId || body.session_id,
                error: "Session not found",
              })
            );
            return;
          }

          const data = (await resp.json()) as Record<string, any>;
          const isPaid = ["paid", "settled"].includes(data.status);
          const result: PaymentResult = {
            verified: isPaid,
            sessionId: data.session_id,
            amount: data.amount || "0",
            currency: data.currency || "USD",
            payerId: data.payer_wallet_id,
            error: isPaid ? undefined : `Session status: ${data.status}`,
          };
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(result));
        } catch (e: any) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: e.message }));
        }
        return;
      }

      // Not a sardis route — pass through
      next();
    };
  }

  return { middleware, price, manifest };
}

/** Parse request body (works with Express, raw Node.js, etc.) */
function parseBody(req: any): Promise<any> {
  if (req.body) return Promise.resolve(req.body);
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk: any) => (data += chunk));
    req.on("end", () => {
      try {
        resolve(JSON.parse(data || "{}"));
      } catch {
        resolve({});
      }
    });
    req.on("error", reject);
  });
}
