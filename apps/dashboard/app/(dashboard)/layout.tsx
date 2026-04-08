import { AppShell } from "@/components/app-shell"

// Every dashboard route is per-user and auth-gated. Pre-rendering them at
// build time has two problems:
//   1. The middleware redirects unauthenticated requests to /auth/sign-in,
//      so the prerendered HTML would always be a sign-in page anyway.
//   2. Pre-render workers try to invoke client-side data hooks during page
//      data collection. With no inbound request, fetch helpers receive
//      empty URLs and Next.js logs "TypeError: Invalid URL ... input: ''"
//      13 times per build (one per pre-rendered dashboard page) — pure
//      noise that masks real build failures.
// Forcing the segment dynamic skips static generation for the whole
// (dashboard) group in one place.
export const dynamic = "force-dynamic"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>
}
