/**
 * `sardis` — Official TypeScript SDK for Sardis.
 *
 * ## Quickstart
 *
 * ```ts
 * import { Sardis } from "sardis";
 *
 * const sardis = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });
 * await sardis.pay({ to: "merchant_abc", amount: 25_00 });
 * ```
 *
 * TASK-1 ships the HTTP core only. Resource namespaces (`sardis.payments`,
 * `sardis.wallets`, ...) land in TASK-2. The full `Sardis` class will be
 * assembled there. For now, the root exports `Engine` + errors so that
 * downstream tasks and tests can build on it.
 */

export { Engine } from './core/engine.js';
export type {
  SardisClientOptions,
  RequestOptions,
  RequestInterceptor,
  ResponseInterceptor,
  RetryConfig,
  TokenRefreshConfig,
  TelemetryConfig,
  HTTPMethod,
  SardisResponse,
  PaginationParams,
  PaginatedResponse,
} from './core/types.js';
export {
  SardisError,
  APIError,
  AuthenticationError,
  RateLimitError,
  TimeoutError,
  AbortError,
  NetworkError,
  ValidationError,
  InsufficientBalanceError,
  NotFoundError,
  PolicyViolationError,
  SpendingLimitError,
  BlockchainError,
  SardisErrorCode,
  isSardisError,
  isRetryableError,
} from './core/errors.js';
export type { ErrorDetails } from './core/errors.js';
