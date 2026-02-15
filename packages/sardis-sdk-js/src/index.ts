/**
 * Sardis TypeScript SDK
 *
 * Official SDK for the Sardis stablecoin execution layer.
 * Enables AI agents to execute programmable payments using stablecoins.
 *
 * @packageDocumentation
 *
 * @example Basic usage
 * ```typescript
 * import { SardisClient } from '@sardis/sdk';
 *
 * const client = new SardisClient({
 *   apiKey: 'your-api-key',
 * });
 *
 * // Execute a payment
 * const result = await client.payments.executeMandate(mandate);
 *
 * // Create a hold
 * const hold = await client.holds.create({
 *   wallet_id: 'wallet_123',
 *   amount: '100.00',
 * });
 * ```
 *
 * @example With request cancellation
 * ```typescript
 * const controller = new AbortController();
 *
 * // Cancel after 5 seconds
 * setTimeout(() => controller.abort(), 5000);
 *
 * try {
 *   const result = await client.payments.executeMandate(mandate, {
 *     signal: controller.signal,
 *   });
 * } catch (error) {
 *   if (error instanceof AbortError) {
 *     console.log('Request was cancelled');
 *   }
 * }
 * ```
 *
 * @example With interceptors
 * ```typescript
 * client.addRequestInterceptor({
 *   onRequest: (config) => {
 *     console.log(`Requesting ${config.method} ${config.url}`);
 *     return config;
 *   },
 * });
 * ```
 *
 * @example With pagination
 * ```typescript
 * for await (const agent of client.paginate(
 *   (params) => client.agents.list(params),
 *   { limit: 100 }
 * )) {
 *   console.log(agent.name);
 * }
 * ```
 */

// Main client
export { SardisClient } from './client.js';

// Errors
export {
  // Error base class
  SardisError,
  // API errors
  APIError,
  AuthenticationError,
  RateLimitError,
  // Network errors
  TimeoutError,
  AbortError,
  NetworkError,
  // Validation errors
  ValidationError,
  // Business logic errors
  InsufficientBalanceError,
  NotFoundError,
  PolicyViolationError,
  SpendingLimitError,
  BlockchainError,
  // Error codes
  SardisErrorCode,
  // Type guards
  isSardisError,
  isRetryableError,
} from './errors.js';

// Types - Client configuration
export type {
  SardisClientOptions,
  RequestOptions,
  RequestInterceptor,
  ResponseInterceptor,
  RetryConfig,
  TokenRefreshConfig,
  PaginationParams,
  PaginatedResponse,
} from './types.js';

// Types - Common
export type {
  Chain,
  Token,
  MPCProvider,
} from './types.js';

// Types - Wallets
export type {
  Wallet,
  WalletBalance,
  TokenLimit,
  CreateWalletInput,
  SetAddressInput,
  WalletTransferInput,
  WalletTransferResponse,
} from './types.js';

// Types - Policies
export type {
  ParsedPolicy,
  PolicyPreviewResponse,
  ApplyPolicyFromNLResponse,
  PolicyCheckResponse,
} from './types.js';

// Types - Cards
export type {
  Card,
  CardStatus,
  IssueCardInput,
  UpdateCardLimitsInput,
  SimulateCardPurchaseInput,
  SimulateCardPurchaseResponse,
  CardTransaction,
} from './types.js';

// Types - Treasury
export type {
  TreasuryVerificationMethod,
  TreasuryOwnerType,
  TreasuryAccountType,
  TreasuryAchMethod,
  TreasurySecCode,
  FinancialAccount,
  TreasuryAddress,
  CreateExternalBankAccountInput,
  ExternalBankAccount,
  VerifyMicroDepositsInput,
  TreasuryPaymentInput,
  TreasuryPaymentResponse,
  TreasuryBalance,
} from './types.js';

// Types - Payments
export type {
  Payment,
  PaymentStatus,
  ExecutePaymentInput,
  ExecuteAP2Input,
  ExecutePaymentResponse,
  ExecuteAP2Response,
} from './types.js';

// Types - Holds
export type {
  Hold,
  HoldStatus,
  CreateHoldInput,
  CaptureHoldInput,
  CreateHoldResponse,
} from './types.js';

// Types - Webhooks
export type {
  Webhook,
  WebhookDelivery,
  WebhookEventType,
  CreateWebhookInput,
  UpdateWebhookInput,
} from './types.js';

// Types - Marketplace
export type {
  Service,
  ServiceOffer,
  ServiceReview,
  ServiceCategory,
  ServiceStatus,
  OfferStatus,
  CreateServiceInput,
  CreateOfferInput,
  SearchServicesInput,
} from './types.js';

// Types - Transactions
export type {
  GasEstimate,
  TransactionStatus,
  ChainInfo,
} from './types.js';

// Types - Ledger
export type {
  LedgerEntry,
} from './types.js';

// Types - Agents
export type {
  Agent,
  CreateAgentInput,
  UpdateAgentInput,
  ListAgentsOptions,
  SpendingLimits,
  AgentPolicy,
  KeyAlgorithm,
} from './types.js';

// Types - Bulk operations
export type {
  BulkOperation,
  BulkOperationResult,
  BulkOptions,
} from './types.js';

// Types - Errors
export type {
  ErrorDetails,
} from './errors.js';

export type {
  SardisErrorDetails,
} from './types.js';

// Integrations
export * as integrations from './integrations/index.js';
