/**
 * Test setup file for Vitest
 * Configures MSW server and global test utilities
 */
import { afterAll, afterEach, beforeAll } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

// Mock API responses
export const mockResponses = {
    health: {
        status: 'healthy',
        version: '0.3.0',
    },
    wallet: {
        id: 'wallet_test123',
        address: '0x1234567890abcdef1234567890abcdef12345678',
        status: 'active',
        chain: 'base_sepolia',
        created_at: '2025-01-20T00:00:00Z',
    },
    balance: {
        wallet_id: 'wallet_test123',
        balances: [
            { token: 'USDC', amount: '1000.00', amount_minor: 1000000000 },
            { token: 'USDT', amount: '500.00', amount_minor: 500000000 },
        ],
    },
    mandate: {
        id: 'mandate_abc123',
        status: 'EXECUTED',
        tx_hash: '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
        created_at: '2025-01-20T00:00:00Z',
    },
    hold: {
        id: 'hold_xyz789',
        wallet_id: 'wallet_test123',
        amount: '100.00',
        amount_minor: 100000000,
        status: 'active',
        expires_at: '2025-01-21T00:00:00Z',
        created_at: '2025-01-20T00:00:00Z',
    },
    webhook: {
        id: 'webhook_def456',
        url: 'https://example.com/webhook',
        events: ['payment.completed', 'payment.failed'],
        active: true,
        created_at: '2025-01-20T00:00:00Z',
    },
    policy: {
        allowed: true,
        policy_id: 'policy_test',
        reason: null,
    },
    policyViolation: {
        allowed: false,
        policy_id: 'policy_test',
        reason: 'Amount exceeds daily limit',
    },
};

// MSW handlers
export const handlers = [
    // Health check
    http.get('https://api.sardis.network/health', () => {
        return HttpResponse.json(mockResponses.health);
    }),

    // Wallets
    http.post('https://api.sardis.network/v1/wallets', () => {
        return HttpResponse.json(mockResponses.wallet);
    }),
    http.get('https://api.sardis.network/v1/wallets/:id', () => {
        return HttpResponse.json(mockResponses.wallet);
    }),
    http.get('https://api.sardis.network/v1/wallets/:id/balance', () => {
        return HttpResponse.json(mockResponses.balance);
    }),

    // Payments
    http.post('https://api.sardis.network/v1/payments/mandate', () => {
        return HttpResponse.json(mockResponses.mandate);
    }),
    http.post('https://api.sardis.network/v1/payments/ap2', () => {
        return HttpResponse.json(mockResponses.mandate);
    }),
    http.post('https://api.sardis.network/v1/payments/ap2/bundle', () => {
        return HttpResponse.json({
            results: [mockResponses.mandate, mockResponses.mandate],
        });
    }),

    // Holds
    http.post('https://api.sardis.network/v1/holds', () => {
        return HttpResponse.json(mockResponses.hold);
    }),
    http.get('https://api.sardis.network/v1/holds/:id', () => {
        return HttpResponse.json(mockResponses.hold);
    }),
    http.post('https://api.sardis.network/v1/holds/:id/capture', () => {
        return HttpResponse.json({ ...mockResponses.hold, status: 'captured' });
    }),
    http.post('https://api.sardis.network/v1/holds/:id/void', () => {
        return HttpResponse.json({ ...mockResponses.hold, status: 'voided' });
    }),

    // Webhooks
    http.post('https://api.sardis.network/v1/webhooks', () => {
        return HttpResponse.json(mockResponses.webhook);
    }),
    http.get('https://api.sardis.network/v1/webhooks', () => {
        return HttpResponse.json({ webhooks: [mockResponses.webhook] });
    }),
    http.get('https://api.sardis.network/v1/webhooks/:id', () => {
        return HttpResponse.json(mockResponses.webhook);
    }),
    http.delete('https://api.sardis.network/v1/webhooks/:id', () => {
        return HttpResponse.json({ success: true });
    }),

    // Policy check
    http.post('https://api.sardis.network/v1/policy/check', async ({ request }) => {
        const body = (await request.json()) as { amount_minor?: number };
        if (body.amount_minor && body.amount_minor > 500000000) {
            return HttpResponse.json(mockResponses.policyViolation);
        }
        return HttpResponse.json(mockResponses.policy);
    }),

    // Error scenarios
    http.get('https://api.sardis.network/v1/error/401', () => {
        return HttpResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }),
    http.get('https://api.sardis.network/v1/error/429', () => {
        return HttpResponse.json(
            { error: 'Rate limit exceeded' },
            {
                status: 429,
                headers: { 'Retry-After': '5' },
            }
        );
    }),
    http.get('https://api.sardis.network/v1/error/500', () => {
        return HttpResponse.json({ error: 'Internal server error' }, { status: 500 });
    }),
];

// Setup MSW server
export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
