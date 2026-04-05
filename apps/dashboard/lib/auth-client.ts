import { createAuthClient } from "better-auth/react";
import { jwtClient, magicLinkClient, oneTapClient, phoneNumberClient } from "better-auth/client/plugins";
import { passkeyClient } from "@better-auth/passkey/client";
import { apiKeyClient } from "@better-auth/api-key/client";

export const authClient = createAuthClient({
  // Use same-origin for auth requests — the Next.js app serves /api/auth/*
  // directly, so we must match the domain the user is on (dashboard.sardis.sh
  // OR app.sardis.sh) to avoid cross-origin CORS failures on get-session.
  baseURL: typeof window !== "undefined"
    ? window.location.origin
    : (process.env.NEXT_PUBLIC_APP_URL || "https://app.sardis.sh"),
  plugins: [
    jwtClient(),
    passkeyClient(),
    apiKeyClient(),
    magicLinkClient(),
    oneTapClient({
      clientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "",
    }),
    phoneNumberClient(),
    // polarClient() and stripeClient() disabled until env vars configured
  ],
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

