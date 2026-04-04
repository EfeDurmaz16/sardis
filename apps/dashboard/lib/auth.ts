import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { passkey } from "@better-auth/passkey";
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
