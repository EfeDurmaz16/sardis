import "server-only"

import { NextResponse } from "next/server"

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

function getSardisApiConfig() {
  const apiKey = process.env.SARDIS_API_KEY
  if (!apiKey) {
    throw new SardisProxyError(
      "Dashboard API proxy is not configured. Set SARDIS_API_KEY for apps/dashboard.",
      503,
      { error: "dashboard_api_key_missing" },
    )
  }

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

export async function sardisProxyFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { apiKey, baseUrl } = getSardisApiConfig()
  const headers = new Headers(init.headers)

  headers.set("X-API-Key", apiKey)
  headers.set("Accept", "application/json")

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  })

  const text = await response.text()
  const payload = text ? safeJsonParse(text) : null

  if (!response.ok) {
    throw new SardisProxyError(buildErrorMessage(response.status, payload), response.status, payload)
  }

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
