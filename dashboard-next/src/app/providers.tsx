"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import posthog from "posthog-js";
import { usePathname, useSearchParams } from "next/navigation";
import { AuthRequiredError, NotFoundError } from "@/api/client";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Don't retry auth or 404 errors — suppress them silently
      retry: (failureCount, error) => {
        if (error instanceof AuthRequiredError) return false;
        if (error instanceof NotFoundError) return false;
        return failureCount < 1;
      },
      staleTime: 30_000,
    },
    mutations: {
      retry: false,
    },
  },
});

function PostHogPageView() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (pathname && posthog.__loaded) {
      let url = window.origin + pathname;
      const search = searchParams?.toString();
      if (search) url += `?${search}`;
      posthog.capture("$pageview", { $current_url: url });
    }
  }, [pathname, searchParams]);

  return null;
}

// In production, filter out known non-critical console errors so the browser
// console stays clean for end users and CSP/CORS noise doesn't obscure real bugs.
const SUPPRESSED_PATTERNS = [
  "Content Security Policy",
  "Refused to",
  "blocked by CORS",
  "Failed to load resource",
  "net::ERR_",
  "ERR_BLOCKED_BY_CSP",
  "posthog",
  "PostHog",
  "Authentication required",
  "Not found:",
  "get-session",
  // React Query internal — these fire on silenced AuthRequiredError / NotFoundError
  "Query data cannot be undefined",
];

if (
  typeof window !== "undefined" &&
  process.env.NODE_ENV === "production"
) {
  const origError = console.error.bind(console);
  console.error = (...args: unknown[]) => {
    const msg = args.map(String).join(" ");
    if (SUPPRESSED_PATTERNS.some((p) => msg.includes(p))) return;
    origError(...args);
  };

  const origWarn = console.warn.bind(console);
  console.warn = (...args: unknown[]) => {
    const msg = args.map(String).join(" ");
    if (SUPPRESSED_PATTERNS.some((p) => msg.includes(p))) return;
    origWarn(...args);
  };
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [phReady, setPhReady] = useState(false);

  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (key && !phReady) {
      posthog.init(key, {
        api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
        capture_pageview: false, // manual tracking via PostHogPageView
        loaded: () => setPhReady(true),
      });
    }
  }, [phReady]);

  return (
    <QueryClientProvider client={queryClient}>
      <PostHogPageView />
      {children}
    </QueryClientProvider>
  );
}
