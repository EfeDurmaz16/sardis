"use client"

// All Sardis API traffic from the browser MUST go through the same-origin
// /api/sardis proxy. The proxy mints a fresh better-auth JWT from the session
// cookie and forwards it to the upstream Sardis API. Calling api.sardis.sh
// directly from the browser does NOT work because:
//   1. The session cookie is HttpOnly — JS cannot read it to attach as a Bearer
//   2. CORS preflight on a different origin would require explicit allow-origin
//   3. No client-side path can mint a JWT — better-auth.api.getToken is server-only
// All requests use a relative URL so they hit the Next.js app on the same domain
// the user is on (dashboard.sardis.sh OR app.sardis.sh).
const PROXY_BASE = "/api/sardis"

export class ApiError extends Error {
  readonly statusCode: number

  constructor(message: string, statusCode: number) {
    super(message)
    this.name = "ApiError"
    this.statusCode = statusCode
  }
}

export class AuthRequiredError extends ApiError {
  constructor(message = "Authentication required") {
    super(message, 401)
    this.name = "AuthRequiredError"
  }
}

export type AgentApiRecord = {
  agent_id: string
  name: string
  description: string | null
  owner_id: string
  wallet_id: string | null
  spending_limits: {
    per_transaction?: string
    daily?: string
    monthly?: string
    total?: string
  }
  policy: Record<string, unknown>
  is_active: boolean
  kya_level: string
  kya_status: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
  next_steps?: string[]
}

export type WalletApiRecord = {
  wallet_id: string
  agent_id: string
  mpc_provider: string
  account_type: string
  addresses: Record<string, string>
  currency: string
  limit_per_tx: string
  limit_total: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type CreateAgentInput = {
  name: string
  description?: string
  spending_limits?: {
    per_transaction?: string
    daily?: string
    monthly?: string
    total?: string
  }
  metadata?: Record<string, unknown>
  create_wallet?: boolean
}

async function requestApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set("Accept", "application/json")

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  // The proxy reads the session cookie automatically — credentials: "include"
  // is required even for same-origin because Next.js can be served from a
  // different subdomain than where the cookie was set during sign-in.
  const response = await fetch(`${PROXY_BASE}/api/v2${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  })

  if (response.status === 401 || response.status === 403) {
    throw new AuthRequiredError()
  }

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => null) as { detail?: string; message?: string } | null
    const message = errorPayload?.detail || errorPayload?.message || `Request failed with HTTP ${response.status}`
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function listAgents() {
  return requestApi<AgentApiRecord[]>("/agents")
}

export function listWallets() {
  return requestApi<WalletApiRecord[]>("/wallets")
}

export function createAgent(input: CreateAgentInput) {
  return requestApi<AgentApiRecord>("/agents", {
    method: "POST",
    body: JSON.stringify(input),
  })
}
