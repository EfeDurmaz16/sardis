/**
 * Treasury Resource
 *
 * Fiat-first treasury operations backed by Lithic financial accounts and ACH.
 */

import { BaseResource } from './base.js';
import type {
  CreateExternalBankAccountInput,
  ExternalBankAccount,
  FinancialAccount,
  RequestOptions,
  TreasuryBalance,
  TreasuryPaymentInput,
  TreasuryPaymentResponse,
  VerifyMicroDepositsInput,
} from '../types.js';

export class TreasuryResource extends BaseResource {
  async syncAccountHolders(
    account_token?: string,
    options?: RequestOptions
  ): Promise<FinancialAccount[]> {
    return this._post<FinancialAccount[]>(
      '/api/v2/treasury/account-holders/sync',
      { account_token },
      options
    );
  }

  async listFinancialAccounts(
    params?: { account_token?: string; refresh?: boolean },
    options?: RequestOptions
  ): Promise<FinancialAccount[]> {
    return this._get<FinancialAccount[]>(
      '/api/v2/treasury/financial-accounts',
      {
        account_token: params?.account_token,
        refresh: params?.refresh ?? false,
      },
      options
    );
  }

  async createExternalBankAccount(
    input: CreateExternalBankAccountInput,
    options?: RequestOptions
  ): Promise<ExternalBankAccount> {
    return this._post<ExternalBankAccount>(
      '/api/v2/treasury/external-bank-accounts',
      input,
      options
    );
  }

  async verifyMicroDeposits(
    token: string,
    input: VerifyMicroDepositsInput,
    options?: RequestOptions
  ): Promise<ExternalBankAccount> {
    return this._post<ExternalBankAccount>(
      `/api/v2/treasury/external-bank-accounts/${token}/verify-micro-deposits`,
      input,
      options
    );
  }

  async fund(
    input: TreasuryPaymentInput,
    options?: RequestOptions
  ): Promise<TreasuryPaymentResponse> {
    return this._post<TreasuryPaymentResponse>('/api/v2/treasury/fund', input, options);
  }

  async withdraw(
    input: TreasuryPaymentInput,
    options?: RequestOptions
  ): Promise<TreasuryPaymentResponse> {
    return this._post<TreasuryPaymentResponse>('/api/v2/treasury/withdraw', input, options);
  }

  async getPayment(
    paymentToken: string,
    options?: RequestOptions
  ): Promise<TreasuryPaymentResponse> {
    return this._get<TreasuryPaymentResponse>(`/api/v2/treasury/payments/${paymentToken}`, undefined, options);
  }

  async getBalances(options?: RequestOptions): Promise<TreasuryBalance[]> {
    return this._get<TreasuryBalance[]>('/api/v2/treasury/balances', undefined, options);
  }
}
