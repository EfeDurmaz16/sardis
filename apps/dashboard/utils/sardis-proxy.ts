import "server-only"

import { headers as nextHeaders } from "next/headers"
import { NextResponse } from "next/server"

import { auth } from "@/lib/auth"

const DEFAULT_SARDIS_API_BASE_URL = "https://api.sardis.sh"

type SardisErrorPayload = {
  detail?: string
  error?: string
  message?: string
}

export class SardisProxyError extends Error {
  status: number
  payload: unknown

  constructor(message: string, status: number, payload: unknown) {
    super(message)
    this.name = "SardisProxyError"
    this.status = status
    this.payload = payload
  }
}

export function getSardisApiConfig() {
  const apiKey = process.env.SARDIS_API_KEY ?? ""

  return {
    apiKey,
    baseUrl: (process.env.SARDIS_API_BASE_URL || DEFAULT_SARDIS_API_BASE_URL).replace(/\/+$/, ""),
  }
}

function buildErrorMessage(status: number, payload: unknown): string {
  if (payload && typeof payload === "object") {
    const candidate = payload as SardisErrorPayload
    return candidate.detail || candidate.error || candidate.message || `Sardis API request failed with status ${status}`
  }
  if (typeof payload === "string" && payload.trim()) {
    return payload
  }
  return `Sardis API request failed with status ${status}`
}

export async function sardisProxyResponse(
  path: string,
  init: RequestInit = {},
  options?: { userJwt?: string },
): Promise<Response> {
  const { baseUrl } = getSardisApiConfig()
  const headers = new Headers(init.headers)

  // Resolve a user JWT in this order:
  //   1. Explicit `options.userJwt` (caller already minted one)
  //   2. better-auth `auth.api.getToken({ headers })` — pulls the
  //      HttpOnly session cookie from the inbound request via Next.js
  //      `headers()` and asks better-auth to issue a fresh EdDSA JWT
  //      bound to that session. This is what every dashboard route
  //      that calls sardisProxyFetch needs by default — without it,
  //      callers were forgetting to pass userJwt and hitting 401 in
  //      production (see 2026-04-08 incident).
  //   3. None — throw 401. We never fall back to SARDIS_API_KEY for
  //      user-facing requests because the server-side API key carries
  //      elevated privileges.
  let userJwt = options?.userJwt
  if (!userJwt) {
    try {
      const inboundHeaders = await nextHeaders()
      const result = await auth.api.getToken({ headers: inboundHeaders })
      userJwt = result?.token
    } catch {
      // Fall through to the 401 below.
    }
  }

  if (userJwt) {
    headers.set("Authorization", `Bearer ${userJwt}`)
  } else {
    throw new SardisProxyError(
      "Authentication required. No user session found.",
      401,
      { error: "authentication_required" },
    )
  }
  headers.set("Accept", "application/json")

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  })

  if (!response.ok) {
    const text = await response.text()
    const payload = text ? safeJsonParse(text) : null
    throw new SardisProxyError(buildErrorMessage(response.status, payload), response.status, payload)
  }

  return response
}

export async function sardisProxyFetch<T>(
  path: string,
  init: RequestInit = {},
  options?: { userJwt?: string },
): Promise<T> {
  const response = await sardisProxyResponse(path, init, options)

  const text = await response.text()
  const payload = text ? safeJsonParse(text) : null

  return payload as T
}

function safeJsonParse(input: string): unknown {
  try {
    return JSON.parse(input)
  } catch {
    return input
  }
}

export function proxyErrorResponse(error: unknown) {
  if (error instanceof SardisProxyError) {
    return NextResponse.json(
      {
        error: error.message,
        details: error.payload,
      },
      { status: error.status },
    )
  }

  const message = error instanceof Error ? error.message : "Unexpected dashboard proxy error"
  return NextResponse.json({ error: message }, { status: 500 })
}
