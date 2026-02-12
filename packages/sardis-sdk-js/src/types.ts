/**
 * Sardis SDK Type Definitions
 *
 * This module contains all TypeScript type definitions used throughout
 * the Sardis SDK.
 *
 * @packageDocumentation
 */

import type { AxiosRequestConfig, AxiosResponse } from 'axios';

// ==================== Common Types ====================

/**
 * Supported blockchain networks.
 *
 * Each network supports different stablecoins and has different
 * transaction characteristics (speed, cost, etc.).
 *
 * @remarks
 * Note: Solana support is planned but NOT YET IMPLEMENTED.
 * Using 'solana' or 'solana_devnet' will throw a NotImplementedError.
 */
export type Chain =
  | 'base'
  | 'base_sepolia'
  | 'polygon'
  | 'polygon_amoy'
  | 'ethereum'
  | 'ethereum_sepolia'
  | 'arbitrum'
  | 'arbitrum_sepolia'
  | 'optimism'
  | 'optimism_sepolia';

/**
 * Experimental chains - NOT YET IMPLEMENTED.
 * These are planned for future releases.
 * @internal
 */
export type ExperimentalChain = 'solana' | 'solana_devnet';

/**
 * Supported stablecoin tokens.
 *
 * - USDC: USD Coin (Circle)
 * - USDT: Tether USD
 * - PYUSD: PayPal USD
 * - EURC: Euro Coin (Circle)
 */
export type Token = 'USDC' | 'USDT' | 'PYUSD' | 'EURC';

/**
 * MPC (Multi-Party Computation) wallet providers.
 *
 * - turnkey: Turnkey.com infrastructure
 * - fireblocks: Fireblocks custody platform
 * - local: Local key management (development only)
 */
export type MPCProvider = 'turnkey' | 'fireblocks' | 'local';

// ==================== Client Configuration Types ====================

/**
 * Configuration options for the SardisClient.
 *
 * @example
 * ```typescript
 * const options: SardisClientOptions = {
 *   apiKey: 'sk_live_xxx',
 *   timeout: 30000,
 *   maxRetries: 3,
 *   retryDelay: 1000,
 * };
 * ```
 */
export interface SardisClientOptions {
  /** API base URL (defaults to https://api.sardis.sh) */
  baseUrl?: string;

  /** API key for authentication (required) */
  apiKey: string;

  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;

  /** Connection timeout in milliseconds (default: 10000) */
  connectTimeout?: number;

  /** Maximum number of retry attempts (default: 3) */
  maxRetries?: number;

  /** Initial retry delay in milliseconds (default: 1000) */
  retryDelay?: number;

  /** Maximum retry delay in milliseconds (default: 30000) */
  maxRetryDelay?: number;

  /** HTTP status codes to retry on (default: [408, 429, 500, 502, 503, 504]) */
  retryOn?: number[];

  /** Whether to retry on network errors (default: true) */
  retryOnNetworkError?: boolean;

  /** Token refresh configuration for automatic token renewal */
  tokenRefresh?: TokenRefreshConfig;
}

/**
 * Configuration for automatic token refresh.
 *
 * @example
 * ```typescript
 * const config: TokenRefreshConfig = {
 *   refreshToken: async () => {
 *     const response = await fetch('/auth/refresh');
 *     const data = await response.json();
 *     return data.accessToken;
 *   },
 * };
 * ```
 */
export interface TokenRefreshConfig {
  /** Function to refresh the authentication token */
  refreshToken: () => Promise<string>;
}

/**
 * Retry configuration options.
 */
export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial retry delay in milliseconds */
  retryDelay: number;
  /** Maximum retry delay in milliseconds */
  maxRetryDelay: number;
  /** HTTP status codes to retry on */
  retryOn: number[];
  /** Whether to retry on network errors */
  retryOnNetworkError: boolean;
}

/**
 * Options for individual requests.
 *
 * @example
 * ```typescript
 * const controller = new AbortController();
 * const options: RequestOptions = {
 *   timeout: 5000,
 *   signal: controller.signal,
 * };
 * ```
 */
export interface RequestOptions {
  /** Query parameters */
  params?: Record<string, unknown>;
  /** Request body data */
  data?: unknown;
  /** AbortSignal for request cancellation */
  signal?: AbortSignal;
  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * Request interceptor for modifying outgoing requests.
 *
 * @example
 * ```typescript
 * const interceptor: RequestInterceptor = {
 *   onRequest: (config) => {
 *     config.headers['X-Request-ID'] = generateRequestId();
 *     return config;
 *   },
 *   onError: (error) => {
 *     console.error('Request failed:', error);
 *     throw error;
 *   },
 * };
 * ```
 */
export interface RequestInterceptor {
  /** Called before each request is sent */
  onRequest?: (config: AxiosRequestConfig) => AxiosRequestConfig | Promise<AxiosRequestConfig>;
  /** Called when an error occurs */
  onError?: (error: Error) => void | Promise<void>;
}

/**
 * Response interceptor for modifying incoming responses.
 *
 * @example
 * ```typescript
 * const interceptor: ResponseInterceptor = {
 *   onResponse: (response) => {
 *     console.log(`Response received: ${response.status}`);
 *     return response;
 *   },
 *   onError: (error) => {
 *     if (error.response?.status === 401) {
 *       // Handle unauthorized
 *     }
 *     throw error;
 *   },
 * };
 * ```
 */
export interface ResponseInterceptor {
  /** Called after each response is received */
  onResponse?: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>;
  /** Called when an error occurs */
  onError?: (error: Error) => void | Promise<void>;
}

/**
 * Pagination parameters for list operations.
 */
export interface PaginationParams {
  /** Maximum number of items to return per page */
  limit?: number;
  /** Cursor for pagination (offset or ID) */
  cursor?: string;
  /** Offset for pagination (alternative to cursor) */
  offset?: number;
}

/**
 * Paginated response structure.
 *
 * @typeParam T - The type of items in the response
 */
export interface PaginatedResponse<T> {
  /** Array of items in this page */
  data: T[];
  /** Whether there are more items */
  hasMore: boolean;
  /** Cursor for the next page */
  nextCursor?: string;
  /** Total count of items (if available) */
  total?: number;
}

// ==================== Wallet Types ====================

/**
 * Token-specific spending limits.
 */
export interface TokenLimit {
  /** Token symbol */
  token: Token;
  /** Per-transaction spending limit (in token's decimal format) */
  limit_per_tx?: string;
  /** Total spending limit (in token's decimal format) */
  limit_total?: string;
}

/**
 * Non-custodial wallet for an agent.
 *
 * Wallets are MPC-based and never hold funds directly -
 * they only sign transactions.
 */
export interface Wallet {
  /** Unique wallet identifier (API field) */
  wallet_id: string;
  /** Backwards-compat alias (older SDKs used `id`) */
  id: string;
  /** ID of the agent that owns this wallet */
  agent_id: string;
  /** MPC provider used for key management */
  mpc_provider: MPCProvider;
  /** Mapping of chain names to wallet addresses */
  addresses: Record<string, string>;
  /** Default currency for display purposes */
  currency: Token;
  /** Token-specific spending limits */
  token_limits: Record<string, TokenLimit>;
  /** Per-transaction spending limit (in default currency) */
  limit_per_tx: string;
  /** Total spending limit (in default currency) */
  limit_total: string;
  /** Whether the wallet is active and can sign transactions */
  is_active: boolean;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** ISO 8601 timestamp of last update */
  updated_at: string;
}

/**
 * Wallet balance for a specific token on a specific chain.
 *
 * Balances are read directly from the blockchain (non-custodial).
 */
export interface WalletBalance {
  /** Wallet ID */
  wallet_id: string;
  /** Chain identifier */
  chain: string;
  /** Token symbol */
  token: Token;
  /** Current balance (from blockchain) */
  balance: string;
  /** Wallet address on this chain */
  address: string;
}

/**
 * Input for creating a new wallet.
 */
export interface CreateWalletInput {
  /** Agent ID that will own this wallet */
  agent_id: string;
  /** MPC provider to use (defaults to 'turnkey') */
  mpc_provider?: MPCProvider;
  /** Default currency (defaults to 'USDC') */
  currency?: Token;
  /** Per-transaction spending limit */
  limit_per_tx?: string;
  /** Total spending limit */
  limit_total?: string;
}

/**
 * Input for setting a wallet address on a chain.
 */
export interface SetAddressInput {
  /** Chain identifier */
  chain: string;
  /** Wallet address on this chain */
  address: string;
}

/**
 * Input for transferring stablecoins from a wallet.
 *
 * This is an "agent action": the caller is the agent process using an API key.
 * Sardis enforces policy + compliance and signs via the agent MPC wallet.
 */
export interface WalletTransferInput {
  destination: string;
  amount: string; // token units (e.g. "1.00" USDC)
  token?: Token;
  chain?: Chain;
  domain?: string; // policy context label (e.g. "aws.amazon.com")
  memo?: string;
}

export interface WalletTransferResponse {
  tx_hash: string;
  status: string;
  from_address: string;
  to_address: string;
  amount: string;
  token: Token;
  chain: Chain;
  audit_anchor?: string | null;
}

// ==================== Payment Types ====================

/**
 * Payment execution status.
 */
export type PaymentStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'refunded';

/**
 * A completed or in-progress payment.
 */
export interface Payment {
  /** Unique payment identifier */
  id: string;
  /** Source wallet address */
  from_wallet: string;
  /** Destination wallet address */
  to_wallet: string;
  /** Payment amount (in token's decimal format) */
  amount: string;
  /** Transaction fee */
  fee: string;
  /** Token used for payment */
  token: Token;
  /** Chain where payment was executed */
  chain: Chain;
  /** Current payment status */
  status: PaymentStatus;
  /** Purpose or description of the payment */
  purpose?: string;
  /** Blockchain transaction hash */
  tx_hash?: string;
  /** Block number where transaction was included */
  block_number?: number;
  /** Error message if payment failed */
  error_message?: string;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** ISO 8601 timestamp of completion */
  completed_at?: string;
}

/**
 * Input for executing a payment mandate.
 */
export interface ExecutePaymentInput {
  /** Payment mandate object */
  mandate: Record<string, unknown>;
}

/**
 * Input for executing an AP2 payment bundle.
 */
export interface ExecuteAP2Input {
  /** Intent object describing the payment purpose */
  intent: Record<string, unknown>;
  /** Cart object with items being purchased */
  cart: Record<string, unknown>;
  /** Payment object with execution details */
  payment: Record<string, unknown>;
}

/**
 * Response from payment execution.
 */
export interface ExecutePaymentResponse {
  /** Payment ID */
  payment_id: string;
  /** Execution status */
  status: PaymentStatus;
  /** Transaction hash (if submitted to chain) */
  tx_hash?: string;
  /** Chain where payment was executed */
  chain: string;
  /** Audit anchor hash */
  audit_anchor?: string;
  /** Ledger transaction ID */
  ledger_tx_id?: string;
}

/**
 * Response from AP2 payment execution.
 */
export interface ExecuteAP2Response {
  /** Mandate ID */
  mandate_id: string;
  /** Ledger transaction ID */
  ledger_tx_id: string;
  /** Blockchain transaction hash */
  chain_tx_hash: string;
  /** Chain where executed */
  chain: string;
  /** Audit anchor hash */
  audit_anchor: string;
  /** Execution status */
  status: string;
  /** Compliance provider used (if any) */
  compliance_provider?: string;
  /** Compliance rule applied (if any) */
  compliance_rule?: string;
}

// ==================== Hold Types ====================

/**
 * Hold (pre-authorization) status.
 */
export type HoldStatus = 'active' | 'captured' | 'voided' | 'expired';

/**
 * A fund hold (pre-authorization).
 *
 * Holds reserve funds for a future payment without actually
 * transferring them.
 */
export interface Hold {
  /** Unique hold identifier */
  id: string;
  /** Wallet ID where funds are held */
  wallet_id: string;
  /** Merchant ID (if applicable) */
  merchant_id?: string;
  /** Hold amount */
  amount: string;
  /** Token being held */
  token: Token;
  /** Current hold status */
  status: HoldStatus;
  /** Purpose or description of the hold */
  purpose?: string;
  /** ISO 8601 timestamp when hold expires */
  expires_at: string;
  /** Amount that was captured (if captured) */
  captured_amount?: string;
  /** ISO 8601 timestamp of capture (if captured) */
  captured_at?: string;
  /** ISO 8601 timestamp of void (if voided) */
  voided_at?: string;
  /** ISO 8601 timestamp of creation */
  created_at: string;
}

/**
 * Input for creating a hold.
 */
export interface CreateHoldInput {
  /** Wallet ID to hold funds from */
  wallet_id: string;
  /** Amount to hold */
  amount: string;
  /** Token to hold (defaults to 'USDC') */
  token?: Token;
  /** Merchant ID */
  merchant_id?: string;
  /** Purpose or description */
  purpose?: string;
  /** Duration in hours before expiration (default: 24) */
  duration_hours?: number;
}

/**
 * Input for capturing a hold.
 */
export interface CaptureHoldInput {
  /** Amount to capture (defaults to full hold amount) */
  amount?: string;
}

/**
 * Response from hold creation.
 */
export interface CreateHoldResponse {
  /** Hold ID */
  hold_id: string;
  /** Initial status */
  status: HoldStatus;
  /** Expiration timestamp */
  expires_at: string;
}

// ==================== Webhook Types ====================

/**
 * Webhook event types.
 */
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

/**
 * A webhook subscription.
 */
export interface Webhook {
  /** Unique webhook identifier */
  id: string;
  /** Organization ID */
  organization_id: string;
  /** Endpoint URL to receive events */
  url: string;
  /** Event types to subscribe to */
  events: WebhookEventType[];
  /** Whether webhook is active */
  is_active: boolean;
  /** Total number of delivery attempts */
  total_deliveries: number;
  /** Number of successful deliveries */
  successful_deliveries: number;
  /** Number of failed deliveries */
  failed_deliveries: number;
  /** ISO 8601 timestamp of last delivery */
  last_delivery_at?: string;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** ISO 8601 timestamp of last update */
  updated_at: string;
}

/**
 * A webhook delivery attempt.
 */
export interface WebhookDelivery {
  /** Unique delivery identifier */
  id: string;
  /** Webhook subscription ID */
  subscription_id: string;
  /** Event ID */
  event_id: string;
  /** Event type */
  event_type: string;
  /** Endpoint URL */
  url: string;
  /** HTTP status code from endpoint */
  status_code?: number;
  /** Whether delivery succeeded */
  success: boolean;
  /** Error message (if failed) */
  error?: string;
  /** Response time in milliseconds */
  duration_ms: number;
  /** Attempt number (for retries) */
  attempt_number: number;
  /** ISO 8601 timestamp of delivery */
  created_at: string;
}

/**
 * Input for creating a webhook.
 */
export interface CreateWebhookInput {
  /** Endpoint URL */
  url: string;
  /** Event types to subscribe to */
  events: WebhookEventType[];
  /** Organization ID (optional) */
  organization_id?: string;
}

/**
 * Input for updating a webhook.
 */
export interface UpdateWebhookInput {
  /** New endpoint URL */
  url?: string;
  /** New event types */
  events?: WebhookEventType[];
  /** Whether webhook is active */
  is_active?: boolean;
}

// ==================== Marketplace Types ====================

/**
 * Service categories in the marketplace.
 */
export type ServiceCategory = 'payment' | 'data' | 'compute' | 'ai' | 'storage' | 'oracle' | 'other';

/**
 * Service listing status.
 */
export type ServiceStatus = 'draft' | 'active' | 'paused' | 'archived';

/**
 * Offer status.
 */
export type OfferStatus = 'pending' | 'accepted' | 'rejected' | 'completed' | 'cancelled' | 'disputed';

/**
 * A service listing in the marketplace.
 */
export interface Service {
  /** Unique service identifier */
  id: string;
  /** Provider agent ID */
  provider_agent_id: string;
  /** Service name */
  name: string;
  /** Service description */
  description?: string;
  /** Service category */
  category: ServiceCategory;
  /** Searchable tags */
  tags: string[];
  /** Price amount */
  price_amount: string;
  /** Price token */
  price_token: Token;
  /** Pricing type (e.g., 'per_request', 'subscription') */
  price_type: string;
  /** Service capabilities */
  capabilities: Record<string, unknown>;
  /** API endpoint URL */
  api_endpoint?: string;
  /** Current status */
  status: ServiceStatus;
  /** Total number of orders */
  total_orders: number;
  /** Number of completed orders */
  completed_orders: number;
  /** Average rating (1-5) */
  rating?: number;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** ISO 8601 timestamp of last update */
  updated_at: string;
}

/**
 * An offer for a service.
 */
export interface ServiceOffer {
  /** Unique offer identifier */
  id: string;
  /** Service ID */
  service_id: string;
  /** Provider agent ID */
  provider_agent_id: string;
  /** Consumer agent ID */
  consumer_agent_id: string;
  /** Total offer amount */
  total_amount: string;
  /** Payment token */
  token: Token;
  /** Current status */
  status: OfferStatus;
  /** Escrow transaction hash */
  escrow_tx_hash?: string;
  /** Amount in escrow */
  escrow_amount: string;
  /** Amount released from escrow */
  released_amount: string;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** ISO 8601 timestamp of acceptance */
  accepted_at?: string;
  /** ISO 8601 timestamp of completion */
  completed_at?: string;
}

/**
 * A review for a service.
 */
export interface ServiceReview {
  /** Unique review identifier */
  id: string;
  /** Offer ID this review is for */
  offer_id: string;
  /** Service ID */
  service_id: string;
  /** Reviewer agent ID */
  reviewer_agent_id: string;
  /** Rating (1-5) */
  rating: number;
  /** Review comment */
  comment?: string;
  /** ISO 8601 timestamp of creation */
  created_at: string;
}

/**
 * Input for creating a service.
 */
export interface CreateServiceInput {
  /** Service name */
  name: string;
  /** Service description */
  description?: string;
  /** Service category */
  category: ServiceCategory;
  /** Searchable tags */
  tags?: string[];
  /** Price amount */
  price_amount: string;
  /** Price token (defaults to 'USDC') */
  price_token?: Token;
  /** Service capabilities */
  capabilities?: Record<string, unknown>;
  /** API endpoint URL */
  api_endpoint?: string;
}

/**
 * Input for creating an offer.
 */
export interface CreateOfferInput {
  /** Service ID */
  service_id: string;
  /** Consumer agent ID */
  consumer_agent_id: string;
  /** Total offer amount */
  total_amount: string;
  /** Payment token (defaults to 'USDC') */
  token?: Token;
}

/**
 * Input for searching services.
 */
export interface SearchServicesInput {
  /** Text query */
  query?: string;
  /** Filter by category */
  category?: ServiceCategory;
  /** Minimum price */
  min_price?: string;
  /** Maximum price */
  max_price?: string;
  /** Filter by tags */
  tags?: string[];
}

// ==================== Transaction Types ====================

/**
 * Gas estimation for a transaction.
 */
export interface GasEstimate {
  /** Estimated gas limit */
  gas_limit: number;
  /** Gas price in Gwei */
  gas_price_gwei: string;
  /** Maximum fee per gas in Gwei (EIP-1559) */
  max_fee_gwei: string;
  /** Maximum priority fee in Gwei (EIP-1559) */
  max_priority_fee_gwei: string;
  /** Estimated cost in Wei */
  estimated_cost_wei: number;
  /** Estimated cost in USD */
  estimated_cost_usd?: string;
}

/**
 * Transaction status on the blockchain.
 */
export interface TransactionStatus {
  /** Transaction hash */
  tx_hash: string;
  /** Chain identifier */
  chain: string;
  /** Current status */
  status: 'pending' | 'submitted' | 'confirming' | 'confirmed' | 'failed';
  /** Block number (if confirmed) */
  block_number?: number;
  /** Number of confirmations */
  confirmations: number;
}

/**
 * Information about a supported blockchain.
 */
export interface ChainInfo {
  /** Chain display name */
  name: string;
  /** Chain ID */
  chain_id: number;
  /** Native token symbol */
  native_token: string;
  /** Average block time in seconds */
  block_time: number;
  /** Block explorer URL */
  explorer: string;
}

// ==================== Ledger Types ====================

/**
 * A ledger entry recording a transaction.
 */
export interface LedgerEntry {
  /** Transaction ID */
  tx_id: string;
  /** Related mandate ID */
  mandate_id?: string;
  /** Source wallet address */
  from_wallet?: string;
  /** Destination wallet address */
  to_wallet?: string;
  /** Transaction amount */
  amount: string;
  /** Currency/token */
  currency: string;
  /** Chain where executed */
  chain?: string;
  /** Blockchain transaction hash */
  chain_tx_hash?: string;
  /** Audit anchor hash */
  audit_anchor?: string;
  /** ISO 8601 timestamp of creation */
  created_at: string;
}

// ==================== Error Types ====================

/**
 * Sardis error details structure.
 */
export interface SardisErrorDetails {
  /** Error code */
  code: string;
  /** Error message */
  message: string;
  /** Additional details */
  details?: Record<string, unknown>;
  /** Request ID for support */
  request_id?: string;
}

// ==================== Agent Types ====================

/**
 * Key algorithm for agent signing.
 */
export type KeyAlgorithm = 'ed25519' | 'ecdsa-p256';

/**
 * Spending limits for an agent.
 */
export interface SpendingLimits {
  /** Per-transaction limit */
  per_transaction?: string;
  /** Daily spending limit */
  daily?: string;
  /** Monthly spending limit */
  monthly?: string;
}

/**
 * Policy configuration for an agent.
 */
export interface AgentPolicy {
  /** Allowed merchant categories */
  allowed_categories?: string[];
  /** Blocked merchants */
  blocked_merchants?: string[];
  /** Allowed merchants (whitelist mode) */
  allowed_merchants?: string[];
  /** Maximum single transaction amount */
  max_transaction_amount?: string;
  /** Require approval above this amount */
  approval_threshold?: string;
}

/**
 * An agent in the Sardis system.
 *
 * Agents are the core identity entities that can own wallets,
 * issue mandates, and be subject to spending policies.
 */
export interface Agent {
  /** Unique agent identifier (API field) */
  agent_id: string;
  /** Backwards-compat alias (older SDKs used `id`) */
  id: string;
  /** Display name */
  name: string;
  /** Agent description */
  description?: string;
  /** Organization ID */
  organization_id?: string;
  /** Associated wallet ID */
  wallet_id?: string;
  /** Public key for signing */
  public_key?: string;
  /** Key algorithm */
  key_algorithm: KeyAlgorithm;
  /** Spending limits */
  spending_limits?: SpendingLimits;
  /** Policy configuration */
  policy?: AgentPolicy;
  /** Whether agent is active */
  is_active: boolean;
  /** Arbitrary metadata */
  metadata: Record<string, unknown>;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** ISO 8601 timestamp of last update */
  updated_at: string;
}

/**
 * Input for creating an agent.
 */
export interface CreateAgentInput {
  /** Display name (required) */
  name: string;
  /** Agent description */
  description?: string;
  /** Organization ID */
  organization_id?: string;
  /** Public key for signing */
  public_key?: string;
  /** Key algorithm */
  key_algorithm?: KeyAlgorithm;
  /** Spending limits */
  spending_limits?: SpendingLimits;
  /** Policy configuration */
  policy?: AgentPolicy;
  /** Arbitrary metadata */
  metadata?: Record<string, unknown>;
}

// ==================== Policy Types ====================

export interface PolicySpendingLimit {
  vendor_pattern: string;
  max_amount: number;
  period: string;
  currency?: string;
}

export interface ParsedPolicy {
  name: string;
  description: string;
  spending_limits?: PolicySpendingLimit[];
  requires_approval_above?: number | null;
  global_daily_limit?: number | null;
  global_monthly_limit?: number | null;
  is_active?: boolean;
  policy_id?: string | null;
  agent_id?: string | null;
  // allow additional fields from server
  [key: string]: unknown;
}

export interface PolicyPreviewResponse {
  parsed: ParsedPolicy;
  warnings: string[];
  requires_confirmation: boolean;
  confirmation_message: string;
}

export interface ApplyPolicyFromNLResponse {
  success: boolean;
  policy_id: string;
  agent_id: string;
  trust_level?: string;
  limit_per_tx?: string;
  limit_total?: string;
  merchant_rules_count?: number;
  message?: string;
  [key: string]: unknown;
}

export interface PolicyCheckResponse {
  allowed: boolean;
  reason: string;
  policy_id?: string | null;
}

// ==================== Cards Types ====================

export type CardStatus = 'pending' | 'active' | 'frozen' | 'cancelled' | string;

export interface Card {
  id: string; // internal UUID
  card_id: string; // stable external ID (vc_...)
  wallet_id: string;
  provider: string;
  provider_card_id?: string | null;
  card_type: string;
  status: CardStatus;
  limit_per_tx: number;
  limit_daily: number;
  limit_monthly: number;
  funded_amount?: number;
  created_at?: string;
  [key: string]: unknown;
}

export interface IssueCardInput {
  wallet_id: string;
  card_type?: string;
  limit_per_tx?: string;
  limit_daily?: string;
  limit_monthly?: string;
  locked_merchant_id?: string | null;
  funding_source?: string;
}

export interface UpdateCardLimitsInput {
  limit_per_tx?: string;
  limit_daily?: string;
  limit_monthly?: string;
}

export interface SimulateCardPurchaseInput {
  amount: string;
  currency?: string;
  merchant_name?: string;
  mcc_code?: string;
  status?: string;
  decline_reason?: string | null;
}

export interface CardTransaction {
  transaction_id: string;
  card_id: string;
  amount: string;
  currency: string;
  merchant_name: string;
  merchant_category: string;
  status: string;
  created_at: string;
  settled_at?: string | null;
  decline_reason?: string | null;
  [key: string]: unknown;
}

export interface SimulateCardPurchaseResponse {
  transaction: CardTransaction;
  policy: { allowed: boolean; reason: string };
  card: Card;
}

/**
 * Input for updating an agent.
 */
// ==================== Agent Group Types ====================

/**
 * Budget limits for an agent group.
 */
export interface GroupBudget {
  /** Per-transaction limit */
  per_transaction?: string;
  /** Daily spending limit */
  daily?: string;
  /** Monthly spending limit */
  monthly?: string;
  /** Total spending limit */
  total?: string;
}

/**
 * Merchant policy for an agent group.
 */
export interface GroupMerchantPolicy {
  /** Allowed merchants (whitelist mode) */
  allowed_merchants?: string[];
  /** Blocked merchants */
  blocked_merchants?: string[];
  /** Allowed categories */
  allowed_categories?: string[];
  /** Blocked categories */
  blocked_categories?: string[];
}

/**
 * An agent group with shared budget and policies.
 */
export interface AgentGroup {
  /** Unique group identifier */
  group_id: string;
  /** Display name */
  name: string;
  /** Organization/user who owns this group */
  owner_id: string;
  /** Shared budget limits */
  budget: GroupBudget;
  /** Merchant policy */
  merchant_policy: GroupMerchantPolicy;
  /** IDs of agents in this group */
  agent_ids: string[];
  /** Arbitrary metadata */
  metadata: Record<string, unknown>;
  /** ISO 8601 timestamp of creation */
  created_at: string;
  /** ISO 8601 timestamp of last update */
  updated_at: string;
}

/**
 * Input for creating an agent group.
 */
export interface CreateGroupInput {
  /** Display name (required) */
  name: string;
  /** Budget limits */
  budget?: GroupBudget;
  /** Merchant policy */
  merchant_policy?: GroupMerchantPolicy;
  /** Arbitrary metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Input for updating an agent group.
 */
export interface UpdateGroupInput {
  /** Display name */
  name?: string;
  /** Budget limits */
  budget?: GroupBudget;
  /** Merchant policy */
  merchant_policy?: GroupMerchantPolicy;
  /** Arbitrary metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Spending summary for a group.
 */
export interface GroupSpending {
  /** Group ID */
  group_id: string;
  /** Group name */
  name: string;
  /** Budget configuration */
  budget: GroupBudget;
  /** Number of agents in the group */
  agent_count: number;
  /** Agent IDs */
  agent_ids: string[];
}

export interface UpdateAgentInput {
  /** Display name */
  name?: string;
  /** Agent description */
  description?: string;
  /** Spending limits */
  spending_limits?: SpendingLimits;
  /** Policy configuration */
  policy?: AgentPolicy;
  /** Whether agent is active */
  is_active?: boolean;
  /** Arbitrary metadata (merged with existing) */
  metadata?: Record<string, unknown>;
}

/**
 * Options for listing agents.
 */
export interface ListAgentsOptions {
  /** Maximum number of agents to return */
  limit?: number;
  /** Pagination offset */
  offset?: number;
  /** Filter by active status */
  is_active?: boolean;
}

// ==================== Bulk Operation Types ====================

/**
 * A single operation in a bulk request.
 */
export interface BulkOperation<T = unknown> {
  /** HTTP method */
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  /** API path */
  path: string;
  /** Query parameters */
  params?: Record<string, unknown>;
  /** Request body */
  data?: T;
}

/**
 * Result of a single bulk operation.
 *
 * @typeParam T - The expected response type
 */
export type BulkOperationResult<T> =
  | { success: true; data: T }
  | { success: false; error: Error };

/**
 * Options for bulk operations.
 */
export interface BulkOptions {
  /** Maximum concurrent requests (default: 5) */
  concurrency?: number;
  /** Stop on first error (default: false) */
  stopOnError?: boolean;
  /** AbortSignal for cancellation */
  signal?: AbortSignal;
}
