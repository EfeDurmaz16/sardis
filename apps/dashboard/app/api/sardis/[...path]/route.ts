import { NextRequest } from "next/server"

import { proxyErrorResponse, sardisProxyResponse } from "@/utils/sardis-proxy"

async function forward(request: NextRequest) {
  const segments = request.nextUrl.pathname.replace(/^\/api\/sardis\//, "")
  const apiPath = `/${segments}${request.nextUrl.search}`

  try {
    const upstream = await sardisProxyResponse(apiPath, {
      method: request.method,
      body: request.method !== "GET" && request.method !== "HEAD" ? await request.text() : undefined,
    })

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
