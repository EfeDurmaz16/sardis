/**
 * The Sardis agent verbs — "Sardis = a TOOL".
 *
 * Each verb is a `SardisToolDefinition` whose `execute()` routes to a method on
 * the Sardis SDK (`sardis`). The adapters NEVER re-implement money movement,
 * signing, or the backend policy decision — they delegate to the client, which
 * talks to the private backend. The local `classify()` is the cheap client-side
 * gate (see `classify.ts`), aligned with the `@sardis/reference` policy
 * simulator's `allow | requires_approval | deny` outcome contract.
 *
 * Routing table (verb -> SDK call):
 *   sardis_give_wallet       -> client.wallets.create({ agent_id, ... })
 *   sardis_spend             -> client.pay({ from, to, amount, ... })
 *   sardis_issue_card        -> client.cards.issue({ wallet_id, ... })
 *   sardis_set_budget        -> client.policies.apply(policy, agentId)
 *   sardis_pay_invoice       -> client.payments.executeMandate(mandate) | client.pay(...)
 *   sardis_check_balance     -> client.wallets.getBalance(walletId, chain, token)
 *   sardis_check_policy      -> client.policies.check({ agent_id, amount, ... })
 *   sardis_list_transactions -> client.ledger.listEntries({ wallet_id, limit })
 *   sardis_freeze_card       -> client.cards.freeze(cardId)   (compensating action)
 */
import { z } from 'zod';
import type { Token, Chain } from 'sardis';
import type { SardisToolContext, SardisToolDefinition } from '../types.js';
import { classifyAction } from '../classify.js';

// ── Schemas (mirror the `sardis/langchain` adapter's zod style) ──────────────

const GiveWalletSchema = z.object({
  agentId: z
    .string()
    .optional()
    .describe('Agent that will own the wallet. Defaults to the context agentId.'),
  currency: z.string().optional().describe('Default token (USDC, EURC, ...). Default USDC.'),
  limitPerTx: z.string().optional().describe('Per-transaction spending limit (token units).'),
  limitTotal: z.string().optional().describe('Total spending limit (token units).'),
});

const SpendSchema = z.object({
  to: z.string().describe('Recipient wallet address, on-chain address, or merchant id.'),
  amount: z.string().describe('Amount in token units, e.g. "25.00".'),
  token: z.string().optional().describe('Stablecoin: USDC, USDT, PYUSD, EURC. Default USDC.'),
  chain: z.string().optional().describe('base, polygon, ethereum, arbitrum, optimism. Default base.'),
  purpose: z.string().optional().describe('Audit memo / reason for the payment.'),
});

const IssueCardSchema = z.object({
  cardType: z.string().optional().describe('Card type (e.g. "virtual"). Provider default if omitted.'),
  limitPerTx: z.string().optional().describe('Per-transaction limit (token units).'),
  limitDaily: z.string().optional().describe('Daily limit (token units).'),
  limitMonthly: z.string().optional().describe('Monthly limit (token units).'),
  lockedMerchantId: z.string().optional().describe('Lock the card to a single merchant.'),
});

const SetBudgetSchema = z.object({
  policy: z
    .string()
    .describe('Natural-language spending policy, e.g. "Allow up to $50/day on AI APIs".'),
  agentId: z.string().optional().describe('Agent to apply to. Defaults to the context agentId.'),
});

const PayInvoiceSchema = z.object({
  mandate: z
    .record(z.string(), z.unknown())
    .optional()
    .describe('An AP2 payment mandate object. If present, routes through mandate execution.'),
  to: z.string().optional().describe('Fallback recipient when no mandate is supplied.'),
  amount: z.string().optional().describe('Fallback amount (token units) when no mandate is supplied.'),
  token: z.string().optional().describe('Fallback token. Default USDC.'),
  chain: z.string().optional().describe('Fallback chain. Default base.'),
  purpose: z.string().optional().describe('Audit memo.'),
});

const CheckBalanceSchema = z.object({
  token: z.string().optional().describe('Token to read. Default USDC.'),
  chain: z.string().optional().describe('Chain to query. Default base.'),
});

const CheckPolicySchema = z.object({
  to: z.string().describe('Recipient address or merchant id.'),
  amount: z.string().describe('Prospective amount (token units) to validate.'),
  currency: z.string().optional().describe('Token. Default USDC.'),
  merchantCategory: z.string().optional().describe('Merchant category, if known.'),
  mccCode: z.string().optional().describe('MCC code, if known.'),
});

const ListTransactionsSchema = z.object({
  limit: z.number().optional().describe('Max number of ledger entries (default 20).'),
});

const FreezeCardSchema = z.object({
  cardId: z.string().describe('Id of the card to freeze (the compensating action for issue-card).'),
});

// ── Helpers ──────────────────────────────────────────────────────────────────

function requireWallet(ctx: SardisToolContext): string {
  if (!ctx.walletId) {
    throw new Error('No walletId in context — give the agent a wallet first (sardis_give_wallet).');
  }
  return ctx.walletId;
}

// `client` resources are typed loosely at the call boundary (the langchain
// adapter does the same): the verbs commit to logical SDK methods, not to the
// exact private response types.
type AnyClient = SardisToolContext['client'];

// ── The verbs ──────────────────────────────────────────────────────────────

export const giveWalletTool: SardisToolDefinition = {
  name: 'sardis_give_wallet',
  description:
    'Create a non-custodial Sardis wallet for an agent. The wallet never holds keys; it signs via MPC. Undoable (archivable).',
  schema: GiveWalletSchema,
  classify: (args, ctx) => classifyAction('sardis_give_wallet', args, ctx),
  execute: async (args, ctx) => {
    const a = GiveWalletSchema.parse(args ?? {});
    const agentId = a.agentId ?? ctx.agentId;
    if (!agentId) {
      throw new Error('sardis_give_wallet requires an agentId (in args or context).');
    }
    return (ctx.client as AnyClient).wallets.create({
      agent_id: agentId,
      ...(a.currency ? { currency: a.currency as Token } : {}),
      ...(a.limitPerTx ? { limit_per_tx: a.limitPerTx } : {}),
      ...(a.limitTotal ? { limit_total: a.limitTotal } : {}),
    });
  },
};

export const spendTool: SardisToolDefinition = {
  name: 'sardis_spend',
  description:
    'Spend stablecoins from the agent wallet. Below the approval threshold it executes; at/above it returns awaiting_approval and does NOT move money.',
  schema: SpendSchema,
  classify: (args, ctx) => classifyAction('sardis_spend', args, ctx),
  execute: async (args, ctx) => {
    const a = SpendSchema.parse(args);
    return ctx.client.pay({
      from: requireWallet(ctx),
      to: a.to,
      amount: a.amount,
      ...(a.token ? { token: a.token as Token } : {}),
      ...(a.chain ? { chain: a.chain as Chain } : {}),
      ...(a.purpose ? { memo: a.purpose } : {}),
    });
  },
};

export const issueCardTool: SardisToolDefinition = {
  name: 'sardis_issue_card',
  description:
    'Issue a virtual card backed by the agent wallet. Compensatable — freeze the card to undo it (sardis_freeze_card).',
  schema: IssueCardSchema,
  classify: (args, ctx) => classifyAction('sardis_issue_card', args, ctx),
  execute: async (args, ctx) => {
    const a = IssueCardSchema.parse(args ?? {});
    return (ctx.client as AnyClient).cards.issue({
      wallet_id: requireWallet(ctx),
      ...(a.cardType ? { card_type: a.cardType } : {}),
      ...(a.limitPerTx ? { limit_per_tx: a.limitPerTx } : {}),
      ...(a.limitDaily ? { limit_daily: a.limitDaily } : {}),
      ...(a.limitMonthly ? { limit_monthly: a.limitMonthly } : {}),
      ...(a.lockedMerchantId ? { locked_merchant_id: a.lockedMerchantId } : {}),
    });
  },
};

export const setBudgetTool: SardisToolDefinition = {
  name: 'sardis_set_budget',
  description:
    'Apply a natural-language spending policy (budget) to the agent. Recorded in the audit ledger. Undoable.',
  schema: SetBudgetSchema,
  classify: (args, ctx) => classifyAction('sardis_set_budget', args, ctx),
  execute: async (args, ctx) => {
    const a = SetBudgetSchema.parse(args);
    const agentId = a.agentId ?? ctx.agentId;
    if (!agentId) {
      throw new Error('sardis_set_budget requires an agentId (in args or context).');
    }
    return (ctx.client as AnyClient).policies.apply(a.policy, agentId);
  },
};

export const payInvoiceTool: SardisToolDefinition = {
  name: 'sardis_pay_invoice',
  description:
    'Pay an invoice. With an AP2 mandate it runs the Intent->Cart->Payment mandate chain; otherwise it falls back to a direct payment. Approval-gated above the threshold.',
  schema: PayInvoiceSchema,
  classify: (args, ctx) => classifyAction('sardis_pay_invoice', args, ctx),
  execute: async (args, ctx) => {
    const a = PayInvoiceSchema.parse(args ?? {});
    if (a.mandate) {
      return ctx.client.payments.executeMandate(a.mandate);
    }
    if (!a.to || !a.amount) {
      throw new Error('sardis_pay_invoice needs either a `mandate` or both `to` and `amount`.');
    }
    return ctx.client.pay({
      from: requireWallet(ctx),
      to: a.to,
      amount: a.amount,
      ...(a.token ? { token: a.token as Token } : {}),
      ...(a.chain ? { chain: a.chain as Chain } : {}),
      ...(a.purpose ? { memo: a.purpose } : {}),
    });
  },
};

export const checkBalanceTool: SardisToolDefinition = {
  name: 'sardis_check_balance',
  description: 'Read the agent wallet balance for a token + chain (read-only).',
  schema: CheckBalanceSchema,
  classify: (args, ctx) => classifyAction('sardis_check_balance', args, ctx),
  execute: async (args, ctx) => {
    const a = CheckBalanceSchema.parse(args ?? {});
    return ctx.client.wallets.getBalance(requireWallet(ctx), a.chain ?? 'base', a.token ?? 'USDC');
  },
};

export const checkPolicyTool: SardisToolDefinition = {
  name: 'sardis_check_policy',
  description:
    'Validate a prospective payment against the active spending policy. Call before sardis_spend for amounts near/over the threshold.',
  schema: CheckPolicySchema,
  classify: (args, ctx) => classifyAction('sardis_check_policy', args, ctx),
  execute: async (args, ctx) => {
    const a = CheckPolicySchema.parse(args);
    if (!ctx.agentId) {
      throw new Error('sardis_check_policy requires an agentId in context.');
    }
    return ctx.client.policies.check({
      agent_id: ctx.agentId,
      amount: a.amount,
      ...(a.currency ? { currency: a.currency } : {}),
      merchant_id: a.to,
      ...(a.merchantCategory ? { merchant_category: a.merchantCategory } : {}),
      ...(a.mccCode ? { mcc_code: a.mccCode } : {}),
    });
  },
};

export const listTransactionsTool: SardisToolDefinition = {
  name: 'sardis_list_transactions',
  description: 'List recent audit-ledger entries for the agent wallet (read-only).',
  schema: ListTransactionsSchema,
  classify: (args, ctx) => classifyAction('sardis_list_transactions', args, ctx),
  execute: async (args, ctx) => {
    const a = ListTransactionsSchema.parse(args ?? {});
    return (ctx.client as AnyClient).ledger.listEntries({
      wallet_id: requireWallet(ctx),
      limit: a.limit ?? 20,
    });
  },
};

export const freezeCardTool: SardisToolDefinition = {
  name: 'sardis_freeze_card',
  description: 'Freeze a card — the compensating action that undoes sardis_issue_card.',
  schema: FreezeCardSchema,
  classify: (args, ctx) => classifyAction('sardis_freeze_card', args, ctx),
  execute: async (args, ctx) => {
    const a = FreezeCardSchema.parse(args);
    return ctx.client.cards.freeze(a.cardId);
  },
};

/** All Sardis verbs, in a stable order. */
export const ALL_VERBS: SardisToolDefinition[] = [
  giveWalletTool,
  spendTool,
  issueCardTool,
  setBudgetTool,
  payInvoiceTool,
  checkBalanceTool,
  checkPolicyTool,
  listTransactionsTool,
  freezeCardTool,
];
