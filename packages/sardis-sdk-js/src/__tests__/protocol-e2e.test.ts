/**
 * E2E Protocol Flow Tests
 *
 * Comprehensive test suite for protocol-level flows:
 * - UCP checkout flows
 * - AP2 payment execution with mandate chains
 * - Protocol error code propagation
 * - 402 Payment Required handling
 * - Retry behavior for protocol rejections
 * - TAP header propagation
 * - Error class mapping
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';
import { SardisClient } from '../client.js';
import {
  APIError,
  SardisErrorCode,
  AuthenticationError,
  ValidationError,
  PolicyViolationError,
} from '../errors.js';

// Mock axios to simulate API responses
vi.mock('axios');

describe('E2E Protocol Flows', () => {
  let client: SardisClient;
  let mockAxiosCreate: ReturnType<typeof vi.fn>;
  let mockAxiosInstance: {
    request: ReturnType<typeof vi.fn>;
    defaults: { headers: Record<string, string> };
  };

  beforeEach(() => {
    // Setup axios mock
    mockAxiosInstance = {
      request: vi.fn(),
      defaults: {
        headers: {
          'X-API-Key': 'test-api-key',
          'Content-Type': 'application/json',
          'User-Agent': '@sardis/sdk/0.2.0',
        },
      },
    };

    mockAxiosCreate = vi.fn().mockReturnValue(mockAxiosInstance);
    (axios.create as unknown as typeof mockAxiosCreate) = mockAxiosCreate;
    (axios.isAxiosError as unknown as ReturnType<typeof vi.fn>) = vi.fn().mockReturnValue(true);
    (axios.isCancel as unknown as ReturnType<typeof vi.fn>) = vi.fn().mockReturnValue(false);

    // Create client instance
    client = new SardisClient({
      apiKey: 'test-api-key',
      baseUrl: 'https://api.sardis.sh',
      maxRetries: 2,
      retryDelay: 100,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('1. Full UCP checkout flow', () => {
    it('should complete full UCP checkout flow: create -> update -> complete', async () => {
      // Step 1: Create checkout
      const createResponse = {
        data: {
          session_id: 'cs_abc123',
          merchant_id: 'merchant_1',
          merchant_name: 'Test Store',
          merchant_domain: 'store.example.com',
          customer_id: 'agent_1',
          status: 'open',
          currency: 'USD',
          line_items: [
            {
              item_id: 'item_1',
              name: 'Widget',
              description: 'A useful widget',
              quantity: 1,
              unit_price_minor: 1000,
            },
          ],
          discounts: [],
          subtotal_minor: 1000,
          taxes_minor: 100,
          shipping_minor: 500,
          total_minor: 1600,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          expires_at: 1704067200,
        },
      };

      mockAxiosInstance.request.mockResolvedValueOnce(createResponse);

      const session = await client.ucp.createCheckout({
        merchant_id: 'merchant_1',
        merchant_name: 'Test Store',
        merchant_domain: 'store.example.com',
        customer_id: 'agent_1',
        line_items: [
          {
            item_id: 'item_1',
            name: 'Widget',
            description: 'A useful widget',
            quantity: 1,
            unit_price_minor: 1000,
          },
        ],
      });

      expect(session.session_id).toBe('cs_abc123');
      expect(session.status).toBe('open');
      expect(session.total_minor).toBe(1600);

      // Step 2: Update checkout
      const updateResponse = {
        data: {
          ...createResponse.data,
          line_items: [
            ...createResponse.data.line_items,
            {
              item_id: 'item_2',
              name: 'Gadget',
              description: 'An extra gadget',
              quantity: 1,
              unit_price_minor: 500,
            },
          ],
          subtotal_minor: 1500,
          total_minor: 2100,
        },
      };

      mockAxiosInstance.request.mockResolvedValueOnce(updateResponse);

      const updated = await client.ucp.updateCheckout('cs_abc123', {
        add_items: [
          {
            item_id: 'item_2',
            name: 'Gadget',
            description: 'An extra gadget',
            quantity: 1,
            unit_price_minor: 500,
          },
        ],
      });

      expect(updated.session_id).toBe('cs_abc123');
      expect(updated.line_items).toHaveLength(2);
      expect(updated.total_minor).toBe(2100);

      // Step 3: Complete checkout
      const completeResponse = {
        data: {
          success: true,
          session_id: 'cs_abc123',
          order_id: 'ord_xyz789',
          payment_mandate: {
            mandate_id: 'mandate_123',
            amount: '21.00',
            token: 'USDC',
            chain: 'base',
          },
          chain_tx_hash: '0xabc123def456',
        },
      };

      mockAxiosInstance.request.mockResolvedValueOnce(completeResponse);

      const result = await client.ucp.completeCheckout('cs_abc123', {
        chain: 'base',
        token: 'USDC',
        destination: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
        subject: 'agent_1',
        issuer: 'sardis.sh',
        execute_payment: true,
      });

      expect(result.success).toBe(true);
      expect(result.order_id).toBe('ord_xyz789');
      expect(result.chain_tx_hash).toBe('0xabc123def456');
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(3);
    });
  });

  describe('2. AP2 payment execution with mandate chain', () => {
    it('should execute AP2 payment with full mandate chain (intent -> cart -> payment)', async () => {
      const intent = {
        intent_id: 'intent_1',
        action: 'purchase',
        subject: 'agent_1',
        issuer: 'sardis.sh',
        timestamp: '2024-01-01T00:00:00Z',
      };

      const cart = {
        cart_id: 'cart_1',
        merchant_id: 'merchant_1',
        items: [
          {
            item_id: 'item_1',
            name: 'Widget',
            quantity: 1,
            price: '10.00',
          },
        ],
        total: '10.00',
      };

      const payment = {
        payment_id: 'payment_1',
        amount: '10.00',
        token: 'USDC',
        chain: 'base',
        destination: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
      };

      const response = {
        data: {
          mandate_id: 'mandate_123',
          ledger_tx_id: 'ledger_456',
          chain_tx_hash: '0xabc123def456',
          chain: 'base',
          audit_anchor: 'anchor_789',
          status: 'completed',
          compliance_provider: 'elliptic',
          compliance_rule: 'sanctions_check',
        },
      };

      mockAxiosInstance.request.mockResolvedValueOnce(response);

      const result = await client.payments.executeAP2(intent, cart, payment);

      expect(result.mandate_id).toBe('mandate_123');
      expect(result.chain_tx_hash).toBe('0xabc123def456');
      expect(result.audit_anchor).toBe('anchor_789');
      expect(result.status).toBe('completed');

      // Verify request structure
      expect(mockAxiosInstance.request).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'POST',
          url: '/api/v2/ap2/payments/execute',
          data: {
            intent,
            cart,
            payment,
          },
        })
      );
    });
  });

  describe('3. SDK propagates protocol error codes', () => {
    it('should map MANDATE_CHAIN_INVALID error correctly', async () => {
      const errorResponse = {
        response: {
          status: 422,
          data: {
            error: {
              code: 'MANDATE_CHAIN_INVALID',
              message: 'Intent signature verification failed',
              details: {
                field: 'intent.signature',
                reason: 'Invalid signature for public key',
              },
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      await expect(
        client.payments.executeAP2(
          { intent_id: 'bad_intent' },
          { cart_id: 'cart_1' },
          { payment_id: 'payment_1' }
        )
      ).rejects.toThrow(APIError);

      try {
        await client.payments.executeAP2(
          { intent_id: 'bad_intent' },
          { cart_id: 'cart_1' },
          { payment_id: 'payment_1' }
        );
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.code).toBe('MANDATE_CHAIN_INVALID');
        expect(apiError.message).toContain('Intent signature verification failed');
        expect(apiError.statusCode).toBe(422);
        expect(apiError.retryable).toBe(false);
      }
    });

    it('should map SECURITY_LOCK_VIOLATION error correctly', async () => {
      const errorResponse = {
        response: {
          status: 403,
          data: {
            error: {
              code: 'SECURITY_LOCK_VIOLATION',
              message: 'Wallet is locked due to suspicious activity',
              details: {
                wallet_id: 'wallet_123',
                lock_reason: 'multiple_failed_transactions',
                locked_until: '2024-01-02T00:00:00Z',
              },
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      await expect(
        client.payments.executeMandate({
          mandate_id: 'mandate_1',
          wallet_id: 'wallet_123',
        })
      ).rejects.toThrow(APIError);

      try {
        await client.payments.executeMandate({
          mandate_id: 'mandate_1',
          wallet_id: 'wallet_123',
        });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.code).toBe('SECURITY_LOCK_VIOLATION');
        expect(apiError.statusCode).toBe(403);
        expect(apiError.details.wallet_id).toBe('wallet_123');
      }
    });

    it('should map POLICY_VIOLATION error correctly', async () => {
      const errorResponse = {
        response: {
          status: 403,
          data: {
            error: {
              code: 'SARDIS_6002',
              message: 'Transaction violates spending policy',
              details: {
                policy_name: 'daily_limit',
                limit: '100.00',
                attempted: '150.00',
              },
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      await expect(
        client.payments.executeMandate({
          mandate_id: 'mandate_1',
          amount: '150.00',
        })
      ).rejects.toThrow(APIError);

      try {
        await client.payments.executeMandate({
          mandate_id: 'mandate_1',
          amount: '150.00',
        });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.code).toBe('SARDIS_6002');
        expect(apiError.details.policy_name).toBe('daily_limit');
      }
    });
  });

  describe('4. SDK handles 402 responses (x402 challenge)', () => {
    it('should parse 402 PaymentRequired with challenge header', async () => {
      const errorResponse = {
        response: {
          status: 402,
          data: {
            error: {
              code: 'PAYMENT_REQUIRED',
              message: 'Insufficient balance to complete transaction',
              details: {
                required: '100.00',
                available: '50.00',
                currency: 'USDC',
              },
            },
          },
          headers: {
            'x-payment-challenge': JSON.stringify({
              challenge_id: 'challenge_123',
              required_amount: '50.00',
              token: 'USDC',
              chain: 'base',
              destination: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
            }),
          },
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      await expect(
        client.payments.executeMandate({
          mandate_id: 'mandate_1',
          amount: '100.00',
        })
      ).rejects.toThrow(APIError);

      try {
        await client.payments.executeMandate({
          mandate_id: 'mandate_1',
          amount: '100.00',
        });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.statusCode).toBe(402);
        expect(apiError.code).toBe('PAYMENT_REQUIRED');
        expect(apiError.headers).toBeDefined();
        expect(apiError.headers?.['x-payment-challenge']).toBeDefined();

        // Parse challenge from header
        const challenge = JSON.parse(apiError.headers?.['x-payment-challenge'] || '{}');
        expect(challenge.challenge_id).toBe('challenge_123');
        expect(challenge.required_amount).toBe('50.00');
        expect(challenge.token).toBe('USDC');
      }
    });
  });

  describe('5. SDK does NOT retry protocol rejections (4xx)', () => {
    it('should NOT retry 400 Bad Request', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: {
            error: {
              code: 'BAD_REQUEST',
              message: 'Invalid request body',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValue(errorResponse);

      await expect(
        client.payments.executeMandate({ mandate_id: 'invalid' })
      ).rejects.toThrow(APIError);

      // Should only be called once (no retries)
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(1);
    });

    it('should NOT retry 403 Forbidden', async () => {
      const errorResponse = {
        response: {
          status: 403,
          data: {
            error: {
              code: 'FORBIDDEN',
              message: 'Access denied',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValue(errorResponse);

      await expect(
        client.payments.executeMandate({ mandate_id: 'mandate_1' })
      ).rejects.toThrow(APIError);

      // Should only be called once (no retries)
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(1);
    });

    it('should NOT retry 422 Unprocessable Entity', async () => {
      const errorResponse = {
        response: {
          status: 422,
          data: {
            error: {
              code: 'UNPROCESSABLE_ENTITY',
              message: 'Validation failed',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValue(errorResponse);

      await expect(
        client.payments.executeMandate({ mandate_id: 'mandate_1' })
      ).rejects.toThrow(APIError);

      // Should only be called once (no retries)
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(1);
    });

    it('should retry 500 Internal Server Error', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: {
            error: {
              code: 'INTERNAL_SERVER_ERROR',
              message: 'Server error',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValue(errorResponse);

      await expect(
        client.payments.executeMandate({ mandate_id: 'mandate_1' })
      ).rejects.toThrow(APIError);

      // Should be called 3 times (1 initial + 2 retries)
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(3);
    });

    it('should retry 503 Service Unavailable', async () => {
      const errorResponse = {
        response: {
          status: 503,
          data: {
            error: {
              code: 'SERVICE_UNAVAILABLE',
              message: 'Service temporarily unavailable',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValue(errorResponse);

      await expect(
        client.payments.executeMandate({ mandate_id: 'mandate_1' })
      ).rejects.toThrow(APIError);

      // Should be called 3 times (1 initial + 2 retries)
      expect(mockAxiosInstance.request).toHaveBeenCalledTimes(3);
    });
  });

  describe('6. SDK passes TAP headers when configured', () => {
    it('should add Signature and Signature-Input headers for TAP', async () => {
      const tapClient = new SardisClient({
        apiKey: 'test-api-key',
        baseUrl: 'https://api.sardis.sh',
      });

      // Add interceptor to inject TAP headers
      tapClient.addRequestInterceptor({
        onRequest: (config) => {
          config.headers = {
            ...config.headers,
            'Signature': 'sig1=:MEUCIQDxyz...:',
            'Signature-Input': 'sig1=("@method" "@authority" "@path" "content-digest");created=1704067200;keyid="agent_123";alg="ed25519"',
          };
          return config;
        },
      });

      const response = {
        data: {
          mandate_id: 'mandate_123',
          status: 'completed',
        },
      };

      mockAxiosInstance.request.mockResolvedValueOnce(response);

      await tapClient.payments.executeMandate({
        mandate_id: 'mandate_1',
        amount: '10.00',
      });

      // Verify headers were added
      const requestConfig = mockAxiosInstance.request.mock.calls[0][0];
      expect(requestConfig.headers?.['Signature']).toBe('sig1=:MEUCIQDxyz...:');
      expect(requestConfig.headers?.['Signature-Input']).toContain('sig1=');
      expect(requestConfig.headers?.['Signature-Input']).toContain('ed25519');
    });

    it('should support ECDSA-P256 TAP signatures', async () => {
      const tapClient = new SardisClient({
        apiKey: 'test-api-key',
        baseUrl: 'https://api.sardis.sh',
      });

      tapClient.addRequestInterceptor({
        onRequest: (config) => {
          config.headers = {
            ...config.headers,
            'Signature': 'sig1=:MEYCIQC...:',
            'Signature-Input': 'sig1=("@method" "@authority" "@path");created=1704067200;keyid="agent_456";alg="ecdsa-p256"',
          };
          return config;
        },
      });

      const response = {
        data: {
          mandate_id: 'mandate_123',
          status: 'completed',
        },
      };

      mockAxiosInstance.request.mockResolvedValueOnce(response);

      await tapClient.payments.executeMandate({
        mandate_id: 'mandate_1',
        amount: '10.00',
      });

      const requestConfig = mockAxiosInstance.request.mock.calls[0][0];
      expect(requestConfig.headers?.['Signature-Input']).toContain('ecdsa-p256');
    });
  });

  describe('7. SDK maps API errors to correct error classes', () => {
    it('should map 401 to AuthenticationError', async () => {
      const errorResponse = {
        response: {
          status: 401,
          data: {
            error: {
              code: 'UNAUTHORIZED',
              message: 'Invalid API key',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      await expect(client.health()).rejects.toThrow(AuthenticationError);
    });

    it('should map 422 validation errors to APIError with correct code', async () => {
      const errorResponse = {
        response: {
          status: 422,
          data: {
            error: {
              code: 'SARDIS_5001',
              message: 'Missing required field: amount',
              details: {
                field: 'amount',
              },
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      try {
        await client.payments.executeMandate({ mandate_id: 'mandate_1' });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.code).toBe('SARDIS_5001');
        expect(apiError.statusCode).toBe(422);
        expect(apiError.details.field).toBe('amount');
      }
    });

    it('should map 404 to NotFound APIError', async () => {
      const errorResponse = {
        response: {
          status: 404,
          data: {
            error: {
              code: 'SARDIS_3404',
              message: 'Wallet not found: wallet_123',
              details: {
                resource_type: 'Wallet',
                resource_id: 'wallet_123',
              },
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      try {
        await client.wallets.get('wallet_123');
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.statusCode).toBe(404);
        expect(apiError.code).toBe('SARDIS_3404');
      }
    });

    it('should preserve request_id in error', async () => {
      const errorResponse = {
        response: {
          status: 500,
          data: {
            error: {
              code: 'INTERNAL_SERVER_ERROR',
              message: 'Internal server error',
              request_id: 'req_abc123xyz',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValue(errorResponse);

      try {
        await client.payments.executeMandate({ mandate_id: 'mandate_1' });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.requestId).toBe('req_abc123xyz');
      }
    });

    it('should handle nested error structures', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: {
            detail: {
              code: 'INVALID_FORMAT',
              message: 'Invalid address format',
              details: {
                field: 'destination',
                expected: 'EVM address (0x...)',
                received: 'invalid',
              },
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      try {
        await client.payments.executeMandate({
          mandate_id: 'mandate_1',
          destination: 'invalid',
        });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.code).toBe('INVALID_FORMAT');
        expect(apiError.details.field).toBe('destination');
      }
    });

    it('should mark 5xx errors as retryable', async () => {
      const errorResponse = {
        response: {
          status: 503,
          data: {
            error: {
              code: 'SERVICE_UNAVAILABLE',
              message: 'Service temporarily unavailable',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValue(errorResponse);

      try {
        await client.payments.executeMandate({ mandate_id: 'mandate_1' });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.retryable).toBe(true);
      }
    });

    it('should mark 4xx errors as not retryable', async () => {
      const errorResponse = {
        response: {
          status: 400,
          data: {
            error: {
              code: 'BAD_REQUEST',
              message: 'Invalid request',
            },
          },
          headers: {},
        },
      };

      mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);

      try {
        await client.payments.executeMandate({ mandate_id: 'mandate_1' });
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        const apiError = error as APIError;
        expect(apiError.retryable).toBe(false);
      }
    });
  });
});
