import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { passkey } from "@better-auth/passkey";
import { apiKey } from "@better-auth/api-key";
import { agentAuth } from "@better-auth/agent-auth";
import type { Capability } from "@better-auth/agent-auth";
import { Pool } from "pg";

/**
 * Agent Auth Protocol configuration.
 *
 * Sardis exposes /.well-known/agent-configuration for AI agent discovery.
 * The dashboard auth config includes agent-specific JWT claims so that
 * dashboard users can manage their registered agents and capability grants.
 *
 * Agent tokens use the X-Agent-JWT header (not Authorization: Bearer)
 * to support dual auth: API key/dashboard JWT + agent identity.
 */
export const AGENT_AUTH_CONFIG = {
  discoveryUrl:
    (process.env.SARDIS_API_URL || "https://api.sardis.sh").trim(),
  discoveryPath: "/.well-known/agent-configuration",
  algorithms: ["Ed25519"] as const,
  supportedModes: ["delegated", "autonomous"] as const,
  capabilities: [
    "payment",
    "fx_quote",
    "policy_check",
    "mandate_create",
    "balance_check",
  ] as const,
  /** Header used for agent JWT tokens (separate from main auth) */
  agentTokenHeader: "X-Agent-JWT",
} as const;

export type AgentCapability = (typeof AGENT_AUTH_CONFIG.capabilities)[number];
export type AgentMode = (typeof AGENT_AUTH_CONFIG.supportedModes)[number];

/**
 * Sardis capability definitions for the Agent Auth Protocol (§4).
 *
 * Each capability maps to a Sardis API operation. The `location` field
 * points to the API endpoint that handles execution. The `input`/`output`
 * fields are JSON Schema describing the request/response shapes.
 *
 * approvalStrength:
 *   - "none"    — auto-grant, no user interaction
 *   - "session" — requires active user session (default)
 *   - "webauthn"— requires proof of physical presence (passkey)
 */
const SARDIS_CAPABILITIES: Capability[] = [
  {
    name: "payment",
    description:
      "Execute payments through Sardis wallets. Transfers stablecoins (USDC, EURC) on supported chains via non-custodial MPC wallets with policy enforcement.",
    location: `${(process.env.SARDIS_API_URL || "https://api.sardis.sh").trim()}/v2/payments/execute`,
    approvalStrength: "webauthn",
    input: {
      type: "object",
      properties: {
        wallet_id: { type: "string", description: "Sardis wallet ID (wal_...)" },
        to: { type: "string", description: "Recipient address or Sardis wallet ID" },
        amount: { type: "string", description: "Amount in token decimals" },
        token: { type: "string", enum: ["USDC", "EURC", "USDT", "PYUSD"] },
        chain: { type: "string", enum: ["base", "ethereum", "polygon", "arbitrum", "optimism"] },
        memo: { type: "string", description: "Optional payment memo" },
      },
      required: ["wallet_id", "to", "amount", "token", "chain"],
    },
    output: {
      type: "object",
      properties: {
        tx_hash: { type: "string" },
        status: { type: "string", enum: ["confirmed", "pending", "failed"] },
        ledger_entry_id: { type: "string" },
      },
    },
  },
  {
    name: "fx_quote",
    description:
      "Get foreign exchange quotes for cross-currency stablecoin conversions. Returns indicative rates with expiry for USDC/EURC/USDT pairs.",
    location: `${(process.env.SARDIS_API_URL || "https://api.sardis.sh").trim()}/v2/fx/quote`,
    approvalStrength: "none",
    input: {
      type: "object",
      properties: {
        from_token: { type: "string", enum: ["USDC", "EURC", "USDT", "PYUSD"] },
        to_token: { type: "string", enum: ["USDC", "EURC", "USDT", "PYUSD"] },
        amount: { type: "string", description: "Amount of from_token" },
      },
      required: ["from_token", "to_token", "amount"],
    },
    output: {
      type: "object",
      properties: {
        rate: { type: "string" },
        to_amount: { type: "string" },
        expires_at: { type: "string", format: "date-time" },
        quote_id: { type: "string" },
      },
    },
  },
  {
    name: "policy_check",
    description:
      "Verify whether a proposed transaction complies with the spending policies attached to a wallet or mandate. Returns pass/fail with violation details.",
    location: `${(process.env.SARDIS_API_URL || "https://api.sardis.sh").trim()}/v2/policies/check`,
    approvalStrength: "none",
    input: {
      type: "object",
      properties: {
        wallet_id: { type: "string" },
        mandate_id: { type: "string", description: "Optional mandate ID to check against" },
        to: { type: "string" },
        amount: { type: "string" },
        token: { type: "string" },
        chain: { type: "string" },
      },
      required: ["wallet_id", "to", "amount", "token", "chain"],
    },
    output: {
      type: "object",
      properties: {
        allowed: { type: "boolean" },
        violations: {
          type: "array",
          items: {
            type: "object",
            properties: {
              rule: { type: "string" },
              message: { type: "string" },
            },
          },
        },
      },
    },
  },
  {
    name: "mandate_create",
    description:
      "Create a spending mandate that defines budget limits, allowed recipients, time windows, and per-transaction caps for an agent wallet.",
    location: `${(process.env.SARDIS_API_URL || "https://api.sardis.sh").trim()}/v2/mandates`,
    approvalStrength: "session",
    input: {
      type: "object",
      properties: {
        wallet_id: { type: "string" },
        name: { type: "string", description: "Human-readable mandate name" },
        budget: { type: "string", description: "Total budget in token decimals" },
        token: { type: "string", enum: ["USDC", "EURC", "USDT", "PYUSD"] },
        per_tx_limit: { type: "string", description: "Max amount per transaction" },
        allowed_recipients: {
          type: "array",
          items: { type: "string" },
          description: "Whitelisted recipient addresses",
        },
        expires_at: { type: "string", format: "date-time" },
      },
      required: ["wallet_id", "name", "budget", "token"],
    },
    output: {
      type: "object",
      properties: {
        mandate_id: { type: "string" },
        status: { type: "string", enum: ["active", "pending_approval"] },
      },
    },
  },
  {
    name: "balance_check",
    description:
      "Check token balances for a Sardis wallet across supported chains. Returns per-chain breakdown with USD equivalents.",
    location: `${(process.env.SARDIS_API_URL || "https://api.sardis.sh").trim()}/v2/wallets/balance`,
    approvalStrength: "none",
    input: {
      type: "object",
      properties: {
        wallet_id: { type: "string", description: "Sardis wallet ID (wal_...)" },
        chain: { type: "string", description: "Optional: filter to a specific chain" },
        token: { type: "string", description: "Optional: filter to a specific token" },
      },
      required: ["wallet_id"],
    },
    output: {
      type: "object",
      properties: {
        wallet_id: { type: "string" },
        balances: {
          type: "array",
          items: {
            type: "object",
            properties: {
              chain: { type: "string" },
              token: { type: "string" },
              amount: { type: "string" },
              usd_value: { type: "string" },
            },
          },
        },
        total_usd: { type: "string" },
      },
    },
  },
];

/**
 * better-auth server configuration for Sardis dashboard.
 *
 * Database: Neon PostgreSQL via pg.Pool (connection-pooler compatible).
 * Tables use "ba_" prefix via modelName to avoid conflicts with existing
 * sardis tables. Column names use snake_case via field mappings to match
 * migration 077_better_auth_tables.sql.
 */
export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
    // Neon connection pooler settings
    max: 10,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 10_000,
    ssl: { rejectUnauthorized: false },
  }),
  baseURL: process.env.BETTER_AUTH_URL || "https://app.sardis.sh",
  secret: process.env.BETTER_AUTH_SECRET,
  // Accept auth requests from all dashboard domains (same Vercel project)
  trustedOrigins: [
    "https://dashboard.sardis.sh",
    "https://app.sardis.sh",
    "https://sardis.sh",
    "http://localhost:3000",
    "http://localhost:3005",
  ],
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
  },
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    },
  },
  plugins: [
    jwt({
      jwt: {
        issuer: process.env.BETTER_AUTH_URL || "https://app.sardis.sh",
        audience: "sardis-api",
        expirationTime: "1h",
        definePayload: async ({ user }) => ({
          sub: user.id,
          email: user.email,
          org_id: (user as Record<string, unknown>).orgId as string | undefined,
          role: (user as Record<string, unknown>).role as string || "user",
        }),
      },
      schema: {
        jwks: { modelName: "ba_jwks" },
      },
    }),
    passkey({
      rpID: process.env.NODE_ENV === "production" ? "sardis.sh" : "localhost",
      rpName: "Sardis",
      origin: process.env.BETTER_AUTH_URL || "https://app.sardis.sh",
    }),
    agentAuth({
      providerName: "Sardis",
      providerDescription:
        "Payment OS for the Agent Economy — non-custodial MPC wallets with natural language spending policies for AI agents.",
      modes: ["delegated", "autonomous"],
      allowedKeyAlgorithms: ["Ed25519"],
      capabilities: SARDIS_CAPABILITIES,
      /**
       * Payment capability requires WebAuthn proof-of-presence so
       * AI agents with browser access cannot self-approve fund transfers.
       */
      proofOfPresence: {
        enabled: true,
        rpId: process.env.NODE_ENV === "production" ? "sardis.sh" : "localhost",
        origin: process.env.BETTER_AUTH_URL || "https://app.sardis.sh",
      },
      maxAgentsPerUser: 25,
      agentSessionTTL: 3600,      // 1 hour sliding window
      agentMaxLifetime: 86400,    // 24 hours max session
      jwtMaxAge: 60,              // 60s JWT validity
      freshSessionWindow: 300,    // 5 min fresh session for approvals
      trustProxy: true,           // Vercel reverse proxy
    }),
  ],
  // Map model names to ba_-prefixed tables (migration 077)
  user: {
    modelName: "ba_user",
    fields: {
      name: "name",
      email: "email",
      emailVerified: "email_verified",
      image: "image",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
    additionalFields: {
      orgId: {
        type: "string",
        required: false,
        fieldName: "org_id",
      },
      role: {
        type: "string",
        required: false,
        defaultValue: "user",
        fieldName: "role",
      },
      kycStatus: {
        type: "string",
        required: false,
        defaultValue: "not_started",
        fieldName: "kyc_status",
      },
      displayName: {
        type: "string",
        required: false,
        fieldName: "display_name",
      },
    },
  },
  session: {
    modelName: "ba_session",
    fields: {
      expiresAt: "expires_at",
      token: "token",
      createdAt: "created_at",
      updatedAt: "updated_at",
      ipAddress: "ip_address",
      userAgent: "user_agent",
      userId: "user_id",
    },
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // refresh daily
  },
  account: {
    modelName: "ba_account",
    fields: {
      accountId: "account_id",
      providerId: "provider_id",
      userId: "user_id",
      accessToken: "access_token",
      refreshToken: "refresh_token",
      idToken: "id_token",
      accessTokenExpiresAt: "access_token_expires_at",
      refreshTokenExpiresAt: "refresh_token_expires_at",
      scope: "scope",
      password: "password",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
    accountLinking: {
      enabled: true,
      trustedProviders: ["google"],
    },
  },
  verification: {
    modelName: "ba_verification",
    fields: {
      identifier: "identifier",
      value: "value",
      expiresAt: "expires_at",
      createdAt: "created_at",
      updatedAt: "updated_at",
    },
  },
  passkey: {
    modelName: "ba_passkey",
    fields: {
      publicKey: "public_key",
      userId: "user_id",
      credentialId: "credential_id",
      deviceType: "device_type",
      backedUp: "backed_up",
      createdAt: "created_at",
    },
  },
});

export type Session = typeof auth.$Infer.Session;
