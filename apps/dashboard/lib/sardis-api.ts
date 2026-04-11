"use client"

import { extractListOrThrow } from "@/lib/collection-response"

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
  initial_balance?: string
}

export type SpendingPolicyTemplateId = "conservative" | "balanced" | "developer"

export type SpendingPolicyTemplate = {
  id: SpendingPolicyTemplateId
  label: string
  description: string
  trust_level: "low" | "medium" | "high"
  spending_limits: {
    per_transaction: string
    daily: string
    monthly: string
    total: string
  }
}

// Mirrors DEFAULT_LIMITS in packages/sardis-core/src/sardis_v2_core/spending_policy.py.
// Do not invent new numbers — if you change these, update the backend too.
export const SPENDING_POLICY_TEMPLATES: SpendingPolicyTemplate[] = [
  {
    id: "conservative",
    label: "Conservative",
    description: "Tight caps. Good for production agents you are still learning to trust.",
    trust_level: "low",
    spending_limits: {
      per_transaction: "50.00",
      daily: "100.00",
      monthly: "1000.00",
      total: "5000.00",
    },
  },
  {
    id: "balanced",
    label: "Balanced",
    description: "Moderate caps for day-to-day agent operations.",
    trust_level: "medium",
    spending_limits: {
      per_transaction: "500.00",
      daily: "1000.00",
      monthly: "10000.00",
      total: "50000.00",
    },
  },
  {
    id: "developer",
    label: "Developer sandbox",
    description: "Low caps, sandbox only. Use this while you are integrating.",
    trust_level: "low",
    spending_limits: {
      per_transaction: "50.00",
      daily: "100.00",
      monthly: "1000.00",
      total: "5000.00",
    },
  },
]

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
  return requestApi<unknown>("/agents").then((payload) =>
    extractListOrThrow<AgentApiRecord>(payload, "Agents response"),
  )
}

export function listWallets() {
  return requestApi<unknown>("/wallets").then((payload) =>
    extractListOrThrow<WalletApiRecord>(payload, "Wallets response"),
  )
}

export function createAgent(input: CreateAgentInput) {
  return requestApi<AgentApiRecord>("/agents", {
    method: "POST",
    body: JSON.stringify(input),
  })
}

// ─── Onboarding wizard ────────────────────────────────────────────────────
// Mirror of packages/sardis-api/src/sardis_api/routers/me.py — keep step
// list in sync.
export const ONBOARDING_STEPS = [
  "profile",
  "api_key",
  "kyc",
  "agent_wallet",
  "spending_policy",
  "sandbox_payment",
  "tour_ready",
] as const

export type OnboardingStep = (typeof ONBOARDING_STEPS)[number]

export type OnboardingState = {
  org_id: string
  current_step: OnboardingStep
  completed_at: string | null
  metadata: Record<string, unknown> & { skipped?: OnboardingStep[] }
  steps: OnboardingStep[]
}

export type OnboardingPatch = {
  current_step?: OnboardingStep
  skipped?: OnboardingStep[]
  metadata_patch?: Record<string, unknown>
  mark_complete?: boolean
}

export function getOnboarding() {
  return requestApi<OnboardingState>("/me/onboarding")
}

export function updateOnboarding(patch: OnboardingPatch) {
  return requestApi<OnboardingState>("/me/onboarding", {
    method: "PATCH",
    body: JSON.stringify(patch),
  })
}

export type BootstrapApiKeyResponse = {
  key: string
  key_id: string
  key_prefix: string
  name: string
  mode: "test"
  created_at: string
}

export function bootstrapApiKey(name = "Default API key") {
  return requestApi<BootstrapApiKeyResponse>("/me/api-keys/bootstrap", {
    method: "POST",
    body: JSON.stringify({ name }),
  })
}

// ─── KYC (Didit) ──────────────────────────────────────────────────────────
// Backed by packages/sardis-api/src/sardis_api/routers/kyc_onboarding.py.
// Don't recreate these — they exist already and are used by the wider
// dashboard KYC pages.

export type KycStatus =
  | "not_started"
  | "pending"
  | "approved"
  | "declined"
  | "expired"
  | "needs_review"

export type KycStatusResponse = {
  status: KycStatus
  provider: string | null
  inquiry_id: string | null
  verified_at: string | null
  expires_at: string | null
  reason: string | null
  can_retry: boolean
}

export type KycInitiateResponse = {
  redirect_url: string | null
  session_token: string | null
  inquiry_id: string | null
  provider: string
  message: string
}

export function getKycStatus() {
  return requestApi<KycStatusResponse>("/kyc/status")
}

export function initiateKyc() {
  return requestApi<KycInitiateResponse>("/kyc/initiate", {
    method: "POST",
    body: JSON.stringify({}),
  })
}
