"use client"

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").trim()

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

function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null
  }

  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null
  }

  return (
    window.localStorage.getItem("sardis_session") ||
    readCookie("better-auth.session_token") ||
    readCookie("sardis_session")
  )
}

async function requestApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE) {
    throw new ApiError("NEXT_PUBLIC_API_URL is not configured", 500)
  }

  const token = getStoredToken()
  if (!token) {
    throw new AuthRequiredError()
  }

  const headers = new Headers(init.headers)
  headers.set("Accept", "application/json")
  headers.set("Authorization", `Bearer ${token}`)

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(`${API_BASE}/api/v2${path}`, {
    ...init,
    headers,
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
