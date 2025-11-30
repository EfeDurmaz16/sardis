// API Response Types

export interface Agent {
  agent_id: string
  name: string
  owner_id: string
  description?: string
  wallet_id: string
  is_active: boolean
  created_at: string
}

export interface Wallet {
  wallet_id: string
  agent_id: string
  balance: string
  currency: string
  limit_per_tx: string
  limit_total: string
  spent_total: string
  remaining_limit: string
  is_active: boolean
  virtual_card?: VirtualCard
  created_at: string
}

export interface VirtualCard {
  card_id: string
  masked_number: string
  is_active: boolean
}

export interface Transaction {
  tx_id: string
  from_wallet: string
  to_wallet: string
  amount: string
  fee: string
  total_cost: string
  currency: string
  purpose?: string
  status: 'pending' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
}

export interface Merchant {
  merchant_id: string
  name: string
  wallet_id: string
  description?: string
  category: string
  is_active: boolean
  created_at: string
}

export interface WebhookSubscription {
  subscription_id: string
  url: string
  events: string[]
  secret: string
  is_active: boolean
  created_at: string
  last_triggered_at?: string
  failed_attempts: number
}

export interface RiskScore {
  score: number
  level: 'low' | 'medium' | 'high' | 'critical'
  is_acceptable: boolean
  factors: string[]
}

export interface DashboardStats {
  total_agents: number
  active_agents: number
  total_transactions: number
  transaction_volume_24h: string
  transaction_volume_7d: string
  transaction_volume_30d: string
  total_merchants: number
  webhook_count: number
}

// Component Props
export interface StatCardProps {
  title: string
  value: string | number
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  icon?: React.ReactNode
}

export interface ChartDataPoint {
  date: string
  value: number
  label?: string
}

