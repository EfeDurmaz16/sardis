/**
 * Sardis MPP Proxy — Route configuration and pricing
 *
 * Defines which routes require payment, how much they cost,
 * accepted payment methods, and the recipient address.
 */

/** A single route that requires payment before access. */
export interface ProtectedRoute {
  /** Glob-style path pattern, e.g. "/v1/data/*" */
  path: string;
  /** Price in USD (string to avoid float rounding) */
  priceUsd: string;
  /** Human-readable description shown in the 402 challenge */
  description: string;
  /** Override the default payment methods for this route */
  methods?: string[];
}

/** Top-level proxy configuration. */
export interface ProxyConfig {
  /** Origin API URL to proxy requests to */
  origin: string;
  /** Routes that require MPP payment */
  protectedRoutes: ProtectedRoute[];
  /** Accepted payment methods (default: ["tempo"]) */
  paymentMethods: string[];
  /** Sardis API key for policy enforcement + audit trail */
  sardisApiKey: string;
  /** Sardis API base URL */
  sardisApiUrl: string;
  /** Recipient wallet address (0x...) */
  recipientAddress: string;
  /** HMAC secret key for MPP payment verification */
  mppSecretKey: string;
  /** USDC contract address on the payment chain */
  paymentCurrency: string;
  /** Stripe secret key for SPT-based fiat payments */
  stripeSecretKey: string;
  /** Stripe network ID (e.g. "internal") */
  stripeNetworkId: string;
  /** Stripe payment method types (e.g. ["card"]) */
  stripePaymentMethodTypes: string[];
}

/** Cloudflare Worker environment bindings */
export interface Env {
  // Required
  MPP_SECRET_KEY: string;
  PAY_TO: string;
  SARDIS_API_KEY: string;

  // Optional with defaults
  ORIGIN_URL?: string;
  SARDIS_API_URL?: string;
  PAYMENT_CURRENCY?: string;
  PROTECTED_ROUTES?: string;
  PAYMENT_METHODS?: string;

  // Stripe SPT (optional — enables fiat payments alongside crypto)
  STRIPE_SECRET_KEY?: string;
  STRIPE_NETWORK_ID?: string;
  STRIPE_PAYMENT_METHOD_TYPES?: string;

  // Service binding (alternative to ORIGIN_URL)
  ORIGIN_SERVICE?: Fetcher;
}

/** Default USDC contract on Tempo mainnet */
const DEFAULT_PAYMENT_CURRENCY =
  '0x20c000000000000000000000b9537d11c60e8b50';

/** Default Sardis API URL */
const DEFAULT_SARDIS_API_URL = 'https://api.sardis.sh';

/**
 * Build proxy configuration from Cloudflare Worker env bindings.
 *
 * Protected routes can be configured via the PROTECTED_ROUTES env var
 * as a JSON array, or fall back to a sensible default that gates
 * every path at $0.01 per request.
 */
export function buildConfig(env: Env): ProxyConfig {
  let protectedRoutes: ProtectedRoute[];
  try {
    protectedRoutes = env.PROTECTED_ROUTES
      ? (JSON.parse(env.PROTECTED_ROUTES) as ProtectedRoute[])
      : [{ path: '/*', priceUsd: '0.01', description: 'API request' }];
  } catch {
    protectedRoutes = [
      { path: '/*', priceUsd: '0.01', description: 'API request' },
    ];
  }

  const defaultMethods = env.STRIPE_SECRET_KEY ? ['tempo', 'stripe'] : ['tempo'];
  let paymentMethods: string[];
  try {
    paymentMethods = env.PAYMENT_METHODS
      ? (JSON.parse(env.PAYMENT_METHODS) as string[])
      : defaultMethods;
  } catch {
    paymentMethods = defaultMethods;
  }

  let stripePaymentMethodTypes: string[];
  try {
    stripePaymentMethodTypes = env.STRIPE_PAYMENT_METHOD_TYPES
      ? (JSON.parse(env.STRIPE_PAYMENT_METHOD_TYPES) as string[])
      : ['card'];
  } catch {
    stripePaymentMethodTypes = ['card'];
  }

  return {
    origin: env.ORIGIN_URL || '',
    protectedRoutes,
    paymentMethods,
    sardisApiKey: env.SARDIS_API_KEY || '',
    sardisApiUrl: (env.SARDIS_API_URL || DEFAULT_SARDIS_API_URL).replace(
      /\/$/,
      '',
    ),
    recipientAddress: env.PAY_TO || '',
    mppSecretKey: env.MPP_SECRET_KEY || '',
    paymentCurrency: env.PAYMENT_CURRENCY || DEFAULT_PAYMENT_CURRENCY,
    stripeSecretKey: env.STRIPE_SECRET_KEY || '',
    stripeNetworkId: env.STRIPE_NETWORK_ID || 'internal',
    stripePaymentMethodTypes,
  };
}

/**
 * Match a request path against a route pattern.
 *
 * Supports:
 *   - Exact match: "/v1/data" matches "/v1/data"
 *   - Wildcard suffix: "/v1/data/*" matches "/v1/data/anything/here"
 *   - Catch-all: "/*" matches everything
 */
export function pathMatchesPattern(
  path: string,
  pattern: string,
): boolean {
  if (pattern === path) return true;
  if (pattern.endsWith('/*')) {
    const prefix = pattern.slice(0, -2);
    return path === prefix || path.startsWith(prefix + '/');
  }
  return false;
}

/**
 * Find the first protected route config that matches the given path.
 * Returns undefined if the path is not protected (pass-through).
 */
export function findProtectedRoute(
  path: string,
  routes: ProtectedRoute[],
): ProtectedRoute | undefined {
  return routes.find((r) => pathMatchesPattern(path, r.path));
}
