// API Client for Sardis Dashboard (Next.js / better-auth)

import type { Agent, Merchant, Transaction, Wallet, WebhookSubscription } from '../types'

// RiskScore is used in client but may not be in types
type RiskScore = { score: number; level: string; factors: string[] }

// Token cache — fetches JWT from better-auth session endpoint
let _cachedToken: string | null = null;
let _tokenExpiry = 0;

function getCurrentToken(): string | null {
  // Synchronous getter for cached token (used in request headers)
  if (_cachedToken && Date.now() < _tokenExpiry) return _cachedToken;
  return null;
}

export async function refreshToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/token", { credentials: "include" });
    if (!res.ok) return null;
    const data = await res.json();
    _cachedToken = data.token || null;
    _tokenExpiry = Date.now() + 50 * 60 * 1000; // 50 min cache
    return _cachedToken;
  } catch {
    return null;
  }
}

// API base URL - can be overridden by environment variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || ''
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

export interface EnterpriseSupportProfile {
  organization_id: string
  plan: 'free' | 'pro' | 'enterprise'
  first_response_sla_minutes: number
  resolution_sla_hours: number
  channels: string[]
  pager: boolean
}

export interface EnterpriseSupportTicket {
  id: string
  organization_id: string
  requester_id: string
  requester_kind: string
  subject: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  category: 'payments' | 'compliance' | 'infrastructure' | 'cards' | 'other'
  status: 'open' | 'acknowledged' | 'resolved' | 'closed'
  first_response_due_at: string
  resolution_due_at: string
  acknowledged_at?: string | null
  resolved_at?: string | null
  response_sla_breached: boolean
  resolution_sla_breached: boolean
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type ApprovalStatus = 'pending' | 'approved' | 'denied' | 'expired' | 'cancelled'
export type ApprovalUrgency = 'low' | 'medium' | 'high'

export interface ApprovalRecord {
  id: string
  action: string
  status: ApprovalStatus
  urgency: ApprovalUrgency
  requested_by: string
  reviewed_by: string | null
  created_at: string
  reviewed_at: string | null
  expires_at: string
  vendor: string | null
  amount: string | null
  purpose: string | null
  reason: string | null
  card_limit: string | null
  agent_id: string | null
  wallet_id: string | null
  organization_id: string | null
  metadata: Record<string, unknown>
}

export interface ApprovalListResponse {
  approvals: ApprovalRecord[]
  total: number
  limit: number
  offset: number
}

export interface ActivePolicyRecord {
  agent_id: string
  policy_id: string
  trust_level: string
  limit_per_tx: string
  limit_total: string
  daily_limit: string | null
  weekly_limit: string | null
  monthly_limit: string | null
  approval_threshold: string | null
  blocked_merchant_categories: string[]
  allowed_chains: string[]
  allowed_tokens: string[]
  allowed_destination_addresses: string[]
  blocked_destination_addresses: string[]
  merchant_rules_count: number
  require_preauth: boolean
}

export interface PolicyHistoryCommit {
  commit_hash: string
  created_at: string | null
  signed: boolean
  signer_did: string | null
}

export interface PolicyHistoryListResponse {
  agent_id: string
  commits: PolicyHistoryCommit[]
  count: number
}

export interface PolicyHistoryDetailResponse {
  agent_id: string
  commit_hash: string
  policy: JsonObject
}


async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  useV2: boolean = false
): Promise<T> {
  const base = useV2 ? API_V2_BASE : API_V1_BASE
  const url = `${base}${endpoint}`

  // Get token — try cache first, refresh if expired
  let token = getCurrentToken()
  if (!token) {
    token = await refreshToken()
  }

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

// Enterprise Support APIs (V2 only)
export const enterpriseSupportApi = {
  profile: () => requestV2<EnterpriseSupportProfile>('/enterprise/support/profile'),

  listTickets: (params?: {
    status_filter?: 'open' | 'acknowledged' | 'resolved' | 'closed'
    priority?: 'low' | 'medium' | 'high' | 'urgent'
    limit?: number
    offset?: number
  }) => {
    const search = new URLSearchParams()
    if (params?.status_filter) search.set('status_filter', params.status_filter)
    if (params?.priority) search.set('priority', params.priority)
    if (typeof params?.limit === 'number') search.set('limit', String(params.limit))
    if (typeof params?.offset === 'number') search.set('offset', String(params.offset))
    const query = search.toString()
    const suffix = query ? `?${query}` : ''
    return requestV2<EnterpriseSupportTicket[]>(`/enterprise/support/tickets${suffix}`)
  },

  createTicket: (data: {
    subject: string
    description: string
    priority?: 'low' | 'medium' | 'high' | 'urgent'
    category?: 'payments' | 'compliance' | 'infrastructure' | 'cards' | 'other'
    metadata?: Record<string, unknown>
  }) => requestV2<EnterpriseSupportTicket>('/enterprise/support/tickets', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  acknowledgeTicket: (ticketId: string) =>
    requestV2<EnterpriseSupportTicket>(`/enterprise/support/tickets/${ticketId}/acknowledge`, {
      method: 'POST',
    }),

  resolveTicket: (ticketId: string, resolution_note?: string) =>
    requestV2<EnterpriseSupportTicket>(`/enterprise/support/tickets/${ticketId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_note }),
    }),
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
    cardholder_name?: string
    cardholder_email?: string
    cardholder_phone?: string
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

  getEphemeralKey: (cardId: string) =>
    requestV2<{ ephemeral_key_secret: string; nonce: string }>(`/cards/${cardId}/ephemeral-key`, { method: 'POST' }),

  revealCard: (cardId: string) =>
    requestV2<{ card_number: string; cvc: string; exp_month: number; exp_year: number; last4: string; brand: string; status: string }>(`/cards/${cardId}/reveal`, { method: 'POST' }),

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

// Kill Switch APIs (V2 - admin router)
export const killSwitchApi = {
  status: () => requestV2<{
    global: Record<string, unknown> | null
    organizations: Record<string, unknown>
    agents: Record<string, unknown>
    rails: Record<string, unknown>
    chains: Record<string, unknown>
  }>('/admin/kill-switch/status'),

  activateRail: (rail: string, data: { reason: string; notes?: string; auto_reactivate_after_seconds?: number }) =>
    requestV2<JsonObject>(`/admin/kill-switch/rail/${rail}/activate`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deactivateRail: (rail: string) =>
    requestV2<JsonObject>(`/admin/kill-switch/rail/${rail}/deactivate`, { method: 'POST' }),

  activateChain: (chain: string, data: { reason: string; notes?: string; auto_reactivate_after_seconds?: number }) =>
    requestV2<JsonObject>(`/admin/kill-switch/chain/${chain}/activate`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deactivateChain: (chain: string) =>
    requestV2<JsonObject>(`/admin/kill-switch/chain/${chain}/deactivate`, { method: 'POST' }),
}

// Approvals APIs (V2)
export const approvalsApi = {
  listPending: () => requestV2<ApprovalListResponse>('/approvals/pending'),

  list: (params?: { status?: string; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.status) search.set('status', params.status)
    if (params?.limit) search.set('limit', String(params.limit))
    const q = search.toString()
    return requestV2<ApprovalListResponse>(`/approvals${q ? `?${q}` : ''}`)
  },

  get: (approvalId: string) => requestV2<ApprovalRecord>(`/approvals/${approvalId}`),

  approve: (approvalId: string, data?: { notes?: string; reviewed_by?: string }) =>
    requestV2<JsonObject>(`/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ reviewed_by: data?.reviewed_by ?? 'dashboard', reason: data?.notes }),
    }),

  deny: (approvalId: string, data?: { reason?: string; reviewed_by?: string }) =>
    requestV2<JsonObject>(`/approvals/${approvalId}/deny`, {
      method: 'POST',
      body: JSON.stringify({ reviewed_by: data?.reviewed_by ?? 'dashboard', reason: data?.reason }),
    }),
}

// Evidence APIs (V2)
export const evidenceApi = {
  getTransactionEvidence: (txId: string) =>
    requestV2<JsonObject>(`/evidence/transactions/${txId}`),

  listPolicyDecisions: (agentId: string, params?: { limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.limit) search.set('limit', String(params.limit))
    const q = search.toString()
    return requestV2<JsonObject[]>(`/evidence/decisions/${agentId}${q ? `?${q}` : ''}`)
  },

  getPolicyDecisionDetail: (agentId: string, decisionId: string) =>
    requestV2<JsonObject>(`/evidence/decisions/${agentId}/${decisionId}`),

  exportPolicyDecision: (agentId: string, decisionId: string) =>
    requestV2<JsonObject>(`/evidence/decisions/${agentId}/${decisionId}/export`),

  exportBundle: (txId: string) =>
    requestV2<JsonObject>(`/evidence/export/${txId}`, { method: 'POST' }),

  verifyBundle: (data: { tx_id: string; content_hash: string; signature: string }) =>
    requestV2<{ valid: boolean; message: string; verified_at: string }>('/evidence/export/verify', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  downloadBundleUrl: (txId: string) =>
    `${API_URL}/api/v2/evidence/export/${txId}/download`,
}

// Live simulation — dry-run through the full control-plane pipeline (V2)
export const simulationApi = {
  simulate: (data: {
    amount: string
    currency?: string
    chain?: string
    /** Agent initiating the payment — maps to sender_agent_id in the API */
    sender_agent_id: string
    sender_wallet_id?: string
    recipient_wallet_id?: string
    recipient_address?: string
    source?: string
  }) =>
    requestV2<{
      intent_id: string
      would_succeed: boolean
      failure_reasons: string[]
      policy_result: JsonObject | null
      compliance_result: JsonObject | null
      cap_check: JsonObject | null
      kill_switch_status: JsonObject | null
    }>('/simulate', {
      method: 'POST',
      body: JSON.stringify({ currency: 'USDC', chain: 'base', source: 'ap2', ...data }),
    }),
}

// Draft policy testing — what-if analysis against a policy definition without executing (V2)
export const policyTestApi = {
  testDraft: (data: {
    amount: string
    currency?: string
    chain?: string
    agent_id?: string
    merchant_id?: string
    merchant_category?: string
    mcc_code?: string
    scope?: string
    /** Optional inline policy definition to test against instead of the agent's active policy */
    definition?: {
      version?: string
      rules: Array<{ type: string; params?: Record<string, unknown> }>
      metadata?: Record<string, unknown>
    }
  }) =>
    requestV2<{
      intent_id: string
      would_succeed: boolean
      failure_reasons: string[]
      policy_result: (JsonObject & { verdict?: string; reason?: string }) | null
      compliance_result: JsonObject | null
    }>('/policies/simulate', {
      method: 'POST',
      body: JSON.stringify({ currency: 'USDC', chain: 'base', ...data }),
    }),
}

// Exceptions APIs (V2)
export interface ExceptionRecord {
  id: string
  transaction_id: string
  agent_id: string
  exception_type: string
  status: string
  strategy: string
  retry_count: number
  max_retries: number
  metadata: Record<string, unknown>
  created_at: string
  resolved_at: string | null
  resolution_notes: string | null
  resolved_by: string | null
  description: string
}

interface RawExceptionResponse {
  exception_id: string
  transaction_id: string
  agent_id: string
  exception_type: string
  status: string
  description: string
  retry_count: number
  max_retries: number
  suggested_strategy: string | null
  resolution_notes: string | null
  resolved_at: string | null
  resolved_by: string | null
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}

function normalizeExceptionRecord(raw: RawExceptionResponse): ExceptionRecord {
  return {
    id: raw.exception_id,
    transaction_id: raw.transaction_id,
    agent_id: raw.agent_id,
    exception_type: raw.exception_type.toUpperCase(),
    status: raw.status.toUpperCase(),
    strategy: (raw.suggested_strategy ?? 'manual_review').toUpperCase(),
    retry_count: raw.retry_count,
    max_retries: raw.max_retries,
    metadata: raw.metadata ?? {},
    created_at: raw.created_at,
    resolved_at: raw.resolved_at,
    resolution_notes: raw.resolution_notes,
    resolved_by: raw.resolved_by,
    description: raw.description,
  }
}

export const exceptionsApi = {
  list: (params?: { agent_id?: string; status?: string; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.agent_id) search.set('agent_id', params.agent_id)
    if (params?.status) search.set('status', params.status)
    if (params?.limit) search.set('limit', String(params.limit))
    const q = search.toString()
    return requestV2<RawExceptionResponse[]>(`/exceptions${q ? `?${q}` : ''}`)
      .then((items) => items.map(normalizeExceptionRecord))
  },

  get: (exceptionId: string) =>
    requestV2<RawExceptionResponse>(`/exceptions/${exceptionId}`)
      .then(normalizeExceptionRecord),

  resolve: (exceptionId: string, data: { resolution_notes?: string }) =>
    requestV2<RawExceptionResponse>(`/exceptions/${exceptionId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({
        notes: data.resolution_notes,
        resolved_by: 'dashboard',
      }),
    }).then(normalizeExceptionRecord),

  escalate: (exceptionId: string, data?: { notes?: string }) =>
    requestV2<RawExceptionResponse>(`/exceptions/${exceptionId}/escalate`, {
      method: 'POST',
      body: JSON.stringify({
        reason: data?.notes ?? 'Escalated from dashboard',
      }),
    }).then(normalizeExceptionRecord),

  retry: (exceptionId: string) =>
    requestV2<RawExceptionResponse>(`/exceptions/${exceptionId}/retry`, {
      method: 'POST',
      body: JSON.stringify({}),
    }).then(normalizeExceptionRecord),
}

// Retry Policy APIs (V2)
export const retryPolicyApi = {
  listRetryPolicies: () => requestV2<JsonObject[]>('/exceptions/retry-policies'),

  createRetryPolicy: (data: {
    name: string
    exception_type: string
    max_retries?: number
    retry_delay_seconds?: number
    backoff_multiplier?: number
    fallback_action?: string
    fallback_rail?: string | null
    enabled?: boolean
    audit_trail?: boolean
    safeguards?: Record<string, unknown>
  }) =>
    requestV2<JsonObject>('/exceptions/retry-policies', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateRetryPolicy: (id: string, data: {
    name: string
    exception_type: string
    max_retries?: number
    retry_delay_seconds?: number
    backoff_multiplier?: number
    fallback_action?: string
    fallback_rail?: string | null
    enabled?: boolean
    audit_trail?: boolean
    safeguards?: Record<string, unknown>
  }) =>
    requestV2<JsonObject>(`/exceptions/retry-policies/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteRetryPolicy: (id: string) =>
    requestV2<void>(`/exceptions/retry-policies/${id}`, { method: 'DELETE' }),
}

// Policies APIs (V2)
export const policiesApi = {
  parse: (data: { natural_language: string }) =>
    requestV2<JsonObject>('/policies/parse', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  preview: (data: { agent_id: string; natural_language: string }) =>
    requestV2<JsonObject>('/policies/preview', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  apply: (data: { agent_id: string; natural_language: string; confirm?: boolean }) =>
    requestV2<JsonObject>('/policies/apply', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  get: (agentId: string) => requestV2<ActivePolicyRecord>(`/policies/${agentId}`),

  history: (agentId: string, limit = 20) =>
    requestV2<PolicyHistoryListResponse>(`/policies/${agentId}/history?limit=${limit}`),

  getHistoryVersion: (agentId: string, commitHash: string) =>
    requestV2<PolicyHistoryDetailResponse>(`/policies/${agentId}/history/${commitHash}`),

  check: (data: {
    agent_id: string
    amount: string
    currency?: string
    merchant_id?: string
    mcc_code?: string
  }) =>
    requestV2<{ allowed: boolean; reason: string; policy_id?: string }>('/policies/check', {
      method: 'POST',
      body: JSON.stringify({ currency: 'USD', ...data }),
    }),
}

// Wallets APIs (V2)
export const walletsApi = {
  list: () => requestV2<JsonObject[]>('/wallets'),

  get: (walletId: string) => requestV2<JsonObject>(`/wallets/${walletId}`),
}

// Anomaly APIs (V2)
export const anomalyApi = {
  assess: (data: { agent_id: string; amount: string; merchant_id?: string; mcc_code?: string }) =>
    requestV2<JsonObject>('/anomaly/assess', { method: 'POST', body: JSON.stringify(data) }),

  events: (params?: { agent_id?: string; min_score?: number; action?: string; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.agent_id) search.set('agent_id', params.agent_id)
    if (params?.min_score) search.set('min_score', String(params.min_score))
    if (params?.action) search.set('action', params.action)
    if (params?.limit) search.set('limit', String(params.limit))
    const q = search.toString()
    return requestV2<JsonObject[]>(`/anomaly/events${q ? `?${q}` : ''}`)
  },

  config: () => requestV2<JsonObject>('/anomaly/config'),

  updateConfig: (data: { thresholds?: Record<string, number>; signal_weights?: Record<string, number> }) =>
    requestV2<JsonObject>('/anomaly/config', { method: 'PUT', body: JSON.stringify(data) }),
}

// Billing APIs (V2)
export interface BillingUsage {
  api_calls_used: number
  api_calls_limit: number | null
  tx_volume_cents: number
  tx_volume_limit_cents: number | null
  agents_used: number
  agents_limit: number | null
}

export interface BillingAccount {
  plan: string
  status: string
  usage: BillingUsage
}

export const billingApi = {
  account: () => requestV2<BillingAccount>('/billing/account'),
}

// Workflow Templates APIs (V2)
export const templatesApi = {
  list: () => requestV2<JsonObject[]>('/templates/'),
  get: (id: string) => requestV2<JsonObject>(`/templates/${id}`),
}

// Environment Templates APIs (V2)
export interface ProviderConfig {
  name: string
  required: boolean
  env_var: string
  status: string
  docs_url: string
}

export interface EnvironmentTemplate {
  id: string
  name: string
  description: string
  lane: string
  providers: ProviderConfig[]
  env_vars: Record<string, string>
  policy_defaults: string
  safety_defaults: Record<string, unknown>
  recommended_for: string[]
}

export const environmentTemplatesApi = {
  list: () => requestV2<EnvironmentTemplate[]>('/environments/'),
  get: (id: string) => requestV2<EnvironmentTemplate>(`/environments/${id}`),
}

// Counterparties APIs (V2)
export interface Counterparty {
  id: string
  name: string
  type: string
  identifier: string
  category: string | null
  trust_status: string
  approval_required: boolean
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CounterpartyTrustProfile {
  counterparty_id: string
  name: string
  trust_score: number
  policy_compatible: boolean
  proof_status: 'verified' | 'partial' | 'none'
  settlement_preference: string
  total_transactions: number
  total_volume: string
  success_rate: number
  avg_settlement_time: string
  last_transaction: string | null
  flags: string[]
}

export const counterpartiesApi = {
  list: (params?: { type?: string; trust_status?: string; limit?: number }) => {
    const search = new URLSearchParams()
    if (params?.type) search.set('type', params.type)
    if (params?.trust_status) search.set('trust_status', params.trust_status)
    if (params?.limit) search.set('limit', String(params.limit))
    const q = search.toString()
    return requestV2<Counterparty[]>(`/counterparties${q ? `?${q}` : ''}`)
  },

  get: (id: string) => requestV2<Counterparty>(`/counterparties/${id}`),

  getTrustProfile: (id: string) =>
    requestV2<CounterpartyTrustProfile>(`/counterparties/${id}/trust-profile`),

  create: (data: {
    name: string
    type?: string
    identifier: string
    category?: string
    trust_status?: string
    approval_required?: boolean
    metadata?: Record<string, unknown>
  }) =>
    requestV2<Counterparty>('/counterparties/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: {
    name?: string
    trust_status?: string
    approval_required?: boolean
    category?: string
    metadata?: Record<string, unknown>
  }) =>
    requestV2<Counterparty>(`/counterparties/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    requestV2<void>(`/counterparties/${id}`, { method: 'DELETE' }),
}

// Policy Analytics APIs (V2)
export interface PolicyAnalyticsSummary {
  total_checks: number
  allowed: number
  denied: number
  escalated: number
  allow_rate: number
  deny_rate: number
  escalation_rate: number
}

export interface PolicyAnalyticsDailyOutcome {
  date: string
  allowed: number
  denied: number
  escalated: number
}

export interface PolicyAnalyticsDenyReason {
  reason: string
  count: number
  pct_of_denials: number
  trend: 'up' | 'down' | 'flat'
}

export interface PolicyAnalyticsVersionImpact {
  version: string
  policy_version_id: string
  agent_id: string
  deployed_at: string
  label: string
  deny_rate_before: number
  deny_rate_after: number
  escalation_rate_before: number
  escalation_rate_after: number
}

export interface PolicyAnalyticsSuggestion {
  id: string
  severity: 'info' | 'warn' | 'action'
  title: string
  body: string
  action_label?: string
}

export interface PolicyAnalyticsOutcomesResponse {
  summary_24h: PolicyAnalyticsSummary
  summary_7d: PolicyAnalyticsSummary
  summary_30d: PolicyAnalyticsSummary
  daily_outcomes: PolicyAnalyticsDailyOutcome[]
  policy_versions: PolicyAnalyticsVersionImpact[]
}

export const policyAnalyticsApi = {
  getOutcomes: (params?: { period?: string }) => {
    const search = new URLSearchParams()
    if (params?.period) search.set('period', params.period)
    const q = search.toString()
    return requestV2<PolicyAnalyticsOutcomesResponse>(`/policies/analytics/outcomes${q ? `?${q}` : ''}`)
  },

  getDenyReasons: () =>
    requestV2<PolicyAnalyticsDenyReason[]>('/policies/analytics/deny-reasons'),

  getSuggestions: () =>
    requestV2<PolicyAnalyticsSuggestion[]>('/policies/analytics/suggestions'),
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

  getCheckoutSecurityPolicy: () =>
    requestV2<JsonObject>('/checkout/secure/security-policy'),

  getAsaSecurityPolicy: () =>
    requestV2<JsonObject>('/cards/asa/security-policy'),

  getA2ATrustSecurityPolicy: () =>
    requestV2<JsonObject>('/a2a/trust/security-policy'),

  getProviderReadiness: () =>
    requestV2<JsonObject>('/cards/providers/readiness'),
}

// ── Approval Config types ────────────────────────────────────────────────────

export interface ApproverGroup {
  id: string
  name: string
  members: string[]
  is_fallback: boolean
}

export interface RoutingRule {
  id: string
  name: string
  condition: string
  approver_group: string
  quorum: number
  distinct_reviewers: boolean
  sla_hours: number
  escalation_hours: number | null
  escalation_group: string | null
}

export interface ApprovalDefaults {
  default_approver_group: string
  default_quorum: number
  default_sla_hours: number
  auto_expire_hours: number
  require_distinct_reviewers: boolean
}

export interface ApprovalConfigData {
  approver_groups: ApproverGroup[]
  routing_rules: RoutingRule[]
  defaults: ApprovalDefaults
}

// Approval Config APIs (V2)
export const approvalConfigApi = {
  get: () => requestV2<ApprovalConfigData>('/approvals/config/'),

  updateGroups: (groups: ApproverGroup[]) =>
    requestV2<ApproverGroup[]>('/approvals/config/groups', {
      method: 'PUT',
      body: JSON.stringify(groups),
    }),

  updateRules: (rules: RoutingRule[]) =>
    requestV2<RoutingRule[]>('/approvals/config/rules', {
      method: 'PUT',
      body: JSON.stringify(rules),
    }),

  updateDefaults: (defaults: ApprovalDefaults) =>
    requestV2<ApprovalDefaults>('/approvals/config/defaults', {
      method: 'PUT',
      body: JSON.stringify(defaults),
    }),
}

// ── Fallback Policies types ──────────────────────────────────────────────────

export interface FallbackRule {
  id: string
  name: string
  primary_rail: string
  fallback_rail: string
  trigger: string
  behavior: string
  max_retries: number
  retry_delay_seconds: number
  enabled: boolean
  audit_log: boolean
}

export interface DegradedModePolicy {
  rail: string
  mode: string
  reason: string | null
  max_amount_override: number | null
  require_approval: boolean
  updated_at: string
}

export interface ProviderReliabilityScorecard {
  provider: string
  chain: string
  period: string
  total_calls: number
  success_count: number
  failure_count: number
  avg_latency_ms: number
  p95_latency_ms: number
  error_rate: number
  availability: number
  computed_at: string
}

export interface ProviderReliabilityListResponse {
  scorecards: ProviderReliabilityScorecard[]
  count: number
}

export const reliabilityApi = {
  listProviders: () =>
    requestV2<ProviderReliabilityListResponse>('/reliability/providers'),

  getProvider: (provider: string, chain: string, period = '24h') =>
    requestV2<ProviderReliabilityScorecard>(
      `/reliability/providers/${encodeURIComponent(provider)}/${encodeURIComponent(chain)}?period=${encodeURIComponent(period)}`,
    ),
}

// Fallback Policies APIs (V2)
// Checkout Controls types
export interface CheckoutControlConfig {
  require_approval_above: number | null
  require_kyc: boolean
  allowed_chains: string[]
  allowed_tokens: string[]
  max_session_amount: number | null
  evidence_export_auto: boolean
  incident_webhook_url: string | null
  freeze_on_dispute: boolean
}

export interface CheckoutIncidentResponse {
  incident_id: string
  session_id: string
  incident_type: string
  severity: string
  status: string
  description: string
  auto_actions_taken: string[]
  created_at: string
}

export const checkoutControlsApi = {
  getConfig: () => requestV2<CheckoutControlConfig>('/checkout-controls/config'),

  updateConfig: (config: CheckoutControlConfig) =>
    requestV2<CheckoutControlConfig>('/checkout-controls/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    }),

  listIncidents: (limit = 50) =>
    requestV2<CheckoutIncidentResponse[]>(`/checkout-controls/incidents?limit=${limit}`),
}

// Fallback Policies APIs (V2)
export const fallbackPoliciesApi = {
  listRules: () => requestV2<FallbackRule[]>('/fallback/rules'),

  createRule: (data: Omit<FallbackRule, 'id'>) =>
    requestV2<FallbackRule>('/fallback/rules', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateRule: (id: string, data: Omit<FallbackRule, 'id'>) =>
    requestV2<FallbackRule>(`/fallback/rules/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteRule: (id: string) =>
    requestV2<void>(`/fallback/rules/${id}`, { method: 'DELETE' }),

  listDegradedModes: () => requestV2<DegradedModePolicy[]>('/fallback/degraded-modes'),

  setDegradedMode: (rail: string, data: Omit<DegradedModePolicy, 'updated_at'>) =>
    requestV2<DegradedModePolicy>(`/fallback/degraded-modes/${rail}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
}

// ─── Sandbox API (no auth required) ──────────────────────────────────────
// Sandbox endpoints use anonymous namespace isolation — no API key needed.
export const sandboxApi = {
  payment: (data: Record<string, unknown>) =>
    fetch(`${API_V2_BASE}/sandbox/payment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => r.ok ? r.json() : null),

  policyCheck: (data: Record<string, unknown>) =>
    fetch(`${API_V2_BASE}/sandbox/policy-check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => r.ok ? r.json() : null),

  health: () =>
    fetch(`${API_V2_BASE}/sandbox/demo-data`)
      .then(r => r.ok)
      .catch(() => false),
}

// Dashboard Metrics API (V2)
export const dashboardApi = {
  getMetrics: () => requestV2<{
    active_agents: number
    total_agents: number
    volume_24h: number
    total_transactions: number
    completed_transactions: number
    total_merchants: number
    total_webhooks: number
  }>('/dashboard/metrics'),
}

// Spending Mandates APIs (V2)
export const spendingMandatesApi = {
  list: () => requestV2<{
    id: string
    org_id: string
    agent_id: string | null
    purpose_scope: string | null
    merchant_scope: Record<string, unknown> | null
    amount_per_tx: string | null
    amount_daily: string | null
    amount_monthly: string | null
    amount_total: string | null
    currency: string
    spent_total: string
    allowed_rails: string[]
    approval_threshold: string | null
    approval_mode: string
    status: string
    version: number
    expires_at: string | null
    created_at: string
  }[]>('/spending-mandates'),

  get: (mandateId: string) => requestV2<JsonObject>(`/spending-mandates/${mandateId}`),

  create: (data: {
    purpose_scope?: string
    amount_per_tx?: number
    amount_daily?: number
    amount_monthly?: number
    amount_total?: number
    allowed_rails?: string[]
    approval_mode?: string
    approval_threshold?: number
    merchant_scope?: Record<string, unknown>
  }) => requestV2<JsonObject>('/spending-mandates', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  transitions: (mandateId: string) =>
    requestV2<{
      id: string
      from_status: string
      to_status: string
      changed_by: string
      reason: string | null
      created_at: string
    }[]>(`/spending-mandates/${mandateId}/transitions`),

  action: (mandateId: string, action: string, reason?: string) =>
    requestV2<JsonObject>(`/spending-mandates/${mandateId}/${action}`, {
      method: 'POST',
      body: JSON.stringify({ reason: reason || `${action} from dashboard` }),
    }),
}

// MPP Sessions APIs (V2)
export const mppApi = {
  listSessions: () => requestV2<{
    session_id: string
    status: 'active' | 'closed' | 'expired' | 'exhausted'
    spending_limit: string
    remaining: string
    payment_count: number
    created_at: string
    updated_at?: string
    agent_id?: string
    description?: string
  }[]>('/mpp/sessions'),

  getSession: (sessionId: string) => requestV2<JsonObject>(`/mpp/sessions/${sessionId}`),
}

// Faucet API (V2 - testnet only)
export const faucetApi = {
  drip: () => requestV2<{
    success: boolean
    amount: string
    token: string
    tx_hash?: string
  }>('/faucet/drip', {
    method: 'POST',
    body: JSON.stringify({}),
  }),
}

// ─── Chain Explorer Helpers ──────────────────────────────────────────────
export const CHAIN_EXPLORERS: Record<string, string> = {
  base: 'https://basescan.org',
  base_sepolia: 'https://sepolia.basescan.org',
  polygon: 'https://polygonscan.com',
  arbitrum: 'https://arbiscan.io',
  optimism: 'https://optimistic.etherscan.io',
  ethereum: 'https://etherscan.io',
}

export function getExplorerTxUrl(chain: string, txHash: string): string | null {
  const base = CHAIN_EXPLORERS[chain]
  return base ? `${base}/tx/${txHash}` : null
}
