/**
 * Tests for TreasuryResource
 */
import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { SardisClient } from '../src/client.js';
import { server } from './setup.js';

describe('TreasuryResource', () => {
  const client = new SardisClient({ apiKey: 'test-key' });

  it('should list financial accounts', async () => {
    server.use(
      http.get('https://api.sardis.sh/api/v2/treasury/financial-accounts', () =>
        HttpResponse.json([
          {
            organization_id: 'org_test',
            financial_account_token: 'fa_123',
            account_role: 'ISSUING',
            currency: 'USD',
            status: 'OPEN',
            is_program_level: false,
          },
        ])
      )
    );

    const accounts = await client.treasury.listFinancialAccounts();
    expect(accounts).toHaveLength(1);
    expect(accounts[0]?.financial_account_token).toBe('fa_123');
  });

  it('should create ACH fund payment', async () => {
    server.use(
      http.post('https://api.sardis.sh/api/v2/treasury/fund', () =>
        HttpResponse.json({
          payment_token: 'pay_123',
          status: 'PENDING',
          result: 'APPROVED',
          direction: 'DEBIT',
          method: 'ACH_NEXT_DAY',
          currency: 'USD',
          pending_amount: 5000,
          settled_amount: 0,
          financial_account_token: 'fa_123',
          external_bank_account_token: 'eba_123',
        })
      )
    );

    const payment = await client.treasury.fund({
      financial_account_token: 'fa_123',
      external_bank_account_token: 'eba_123',
      amount_minor: 5000,
      sec_code: 'CCD',
    });

    expect(payment.payment_token).toBe('pay_123');
    expect(payment.pending_amount).toBe(5000);
  });

  it('should return treasury balances', async () => {
    server.use(
      http.get('https://api.sardis.sh/api/v2/treasury/balances', () =>
        HttpResponse.json([
          {
            organization_id: 'org_test',
            financial_account_token: 'fa_123',
            currency: 'USD',
            available_amount_minor: 120000,
            pending_amount_minor: 5000,
            total_amount_minor: 125000,
          },
        ])
      )
    );

    const balances = await client.treasury.getBalances();
    expect(balances).toHaveLength(1);
    expect(balances[0]?.total_amount_minor).toBe(125000);
  });
});
