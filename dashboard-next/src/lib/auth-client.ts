import { createAuthClient } from "better-auth/react";
import { jwtClient } from "better-auth/client/plugins";
// TODO: Add passkeyClient(), magicLinkClient() after installing deps

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL || "https://app.sardis.sh",
  plugins: [jwtClient()],
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
