import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Public pages — no auth required (landing, docs, marketing, auth)
const PUBLIC_PREFIXES = [
  "/login", "/signup", "/forgot-password", "/reset-password",
  "/docs", "/pricing", "/enterprise", "/demo", "/playground",
  "/status", "/solutions",
];

// Dashboard pages — require auth
const DASHBOARD_PREFIXES = [
  "/overview", "/agents", "/mandates", "/transactions", "/policies",
  "/policy-manager", "/api-keys", "/go-live", "/cards", "/analytics",
  "/settings", "/billing", "/webhooks", "/onboarding",
  "/control-center", "/approvals", "/kill-switch", "/evidence",
  "/anomaly", "/simulation", "/reconciliation", "/merchants",
  "/mpp-sessions", "/stripe-issuing", "/enterprise-support",
  "/environment-templates", "/workflow-templates", "/holds",
  "/invoices", "/alert-preferences", "/agent-identity",
  "/agent-observability", "/guardrails", "/confidence-router",
  "/audit-anchors", "/goal-drift", "/policy-analytics",
  "/policy-playground", "/policy-management", "/checkout-controls",
  "/provider-health", "/counterparties", "/fallback-rules",
  "/live-events", "/approval-config", "/exceptions",
  "/webhook-manager",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow API routes (better-auth + Next.js internal)
  if (pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  // Allow static assets
  if (pathname.startsWith("/_next/") || pathname.startsWith("/static/") || pathname === "/favicon.ico" || pathname === "/robots.txt" || pathname === "/sitemap.xml") {
    return NextResponse.next();
  }

  // Root path (/) is the landing page — always public
  if (pathname === "/") {
    return NextResponse.next();
  }

  // Public pages — no auth needed
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Dashboard pages — require auth
  if (DASHBOARD_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    const sessionToken =
      request.cookies.get("better-auth.session_token")?.value ||
      request.cookies.get("__Secure-better-auth.session_token")?.value;

    if (!sessionToken) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico).*)"],
};
