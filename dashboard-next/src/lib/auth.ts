import { betterAuth } from "better-auth";
import { jwt } from "better-auth/plugins";
import { Pool } from "pg";

export const auth = betterAuth({
  database: new Pool({
    connectionString: process.env.DATABASE_URL,
  }),
  baseURL: process.env.BETTER_AUTH_URL || "https://app.sardis.sh",
  secret: process.env.BETTER_AUTH_SECRET,
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
      jwks: { enabled: true },
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
    }),
  ],
  user: {
    additionalFields: {
      orgId: { type: "string", required: false },
      role: { type: "string", required: false, defaultValue: "user" },
      kycStatus: { type: "string", required: false, defaultValue: "not_started" },
      displayName: { type: "string", required: false },
    },
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // refresh daily
  },
  account: {
    accountLinking: {
      enabled: true,
      trustedProviders: ["google"],
    },
  },
  advanced: {
    database: {
      // Prefix tables to avoid conflicts with existing sardis tables
      tablePrefix: "ba_",
    },
  },
});

export type Session = typeof auth.$Infer.Session;
