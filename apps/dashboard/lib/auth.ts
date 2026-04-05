import { betterAuth } from "better-auth";
import { jwt, magicLink, oneTap, phoneNumber } from "better-auth/plugins";
import { passkey } from "@better-auth/passkey";
import { apiKey } from "@better-auth/api-key";
import { agentAuth } from "@better-auth/agent-auth";
import type { Capability } from "@better-auth/agent-auth";
import { polar, checkout, portal, usage, webhooks } from "@polar-sh/better-auth";
import { stripe } from "@better-auth/stripe";
import { Polar } from "@polar-sh/sdk";
import Stripe from "stripe";
import { Pool } from "pg";

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
    "https://dashboard-wine-alpha-31.vercel.app",
    "http://localhost:3000",
    "http://localhost:3005",
  ],
  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    sendResetPassword: async ({ user, url }) => {
      const RESEND_API_KEY = process.env.RESEND_API_KEY;
      if (!RESEND_API_KEY) {
        console.warn("[reset-password] RESEND_API_KEY not set — logging link");
        console.log(`[reset-password] ${user.email}: ${url}`);
        return;
      }
      await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${RESEND_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          from: "Sardis <auth@mail.sardis.sh>",
          to: user.email,
          subject: "Reset your Sardis password",
          html: `<p>Click <a href="${url}">here</a> to reset your password. This link expires in 1 hour.</p><p>If you didn't request this, you can safely ignore this email.</p>`,
        }),
      });
    },
    password: {
      verify: async ({ hash, password }) => {
        // Legacy format: "pbkdf2:salt:dk_hex" (100k iterations, sha256)
        if (hash.startsWith("pbkdf2:")) {
          const crypto = await import("crypto");
          const [, salt, storedDk] = hash.split(":", 3);
          if (!salt || !storedDk) return false;
          const derived = crypto.pbkdf2Sync(
            password, salt, 100_000, 32, "sha256"
          );
          return crypto.timingSafeEqual(
            Buffer.from(derived.toString("hex")),
            Buffer.from(storedDk)
          );
        }
        // better-auth default format: "salt:hash" (scrypt)
        const { verifyPassword } = await import("better-auth/crypto");
        return verifyPassword({ hash, password });
      },
    },
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
        jwks: {
          modelName: "ba_jwks",
          fields: {
            publicKey: "public_key",
            privateKey: "private_key",
            createdAt: "created_at",
          },
        },
      },
    }),
    passkey({
      rpID: process.env.NODE_ENV === "production" ? "app.sardis.sh" : "localhost",
      rpName: "Sardis",
      origin: process.env.BETTER_AUTH_URL || "https://app.sardis.sh",
    }),
    /**
     * API Key management plugin — two configs for test/live mode.
     *
     * Test keys (sk_test_*): lower rate limits, safe for development.
     * Live keys (sk_live_*): production rate limits, full capabilities.
     *
     * Permissions use Sardis resource-action model:
     *   wallets: read, write   — wallet creation, balance checks
     *   payments: read, write  — payment execution, history
     *   policies: read, write  — policy CRUD
     *   mandates: read, write  — spending mandate management
     *   agents: read, write    — agent registration, capability grants
     *   admin: read, write     — org settings, billing, key management
     *
     * Keys are hashed with the built-in SHA-256 hasher (default).
     * Metadata is enabled to store mode, environment, and custom labels.
     * Table: ba_apikey (via schema mapping to match ba_ prefix convention).
     */
    apiKey(
      [
        {
          configId: "test",
          defaultPrefix: "sk_test_",
          defaultKeyLength: 48,
          requireName: true,
          enableMetadata: true,
          rateLimit: {
            enabled: true,
            timeWindow: 1000 * 60 * 60,      // 1 hour window
            maxRequests: 100,                 // 100 req/hour for test keys
          },
          keyExpiration: {
            defaultExpiresIn: 1000 * 60 * 60 * 24 * 90, // 90 days default
            maxExpiresIn: 365,                           // max 1 year
          },
          permissions: {
            defaultPermissions: {
              wallets: ["read"],
              payments: ["read"],
              policies: ["read"],
              mandates: ["read"],
              agents: ["read"],
            },
          },
          startingCharactersConfig: {
            shouldStore: true,
            charactersLength: 12,   // prefix + first 4 chars of key
          },
        },
        {
          configId: "live",
          defaultPrefix: "sk_live_",
          defaultKeyLength: 48,
          requireName: true,
          enableMetadata: true,
          rateLimit: {
            enabled: true,
            timeWindow: 1000 * 60 * 60,      // 1 hour window
            maxRequests: 1000,                // 1000 req/hour for live keys
          },
          keyExpiration: {
            defaultExpiresIn: null,           // no expiration by default
            maxExpiresIn: 365,                // max 1 year if set
          },
          permissions: {
            defaultPermissions: {
              wallets: ["read", "write"],
              payments: ["read", "write"],
              policies: ["read", "write"],
              mandates: ["read", "write"],
              agents: ["read", "write"],
            },
          },
          startingCharactersConfig: {
            shouldStore: true,
            charactersLength: 12,   // prefix + first 4 chars of key
          },
        },
      ],
      {
        schema: {
          apikey: {
            modelName: "ba_apikey",
            fields: {
              configId: "config_id",
              referenceId: "reference_id",
              refillInterval: "refill_interval",
              refillAmount: "refill_amount",
              lastRefillAt: "last_refill_at",
              rateLimitEnabled: "rate_limit_enabled",
              rateLimitTimeWindow: "rate_limit_time_window",
              rateLimitMax: "rate_limit_max",
              requestCount: "request_count",
              lastRequest: "last_request",
              expiresAt: "expires_at",
              createdAt: "created_at",
              updatedAt: "updated_at",
            },
          },
        },
      },
    ),
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
        rpId: process.env.NODE_ENV === "production" ? "app.sardis.sh" : "localhost",
        origin: process.env.BETTER_AUTH_URL || "https://app.sardis.sh",
      },
      maxAgentsPerUser: 25,
      agentSessionTTL: 3600,      // 1 hour sliding window
      agentMaxLifetime: 86400,    // 24 hours max session
      jwtMaxAge: 60,              // 60s JWT validity
      freshSessionWindow: 300,    // 5 min fresh session for approvals
      trustProxy: true,           // Vercel reverse proxy
      schema: {
        agentHost: {
          modelName: "ba_agent_host",
          fields: {
            userId: "user_id",
            defaultCapabilities: "default_capabilities",
            publicKey: "public_key",
            jwksUrl: "jwks_url",
            enrollmentTokenHash: "enrollment_token_hash",
            enrollmentTokenExpiresAt: "enrollment_token_expires_at",
            activatedAt: "activated_at",
            expiresAt: "expires_at",
            lastUsedAt: "last_used_at",
            createdAt: "created_at",
            updatedAt: "updated_at",
          },
        },
        agent: {
          modelName: "ba_agent",
          fields: {
            userId: "user_id",
            hostId: "host_id",
            publicKey: "public_key",
            jwksUrl: "jwks_url",
            lastUsedAt: "last_used_at",
            activatedAt: "activated_at",
            expiresAt: "expires_at",
            createdAt: "created_at",
            updatedAt: "updated_at",
          },
        },
        agentCapabilityGrant: {
          modelName: "ba_agent_capability_grant",
          fields: {
            agentId: "agent_id",
            deniedBy: "denied_by",
            grantedBy: "granted_by",
            expiresAt: "expires_at",
            createdAt: "created_at",
            updatedAt: "updated_at",
          },
        },
        approvalRequest: {
          modelName: "ba_approval_request",
          fields: {
            agentId: "agent_id",
            hostId: "host_id",
            userId: "user_id",
            userCodeHash: "user_code_hash",
            loginHint: "login_hint",
            bindingMessage: "binding_message",
            clientNotificationToken: "client_notification_token",
            clientNotificationEndpoint: "client_notification_endpoint",
            deliveryMode: "delivery_mode",
            lastPolledAt: "last_polled_at",
            expiresAt: "expires_at",
            createdAt: "created_at",
            updatedAt: "updated_at",
          },
        },
      },
    }),
    /**
     * Magic Link — passwordless email login.
     * Requires RESEND_API_KEY (or other email provider) to send magic links.
     * The sendMagicLink callback must be implemented to deliver the link.
     */
    magicLink({
      sendMagicLink: async ({ email, token, url }, ctx) => {
        // Use Resend or other email service to deliver magic links.
        // In production, replace with real email delivery.
        const RESEND_API_KEY = process.env.RESEND_API_KEY;
        if (!RESEND_API_KEY) {
          console.warn("[magic-link] RESEND_API_KEY not set — logging link to console");
          console.log(`[magic-link] ${email}: ${url}`);
          return;
        }
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${RESEND_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: "Sardis <auth@mail.sardis.sh>",
            to: email,
            subject: "Sign in to Sardis",
            html: `<p>Click <a href="${url}">here</a> to sign in to your Sardis account. This link expires in 5 minutes.</p>`,
          }),
        });
      },
    }),
    /**
     * Google One Tap — seamless Google sign-in popup.
     * Server plugin; client-side configured separately in auth-client.ts.
     */
    oneTap(),
    /**
     * Phone Number — OTP-based phone authentication.
     * Requires an SMS provider (Twilio, etc.) to send OTP codes.
     */
    phoneNumber({
      sendOTP: async ({ phoneNumber: phone, code }, ctx) => {
        // Use Twilio or other SMS provider to deliver OTP.
        const TWILIO_SID = process.env.TWILIO_ACCOUNT_SID;
        const TWILIO_TOKEN = process.env.TWILIO_AUTH_TOKEN;
        const TWILIO_FROM = process.env.TWILIO_PHONE_NUMBER;
        if (!TWILIO_SID || !TWILIO_TOKEN || !TWILIO_FROM) {
          console.warn("[phone] Twilio credentials not set — logging OTP to console");
          console.log(`[phone] ${phone}: ${code}`);
          return;
        }
        await fetch(
          `https://api.twilio.com/2010-04-01/Accounts/${TWILIO_SID}/Messages.json`,
          {
            method: "POST",
            headers: {
              Authorization: `Basic ${Buffer.from(`${TWILIO_SID}:${TWILIO_TOKEN}`).toString("base64")}`,
              "Content-Type": "application/x-www-form-urlencoded",
            },
            body: new URLSearchParams({
              From: TWILIO_FROM,
              To: phone,
              Body: `Your Sardis verification code is: ${code}`,
            }).toString(),
          },
        );
      },
    }),
    /**
     * Polar — usage-based billing via Polar.sh (primary billing provider).
     * Only initialized if POLAR_ACCESS_TOKEN is set.
     */
    ...(process.env.POLAR_ACCESS_TOKEN ? [polar({
      client: new Polar({
        accessToken: process.env.POLAR_ACCESS_TOKEN,
        server: (process.env.POLAR_ENVIRONMENT as "sandbox" | "production") || "sandbox",
      }),
      createCustomerOnSignUp: true,
      use: [
        checkout({
          products: [
            { productId: "7aa8578d-ea9f-4e19-8d5a-377fb3b6e1d9", slug: "starter" },
            { productId: "0f0009fe-fa2f-4052-9af1-ff6fb076055d", slug: "growth" },
          ],
          successUrl: "/billing?checkout=success&checkout_id={CHECKOUT_ID}",
          authenticatedUsersOnly: true,
        }),
        portal(),
        usage(),
        ...(process.env.POLAR_WEBHOOK_SECRET ? [webhooks({
          secret: process.env.POLAR_WEBHOOK_SECRET,
          onPayload: async (payload) => {
            console.log("[polar-webhook]", payload.type);
          },
        })] : []),
      ],
    })] : []),
    /**
     * Stripe — fallback billing provider (primary once Stripe Atlas completes).
     * Only initialized if STRIPE_SECRET_KEY is set.
     */
    ...(process.env.STRIPE_SECRET_KEY ? [stripe({
      stripeClient: new Stripe(process.env.STRIPE_SECRET_KEY, {
        apiVersion: "2026-02-25.clover",
      }),
      stripeWebhookSecret: process.env.STRIPE_WEBHOOK_SECRET!,
      createCustomerOnSignUp: true,
    })] : []),
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
      // Phone number plugin fields (migration 099)
      phoneNumber: {
        type: "string",
        required: false,
        fieldName: "phone_number",
      },
      phoneNumberVerified: {
        type: "boolean",
        required: false,
        fieldName: "phone_number_verified",
      },
      // Stripe plugin field (migration 099)
      stripeCustomerId: {
        type: "string",
        required: false,
        fieldName: "stripe_customer_id",
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
      credentialID: "credential_id",
      deviceType: "device_type",
      backedUp: "backed_up",
      createdAt: "created_at",
    },
  },
});

export type Session = typeof auth.$Infer.Session;
