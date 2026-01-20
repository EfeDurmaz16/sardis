/**
 * Sardis SDK Type Definitions
 */

// ==================== Common Types ====================

export type Chain = 'base' | 'base_sepolia' | 'polygon' | 'polygon_amoy' | 'ethereum' | 'ethereum_sepolia';
export type Token = 'USDC' | 'USDT' | 'PYUSD' | 'EURC';
export type MPCProvider = 'turnkey' | 'fireblocks' | 'local';

// ==================== Wallet Types ====================

export interface TokenLimit {
  /** Token symbol */
  token: Token;
  /** Per-transaction spending limit */
  limit_per_tx?: string;
  /** Total spending limit */
  limit_total?: string;
  // Note: No balance field - balances are read from chain (non-custodial)
}

export interface Wallet {
  /** Wallet ID */
  id: string;
  /** Agent ID that owns this wallet */
  agent_id: string;
  /** MPC provider ("turnkey", "fireblocks", or "local") */
  mpc_provider: MPCProvider;
  /** Chain -> address mapping */
  addresses: Record<string, string>;
  /** Default currency for display */
  currency: Token;
  /** Token-specific spending limits */
  token_limits: Record<string, TokenLimit>;
  /** Per-transaction spending limit */
  limit_per_tx: string;
  /** Total spending limit */
  limit_total: string;
  /** Whether wallet is active */
  is_active: boolean;
  /** Creation timestamp */
  created_at: string;
  /** Last update timestamp */
  updated_at: string;
}

export interface WalletBalance {
  /** Wallet ID */
  wallet_id: string;
  /** Chain identifier */
  chain: string;
  /** Token symbol */
  token: Token;
  /** Balance from chain (read-only) */
  balance: string;
  /** Wallet address on chain */
  address: string;
}

export interface CreateWalletInput {
  /** Agent ID */
  agent_id: string;
  /** MPC provider */
  mpc_provider?: MPCProvider;
  /** Default currency */
  currency?: Token;
  /** Per-transaction limit */
  limit_per_tx?: string;
  /** Total spending limit */
  limit_total?: string;
}

export interface SetAddressInput {
  /** Chain identifier */
  chain: string;
  /** Wallet address on chain */
  address: string;
}

// ==================== Payment Types ====================

export type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'refunded';

export interface Payment {
  id: string;
  from_wallet: string;
  to_wallet: string;
  amount: string;
  fee: string;
  token: Token;
  chain: Chain;
  status: PaymentStatus;
  purpose?: string;
  tx_hash?: string;
  block_number?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface ExecutePaymentInput {
  mandate: Record<string, unknown>;
}

export interface ExecuteAP2Input {
  intent: Record<string, unknown>;
  cart: Record<string, unknown>;
  payment: Record<string, unknown>;
}

export interface ExecutePaymentResponse {
  payment_id: string;
  status: PaymentStatus;
  tx_hash?: string;
  chain: string;
  audit_anchor?: string;
  ledger_tx_id?: string;
}

export interface ExecuteAP2Response {
  mandate_id: string;
  ledger_tx_id: string;
  chain_tx_hash: string;
  chain: string;
  audit_anchor: string;
  status: string;
  compliance_provider?: string;
  compliance_rule?: string;
}

// ==================== Hold Types ====================

export type HoldStatus = 'active' | 'captured' | 'voided' | 'expired';

export interface Hold {
  id: string;
  wallet_id: string;
  merchant_id?: string;
  amount: string;
  token: Token;
  status: HoldStatus;
  purpose?: string;
  expires_at: string;
  captured_amount?: string;
  captured_at?: string;
  voided_at?: string;
  created_at: string;
}

export interface CreateHoldInput {
  wallet_id: string;
  amount: string;
  token?: Token;
  merchant_id?: string;
  purpose?: string;
  duration_hours?: number;
}

export interface CaptureHoldInput {
  amount?: string;
}

export interface CreateHoldResponse {
  hold_id: string;
  status: HoldStatus;
  expires_at: string;
}

// ==================== Webhook Types ====================

export type WebhookEventType =
  | 'payment.completed'
  | 'payment.failed'
  | 'hold.created'
  | 'hold.captured'
  | 'hold.voided'
  | 'hold.expired'
  | 'wallet.funded'
  | 'wallet.low_balance'
  | 'offer.received'
  | 'offer.accepted'
  | 'offer.completed';

export interface Webhook {
  id: string;
  organization_id: string;
  url: string;
  events: WebhookEventType[];
  is_active: boolean;
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  last_delivery_at?: string;
  created_at: string;
  updated_at: string;
}

export interface WebhookDelivery {
  id: string;
  subscription_id: string;
  event_id: string;
  event_type: string;
  url: string;
  status_code?: number;
  success: boolean;
  error?: string;
  duration_ms: number;
  attempt_number: number;
  created_at: string;
}

export interface CreateWebhookInput {
  url: string;
  events: WebhookEventType[];
  organization_id?: string;
}

export interface UpdateWebhookInput {
  url?: string;
  events?: WebhookEventType[];
  is_active?: boolean;
}

// ==================== Marketplace Types ====================

export type ServiceCategory = 'payment' | 'data' | 'compute' | 'ai' | 'storage' | 'oracle' | 'other';
export type ServiceStatus = 'draft' | 'active' | 'paused' | 'archived';
export type OfferStatus = 'pending' | 'accepted' | 'rejected' | 'completed' | 'cancelled' | 'disputed';

export interface Service {
  id: string;
  provider_agent_id: string;
  name: string;
  description?: string;
  category: ServiceCategory;
  tags: string[];
  price_amount: string;
  price_token: Token;
  price_type: string;
  capabilities: Record<string, unknown>;
  api_endpoint?: string;
  status: ServiceStatus;
  total_orders: number;
  completed_orders: number;
  rating?: number;
  created_at: string;
  updated_at: string;
}

export interface ServiceOffer {
  id: string;
  service_id: string;
  provider_agent_id: string;
  consumer_agent_id: string;
  total_amount: string;
  token: Token;
  status: OfferStatus;
  escrow_tx_hash?: string;
  escrow_amount: string;
  released_amount: string;
  created_at: string;
  accepted_at?: string;
  completed_at?: string;
}

export interface ServiceReview {
  id: string;
  offer_id: string;
  service_id: string;
  reviewer_agent_id: string;
  rating: number;
  comment?: string;
  created_at: string;
}

export interface CreateServiceInput {
  name: string;
  description?: string;
  category: ServiceCategory;
  tags?: string[];
  price_amount: string;
  price_token?: Token;
  capabilities?: Record<string, unknown>;
  api_endpoint?: string;
}

export interface CreateOfferInput {
  service_id: string;
  consumer_agent_id: string;
  total_amount: string;
  token?: Token;
}

export interface SearchServicesInput {
  query?: string;
  category?: ServiceCategory;
  min_price?: string;
  max_price?: string;
  tags?: string[];
}

// ==================== Transaction Types ====================

export interface GasEstimate {
  gas_limit: number;
  gas_price_gwei: string;
  max_fee_gwei: string;
  max_priority_fee_gwei: string;
  estimated_cost_wei: number;
  estimated_cost_usd?: string;
}

export interface TransactionStatus {
  tx_hash: string;
  chain: string;
  status: 'pending' | 'submitted' | 'confirming' | 'confirmed' | 'failed';
  block_number?: number;
  confirmations: number;
}

export interface ChainInfo {
  name: string;
  chain_id: number;
  native_token: string;
  block_time: number;
  explorer: string;
}

// ==================== Ledger Types ====================

export interface LedgerEntry {
  tx_id: string;
  mandate_id?: string;
  from_wallet?: string;
  to_wallet?: string;
  amount: string;
  currency: string;
  chain?: string;
  chain_tx_hash?: string;
  audit_anchor?: string;
  created_at: string;
}

// ==================== Error Types ====================

export interface SardisErrorDetails {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

// ==================== Client Options ====================

export interface SardisClientOptions {
  baseUrl?: string;
  apiKey: string;
  timeout?: number;
  maxRetries?: number;
}
