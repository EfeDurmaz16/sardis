import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Routes that don't require authentication */
const PUBLIC_PATHS = ["/login", "/signup", "/forgot-password", "/api/auth"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes, static assets, and Next.js internals
  if (
    isPublicPath(pathname) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/static") ||
    pathname === "/favicon.ico" ||
    pathname === "/icon.svg"
  ) {
    return NextResponse.next();
  }

  // NOTE: Middleware only checks cookie presence for routing decisions.
  // Actual token validation happens server-side on every API call.
  // This is acceptable because dashboard pages fetch data via authenticated API calls.
  const sessionToken =
    request.cookies.get("better-auth.session_token")?.value ||
    request.cookies.get("sardis_session")?.value;

  if (!sessionToken) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Best-effort JWT expiry check — if the token has three dot-separated
  // segments we can decode the payload and compare `exp` without a
  // crypto dependency.  An expired token still gets through to the API
  // which will reject it server-side, but redirecting early improves UX.
  if (sessionToken.split(".").length === 3) {
    try {
      const payload = JSON.parse(atob(sessionToken.split(".")[1]));
      if (typeof payload.exp === "number" && payload.exp * 1000 < Date.now()) {
        const loginUrl = new URL("/login", request.url);
        loginUrl.searchParams.set("callbackUrl", pathname);
        return NextResponse.redirect(loginUrl);
      }
    } catch {
      // Malformed token — let the API handle rejection
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico|icon.svg).*)"],
};
