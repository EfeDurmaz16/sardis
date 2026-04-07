import { NextRequest, NextResponse } from "next/server"

import { auth } from "@/lib/auth"
import { proxyErrorResponse, sardisProxyResponse } from "@/utils/sardis-proxy"

async function forward(request: NextRequest) {
  // ── Auth gate: mint a fresh JWT from the better-auth session cookie ──
  // better-auth sets an HttpOnly session cookie (__Secure-better-auth.session_token
  // in production, better-auth.session_token in dev). The Sardis API expects an
  // EdDSA JWT in `Authorization: Bearer ...` and validates it via JWKS. The JWT
  // plugin exposes `/api/auth/token` (auth.api.getToken) which mints a short-lived
  // JWT bound to the current session. We mint per-request because tokens are
  // 1h-scoped, the cost is one in-process call (no network), and per-request
  // minting keeps the proxy stateless.
  let userJwt: string
  try {
    const result = await auth.api.getToken({ headers: request.headers })
    userJwt = result.token
  } catch {
    return NextResponse.json(
      { error: "Unauthorized", detail: "No active session. Please sign in." },
      { status: 401 },
    )
  }

  const segments = request.nextUrl.pathname.replace(/^\/api\/sardis\//, "")
  const apiPath = `/${segments}${request.nextUrl.search}`

  try {
    const upstream = await sardisProxyResponse(
      apiPath,
      {
        method: request.method,
        body: request.method !== "GET" && request.method !== "HEAD" ? await request.text() : undefined,
      },
      { userJwt },
    )

    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "application/json",
        "Cache-Control": "no-store",
      },
    })
  } catch (error) {
    return proxyErrorResponse(error)
  }
}

export const GET = forward
export const POST = forward
export const PUT = forward
export const PATCH = forward
export const DELETE = forward
