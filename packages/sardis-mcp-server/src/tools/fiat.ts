/**
 * Fiat/Treasury tools for MCP server
 *
 * USD-first launch with multi-currency-ready schemas.
 */

import { z } from 'zod';
import { getConfig } from '../config.js';
import { apiRequest } from '../api.js';
import type { ToolDefinition, ToolHandler, ToolResult } from './types.js';

const AccountHolderSyncSchema = z.object({
  account_token: z.string().optional(),
});

const ListFinancialAccountsSchema = z.object({
  account_token: z.string().optional(),
  refresh: z.boolean().optional(),
});

const LinkExternalBankSchema = z.object({
  financial_account_token: z.string(),
  verification_method: z.enum(['MICRO_DEPOSIT', 'PRENOTE', 'EXTERNALLY_VERIFIED']).optional(),
  owner_type: z.enum(['INDIVIDUAL', 'BUSINESS']).optional(),
  owner: z.string(),
  account_type: z.enum(['CHECKING', 'SAVINGS']).optional(),
  routing_number: z.string(),
  account_number: z.string(),
  name: z.string().optional(),
  currency: z.string().optional(),
  country: z.string().optional(),
  account_token: z.string().optional(),
  company_id: z.string().optional(),
  user_defined_id: z.string().optional(),
});

const VerifyMicroDepositsSchema = z.object({
  token: z.string(),
  micro_deposits: z.tuple([z.string(), z.string()]),
});

const FundWalletSchema = z.object({
  wallet_id: z.string().optional().describe('Optional wallet reference for metadata'),
  amount: z.union([z.string(), z.number()]).optional().describe('Legacy amount in major units'),
  amount_minor: z.number().int().positive().optional().describe('Amount in minor units'),
  source: z.enum(['ach', 'wire', 'card', 'bank_account']).optional(),
  currency: z.string().optional(),
  source_id: z.string().optional(),
  financial_account_token: z.string().optional(),
  external_bank_account_token: z.string().optional(),
  method: z.enum(['ACH_NEXT_DAY', 'ACH_SAME_DAY']).optional(),
  sec_code: z.enum(['CCD', 'PPD', 'WEB']).optional(),
  memo: z.string().optional(),
  idempotency_key: z.string().optional(),
  user_defined_id: z.string().optional(),
});

const WithdrawSchema = z.object({
  wallet_id: z.string().optional(),
  amount: z.union([z.string(), z.number()]).optional(),
  amount_minor: z.number().int().positive().optional(),
  destination_id: z.string().optional().describe('Legacy destination alias'),
  account_id: z.string().optional().describe('Legacy destination alias'),
  financial_account_token: z.string().optional(),
  external_bank_account_token: z.string().optional(),
  method: z.enum(['ACH_NEXT_DAY', 'ACH_SAME_DAY']).optional(),
  sec_code: z.enum(['CCD', 'PPD', 'WEB']).optional(),
  memo: z.string().optional(),
  idempotency_key: z.string().optional(),
  user_defined_id: z.string().optional(),
});

const StatusSchema = z.object({
  payment_token: z.string().optional(),
  transfer_id: z.string().optional(),
  funding_id: z.string().optional(),
});

const FundingListSchema = z.object({
  type: z.enum(['deposit', 'withdrawal', 'all']).optional(),
  limit: z.number().int().positive().optional(),
});

interface TreasuryPaymentResult {
  payment_token: string;
  status: string;
  result: string;
  direction: string;
  method: string;
  currency: string;
  pending_amount: number;
  settled_amount: number;
  financial_account_token: string;
  external_bank_account_token: string;
  user_defined_id?: string | null;
}

interface TreasuryBalanceResult {
  organization_id: string;
  financial_account_token: string;
  currency: string;
  available_amount_minor: number;
  pending_amount_minor: number;
  total_amount_minor: number;
  as_of_event_token?: string | null;
}

function toMinorUnits(input: number | string | undefined): number {
  if (input === undefined) return 0;
  const value = typeof input === 'number' ? input : Number.parseFloat(input);
  if (!Number.isFinite(value) || value <= 0) return 0;
  return Math.round(value * 100);
}

function buildSimulatedPayment(
  prefix: 'fund' | 'wd',
  direction: 'DEBIT' | 'CREDIT',
  amountMinor: number
): TreasuryPaymentResult & { funding_id?: string; withdrawal_id?: string } {
  const token = `${prefix}_${Date.now().toString(36)}`;
  const common = {
    payment_token: token,
    status: 'PENDING',
    result: 'APPROVED',
    direction,
    method: 'ACH_NEXT_DAY',
    currency: 'USD',
    pending_amount: amountMinor,
    settled_amount: 0,
    financial_account_token: 'fa_simulated',
    external_bank_account_token: 'eba_simulated',
  };
  return prefix === 'fund' ? { ...common, funding_id: token } : { ...common, withdrawal_id: token };
}

function serialize(result: unknown): ToolResult {
  return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
}

function validateLiveTreasuryArgs(
  financialAccountToken: string | undefined,
  externalBankAccountToken: string | undefined,
  amountMinor: number
): string | null {
  if (!financialAccountToken) return 'financial_account_token is required in live mode';
  if (!externalBankAccountToken) return 'external_bank_account_token is required in live mode';
  if (amountMinor <= 0) return 'amount or amount_minor must be greater than 0';
  return null;
}

export const fiatToolDefinitions: ToolDefinition[] = [
  {
    name: 'sardis_sync_treasury_account_holder',
    description: 'Sync financial accounts from Lithic for an account holder token.',
    inputSchema: {
      type: 'object',
      properties: { account_token: { type: 'string' } },
      required: [],
    },
  },
  {
    name: 'sardis_list_financial_accounts',
    description: 'List treasury financial accounts available for ACH funding and settlement.',
    inputSchema: {
      type: 'object',
      properties: {
        account_token: { type: 'string' },
        refresh: { type: 'boolean' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_link_external_bank_account',
    description: 'Create and link an external bank account for ACH rails.',
    inputSchema: {
      type: 'object',
      properties: {
        financial_account_token: { type: 'string' },
        verification_method: { type: 'string', enum: ['MICRO_DEPOSIT', 'PRENOTE', 'EXTERNALLY_VERIFIED'] },
        owner_type: { type: 'string', enum: ['INDIVIDUAL', 'BUSINESS'] },
        owner: { type: 'string' },
        account_type: { type: 'string', enum: ['CHECKING', 'SAVINGS'] },
        routing_number: { type: 'string' },
        account_number: { type: 'string' },
        name: { type: 'string' },
        currency: { type: 'string' },
        country: { type: 'string' },
      },
      required: ['financial_account_token', 'owner', 'routing_number', 'account_number'],
    },
  },
  {
    name: 'sardis_verify_micro_deposits',
    description: 'Verify external bank account ownership with two micro-deposit amounts.',
    inputSchema: {
      type: 'object',
      properties: {
        token: { type: 'string' },
        micro_deposits: { type: 'array', items: { type: 'string' }, minItems: 2, maxItems: 2 },
      },
      required: ['token', 'micro_deposits'],
    },
  },
  {
    name: 'sardis_fund_wallet',
    description: 'fund treasury via ACH collection. USD-first route for card spend backing.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: { type: 'number', description: 'Legacy amount in major units (USD)' },
        amount_minor: { type: 'number', description: 'Amount in minor units (e.g. cents)' },
        financial_account_token: { type: 'string' },
        external_bank_account_token: { type: 'string' },
        method: { type: 'string', enum: ['ACH_NEXT_DAY', 'ACH_SAME_DAY'] },
        sec_code: { type: 'string', enum: ['CCD', 'PPD', 'WEB'] },
        memo: { type: 'string' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_withdraw_to_bank',
    description: 'Withdraw treasury funds to an external bank account via ACH payment.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: { type: 'number', description: 'Legacy amount in major units (USD)' },
        amount_minor: { type: 'number', description: 'Amount in minor units (e.g. cents)' },
        financial_account_token: { type: 'string' },
        external_bank_account_token: { type: 'string' },
        method: { type: 'string', enum: ['ACH_NEXT_DAY', 'ACH_SAME_DAY'] },
        sec_code: { type: 'string', enum: ['CCD', 'PPD', 'WEB'] },
      },
      required: [],
    },
  },
  {
    name: 'sardis_withdraw',
    description: 'Alias for sardis_withdraw_to_bank.',
    inputSchema: {
      type: 'object',
      properties: {
        amount: { type: 'number' },
        amount_minor: { type: 'number' },
        account_id: { type: 'string' },
        financial_account_token: { type: 'string' },
        external_bank_account_token: { type: 'string' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_funding_status',
    description: 'Get status of a treasury payment token.',
    inputSchema: {
      type: 'object',
      properties: {
        payment_token: { type: 'string' },
        transfer_id: { type: 'string' },
        funding_id: { type: 'string' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_withdrawal_status',
    description: 'Get withdrawal status by treasury payment token.',
    inputSchema: {
      type: 'object',
      properties: {
        payment_token: { type: 'string' },
        transfer_id: { type: 'string' },
      },
      required: [],
    },
  },
  {
    name: 'sardis_get_treasury_balances',
    description: 'Get latest treasury balances across linked financial accounts.',
    inputSchema: {
      type: 'object',
      properties: {},
      required: [],
    },
  },
  {
    name: 'sardis_list_funding_transactions',
    description: 'List treasury funding and withdrawal activity (simulated summary in sandbox mode).',
    inputSchema: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['deposit', 'withdrawal', 'all'] },
        limit: { type: 'number' },
      },
      required: [],
    },
  },
];

export const fiatToolHandlers: Record<string, ToolHandler> = {
  sardis_sync_treasury_account_holder: async (args: unknown): Promise<ToolResult> => {
    const parsed = AccountHolderSyncSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return serialize([
        {
          organization_id: 'org_simulated',
          financial_account_token: 'fa_simulated',
          account_role: 'ISSUING',
          currency: 'USD',
          status: 'OPEN',
          is_program_level: false,
        },
      ]);
    }
    try {
      return serialize(await apiRequest('POST', '/api/v2/treasury/account-holders/sync', parsed.data));
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to sync account holder: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_list_financial_accounts: async (args: unknown): Promise<ToolResult> => {
    const parsed = ListFinancialAccountsSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return serialize([
        {
          organization_id: 'org_simulated',
          financial_account_token: 'fa_simulated',
          account_role: 'ISSUING',
          currency: 'USD',
          status: 'OPEN',
          is_program_level: false,
        },
      ]);
    }
    try {
      const search = new URLSearchParams();
      if (parsed.data.account_token) search.set('account_token', parsed.data.account_token);
      search.set('refresh', String(parsed.data.refresh ?? false));
      return serialize(await apiRequest('GET', `/api/v2/treasury/financial-accounts?${search.toString()}`));
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to list financial accounts: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_link_external_bank_account: async (args: unknown): Promise<ToolResult> => {
    const parsed = LinkExternalBankSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return serialize({
        organization_id: 'org_simulated',
        external_bank_account_token: 'eba_simulated',
        financial_account_token: parsed.data.financial_account_token,
        owner: parsed.data.owner,
        owner_type: parsed.data.owner_type ?? 'BUSINESS',
        verification_method: parsed.data.verification_method ?? 'MICRO_DEPOSIT',
        verification_state: 'PENDING',
        state: 'ENABLED',
        account_type: parsed.data.account_type ?? 'CHECKING',
        currency: parsed.data.currency ?? 'USD',
        country: parsed.data.country ?? 'USA',
      });
    }
    try {
      return serialize(await apiRequest('POST', '/api/v2/treasury/external-bank-accounts', parsed.data));
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to link bank account: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_verify_micro_deposits: async (args: unknown): Promise<ToolResult> => {
    const parsed = VerifyMicroDepositsSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return serialize({
        external_bank_account_token: parsed.data.token,
        verification_state: 'ENABLED',
        state: 'ENABLED',
      });
    }
    try {
      return serialize(
        await apiRequest(
          'POST',
          `/api/v2/treasury/external-bank-accounts/${parsed.data.token}/verify-micro-deposits`,
          { micro_deposits: parsed.data.micro_deposits }
        )
      );
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to verify micro deposits: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_fund_wallet: async (args: unknown): Promise<ToolResult> => {
    const parsed = FundWalletSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const amountMinor = parsed.data.amount_minor ?? toMinorUnits(parsed.data.amount);
    if (amountMinor <= 0) {
      return { content: [{ type: 'text', text: 'Invalid request: amount or amount_minor is required' }], isError: true };
    }
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simulated = buildSimulatedPayment('fund', 'DEBIT', amountMinor || 10000);
      return serialize({
        ...simulated,
        wallet_id: parsed.data.wallet_id || config.walletId || 'wallet_default',
        source_type: parsed.data.source || 'ach',
        message: `Funding initiated for ${((simulated.pending_amount || 0) / 100).toFixed(2)} USD`,
      });
    }

    const validationError = validateLiveTreasuryArgs(
      parsed.data.financial_account_token,
      parsed.data.external_bank_account_token,
      amountMinor
    );
    if (validationError) return { content: [{ type: 'text', text: `Invalid request: ${validationError}` }], isError: true };

    try {
      const result = await apiRequest<TreasuryPaymentResult>('POST', '/api/v2/treasury/fund', {
        financial_account_token: parsed.data.financial_account_token,
        external_bank_account_token: parsed.data.external_bank_account_token,
        amount_minor: amountMinor,
        method: parsed.data.method ?? 'ACH_NEXT_DAY',
        sec_code: parsed.data.sec_code ?? 'CCD',
        memo: parsed.data.memo,
        idempotency_key: parsed.data.idempotency_key,
        user_defined_id: parsed.data.user_defined_id,
      });
      return serialize({ ...result, funding_id: result.payment_token });
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to fund wallet: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_withdraw_to_bank: async (args: unknown): Promise<ToolResult> => {
    const parsed = WithdrawSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const amountMinor = parsed.data.amount_minor ?? toMinorUnits(parsed.data.amount);
    if (amountMinor <= 0) {
      return { content: [{ type: 'text', text: 'Invalid request: amount or amount_minor is required' }], isError: true };
    }
    const externalBankAccountToken = parsed.data.external_bank_account_token ?? parsed.data.destination_id ?? parsed.data.account_id;
    const config = getConfig();

    if (!config.apiKey || config.mode === 'simulated') {
      const simulated = buildSimulatedPayment('wd', 'CREDIT', amountMinor || 10000);
      return serialize({
        ...simulated,
        wallet_id: parsed.data.wallet_id || config.walletId || 'wallet_default',
        destination_bank: externalBankAccountToken || 'eba_simulated',
        estimated_arrival: '1-2 business days',
      });
    }

    const validationError = validateLiveTreasuryArgs(
      parsed.data.financial_account_token,
      externalBankAccountToken,
      amountMinor
    );
    if (validationError) return { content: [{ type: 'text', text: `Invalid request: ${validationError}` }], isError: true };

    try {
      const result = await apiRequest<TreasuryPaymentResult>('POST', '/api/v2/treasury/withdraw', {
        financial_account_token: parsed.data.financial_account_token,
        external_bank_account_token: externalBankAccountToken,
        amount_minor: amountMinor,
        method: parsed.data.method ?? 'ACH_NEXT_DAY',
        sec_code: parsed.data.sec_code ?? 'CCD',
        memo: parsed.data.memo,
        idempotency_key: parsed.data.idempotency_key,
        user_defined_id: parsed.data.user_defined_id,
      });
      return serialize({ ...result, withdrawal_id: result.payment_token });
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to withdraw: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_get_funding_status: async (args: unknown): Promise<ToolResult> => {
    const parsed = StatusSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const token = parsed.data.payment_token || parsed.data.transfer_id || parsed.data.funding_id;
    if (!token) return { content: [{ type: 'text', text: 'Invalid request: payment_token or transfer_id is required' }], isError: true };
    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return serialize({ payment_token: token, funding_id: token, status: 'SETTLED', type: 'funding' });
    }
    try {
      const result = await apiRequest<TreasuryPaymentResult>('GET', `/api/v2/treasury/payments/${token}`);
      return serialize({ ...result, funding_id: result.payment_token });
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to get status: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_get_withdrawal_status: async (args: unknown): Promise<ToolResult> => {
    const parsed = StatusSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const token = parsed.data.payment_token || parsed.data.transfer_id;
    if (!token) return { content: [{ type: 'text', text: 'Invalid request: payment_token or transfer_id is required' }], isError: true };
    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return serialize({ payment_token: token, withdrawal_id: token, status: 'PROCESSING', type: 'withdrawal' });
    }
    try {
      const result = await apiRequest<TreasuryPaymentResult>('GET', `/api/v2/treasury/payments/${token}`);
      return serialize({ ...result, withdrawal_id: result.payment_token });
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to get status: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_get_treasury_balances: async (): Promise<ToolResult> => {
    const config = getConfig();
    if (!config.apiKey || config.mode === 'simulated') {
      return serialize([
        {
          organization_id: 'org_simulated',
          financial_account_token: 'fa_simulated',
          currency: 'USD',
          available_amount_minor: 250000,
          pending_amount_minor: 10000,
          total_amount_minor: 260000,
        },
      ]);
    }
    try {
      return serialize(await apiRequest<TreasuryBalanceResult[]>('GET', '/api/v2/treasury/balances'));
    } catch (error) {
      return { content: [{ type: 'text', text: `Failed to fetch balances: ${error instanceof Error ? error.message : 'Unknown error'}` }], isError: true };
    }
  },

  sardis_withdraw: async (args: unknown): Promise<ToolResult> => {
    const withdrawToBankHandler = fiatToolHandlers['sardis_withdraw_to_bank'];
    if (!withdrawToBankHandler) {
      return { content: [{ type: 'text', text: 'withdraw handler is unavailable' }], isError: true };
    }
    return withdrawToBankHandler(args);
  },

  sardis_list_funding_transactions: async (args: unknown): Promise<ToolResult> => {
    const parsed = FundingListSchema.safeParse(args);
    if (!parsed.success) return { content: [{ type: 'text', text: `Invalid request: ${parsed.error.message}` }], isError: true };
    const config = getConfig();
    const typeFilter = parsed.data.type ?? 'all';
    const limit = parsed.data.limit ?? 20;

    if (!config.apiKey || config.mode === 'simulated') {
      const mockTransactions = [
        { id: 'fund_001', type: 'deposit', amount_minor: 100000, status: 'SETTLED' },
        { id: 'wd_001', type: 'withdrawal', amount_minor: 25000, status: 'PENDING' },
      ];
      const filtered = typeFilter === 'all' ? mockTransactions : mockTransactions.filter((tx) => tx.type === typeFilter);
      return serialize(filtered.slice(0, limit));
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify(
          {
            message: 'List endpoint is not exposed yet. Use sardis_get_funding_status/sardis_get_withdrawal_status per payment token.',
            supported_paths: ['/api/v2/treasury/payments/{payment_token}', '/api/v2/treasury/balances'],
          },
          null,
          2
        ),
      }],
    };
  },
};
