"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import posthog from "posthog-js";
import { usePathname, useSearchParams } from "next/navigation";
import { AuthRequiredError } from "@/api/client";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      // Don't retry auth errors — the user simply isn't logged in
      retry: (failureCount, error) => {
        if (error instanceof AuthRequiredError) return false;
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
