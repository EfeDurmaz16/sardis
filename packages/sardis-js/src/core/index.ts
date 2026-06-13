/**
 * `sardis/core` — low-level HTTP engine, types, and error classes.
 *
 * Use this only when building custom resources or layering your own
 * SDK on top of the Sardis HTTP surface. The 90% surface lives at the
 * package root (`sardis`).
 */

export { Engine } from './engine.js';
export { BaseResource } from './base-resource.js';
export type {
  SardisClientOptions,
  RequestOptions,
  RequestInterceptor,
  ResponseInterceptor,
  RetryConfig,
  TokenRefreshConfig,
  TelemetryConfig,
  HTTPMethod,
  NormalizedRequest,
  SardisResponse,
  PaginationParams,
  PaginatedResponse,
} from './types.js';
export {
  SardisError,
  APIError,
  BadRequestError,
  AuthenticationError,
  PermissionDeniedError,
  NotFoundError,
  ConflictError,
  UnprocessableEntityError,
  RateLimitError,
  InternalServerError,
  TimeoutError,
  AbortError,
  NetworkError,
  APIConnectionError,
  APIConnectionTimeoutError,
  APIUserAbortError,
  ValidationError,
  InsufficientBalanceError,
  PolicyViolationError,
  SpendingLimitError,
  BlockchainError,
  SardisErrorCode,
  isSardisError,
  isRetryableError,
} from './errors.js';
export type { ErrorDetails } from './errors.js';
export { Page } from './pagination.js';
export type { PageParams, PageResponse, PageFetcher } from './pagination.js';
