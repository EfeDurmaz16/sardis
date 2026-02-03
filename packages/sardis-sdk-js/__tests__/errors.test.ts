/**
 * Tests for Error Classes
 */
import { describe, it, expect } from 'vitest';
import {
  SardisError,
  APIError,
  AuthenticationError,
  RateLimitError,
  ValidationError,
  InsufficientBalanceError,
  NotFoundError,
} from '../src/errors.js';

describe('Error Classes', () => {
  describe('SardisError', () => {
    it('should create error with default values', () => {
      const error = new SardisError('Test error');
      expect(error.message).toBe('Test error');
      expect(error.code).toBe('SARDIS_1000');
      expect(error.details).toEqual({});
      expect(error.requestId).toBeUndefined();
      expect(error.name).toBe('SardisError');
    });

    it('should create error with all parameters', () => {
      const error = new SardisError(
        'Test error',
        'CUSTOM_CODE',
        { key: 'value' },
        'req_123'
      );
      expect(error.message).toBe('Test error');
      expect(error.code).toBe('CUSTOM_CODE');
      expect(error.details).toEqual({ key: 'value' });
      expect(error.requestId).toBe('req_123');
    });

    it('should serialize to JSON', () => {
      const error = new SardisError(
        'Test error',
        'CUSTOM_CODE',
        { key: 'value' },
        'req_123'
      );
      const json = error.toJSON();
      expect(json.code).toBe('CUSTOM_CODE');
      expect(json.message).toBe('Test error');
      expect(json.details).toEqual({ key: 'value' });
      expect(json.request_id).toBe('req_123');
      expect(json.timestamp).toBeDefined();
    });

    it('should serialize to JSON without request_id', () => {
      const error = new SardisError('Test error');
      const json = error.toJSON();
      expect(json.code).toBe('SARDIS_1000');
      expect(json.message).toBe('Test error');
      expect(json.details).toEqual({});
      expect(json.request_id).toBeUndefined();
      expect(json.timestamp).toBeDefined();
    });
  });

  describe('APIError', () => {
    it('should create API error with status code', () => {
      const error = new APIError('Not Found', 404);
      expect(error.message).toBe('Not Found');
      expect(error.statusCode).toBe(404);
      expect(error.code).toBe('SARDIS_3000');
      expect(error.name).toBe('APIError');
    });

    it('should create API error with all parameters', () => {
      const error = new APIError(
        'Server Error',
        500,
        'SERVER_ERROR',
        { trace: 'abc' },
        'req_456'
      );
      expect(error.message).toBe('Server Error');
      expect(error.statusCode).toBe(500);
      expect(error.code).toBe('SERVER_ERROR');
      expect(error.details).toEqual({ trace: 'abc' });
      expect(error.requestId).toBe('req_456');
    });

    it('should create from response with string error', () => {
      const error = APIError.fromResponse(400, { error: 'Bad request' });
      expect(error.message).toBe('Bad request');
      expect(error.statusCode).toBe(400);
    });

    it('should create from response with error object', () => {
      const error = APIError.fromResponse(400, {
        error: {
          message: 'Validation failed',
          code: 'VALIDATION_ERROR',
          details: { field: 'email' },
          request_id: 'req_789',
        },
      });
      expect(error.message).toBe('Validation failed');
      expect(error.code).toBe('VALIDATION_ERROR');
      expect(error.details).toEqual({ field: 'email' });
      expect(error.requestId).toBe('req_789');
    });

    it('should create from response with detail field', () => {
      const error = APIError.fromResponse(422, { detail: 'Invalid input' });
      expect(error.message).toBe('Invalid input');
    });

    it('should create from response with direct error object', () => {
      const error = APIError.fromResponse(400, {
        message: 'Direct error',
        code: 'DIRECT_CODE',
      });
      expect(error.message).toBe('Direct error');
      expect(error.code).toBe('DIRECT_CODE');
    });

    it('should handle empty error object', () => {
      const error = APIError.fromResponse(500, {});
      expect(error.message).toBe('Unknown API error');
    });

    it('should handle response with missing message in error object', () => {
      const error = APIError.fromResponse(400, {
        error: { code: 'SOME_CODE' },
      });
      expect(error.message).toBe('Unknown API error');
      expect(error.code).toBe('SOME_CODE');
    });
  });

  describe('AuthenticationError', () => {
    it('should create with default message', () => {
      const error = new AuthenticationError();
      expect(error.message).toBe('Invalid or missing API key');
      expect(error.code).toBe('SARDIS_2000');
      expect(error.name).toBe('AuthenticationError');
    });

    it('should create with custom message', () => {
      const error = new AuthenticationError('Token expired');
      expect(error.message).toBe('Token expired');
    });
  });

  describe('RateLimitError', () => {
    it('should create with default message', () => {
      const error = new RateLimitError();
      expect(error.message).toBe('Rate limit exceeded');
      expect(error.code).toBe('SARDIS_3429');
      expect(error.name).toBe('RateLimitError');
      expect(error.retryAfter).toBeUndefined();
    });

    it('should create with retry after value', () => {
      const error = new RateLimitError('Too many requests', 30);
      expect(error.message).toBe('Too many requests');
      expect(error.retryAfter).toBe(30);
    });
  });

  describe('ValidationError', () => {
    it('should create with message only', () => {
      const error = new ValidationError('Invalid email format');
      expect(error.message).toBe('Invalid email format');
      expect(error.code).toBe('SARDIS_5000');
      expect(error.name).toBe('ValidationError');
      expect(error.field).toBeUndefined();
      expect(error.details).toEqual({ field: undefined, expected: undefined, received: undefined });
    });

    it('should create with field name', () => {
      const error = new ValidationError('Must be a valid email', 'email');
      expect(error.message).toBe('Must be a valid email');
      expect(error.field).toBe('email');
      expect(error.details).toEqual({ field: 'email', expected: undefined, received: undefined });
    });
  });

  describe('InsufficientBalanceError', () => {
    it('should create with balance details', () => {
      const error = new InsufficientBalanceError(
        'Insufficient USDC balance',
        '100.00',
        '50.00',
        'USDC'
      );
      expect(error.message).toBe('Insufficient USDC balance');
      expect(error.code).toBe('SARDIS_6000');
      expect(error.name).toBe('InsufficientBalanceError');
      expect(error.required).toBe('100.00');
      expect(error.available).toBe('50.00');
      expect(error.currency).toBe('USDC');
      expect(error.details).toEqual({
        required: '100.00',
        available: '50.00',
        currency: 'USDC',
        wallet_id: undefined,
      });
    });
  });

  describe('NotFoundError', () => {
    it('should create with resource details', () => {
      const error = new NotFoundError('Wallet', 'wallet_123');
      expect(error.message).toBe('Wallet not found: wallet_123');
      expect(error.code).toBe('SARDIS_3404');
      expect(error.name).toBe('NotFoundError');
      expect(error.resourceType).toBe('Wallet');
      expect(error.resourceId).toBe('wallet_123');
      expect(error.details).toEqual({
        resource_type: 'Wallet',
        resource_id: 'wallet_123',
      });
    });
  });

  describe('Error inheritance', () => {
    it('should be instanceof Error', () => {
      const error = new SardisError('Test');
      expect(error).toBeInstanceOf(Error);
    });

    it('should be instanceof SardisError', () => {
      const apiError = new APIError('Test', 400);
      expect(apiError).toBeInstanceOf(SardisError);

      const authError = new AuthenticationError();
      expect(authError).toBeInstanceOf(SardisError);

      const rateError = new RateLimitError();
      expect(rateError).toBeInstanceOf(SardisError);

      const validationError = new ValidationError('Test');
      expect(validationError).toBeInstanceOf(SardisError);

      const balanceError = new InsufficientBalanceError('Test', '100', '50', 'USDC');
      expect(balanceError).toBeInstanceOf(SardisError);

      const notFoundError = new NotFoundError('Test', '123');
      expect(notFoundError).toBeInstanceOf(SardisError);
    });

    it('should be catchable as Error', () => {
      const throwAndCatch = () => {
        try {
          throw new APIError('Test', 400);
        } catch (e) {
          if (e instanceof Error) {
            return e.message;
          }
          return 'not an error';
        }
      };

      expect(throwAndCatch()).toBe('Test');
    });
  });
});
