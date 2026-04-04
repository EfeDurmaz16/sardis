import { createAuthClient } from "better-auth/react";
import { jwtClient } from "better-auth/client/plugins";
import { passkeyClient } from "@better-auth/passkey/client";
import { apiKeyClient } from "@better-auth/api-key/client";

export const authClient = createAuthClient({
  // Use same-origin for auth requests — the Next.js app serves /api/auth/*
  // directly, so we must match the domain the user is on (dashboard.sardis.sh
  // OR app.sardis.sh) to avoid cross-origin CORS failures on get-session.
  baseURL: typeof window !== "undefined"
    ? window.location.origin
    : (process.env.NEXT_PUBLIC_APP_URL || "https://app.sardis.sh"),
  plugins: [jwtClient(), passkeyClient(), apiKeyClient()],
});

export const {
  signIn,
  signUp,
  signOut,
  useSession,
  getSession,
} = authClient;

// Compat: dashboard pages import useAuth which maps to useSession
export function useAuth() {
  const session = useSession();
  return {
    token: session.data?.session?.token || null,
    isAuthenticated: !!session.data,
    user: session.data?.user || null,
    needsOnboarding: false,
    login: async () => {},
    logout: signOut,
    completeOnboarding: () => {
      localStorage.setItem("sardis_onboarding_complete", "true");
    },
  };
}

// ---------------------------------------------------------------------------
// Agent Auth Protocol helpers
// ---------------------------------------------------------------------------

const SARDIS_API_URL =
  (process.env.NEXT_PUBLIC_SARDIS_API_URL || "https://api.sardis.sh").trim();

/** Fetch the Agent Auth discovery document from the API. */
export async function fetchAgentDiscovery() {
  const resp = await fetch(
    `${SARDIS_API_URL}/.well-known/agent-configuration`
  );
  if (!resp.ok) throw new Error("Failed to fetch agent discovery");
  return resp.json();
}

/** Register an agent via the Agent Auth Protocol. */
export async function registerAgent(
  apiKey: string,
  params: {
    agent_name: string;
    public_key: string;
    mode?: "delegated" | "autonomous";
    capabilities_requested?: string[];
  }
) {
  const resp = await fetch(`${SARDIS_API_URL}/api/v2/agent/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error("Agent registration failed");
  return resp.json();
}

/** Execute a capability on behalf of an agent. */
export async function executeCapability(
  apiKey: string,
  agentJwt: string | null,
  params: {
    capability: string;
    parameters: Record<string, unknown>;
  }
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-API-Key": apiKey,
  };
  if (agentJwt) {
    headers["X-Agent-JWT"] = agentJwt;
  }

  const resp = await fetch(`${SARDIS_API_URL}/api/v2/capability/execute`, {
    method: "POST",
    headers,
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new Error("Capability execution failed");
  return resp.json();
}
