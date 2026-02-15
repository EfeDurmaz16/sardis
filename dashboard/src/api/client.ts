// API Client for Sardis Dashboard

import { getCurrentToken } from '../auth/AuthContext'
import type { Agent, Merchant, RiskScore, Transaction, Wallet, WebhookSubscription } from '../types'

// API base URL - can be overridden by environment variable
const API_URL = import.meta.env.VITE_API_URL || ''
const API_V1_BASE = `${API_URL}/api/v1`
const API_V2_BASE = `${API_URL}/api/v2`

type JsonObject = Record<string, unknown>

export interface AgentInstructionResponse {
  response?: string
  error?: string
  tool_call?: {
    name?: string
    arguments?: Record<string, unknown>
  }
  tx_id?: string
}


async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  useV2: boolean = false
): Promise<T> {
  const base = useV2 ? API_V2_BASE : API_V1_BASE
  const url = `${base}${endpoint}`

  const token = getCurrentToken()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(url, {
    headers: {
      ...headers,
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || error.message || `HTTP ${response.status}`)
  }

  return response.json()
}

// V2 API request helper
async function requestV2<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  return request<T>(endpoint, options, true)
}

// Agent APIs (V2)
export const agentApi = {
  list: () => requestV2<Agent[]>('/agents'),

  get: (agentId: string) => requestV2<Agent>(`/agents/${agentId}`),

  create: (data: {
    name: string
    description?: string
    spending_limits?: {
      per_transaction?: string
      total?: string
    }
    create_wallet?: boolean
  }) => requestV2<Agent>('/agents', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getWallet: (agentId: string) => requestV2<Wallet>(`/agents/${agentId}/wallet`),

  getTransactions: (agentId: string, limit = 50) =>
    requestV2<Transaction[]>(`/payments/agent/${agentId}?limit=${limit}`),

  instruct: (agentId: string, instruction: string) => requestV2<AgentInstructionResponse>(`/agents/${agentId}/instruct`, {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  }),
}

// Payment APIs (V2)
export const paymentApi = {
  estimate: (amount: string, currency = 'USDC') =>
    requestV2<JsonObject>(`/payments/estimate?amount=${amount}&currency=${currency}`),

  create: (data: {
    agent_id: string
    amount: string
    currency: string
    merchant_id?: string
    recipient_wallet_id?: string
    purpose?: string
  }) => requestV2<JsonObject>('/payments', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getHistory: (limit = 100) => requestV2<Transaction[]>(`/payments?limit=${limit}`),
}

// Merchant APIs (V2)
export const merchantApi = {
  list: () => requestV2<Merchant[]>('/merchants'),

  create: (data: {
    name: string
    description?: string
    category: string
  }) => requestV2<Merchant>('/merchants', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
}

// Webhook APIs (V2)
export const webhookApi = {
  list: () => requestV2<WebhookSubscription[]>('/webhooks'),

  create: (data: {
    url: string
    events: string[]
  }) => requestV2<WebhookSubscription>('/webhooks', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  update: (subscriptionId: string, data: Partial<{
    url: string
    events: string[]
    is_active: boolean
  }>) => requestV2<WebhookSubscription>(`/webhooks/${subscriptionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  delete: (subscriptionId: string) => requestV2<void>(`/webhooks/${subscriptionId}`, {
    method: 'DELETE',
  }),
}

// Risk APIs (V2)
export const riskApi = {
  getScore: (agentId: string) => requestV2<RiskScore>(`/risk/agents/${agentId}/score`),

  authorize: (agentId: string, serviceId: string) =>
    requestV2<JsonObject>(`/risk/agents/${agentId}/authorize`, {
      method: 'POST',
      body: JSON.stringify({ service_id: serviceId }),
    }),
}

// Health check - uses V2 API
export const healthApi = {
  check: () => requestV2<{ status: string; service: string; version: string; environment?: string }>('/health'),
  checkV1: () => request<{ status: string; service: string; version: string }>('/'),
}

// AP2 Payment APIs (V2 only)
export const ap2Api = {
  // Execute an AP2 payment bundle
  execute: (data: {
    mandate_chain: {
      intent?: JsonObject
      cart?: JsonObject
      payment: {
        mandate_id: string
        issuer: string
        subject: string
        destination: string
        amount_minor: number
        token: string
        expires_at: number
        proof?: JsonObject
      }
    }
  }) => requestV2<{
    status: string
    tx_id: string
    chain_tx_hash?: string
    audit_anchor?: string
  }>('/ap2/execute', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Verify a mandate without executing
  verify: (data: { mandate_chain: JsonObject }) => requestV2<{
    valid: boolean
    errors?: string[]
  }>('/mandates/verify', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
}

// Ledger APIs (V2 only)
export const ledgerApi = {
  // Get recent transactions
  recent: (limit = 50) => requestV2<JsonObject[]>(`/ledger/recent?limit=${limit}`),
}

// Transactions APIs (V2 only - chain operations)
export const transactionsApi = {
  // List supported chains
  chains: () => requestV2<{
    chains: Array<{
      name: string
      chain_id: number
      rpc_url: string
      explorer: string
      native_token: string
      supported_tokens: string[]
    }>
  }>('/transactions/chains'),

  // Estimate gas for a transfer
  estimateGas: (data: {
    chain?: string
    token?: string
    amount: string
    destination: string
  }) => requestV2<{
    gas_limit: number
    gas_price_gwei: string
    max_fee_gwei: string
    max_priority_fee_gwei: string
    estimated_cost_wei: number
    estimated_cost_eth: string
  }>('/transactions/estimate-gas', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Get transaction status
  status: (txHash: string, chain = 'base_sepolia') =>
    requestV2<{
      tx_hash: string
      chain: string
      status: string
      block_number?: number
      confirmations?: number
      explorer_url?: string
    }>(`/transactions/status/${txHash}?chain=${chain}`),

  // List tokens for a chain
  tokens: (chain: string) => requestV2<{
    chain: string
    tokens: Array<{ symbol: string; address: string }>
  }>(`/transactions/tokens/${chain}`),
}

// Webhooks APIs (V2 only)
export const webhooksApiV2 = {
  // List event types
  eventTypes: () => requestV2<{ event_types: string[] }>('/webhooks/event-types'),

  // Create a webhook subscription
  create: (data: {
    url: string
    events?: string[]
  }) => requestV2<{
    subscription_id: string
    url: string
    events: string[]
    secret: string
    is_active: boolean
    total_deliveries: number
    successful_deliveries: number
    failed_deliveries: number
  }>('/webhooks', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // List webhooks
  list: () => requestV2<JsonObject[]>('/webhooks'),

  // Get a webhook by ID
  get: (subscriptionId: string) => requestV2<JsonObject>(`/webhooks/${subscriptionId}`),

  // Update a webhook
  update: (subscriptionId: string, data: {
    url?: string
    events?: string[]
    is_active?: boolean
  }) => requestV2<JsonObject>(`/webhooks/${subscriptionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  // Delete a webhook
  delete: (subscriptionId: string) => requestV2<void>(`/webhooks/${subscriptionId}`, {
    method: 'DELETE',
  }),

  // Test a webhook
  test: (subscriptionId: string) => requestV2<{
    success: boolean
    status_code?: number
    error?: string
    duration_ms: number
  }>(`/webhooks/${subscriptionId}/test`, {
    method: 'POST',
  }),

  // List deliveries for a webhook
  deliveries: (subscriptionId: string, limit = 50) =>
    requestV2<JsonObject[]>(`/webhooks/${subscriptionId}/deliveries?limit=${limit}`),

  // Rotate webhook secret
  rotateSecret: (subscriptionId: string) => requestV2<JsonObject>(`/webhooks/${subscriptionId}/rotate-secret`, {
    method: 'POST',
  }),
}

// Holds APIs (V2 only - pre-authorization)
export const holdsApi = {
  // Create a hold
  create: (data: {
    wallet_id: string
    amount: string
    token?: string
    merchant_id?: string
    purpose?: string
    expiration_hours?: number
  }) => requestV2<{
    success: boolean
    hold?: JsonObject
    error?: string
  }>('/holds', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Get a hold by ID
  get: (holdId: string) => requestV2<JsonObject>(`/holds/${holdId}`),

  // Capture a hold
  capture: (holdId: string, amount?: string, txId?: string) => requestV2<{
    success: boolean
    hold?: JsonObject
    error?: string
  }>(`/holds/${holdId}/capture`, {
    method: 'POST',
    body: JSON.stringify({ amount, tx_id: txId }),
  }),

  // Void a hold
  void: (holdId: string) => requestV2<{
    success: boolean
    hold?: JsonObject
    error?: string
  }>(`/holds/${holdId}/void`, {
    method: 'POST',
  }),

  // List holds for a wallet
  listByWallet: (walletId: string, status?: string, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (status) params.append('status', status)
    return requestV2<JsonObject[]>(`/holds/wallet/${walletId}?${params}`)
  },

  // List all active holds
  listActive: (limit = 100) => requestV2<JsonObject[]>(`/holds?limit=${limit}`),
}

// Invoices APIs (V2 only)
export const invoicesApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.limit) searchParams.append('limit', String(params.limit))
    if (params?.offset) searchParams.append('offset', String(params.offset))
    return requestV2<JsonObject[]>(`/invoices?${searchParams}`)
  },

  get: (invoiceId: string) => requestV2<JsonObject>(`/invoices/${invoiceId}`),

  create: (data: {
    amount: string
    currency?: string
    description?: string
    merchant_name?: string
    payer_agent_id?: string
    reference?: string
  }) => requestV2<JsonObject>('/invoices', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateStatus: (invoiceId: string, status: string) =>
    requestV2<JsonObject>(`/invoices/${invoiceId}?status=${status}`, {
      method: 'PATCH',
    }),
}

// Marketplace APIs (V2 only - A2A service discovery)
export const marketplaceApi = {
  // List categories
  categories: () => requestV2<{
    categories: Array<{ value: string; name: string }>
  }>('/marketplace/categories'),

  // Create a service listing
  createService: (data: {
    name: string
    description: string
    category?: string
    tags?: string[]
    price_amount: string
    price_token?: string
    price_type?: string
  }) => requestV2<JsonObject>('/marketplace/services', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // List services
  listServices: (params?: {
    category?: string
    provider_id?: string
    limit?: number
  }) => {
    const searchParams = new URLSearchParams()
    if (params?.category) searchParams.append('category', params.category)
    if (params?.provider_id) searchParams.append('provider_id', params.provider_id)
    if (params?.limit) searchParams.append('limit', String(params.limit))
    return requestV2<JsonObject[]>(`/marketplace/services?${searchParams}`)
  },

  // Get a service
  getService: (serviceId: string) => requestV2<JsonObject>(`/marketplace/services/${serviceId}`),

  // Search services
  searchServices: (query: string, filters?: {
    category?: string
    min_rating?: string
    max_price?: string
  }) => requestV2<JsonObject[]>('/marketplace/services/search', {
    method: 'POST',
    body: JSON.stringify({ query, ...filters }),
  }),

  // Create an offer
  createOffer: (data: {
    service_id: string
    total_amount: string
    token?: string
    milestones?: Array<{ name: string; description: string; amount: string }>
  }) => requestV2<JsonObject>('/marketplace/offers', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // List offers
  listOffers: (params?: {
    role?: 'provider' | 'consumer' | 'any'
    status?: string
    limit?: number
  }) => {
    const searchParams = new URLSearchParams()
    if (params?.role) searchParams.append('role', params.role)
    if (params?.status) searchParams.append('status', params.status)
    if (params?.limit) searchParams.append('limit', String(params.limit))
    return requestV2<JsonObject[]>(`/marketplace/offers?${searchParams}`)
  },

  // Get an offer
  getOffer: (offerId: string) => requestV2<JsonObject>(`/marketplace/offers/${offerId}`),

  // Accept an offer
  acceptOffer: (offerId: string) => requestV2<JsonObject>(`/marketplace/offers/${offerId}/accept`, {
    method: 'POST',
  }),

  // Reject an offer
  rejectOffer: (offerId: string) => requestV2<JsonObject>(`/marketplace/offers/${offerId}/reject`, {
    method: 'POST',
  }),

  // Complete an offer
  completeOffer: (offerId: string) => requestV2<JsonObject>(`/marketplace/offers/${offerId}/complete`, {
    method: 'POST',
  }),

  // Create a review
  createReview: (offerId: string, data: {
    rating: number
    comment?: string
  }) => requestV2<JsonObject>(`/marketplace/offers/${offerId}/review`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // List reviews for a service
  listReviews: (serviceId: string, limit = 50) =>
    requestV2<JsonObject[]>(`/marketplace/services/${serviceId}/reviews?limit=${limit}`),
}

// Cards APIs (V2)
export const cardsApi = {
  list: (walletId: string) => requestV2<JsonObject[]>(`/cards?wallet_id=${walletId}`),

  get: (cardId: string) => requestV2<JsonObject>(`/cards/${cardId}`),

  issue: (data: {
    wallet_id: string
    card_type?: string
    limit_per_tx?: string
    limit_daily?: string
    limit_monthly?: string
  }) => requestV2<JsonObject>('/cards', {
    method: 'POST',
    body: JSON.stringify({
      card_type: 'multi_use',
      limit_per_tx: '100.00',
      limit_daily: '500.00',
      limit_monthly: '2000.00',
      ...data,
    }),
  }),

  freeze: (cardId: string) => requestV2<JsonObject>(`/cards/${cardId}/freeze`, { method: 'POST' }),

  unfreeze: (cardId: string) => requestV2<JsonObject>(`/cards/${cardId}/unfreeze`, { method: 'POST' }),

  cancel: (cardId: string) => requestV2<void>(`/cards/${cardId}`, { method: 'DELETE' }),

  simulatePurchase: (cardId: string, data: {
    amount: string
    currency?: string
    merchant_name?: string
    mcc_code?: string
  }) => requestV2<JsonObject>(`/cards/${cardId}/simulate-purchase`, {
    method: 'POST',
    body: JSON.stringify({
      currency: 'USD',
      merchant_name: 'Demo Merchant',
      mcc_code: '5734',
      ...data,
    }),
  }),

  listTransactions: (cardId: string, limit = 50) =>
    requestV2<JsonObject[]>(`/cards/${cardId}/transactions?limit=${limit}`),
}

// Treasury Ops APIs (V2 only - operator controls)
export const treasuryOpsApi = {
  listJourneys: (params?: {
    rail?: string
    canonical_state?: string
    break_status?: string
    limit?: number
  }) => {
    const search = new URLSearchParams()
    if (params?.rail) search.append('rail', params.rail)
    if (params?.canonical_state) search.append('canonical_state', params.canonical_state)
    if (params?.break_status) search.append('break_status', params.break_status)
    if (params?.limit) search.append('limit', String(params.limit))
    return requestV2<{ items: JsonObject[]; count: number }>(`/treasury/ops/journeys?${search}`)
  },

  listDrift: (status_value = 'open', limit = 100) =>
    requestV2<{ items: JsonObject[]; count: number }>(
      `/treasury/ops/drift?status_value=${encodeURIComponent(status_value)}&limit=${limit}`
    ),

  listReturns: (codes = 'R01,R09,R29', limit = 200) =>
    requestV2<{ items: JsonObject[]; count: number; codes: string[] }>(
      `/treasury/ops/returns?codes=${encodeURIComponent(codes)}&limit=${limit}`
    ),

  listManualReviews: (status_value = 'queued', limit = 100) =>
    requestV2<{ items: JsonObject[]; count: number }>(
      `/treasury/ops/manual-reviews?status_value=${encodeURIComponent(status_value)}&limit=${limit}`
    ),

  resolveManualReview: (reviewId: string, data: { status: 'in_review' | 'resolved' | 'dismissed'; notes?: string }) =>
    requestV2<JsonObject>(`/treasury/ops/manual-reviews/${reviewId}/resolve`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  exportAuditEvidence: (journeyId?: string, limit = 500) => {
    const search = new URLSearchParams()
    search.append('format', 'json')
    search.append('limit', String(limit))
    if (journeyId) search.append('journey_id', journeyId)
    return requestV2<JsonObject>(`/treasury/ops/audit-evidence/export?${search}`)
  },
}

// Demo APIs (V2)
export const demoApi = {
  bootstrapApiKey: (data: {
    name?: string
    scopes?: string[]
    rate_limit?: number
    expires_in_days?: number | null
    organization_id?: string | null
  }) =>
    requestV2<{
      key: string
      key_id: string
      key_prefix: string
      organization_id: string
      scopes: string[]
      rate_limit: number
      expires_at?: string | null
    }>('/auth/bootstrap-api-key', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createWallet: (data: {
    agent_id: string
    mpc_provider?: string
    currency?: string
    limit_per_tx?: string
    limit_total?: string
    wallet_name?: string
  }) =>
    requestV2<JsonObject>('/wallets', {
      method: 'POST',
      body: JSON.stringify({
        mpc_provider: 'turnkey',
        currency: 'USDC',
        limit_per_tx: '100.00',
        limit_total: '1000.00',
        ...data,
      }),
    }),

  applyPolicy: (data: { agent_id: string; natural_language: string }) =>
    requestV2<JsonObject>('/policies/apply', {
      method: 'POST',
      body: JSON.stringify({ ...data, confirm: true }),
    }),

  getPolicy: (agentId: string) => requestV2<JsonObject>(`/policies/${agentId}`),

  checkPolicy: (data: {
    agent_id: string
    amount: string
    currency?: string
    merchant_id?: string
    mcc_code?: string
  }) =>
    requestV2<{ allowed: boolean; reason: string; policy_id?: string }>('/policies/check', {
      method: 'POST',
      body: JSON.stringify({
        currency: 'USD',
        ...data,
      }),
    }),

  issueCard: (data: { wallet_id: string; limit_per_tx?: string; limit_daily?: string; limit_monthly?: string }) =>
    requestV2<JsonObject>('/cards', {
      method: 'POST',
      body: JSON.stringify({
        limit_per_tx: '100.00',
        limit_daily: '500.00',
        limit_monthly: '2000.00',
        ...data,
      }),
    }),

  simulatePurchase: (cardId: string, data: { amount: string; currency?: string; merchant_name?: string; mcc_code?: string }) =>
    requestV2<JsonObject>(`/cards/${cardId}/simulate-purchase`, {
      method: 'POST',
      body: JSON.stringify({
        currency: 'USD',
        merchant_name: 'Demo Merchant',
        mcc_code: '5734',
        ...data,
      }),
    }),

  listCardTransactions: (cardId: string, limit = 50) =>
    requestV2<JsonObject[]>(`/cards/${cardId}/transactions?limit=${limit}`),
}
