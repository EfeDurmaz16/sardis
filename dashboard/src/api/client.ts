// API Client for Sardis Dashboard

// API base URL - can be overridden by environment variable
const API_URL = import.meta.env.VITE_API_URL || ''
const API_V1_BASE = `${API_URL}/api/v1`
const API_V2_BASE = `${API_URL}/api/v2`

// Use V2 API if available, fall back to V1
const USE_V2_API = import.meta.env.VITE_USE_V2_API === 'true'

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  useV2: boolean = false
): Promise<T> {
  const base = useV2 ? API_V2_BASE : API_V1_BASE
  const url = `${base}${endpoint}`

  // Get API key from localStorage (set by Settings page)
  const apiKey = localStorage.getItem('sardis_api_key') || ''

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  
  if (apiKey) {
    headers['X-API-Key'] = apiKey
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

// Agent APIs
export const agentApi = {
  list: () => request<any[]>('/agents'),

  get: (agentId: string) => request<any>(`/agents/${agentId}`),

  create: (data: {
    name: string
    owner_id: string
    description?: string
    initial_balance: string
    limit_per_tx: string
    limit_total: string
  }) => request<any>('/agents', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getWallet: (agentId: string) => request<any>(`/agents/${agentId}/wallet`),

  getTransactions: (agentId: string, limit = 50) =>
    request<any[]>(`/payments/agent/${agentId}?limit=${limit}`),

  instruct: (agentId: string, instruction: string) => request<any>(`/agents/${agentId}/instruct`, {
    method: 'POST',
    body: JSON.stringify({ instruction }),
  }),
}

// Payment APIs
export const paymentApi = {
  estimate: (amount: string, currency = 'USDC') =>
    request<any>(`/payments/estimate?amount=${amount}&currency=${currency}`),

  create: (data: {
    agent_id: string
    amount: string
    currency: string
    merchant_id?: string
    recipient_wallet_id?: string
    purpose?: string
  }) => request<any>('/payments', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getHistory: (limit = 100) => request<any[]>(`/payments?limit=${limit}`),
}

// Merchant APIs
export const merchantApi = {
  list: () => request<any[]>('/merchants'),

  create: (data: {
    name: string
    description?: string
    category: string
  }) => request<any>('/merchants', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
}

// Webhook APIs
export const webhookApi = {
  list: () => request<any[]>('/webhooks'),

  create: (data: {
    url: string
    events: string[]
  }) => request<any>('/webhooks', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  update: (subscriptionId: string, data: Partial<{
    url: string
    events: string[]
    is_active: boolean
  }>) => request<any>(`/webhooks/${subscriptionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  delete: (subscriptionId: string) => request<void>(`/webhooks/${subscriptionId}`, {
    method: 'DELETE',
  }),
}

// Risk APIs
export const riskApi = {
  getScore: (agentId: string) => request<any>(`/risk/agents/${agentId}/score`),

  authorize: (agentId: string, serviceId: string) =>
    request<any>(`/risk/agents/${agentId}/authorize`, {
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
      intent?: any
      cart?: any
      payment: {
        mandate_id: string
        issuer: string
        subject: string
        destination: string
        amount_minor: number
        token: string
        expires_at: number
        proof?: any
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
  verify: (data: { mandate_chain: any }) => requestV2<{
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
  recent: (limit = 50) => requestV2<any[]>(`/ledger/recent?limit=${limit}`),
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
  list: () => requestV2<any[]>('/webhooks'),

  // Get a webhook by ID
  get: (subscriptionId: string) => requestV2<any>(`/webhooks/${subscriptionId}`),

  // Update a webhook
  update: (subscriptionId: string, data: {
    url?: string
    events?: string[]
    is_active?: boolean
  }) => requestV2<any>(`/webhooks/${subscriptionId}`, {
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
    requestV2<any[]>(`/webhooks/${subscriptionId}/deliveries?limit=${limit}`),

  // Rotate webhook secret
  rotateSecret: (subscriptionId: string) => requestV2<any>(`/webhooks/${subscriptionId}/rotate-secret`, {
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
    hold?: any
    error?: string
  }>('/holds', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Get a hold by ID
  get: (holdId: string) => requestV2<any>(`/holds/${holdId}`),

  // Capture a hold
  capture: (holdId: string, amount?: string, txId?: string) => requestV2<{
    success: boolean
    hold?: any
    error?: string
  }>(`/holds/${holdId}/capture`, {
    method: 'POST',
    body: JSON.stringify({ amount, tx_id: txId }),
  }),

  // Void a hold
  void: (holdId: string) => requestV2<{
    success: boolean
    hold?: any
    error?: string
  }>(`/holds/${holdId}/void`, {
    method: 'POST',
  }),

  // List holds for a wallet
  listByWallet: (walletId: string, status?: string, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (status) params.append('status', status)
    return requestV2<any[]>(`/holds/wallet/${walletId}?${params}`)
  },

  // List all active holds
  listActive: (limit = 100) => requestV2<any[]>(`/holds?limit=${limit}`),
}

// Invoices APIs (V2 only)
export const invoicesApi = {
  list: (params?: { status?: string; limit?: number; offset?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.limit) searchParams.append('limit', String(params.limit))
    if (params?.offset) searchParams.append('offset', String(params.offset))
    return requestV2<any[]>(`/invoices?${searchParams}`)
  },

  get: (invoiceId: string) => requestV2<any>(`/invoices/${invoiceId}`),

  create: (data: {
    amount: string
    currency?: string
    description?: string
    merchant_name?: string
    payer_agent_id?: string
    reference?: string
  }) => requestV2<any>('/invoices', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateStatus: (invoiceId: string, status: string) =>
    requestV2<any>(`/invoices/${invoiceId}?status=${status}`, {
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
  }) => requestV2<any>('/marketplace/services', {
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
    return requestV2<any[]>(`/marketplace/services?${searchParams}`)
  },

  // Get a service
  getService: (serviceId: string) => requestV2<any>(`/marketplace/services/${serviceId}`),

  // Search services
  searchServices: (query: string, filters?: {
    category?: string
    min_rating?: string
    max_price?: string
  }) => requestV2<any[]>('/marketplace/services/search', {
    method: 'POST',
    body: JSON.stringify({ query, ...filters }),
  }),

  // Create an offer
  createOffer: (data: {
    service_id: string
    total_amount: string
    token?: string
    milestones?: Array<{ name: string; description: string; amount: string }>
  }) => requestV2<any>('/marketplace/offers', {
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
    return requestV2<any[]>(`/marketplace/offers?${searchParams}`)
  },

  // Get an offer
  getOffer: (offerId: string) => requestV2<any>(`/marketplace/offers/${offerId}`),

  // Accept an offer
  acceptOffer: (offerId: string) => requestV2<any>(`/marketplace/offers/${offerId}/accept`, {
    method: 'POST',
  }),

  // Reject an offer
  rejectOffer: (offerId: string) => requestV2<any>(`/marketplace/offers/${offerId}/reject`, {
    method: 'POST',
  }),

  // Complete an offer
  completeOffer: (offerId: string) => requestV2<any>(`/marketplace/offers/${offerId}/complete`, {
    method: 'POST',
  }),

  // Create a review
  createReview: (offerId: string, data: {
    rating: number
    comment?: string
  }) => requestV2<any>(`/marketplace/offers/${offerId}/review`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // List reviews for a service
  listReviews: (serviceId: string, limit = 50) =>
    requestV2<any[]>(`/marketplace/services/${serviceId}/reviews?limit=${limit}`),
}
