/**
 * Tests for UCPResource
 */
import { describe, it, expect } from 'vitest';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';
import { http, HttpResponse } from 'msw';

describe('UCPResource', () => {
  const client = new SardisClient({ apiKey: 'test-key' });

  const mockCheckoutSession = {
    session_id: 'cs_abc123',
    merchant_id: 'merchant_456',
    merchant_name: 'Test Store',
    merchant_domain: 'store.test.com',
    customer_id: 'agent_abc',
    status: 'open',
    currency: 'USD',
    line_items: [
      {
        item_id: 'item_1',
        name: 'Widget',
        description: 'A useful widget',
        quantity: 2,
        unit_price_minor: 1000,
      },
    ],
    discounts: [],
    subtotal_minor: 2000,
    taxes_minor: 160,
    shipping_minor: 0,
    total_minor: 2160,
    created_at: '2025-01-20T00:00:00Z',
    updated_at: '2025-01-20T00:00:00Z',
    expires_at: 1737504000,
  };

  const mockOrder = {
    order_id: 'ord_xyz789',
    checkout_session_id: 'cs_abc123',
    merchant_id: 'merchant_456',
    customer_id: 'agent_abc',
    status: 'confirmed',
    line_items: mockCheckoutSession.line_items,
    currency: 'USD',
    subtotal_minor: 2000,
    taxes_minor: 160,
    shipping_minor: 0,
    discount_minor: 0,
    total_minor: 2160,
    payment_mandate_id: 'pay_mandate_123',
    chain_tx_hash: '0xabcdef1234567890',
    created_at: '2025-01-20T00:00:00Z',
    updated_at: '2025-01-20T00:00:00Z',
  };

  describe('createCheckout', () => {
    it('should create a checkout session', async () => {
      server.use(
        http.post('https://api.sardis.network/api/v2/ucp/checkout', () => {
          return HttpResponse.json(mockCheckoutSession);
        })
      );

      const session = await client.ucp.createCheckout({
        merchant_id: 'merchant_456',
        merchant_name: 'Test Store',
        merchant_domain: 'store.test.com',
        customer_id: 'agent_abc',
        line_items: [
          {
            item_id: 'item_1',
            name: 'Widget',
            description: 'A useful widget',
            quantity: 2,
            unit_price_minor: 1000,
          },
        ],
      });

      expect(session).toBeDefined();
      expect(session.session_id).toBe('cs_abc123');
      expect(session.status).toBe('open');
      expect(session.subtotal_minor).toBe(2000);
      expect(session.total_minor).toBe(2160);
      expect(session.line_items).toHaveLength(1);
    });

    it('should include all checkout fields in request', async () => {
      let receivedBody: any;
      server.use(
        http.post('https://api.sardis.network/api/v2/ucp/checkout', async ({ request }) => {
          receivedBody = await request.json();
          return HttpResponse.json(mockCheckoutSession);
        })
      );

      await client.ucp.createCheckout({
        merchant_id: 'merchant_456',
        merchant_name: 'Test Store',
        merchant_domain: 'store.test.com',
        customer_id: 'agent_abc',
        line_items: [
          {
            item_id: 'item_1',
            name: 'Widget',
            description: 'A widget',
            quantity: 3,
            unit_price_minor: 1500,
            sku: 'WDG-001',
            taxable: true,
          },
        ],
        currency: 'USD',
        tax_rate: '0.08',
        shipping_minor: 500,
        metadata: { source: 'test' },
      });

      expect(receivedBody).toBeDefined();
      expect(receivedBody.merchant_id).toBe('merchant_456');
      expect(receivedBody.line_items[0].sku).toBe('WDG-001');
      expect(receivedBody.shipping_minor).toBe(500);
      expect(receivedBody.metadata.source).toBe('test');
    });
  });

  describe('getCheckout', () => {
    it('should get a checkout session', async () => {
      server.use(
        http.get('https://api.sardis.network/api/v2/ucp/checkout/:sessionId', () => {
          return HttpResponse.json(mockCheckoutSession);
        })
      );

      const session = await client.ucp.getCheckout('cs_abc123');

      expect(session).toBeDefined();
      expect(session.session_id).toBe('cs_abc123');
      expect(session.merchant_name).toBe('Test Store');
    });

    it('should handle not found error', async () => {
      server.use(
        http.get('https://api.sardis.network/api/v2/ucp/checkout/:sessionId', () => {
          return HttpResponse.json(
            { error: 'Session not found', code: 'NOT_FOUND' },
            { status: 404 }
          );
        })
      );

      await expect(client.ucp.getCheckout('cs_nonexistent')).rejects.toThrow();
    });
  });

  describe('updateCheckout', () => {
    it('should add items to checkout', async () => {
      const updatedSession = {
        ...mockCheckoutSession,
        line_items: [
          ...mockCheckoutSession.line_items,
          {
            item_id: 'item_2',
            name: 'Gadget',
            description: 'A cool gadget',
            quantity: 1,
            unit_price_minor: 2500,
          },
        ],
        subtotal_minor: 4500,
        taxes_minor: 360,
        total_minor: 4860,
      };

      server.use(
        http.patch('https://api.sardis.network/api/v2/ucp/checkout/:sessionId', () => {
          return HttpResponse.json(updatedSession);
        })
      );

      const session = await client.ucp.updateCheckout('cs_abc123', {
        add_items: [
          {
            item_id: 'item_2',
            name: 'Gadget',
            description: 'A cool gadget',
            quantity: 1,
            unit_price_minor: 2500,
          },
        ],
      });

      expect(session.line_items).toHaveLength(2);
      expect(session.subtotal_minor).toBe(4500);
    });

    it('should remove items from checkout', async () => {
      const updatedSession = {
        ...mockCheckoutSession,
        line_items: [],
        subtotal_minor: 0,
        taxes_minor: 0,
        total_minor: 0,
      };

      server.use(
        http.patch('https://api.sardis.network/api/v2/ucp/checkout/:sessionId', () => {
          return HttpResponse.json(updatedSession);
        })
      );

      const session = await client.ucp.updateCheckout('cs_abc123', {
        remove_item_ids: ['item_1'],
      });

      expect(session.line_items).toHaveLength(0);
    });

    it('should add discount to checkout', async () => {
      const updatedSession = {
        ...mockCheckoutSession,
        discounts: [
          {
            discount_id: 'disc_1',
            name: '10% Off',
            discount_type: 'percentage',
            value: '10',
          },
        ],
        total_minor: 1944, // 2160 - 216 (10%)
      };

      server.use(
        http.patch('https://api.sardis.network/api/v2/ucp/checkout/:sessionId', () => {
          return HttpResponse.json(updatedSession);
        })
      );

      const session = await client.ucp.updateCheckout('cs_abc123', {
        add_discounts: [
          {
            discount_id: 'disc_1',
            name: '10% Off',
            discount_type: 'percentage',
            value: '10',
          },
        ],
      });

      expect(session.discounts).toHaveLength(1);
      expect(session.total_minor).toBe(1944);
    });
  });

  describe('completeCheckout', () => {
    it('should complete checkout successfully', async () => {
      server.use(
        http.post('https://api.sardis.network/api/v2/ucp/checkout/:sessionId/complete', () => {
          return HttpResponse.json({
            success: true,
            session_id: 'cs_abc123',
            order_id: 'ord_xyz789',
            payment_mandate: {
              mandate_id: 'pay_mandate_123',
              chain: 'base',
              token: 'USDC',
              amount_minor: 2160,
            },
            chain_tx_hash: '0xabcdef1234567890',
          });
        })
      );

      const result = await client.ucp.completeCheckout('cs_abc123', {
        chain: 'base',
        token: 'USDC',
        destination: '0x1234567890abcdef1234567890abcdef12345678',
        subject: 'agent_abc',
        issuer: 'sardis.sh',
      });

      expect(result.success).toBe(true);
      expect(result.order_id).toBe('ord_xyz789');
      expect(result.chain_tx_hash).toBe('0xabcdef1234567890');
      expect(result.payment_mandate).toBeDefined();
    });

    it('should handle empty cart error', async () => {
      server.use(
        http.post('https://api.sardis.network/api/v2/ucp/checkout/:sessionId/complete', () => {
          return HttpResponse.json({
            success: false,
            session_id: 'cs_abc123',
            error: 'Cannot complete checkout with empty cart',
            error_code: 'empty_cart',
          });
        })
      );

      const result = await client.ucp.completeCheckout('cs_abc123', {
        chain: 'base',
        token: 'USDC',
        destination: '0x1234',
        subject: 'agent_abc',
        issuer: 'sardis.sh',
      });

      expect(result.success).toBe(false);
      expect(result.error_code).toBe('empty_cart');
    });

    it('should send execute_payment flag', async () => {
      let receivedBody: any;
      server.use(
        http.post(
          'https://api.sardis.network/api/v2/ucp/checkout/:sessionId/complete',
          async ({ request }) => {
            receivedBody = await request.json();
            return HttpResponse.json({
              success: true,
              session_id: 'cs_abc123',
            });
          }
        )
      );

      await client.ucp.completeCheckout('cs_abc123', {
        chain: 'base',
        token: 'USDC',
        destination: '0x1234',
        subject: 'agent_abc',
        issuer: 'sardis.sh',
        execute_payment: false,
      });

      expect(receivedBody.execute_payment).toBe(false);
    });
  });

  describe('cancelCheckout', () => {
    it('should cancel checkout', async () => {
      server.use(
        http.post('https://api.sardis.network/api/v2/ucp/checkout/:sessionId/cancel', () => {
          return HttpResponse.json({
            ...mockCheckoutSession,
            status: 'cancelled',
          });
        })
      );

      const session = await client.ucp.cancelCheckout('cs_abc123');

      expect(session.status).toBe('cancelled');
    });

    it('should handle already completed error', async () => {
      server.use(
        http.post('https://api.sardis.network/api/v2/ucp/checkout/:sessionId/cancel', () => {
          return HttpResponse.json(
            {
              error: 'Cannot cancel completed checkout',
              code: 'INVALID_OPERATION',
            },
            { status: 400 }
          );
        })
      );

      await expect(client.ucp.cancelCheckout('cs_abc123')).rejects.toThrow();
    });
  });

  describe('getOrder', () => {
    it('should get an order', async () => {
      server.use(
        http.get('https://api.sardis.network/api/v2/ucp/orders/:orderId', () => {
          return HttpResponse.json(mockOrder);
        })
      );

      const order = await client.ucp.getOrder('ord_xyz789');

      expect(order).toBeDefined();
      expect(order.order_id).toBe('ord_xyz789');
      expect(order.status).toBe('confirmed');
      expect(order.chain_tx_hash).toBe('0xabcdef1234567890');
    });
  });

  describe('listOrders', () => {
    it('should list orders', async () => {
      server.use(
        http.get('https://api.sardis.network/api/v2/ucp/orders', () => {
          return HttpResponse.json({
            orders: [mockOrder],
          });
        })
      );

      const orders = await client.ucp.listOrders();

      expect(orders).toHaveLength(1);
      expect(orders[0].order_id).toBe('ord_xyz789');
    });

    it('should filter orders by customer_id', async () => {
      let receivedParams: URLSearchParams | null = null;
      server.use(
        http.get('https://api.sardis.network/api/v2/ucp/orders', ({ request }) => {
          const url = new URL(request.url);
          receivedParams = url.searchParams;
          return HttpResponse.json({ orders: [] });
        })
      );

      await client.ucp.listOrders({
        customer_id: 'agent_abc',
        status: 'confirmed',
      });

      expect(receivedParams?.get('customer_id')).toBe('agent_abc');
      expect(receivedParams?.get('status')).toBe('confirmed');
    });

    it('should handle array response format', async () => {
      server.use(
        http.get('https://api.sardis.network/api/v2/ucp/orders', () => {
          return HttpResponse.json([mockOrder]);
        })
      );

      const orders = await client.ucp.listOrders();

      expect(orders).toHaveLength(1);
    });
  });
});
