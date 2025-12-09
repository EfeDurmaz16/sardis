/**
 * Sardis SDK Error Classes
 */

export interface ErrorDetails {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id?: string;
}

/**
 * Base error class for Sardis SDK
 */
export class SardisError extends Error {
  public readonly code: string;
  public readonly details: Record<string, unknown>;
  public readonly requestId?: string;

  constructor(
    message: string,
    code: string = 'SARDIS_ERROR',
    details: Record<string, unknown> = {},
    requestId?: string
  ) {
    super(message);
    this.name = 'SardisError';
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }

  toJSON(): ErrorDetails {
    return {
      code: this.code,
      message: this.message,
      details: this.details,
      request_id: this.requestId,
    };
  }
}

/**
 * API error from HTTP response
 */
export class APIError extends SardisError {
  public readonly statusCode: number;

  constructor(
    message: string,
    statusCode: number,
    code: string = 'API_ERROR',
    details: Record<string, unknown> = {},
    requestId?: string
  ) {
    super(message, code, details, requestId);
    this.name = 'APIError';
    this.statusCode = statusCode;
  }

  static fromResponse(statusCode: number, body: Record<string, unknown>): APIError {
    const error = body.error || body.detail || body;
    if (typeof error === 'string') {
      return new APIError(error, statusCode, 'API_ERROR');
    }
    return new APIError(
      (error as Record<string, unknown>).message as string || 'Unknown error',
      statusCode,
      (error as Record<string, unknown>).code as string || 'API_ERROR',
      (error as Record<string, unknown>).details as Record<string, unknown>,
      (error as Record<string, unknown>).request_id as string
    );
  }
}

/**
 * Authentication error
 */
export class AuthenticationError extends SardisError {
  constructor(message: string = 'Invalid or missing API key') {
    super(message, 'AUTHENTICATION_ERROR');
    this.name = 'AuthenticationError';
  }
}

/**
 * Rate limit exceeded error
 */
export class RateLimitError extends SardisError {
  public readonly retryAfter?: number;

  constructor(message: string = 'Rate limit exceeded', retryAfter?: number) {
    super(message, 'RATE_LIMIT_EXCEEDED');
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

/**
 * Validation error
 */
export class ValidationError extends SardisError {
  public readonly field?: string;

  constructor(message: string, field?: string) {
    super(message, 'VALIDATION_ERROR', { field });
    this.name = 'ValidationError';
    this.field = field;
  }
}

/**
 * Insufficient balance error
 */
export class InsufficientBalanceError extends SardisError {
  public readonly required: string;
  public readonly available: string;
  public readonly currency: string;

  constructor(message: string, required: string, available: string, currency: string) {
    super(message, 'INSUFFICIENT_BALANCE', { required, available, currency });
    this.name = 'InsufficientBalanceError';
    this.required = required;
    this.available = available;
    this.currency = currency;
  }
}

/**
 * Resource not found error
 */
export class NotFoundError extends SardisError {
  public readonly resourceType: string;
  public readonly resourceId: string;

  constructor(resourceType: string, resourceId: string) {
    super(`${resourceType} not found: ${resourceId}`, 'NOT_FOUND', {
      resource_type: resourceType,
      resource_id: resourceId,
    });
    this.name = 'NotFoundError';
    this.resourceType = resourceType;
    this.resourceId = resourceId;
  }
}
