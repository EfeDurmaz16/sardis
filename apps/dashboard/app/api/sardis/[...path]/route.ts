import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

import { proxyErrorResponse, sardisProxyResponse } from "@/utils/sardis-proxy"

async function forward(request: NextRequest) {
  // ── Auth gate: require a valid session cookie before proxying ──
  const cookieStore = await cookies()
  const sessionToken =
    cookieStore.get("__Secure-better-auth.session_token")?.value ||
    cookieStore.get("better-auth.session_token")?.value ||
    cookieStore.get("sardis_session")?.value

  if (!sessionToken) {
    return NextResponse.json(
      { error: "Unauthorized", detail: "No active session. Please sign in." },
      { status: 401 },
    )
  }

  // Extract user JWT from sardis_session cookie for per-user auth
  const userJwt = cookieStore.get("sardis_session")?.value

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
