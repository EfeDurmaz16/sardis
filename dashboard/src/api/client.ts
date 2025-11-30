// API Client for Sardis Dashboard

const API_BASE = '/api/v1'

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }
  
  return response.json()
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

// Health check
export const healthApi = {
  check: () => request<{ status: string; service: string; version: string }>('/'),
}

