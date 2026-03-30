import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Public pages — no auth required (landing, docs, marketing, auth)
const PUBLIC_PREFIXES = [
  "/login", "/signup", "/forgot-password", "/reset-password",
  "/docs", "/pricing", "/enterprise", "/demo", "/playground",
  "/status", "/solutions",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hostname = request.headers.get("host") || "";

  // Consolidate: redirect dashboard.sardis.sh -> app.sardis.sh (same project)
  if (hostname === "dashboard.sardis.sh") {
    const url = new URL(request.url);
    url.hostname = "app.sardis.sh";
    url.host = "app.sardis.sh";
    return NextResponse.redirect(url, 301);
  }

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

  // Skip auth check in local dev
  if (process.env.NODE_ENV === "development") {
    return NextResponse.next();
  }

  // Check for any auth cookie
  const sessionToken =
    request.cookies.get("better-auth.session_token")?.value ||
    request.cookies.get("__Secure-better-auth.session_token")?.value ||
    request.cookies.get("sardis_session")?.value;

  if (!sessionToken) {
    // RSC prefetch requests — don't redirect, just pass through
    // (the page component will handle auth state client-side)
    const isRSC = request.headers.get("rsc") === "1" ||
      request.nextUrl.searchParams.has("_rsc");
    if (isRSC) {
      return NextResponse.next();
    }

    // Full page navigation without auth — redirect to login
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico).*)"],
};
