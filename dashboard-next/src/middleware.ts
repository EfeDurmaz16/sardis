import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const hostname = request.headers.get("host") || "";

  // Consolidate: redirect dashboard.sardis.sh -> app.sardis.sh (same project)
  if (hostname === "dashboard.sardis.sh") {
    const url = new URL(request.url);
    url.hostname = "app.sardis.sh";
    url.host = "app.sardis.sh";
    return NextResponse.redirect(url, 301);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico).*)"],
};
