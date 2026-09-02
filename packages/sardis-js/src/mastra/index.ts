/**
 * `sardis/mastra` — Mastra (@mastra/core) integration.
 *
 * Mastra (https://mastra.ai) is a TS-native agent framework whose tool
 * pattern is `{ id, description, inputSchema, execute }`. This module
 * exposes the same 6 payment primitives as `sardis/ai-sdk`, shaped for
 * Mastra agents and workflows.
 *
 * `@mastra/core` is an *optional* peer dep — we never `import` it here.
 * Mastra accepts duck-typed tools so the plain objects we return Just Work.
 *
 * ```ts
 * import { Agent } from "@mastra/core";
 * import { createSardisMastraTools } from "sardis/mastra";
 *
 * const sardisTools = createSardisMastraTools({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: "wallet_abc",
 * });
 *
 * const agent = new Agent({
 *   name: "treasurer",
 *   instructions: "Manage company payments responsibly.",
 *   model: openai("gpt-4o"),
 *   tools: sardisTools,
 * });
 * ```
 */

import { z } from 'zod';
import { Sardis } from '../index.js';
import type { SardisClientOptions } from '../core/types.js';
import type { Chain, Token } from '../types.js';

export interface CreateSardisMastraOptions extends SardisClientOptions {
  walletId: string;
  agentId?: string;
  client?: Sardis;
}

/**
 * Mastra tool shape — `{ id, description, inputSchema, execute }`.
 *
 * `execute` returns the raw response object so Mastra workflows can branch
 * on it. Errors throw — Mastra's agent loop catches them and surfaces them
 * to the LLM as tool failures.
 */
export interface MastraTool<TInput = unknown, TOutput = unknown> {
  id: string;
  description: string;
  inputSchema: z.ZodTypeAny;
  execute: (ctx: { context: TInput }) => Promise<TOutput>;
}

const PaySchema = z.object({
  to: z.string(),
  amount: z.string(),
  token: z.string().optional(),
  chain: z.string().optional(),
  memo: z.string().optional(),
});

const HoldCreateSchema = z.object({
  amount: z.string(),
  token: z.string().optional(),
  merchantId: z.string().optional(),
  purpose: z.string().optional(),
  durationHours: z.number().optional(),
});

const HoldCaptureSchema = z.object({ holdId: z.string(), amount: z.string().optional() });
const HoldVoidSchema = z.object({ holdId: z.string() });
const BalanceSchema = z.object({ token: z.string().optional(), chain: z.string().optional() });
const PolicyCheckSchema = z.object({
  amount: z.string(),
  merchant: z.string().optional(),
  category: z.string().optional(),
});

/**
 * Build Mastra tools from a Sardis configuration. Returns an object keyed
 * by tool id so callers can spread `...sardisTools` into an Agent.
 */
export function createSardisMastraTools(
  opts: CreateSardisMastraOptions,
): Record<string, MastraTool> {
  const client = opts.client ?? new Sardis(opts);
  const walletId = opts.walletId;

  return {
    sardis_pay: {
      id: 'sardis_pay',
      description: 'Execute a stablecoin payment from the configured Sardis wallet.',
      inputSchema: PaySchema,
      execute: async ({ context }) => {
        const input = PaySchema.parse(context);
        return client.pay({
          from: walletId,
          to: input.to,
          amount: input.amount,
          ...(input.token ? { token: input.token as Token } : {}),
          ...(input.chain ? { chain: input.chain as Chain } : {}),
          ...(input.memo ? { memo: input.memo } : {}),
        });
      },
    },
    sardis_create_hold: {
      id: 'sardis_create_hold',
      description: 'Reserve funds for a payment whose final amount is not yet known.',
      inputSchema: HoldCreateSchema,
      execute: async ({ context }) => {
        const input = HoldCreateSchema.parse(context);
        return client.holds.create({
          wallet_id: walletId,
          amount: input.amount,
          ...(input.token ? { token: input.token as Token } : {}),
          ...(input.merchantId ? { merchant_id: input.merchantId } : {}),
          ...(input.purpose ? { purpose: input.purpose } : {}),
          ...(input.durationHours ? { duration_hours: input.durationHours } : {}),
        } as never);
      },
    },
    sardis_capture_hold: {
      id: 'sardis_capture_hold',
      description: 'Capture a previously created hold, settling the payment.',
      inputSchema: HoldCaptureSchema,
      execute: async ({ context }) => {
        const input = HoldCaptureSchema.parse(context);
        return client.holds.capture(input.holdId, input.amount);
      },
    },
    sardis_void_hold: {
      id: 'sardis_void_hold',
      description: 'Cancel a hold and release the reserved funds.',
      inputSchema: HoldVoidSchema,
      execute: async ({ context }) => {
        const input = HoldVoidSchema.parse(context);
        return client.holds.void(input.holdId);
      },
    },
    sardis_get_balance: {
      id: 'sardis_get_balance',
      description: 'Read the configured wallet balance.',
      inputSchema: BalanceSchema,
      execute: async ({ context }) => {
        const input = BalanceSchema.parse(context);
        return client.wallets.getBalance(walletId, input.chain ?? 'base', input.token ?? 'USDC');
      },
    },
    sardis_check_policy: {
      id: 'sardis_check_policy',
      description: 'Verify a prospective payment against the active spending policy.',
      inputSchema: PolicyCheckSchema,
      execute: async ({ context }) => {
        const input = PolicyCheckSchema.parse(context);
        return client.policies.check({
          agent_id: opts.agentId ?? '',
          amount: input.amount,
          ...(input.merchant ? { merchant_id: input.merchant } : {}),
          ...(input.category ? { merchant_category: input.category } : {}),
        });
      },
    },
  };
}
