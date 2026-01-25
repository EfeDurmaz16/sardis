/**
 * Sardis SDK Error Classes
 *
 * Comprehensive error types for the Sardis SDK with standardized error codes
 * for better error handling and debugging.
 *
 * @packageDocumentation
 */

/**
 * Error codes used throughout the Sardis SDK.
 * These codes provide machine-readable error identification.
 */
export enum SardisErrorCode {
  // General errors (1xxx)
  UNKNOWN_ERROR = 'SARDIS_1000',
  CONFIGURATION_ERROR = 'SARDIS_1001',
  INITIALIZATION_ERROR = 'SARDIS_1002',
  INVALID_ARGUMENT = 'SARDIS_1003',

  // Authentication errors (2xxx)
  AUTHENTICATION_ERROR = 'SARDIS_2000',
  INVALID_API_KEY = 'SARDIS_2001',
  EXPIRED_TOKEN = 'SARDIS_2002',
  INSUFFICIENT_PERMISSIONS = 'SARDIS_2003',
  TOKEN_REFRESH_FAILED = 'SARDIS_2004',

  // API errors (3xxx)
  API_ERROR = 'SARDIS_3000',
  BAD_REQUEST = 'SARDIS_3400',
  UNAUTHORIZED = 'SARDIS_3401',
  FORBIDDEN = 'SARDIS_3403',
  NOT_FOUND = 'SARDIS_3404',
  METHOD_NOT_ALLOWED = 'SARDIS_3405',
  CONFLICT = 'SARDIS_3409',
  UNPROCESSABLE_ENTITY = 'SARDIS_3422',
  RATE_LIMIT_EXCEEDED = 'SARDIS_3429',
  INTERNAL_SERVER_ERROR = 'SARDIS_3500',
  SERVICE_UNAVAILABLE = 'SARDIS_3503',

  // Network errors (4xxx)
  NETWORK_ERROR = 'SARDIS_4000',
  TIMEOUT_ERROR = 'SARDIS_4001',
  CONNECTION_ERROR = 'SARDIS_4002',
  REQUEST_ABORTED = 'SARDIS_4003',
  DNS_ERROR = 'SARDIS_4004',
  SSL_ERROR = 'SARDIS_4005',

  // Validation errors (5xxx)
  VALIDATION_ERROR = 'SARDIS_5000',
  MISSING_REQUIRED_FIELD = 'SARDIS_5001',
  INVALID_FORMAT = 'SARDIS_5002',
  VALUE_OUT_OF_RANGE = 'SARDIS_5003',
  INVALID_CHAIN = 'SARDIS_5004',
  INVALID_TOKEN = 'SARDIS_5005',
  INVALID_ADDRESS = 'SARDIS_5006',

  // Business logic errors (6xxx)
  INSUFFICIENT_BALANCE = 'SARDIS_6000',
  SPENDING_LIMIT_EXCEEDED = 'SARDIS_6001',
  POLICY_VIOLATION = 'SARDIS_6002',
  WALLET_INACTIVE = 'SARDIS_6003',
  HOLD_EXPIRED = 'SARDIS_6004',
  HOLD_ALREADY_CAPTURED = 'SARDIS_6005',
  HOLD_ALREADY_VOIDED = 'SARDIS_6006',
  DUPLICATE_TRANSACTION = 'SARDIS_6007',
  AGENT_INACTIVE = 'SARDIS_6008',

  // Blockchain errors (7xxx)
  BLOCKCHAIN_ERROR = 'SARDIS_7000',
  TRANSACTION_FAILED = 'SARDIS_7001',
  GAS_ESTIMATION_FAILED = 'SARDIS_7002',
  NONCE_ERROR = 'SARDIS_7003',
  CONTRACT_ERROR = 'SARDIS_7004',
  CHAIN_UNAVAILABLE = 'SARDIS_7005',
}

/**
 * Detailed error information structure.
 */
export interface ErrorDetails {
  /** Machine-readable error code */
  code: string;
  /** Human-readable error message */
  message: string;
  /** Additional error context */
  details?: Record<string, unknown>;
  /** Request ID for support reference */
  request_id?: string;
  /** HTTP status code (if applicable) */
  status_code?: number;
  /** Timestamp when error occurred */
  timestamp?: string;
}

/**
 * Base error class for all Sardis SDK errors.
 *
 * All errors thrown by the SDK extend this class, providing consistent
 * error handling capabilities across the SDK.
 *
 * @example
 * ```typescript
 * try {
 *   await client.payments.executeMandate(mandate);
 * } catch (error) {
 *   if (error instanceof SardisError) {
 *     console.error(`Error [${error.code}]: ${error.message}`);
 *     console.error('Request ID:', error.requestId);
 *   }
 * }
 * ```
 */
export class SardisError extends Error {
  /** Machine-readable error code */
  public readonly code: string;
  /** Additional error context */
  public readonly details: Record<string, unknown>;
  /** Request ID for support reference */
  public readonly requestId?: string;
  /** Timestamp when error occurred */
  public readonly timestamp: string;
  /** Whether the error is retryable */
  public readonly retryable: boolean;

  /**
   * Creates a new SardisError instance.
   *
   * @param message - Human-readable error message
   * @param code - Machine-readable error code
   * @param details - Additional error context
   * @param requestId - Request ID for support reference
   * @param retryable - Whether the operation can be retried
   */
  constructor(
    message: string,
    code: string = SardisErrorCode.UNKNOWN_ERROR,
    details: Record<string, unknown> = {},
    requestId?: string,
    retryable: boolean = false
  ) {
    super(message);
    this.name = 'SardisError';
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.retryable = retryable;
    this.timestamp = new Date().toISOString();

    // Ensure proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, SardisError.prototype);
  }

  /**
   * Converts the error to a JSON-serializable object.
   *
   * @returns Error details as a plain object
   */
  toJSON(): ErrorDetails {
    return {
      code: this.code,
      message: this.message,
      details: this.details,
      request_id: this.requestId,
      timestamp: this.timestamp,
    };
  }

  /**
   * Returns a string representation of the error.
   *
   * @returns Formatted error string
   */
  toString(): string {
    const parts = [`[${this.code}] ${this.message}`];
    if (this.requestId) {
      parts.push(`(Request ID: ${this.requestId})`);
    }
    return parts.join(' ');
  }
}

/**
 * API error from HTTP response.
 *
 * Thrown when the Sardis API returns an error response (4xx or 5xx status codes).
 *
 * @example
 * ```typescript
 * try {
 *   await client.wallets.get('invalid_id');
 * } catch (error) {
 *   if (error instanceof APIError) {
 *     console.error(`HTTP ${error.statusCode}: ${error.message}`);
 *   }
 * }
 * ```
 */
export class APIError extends SardisError {
  /** HTTP status code */
  public readonly statusCode: number;
  /** Response headers (if available) */
  public readonly headers?: Record<string, string>;

  /**
   * Creates a new APIError instance.
   *
   * @param message - Human-readable error message
   * @param statusCode - HTTP status code
   * @param code - Machine-readable error code
   * @param details - Additional error context
   * @param requestId - Request ID for support reference
   * @param headers - Response headers
   */
  constructor(
    message: string,
    statusCode: number,
    code: string = SardisErrorCode.API_ERROR,
    details: Record<string, unknown> = {},
    requestId?: string,
    headers?: Record<string, string>
  ) {
    // Determine if retryable based on status code
    const retryable = statusCode >= 500 || statusCode === 429;
    super(message, code, details, requestId, retryable);
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.headers = headers;
    Object.setPrototypeOf(this, APIError.prototype);
  }

  /**
   * Creates an APIError from an HTTP response.
   *
   * @param statusCode - HTTP status code
   * @param body - Response body
   * @param headers - Response headers
   * @returns APIError instance
   */
  static fromResponse(
    statusCode: number,
    body: Record<string, unknown>,
    headers?: Record<string, string>
  ): APIError {
    const error = body.error || body.detail || body;
    const errorCode = APIError.getErrorCodeForStatus(statusCode);

    if (typeof error === 'string') {
      return new APIError(error, statusCode, errorCode, {}, undefined, headers);
    }

    const errorObj = error as Record<string, unknown>;
    return new APIError(
      (errorObj.message as string) || 'Unknown API error',
      statusCode,
      (errorObj.code as string) || errorCode,
      (errorObj.details as Record<string, unknown>) || {},
      errorObj.request_id as string,
      headers
    );
  }

  /**
   * Maps HTTP status codes to Sardis error codes.
   */
  private static getErrorCodeForStatus(statusCode: number): string {
    switch (statusCode) {
      case 400:
        return SardisErrorCode.BAD_REQUEST;
      case 401:
        return SardisErrorCode.UNAUTHORIZED;
      case 403:
        return SardisErrorCode.FORBIDDEN;
      case 404:
        return SardisErrorCode.NOT_FOUND;
      case 405:
        return SardisErrorCode.METHOD_NOT_ALLOWED;
      case 409:
        return SardisErrorCode.CONFLICT;
      case 422:
        return SardisErrorCode.UNPROCESSABLE_ENTITY;
      case 429:
        return SardisErrorCode.RATE_LIMIT_EXCEEDED;
      case 500:
        return SardisErrorCode.INTERNAL_SERVER_ERROR;
      case 503:
        return SardisErrorCode.SERVICE_UNAVAILABLE;
      default:
        return SardisErrorCode.API_ERROR;
    }
  }

  /**
   * Converts the error to a JSON-serializable object.
   */
  override toJSON(): ErrorDetails {
    return {
      ...super.toJSON(),
      status_code: this.statusCode,
    };
  }
}

/**
 * Authentication error.
 *
 * Thrown when authentication fails due to invalid or missing credentials.
 *
 * @example
 * ```typescript
 * try {
 *   await client.health();
 * } catch (error) {
 *   if (error instanceof AuthenticationError) {
 *     console.error('Please check your API key');
 *   }
 * }
 * ```
 */
export class AuthenticationError extends SardisError {
  /**
   * Creates a new AuthenticationError instance.
   *
   * @param message - Human-readable error message
   * @param code - Machine-readable error code
   */
  constructor(
    message: string = 'Invalid or missing API key',
    code: string = SardisErrorCode.AUTHENTICATION_ERROR
  ) {
    super(message, code, {}, undefined, false);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

/**
 * Rate limit exceeded error.
 *
 * Thrown when the API rate limit has been exceeded. Includes retry information.
 *
 * @example
 * ```typescript
 * try {
 *   await client.payments.executeMandate(mandate);
 * } catch (error) {
 *   if (error instanceof RateLimitError) {
 *     console.log(`Rate limited. Retry after ${error.retryAfter} seconds`);
 *     await sleep(error.retryAfter * 1000);
 *   }
 * }
 * ```
 */
export class RateLimitError extends SardisError {
  /** Seconds to wait before retrying */
  public readonly retryAfter?: number;
  /** Rate limit quota (requests per period) */
  public readonly limit?: number;
  /** Remaining requests in current period */
  public readonly remaining?: number;
  /** Timestamp when rate limit resets */
  public readonly resetAt?: Date;

  /**
   * Creates a new RateLimitError instance.
   *
   * @param message - Human-readable error message
   * @param retryAfter - Seconds to wait before retrying
   * @param limit - Rate limit quota
   * @param remaining - Remaining requests
   * @param resetAt - Reset timestamp
   */
  constructor(
    message: string = 'Rate limit exceeded',
    retryAfter?: number,
    limit?: number,
    remaining?: number,
    resetAt?: Date
  ) {
    super(
      message,
      SardisErrorCode.RATE_LIMIT_EXCEEDED,
      { retry_after: retryAfter, limit, remaining },
      undefined,
      true
    );
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
    this.limit = limit;
    this.remaining = remaining;
    this.resetAt = resetAt;
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}

/**
 * Request timeout error.
 *
 * Thrown when a request times out before completing.
 *
 * @example
 * ```typescript
 * try {
 *   await client.payments.executeMandate(mandate);
 * } catch (error) {
 *   if (error instanceof TimeoutError) {
 *     console.error(`Request timed out after ${error.timeout}ms`);
 *   }
 * }
 * ```
 */
export class TimeoutError extends SardisError {
  /** Timeout duration in milliseconds */
  public readonly timeout: number;

  /**
   * Creates a new TimeoutError instance.
   *
   * @param message - Human-readable error message
   * @param timeout - Timeout duration in milliseconds
   */
  constructor(message: string = 'Request timed out', timeout: number = 30000) {
    super(message, SardisErrorCode.TIMEOUT_ERROR, { timeout_ms: timeout }, undefined, true);
    this.name = 'TimeoutError';
    this.timeout = timeout;
    Object.setPrototypeOf(this, TimeoutError.prototype);
  }
}

/**
 * Request aborted error.
 *
 * Thrown when a request is cancelled via AbortController.
 *
 * @example
 * ```typescript
 * const controller = new AbortController();
 * setTimeout(() => controller.abort(), 1000);
 *
 * try {
 *   await client.payments.executeMandate(mandate, { signal: controller.signal });
 * } catch (error) {
 *   if (error instanceof AbortError) {
 *     console.log('Request was cancelled');
 *   }
 * }
 * ```
 */
export class AbortError extends SardisError {
  /**
   * Creates a new AbortError instance.
   *
   * @param message - Human-readable error message
   */
  constructor(message: string = 'Request was aborted') {
    super(message, SardisErrorCode.REQUEST_ABORTED, {}, undefined, false);
    this.name = 'AbortError';
    Object.setPrototypeOf(this, AbortError.prototype);
  }
}

/**
 * Network error.
 *
 * Thrown when a network-level error occurs (connection refused, DNS failure, etc.).
 *
 * @example
 * ```typescript
 * try {
 *   await client.health();
 * } catch (error) {
 *   if (error instanceof NetworkError) {
 *     console.error('Network error:', error.cause);
 *   }
 * }
 * ```
 */
export class NetworkError extends SardisError {
  /** Original error that caused this error */
  public readonly cause?: Error;

  /**
   * Creates a new NetworkError instance.
   *
   * @param message - Human-readable error message
   * @param cause - Original error
   * @param code - Machine-readable error code
   */
  constructor(
    message: string = 'Network error occurred',
    cause?: Error,
    code: string = SardisErrorCode.NETWORK_ERROR
  ) {
    super(message, code, { original_error: cause?.message }, undefined, true);
    this.name = 'NetworkError';
    this.cause = cause;
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

/**
 * Validation error.
 *
 * Thrown when input validation fails.
 *
 * @example
 * ```typescript
 * try {
 *   await client.holds.create({ wallet_id: '', amount: '-100' });
 * } catch (error) {
 *   if (error instanceof ValidationError) {
 *     console.error(`Validation failed for ${error.field}: ${error.message}`);
 *   }
 * }
 * ```
 */
export class ValidationError extends SardisError {
  /** Field that failed validation */
  public readonly field?: string;
  /** Expected value or format */
  public readonly expected?: string;
  /** Actual value received */
  public readonly received?: unknown;

  /**
   * Creates a new ValidationError instance.
   *
   * @param message - Human-readable error message
   * @param field - Field that failed validation
   * @param expected - Expected value or format
   * @param received - Actual value received
   */
  constructor(message: string, field?: string, expected?: string, received?: unknown) {
    super(message, SardisErrorCode.VALIDATION_ERROR, { field, expected, received });
    this.name = 'ValidationError';
    this.field = field;
    this.expected = expected;
    this.received = received;
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

/**
 * Insufficient balance error.
 *
 * Thrown when a payment cannot be completed due to insufficient funds.
 *
 * @example
 * ```typescript
 * try {
 *   await client.payments.executeMandate(mandate);
 * } catch (error) {
 *   if (error instanceof InsufficientBalanceError) {
 *     console.error(
 *       `Need ${error.required} ${error.currency} but only have ${error.available}`
 *     );
 *   }
 * }
 * ```
 */
export class InsufficientBalanceError extends SardisError {
  /** Required amount */
  public readonly required: string;
  /** Available balance */
  public readonly available: string;
  /** Currency/token */
  public readonly currency: string;
  /** Wallet ID */
  public readonly walletId?: string;

  /**
   * Creates a new InsufficientBalanceError instance.
   *
   * @param message - Human-readable error message
   * @param required - Required amount
   * @param available - Available balance
   * @param currency - Currency/token
   * @param walletId - Wallet ID
   */
  constructor(
    message: string,
    required: string,
    available: string,
    currency: string,
    walletId?: string
  ) {
    super(message, SardisErrorCode.INSUFFICIENT_BALANCE, {
      required,
      available,
      currency,
      wallet_id: walletId,
    });
    this.name = 'InsufficientBalanceError';
    this.required = required;
    this.available = available;
    this.currency = currency;
    this.walletId = walletId;
    Object.setPrototypeOf(this, InsufficientBalanceError.prototype);
  }
}

/**
 * Resource not found error.
 *
 * Thrown when a requested resource does not exist.
 *
 * @example
 * ```typescript
 * try {
 *   await client.wallets.get('nonexistent_wallet');
 * } catch (error) {
 *   if (error instanceof NotFoundError) {
 *     console.error(`${error.resourceType} not found: ${error.resourceId}`);
 *   }
 * }
 * ```
 */
export class NotFoundError extends SardisError {
  /** Type of resource (e.g., 'Wallet', 'Agent', 'Hold') */
  public readonly resourceType: string;
  /** ID of the resource */
  public readonly resourceId: string;

  /**
   * Creates a new NotFoundError instance.
   *
   * @param resourceType - Type of resource
   * @param resourceId - ID of the resource
   */
  constructor(resourceType: string, resourceId: string) {
    super(`${resourceType} not found: ${resourceId}`, SardisErrorCode.NOT_FOUND, {
      resource_type: resourceType,
      resource_id: resourceId,
    });
    this.name = 'NotFoundError';
    this.resourceType = resourceType;
    this.resourceId = resourceId;
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}

/**
 * Policy violation error.
 *
 * Thrown when an operation violates spending policies or limits.
 *
 * @example
 * ```typescript
 * try {
 *   await client.payments.executeMandate(mandate);
 * } catch (error) {
 *   if (error instanceof PolicyViolationError) {
 *     console.error(`Policy violated: ${error.policyName}`);
 *     console.error(`Limit: ${error.limit}, Attempted: ${error.attempted}`);
 *   }
 * }
 * ```
 */
export class PolicyViolationError extends SardisError {
  /** Name of the violated policy */
  public readonly policyName: string;
  /** Policy limit value */
  public readonly limit?: string;
  /** Attempted value */
  public readonly attempted?: string;

  /**
   * Creates a new PolicyViolationError instance.
   *
   * @param message - Human-readable error message
   * @param policyName - Name of the violated policy
   * @param limit - Policy limit value
   * @param attempted - Attempted value
   */
  constructor(message: string, policyName: string, limit?: string, attempted?: string) {
    super(message, SardisErrorCode.POLICY_VIOLATION, {
      policy_name: policyName,
      limit,
      attempted,
    });
    this.name = 'PolicyViolationError';
    this.policyName = policyName;
    this.limit = limit;
    this.attempted = attempted;
    Object.setPrototypeOf(this, PolicyViolationError.prototype);
  }
}

/**
 * Spending limit exceeded error.
 *
 * Thrown when a transaction exceeds configured spending limits.
 */
export class SpendingLimitError extends SardisError {
  /** Type of limit (per_transaction, daily, monthly, total) */
  public readonly limitType: string;
  /** Limit amount */
  public readonly limit: string;
  /** Attempted amount */
  public readonly attempted: string;
  /** Currency */
  public readonly currency: string;

  /**
   * Creates a new SpendingLimitError instance.
   *
   * @param message - Human-readable error message
   * @param limitType - Type of limit
   * @param limit - Limit amount
   * @param attempted - Attempted amount
   * @param currency - Currency
   */
  constructor(
    message: string,
    limitType: string,
    limit: string,
    attempted: string,
    currency: string
  ) {
    super(message, SardisErrorCode.SPENDING_LIMIT_EXCEEDED, {
      limit_type: limitType,
      limit,
      attempted,
      currency,
    });
    this.name = 'SpendingLimitError';
    this.limitType = limitType;
    this.limit = limit;
    this.attempted = attempted;
    this.currency = currency;
    Object.setPrototypeOf(this, SpendingLimitError.prototype);
  }
}

/**
 * Blockchain transaction error.
 *
 * Thrown when a blockchain transaction fails.
 */
export class BlockchainError extends SardisError {
  /** Chain where error occurred */
  public readonly chain: string;
  /** Transaction hash (if available) */
  public readonly txHash?: string;
  /** Block number (if available) */
  public readonly blockNumber?: number;

  /**
   * Creates a new BlockchainError instance.
   *
   * @param message - Human-readable error message
   * @param chain - Chain where error occurred
   * @param code - Machine-readable error code
   * @param txHash - Transaction hash
   * @param blockNumber - Block number
   */
  constructor(
    message: string,
    chain: string,
    code: string = SardisErrorCode.BLOCKCHAIN_ERROR,
    txHash?: string,
    blockNumber?: number
  ) {
    super(message, code, { chain, tx_hash: txHash, block_number: blockNumber }, undefined, false);
    this.name = 'BlockchainError';
    this.chain = chain;
    this.txHash = txHash;
    this.blockNumber = blockNumber;
    Object.setPrototypeOf(this, BlockchainError.prototype);
  }
}

/**
 * Type guard to check if an error is a SardisError.
 *
 * @param error - Error to check
 * @returns True if error is a SardisError
 */
export function isSardisError(error: unknown): error is SardisError {
  return error instanceof SardisError;
}

/**
 * Type guard to check if an error is retryable.
 *
 * @param error - Error to check
 * @returns True if error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  if (error instanceof SardisError) {
    return error.retryable;
  }
  return false;
}
