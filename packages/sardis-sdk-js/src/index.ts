/**
 * @sardis/sdk — DEPRECATED.
 *
 * This package is now a thin re-export shim over `sardis@^2`. New code
 * should `npm install sardis` and `import { Sardis } from "sardis"`.
 *
 * Migration:
 *
 * ```diff
 * - import { SardisClient } from "@sardis/sdk";
 * + import { Sardis } from "sardis";
 * - const client = new SardisClient({ apiKey });
 * + const sardis = new Sardis({ apiKey });
 * ```
 *
 * Run `npx sardis-migrate` to apply this codemod automatically (see
 * packages/sardis-js/scripts/migrate.js).
 *
 * This shim will be removed after one minor cycle (target: sardis@2.1).
 */

let warned = false;
function emitDeprecationWarning(): void {
  if (warned) return;
  warned = true;
  const msg =
    '[@sardis/sdk] DEPRECATED — use the `sardis` package instead. Run `npx sardis-migrate` to upgrade. See https://sardis.sh/docs/ts-migration';
  if (typeof process !== 'undefined' && process.emitWarning) {
    process.emitWarning(msg, 'DeprecationWarning');
  } else if (typeof console !== 'undefined') {
    console.warn(msg);
  }
}

emitDeprecationWarning();

/* eslint-disable @typescript-eslint/no-explicit-any */

// Re-export everything from sardis@2. `SardisClient` is aliased to the new
// `Sardis` class so existing imports continue to compile.
export { Sardis as SardisClient, Sardis } from 'sardis';
export type {
  SardisClientOptions,
  RequestOptions,
  RetryConfig,
  TokenRefreshConfig,
  TelemetryConfig,
  HTTPMethod,
  SardisResponse,
  PaginationParams,
  PaginatedResponse,
  RequestInterceptor,
  ResponseInterceptor,
} from 'sardis';
export {
  Engine,
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
} from 'sardis';
export type { ErrorDetails } from 'sardis';
// Resource classes + every domain type
export * from 'sardis';
