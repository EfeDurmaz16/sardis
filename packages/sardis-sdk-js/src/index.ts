/**
 * Sardis TypeScript SDK
 *
 * Official SDK for the Sardis stablecoin execution layer.
 * Enables AI agents to execute programmable payments using stablecoins.
 *
 * @example
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
 */

// Main client
export { SardisClient } from './client.js';

// Errors
export {
  SardisError,
  APIError,
  AuthenticationError,
  RateLimitError,
  ValidationError,
  InsufficientBalanceError,
  NotFoundError,
} from './errors.js';

// Types
export type {
  // Common
  Chain,
  Token,
  MPCProvider,
  SardisClientOptions,
  // Wallets
  Wallet,
  WalletBalance,
  TokenLimit,
  CreateWalletInput,
  SetAddressInput,
  // Payments
  Payment,
  PaymentStatus,
  ExecutePaymentInput,
  ExecuteAP2Input,
  ExecutePaymentResponse,
  ExecuteAP2Response,
  // Holds
  Hold,
  HoldStatus,
  CreateHoldInput,
  CaptureHoldInput,
  CreateHoldResponse,
  // Webhooks
  Webhook,
  WebhookDelivery,
  WebhookEventType,
  CreateWebhookInput,
  UpdateWebhookInput,
  // Marketplace
  Service,
  ServiceOffer,
  ServiceReview,
  ServiceCategory,
  ServiceStatus,
  OfferStatus,
  CreateServiceInput,
  CreateOfferInput,
  SearchServicesInput,
  // Transactions
  GasEstimate,
  TransactionStatus,
  ChainInfo,
  // Ledger
  LedgerEntry,
} from './types.js';
