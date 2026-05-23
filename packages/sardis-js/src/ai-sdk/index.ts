/**
 * `sardis/ai-sdk` — Vercel AI SDK provider.
 *
 * Mirrors the Vercel AI SDK provider convention (`createOpenAI`,
 * `createAnthropic`, ...) — exposes a `createSardis(opts)` factory plus
 * a default `sardisProvider` helper.
 *
 * Crucially, this provider INTERNALLY uses the umbrella `Sardis` client
 * from the package root. The v1 `@sardis/ai-sdk` package re-implemented
 * REST calls directly against axios, which is the root cause of API
 * fragmentation called out in `~/project-directions/sardis-ts-sdk-redesign.md`.
 * Here we have exactly one HTTP path, exactly one error hierarchy, and
 * exactly one set of types.
 *
 * ```ts
 * import { createSardis } from "sardis/ai-sdk";
 * import { generateText } from "ai";
 * import { openai } from "@ai-sdk/openai";
 *
 * const sardis = createSardis({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: "wallet_abc",
 * });
 *
 * await generateText({
 *   model: openai("gpt-4o"),
 *   tools: sardis.tools,
 *   system: sardis.systemPrompt,
 *   prompt: "Pay $20 for OpenAI credits",
 * });
 * ```
 */

import { z } from 'zod';
import { Sardis } from '../index.js';
import type { SardisClientOptions } from '../core/types.js';
import type { Chain, Token } from '../types.js';

/* -------------------------------------------------------------------------- */
/* Tool I/O schemas (Zod) — exported so callers can compose                    */
/* -------------------------------------------------------------------------- */

export const PayInputSchema = z.object({
  to: z.string().describe('Recipient wallet address or merchant ID'),
  amount: z.string().describe('Amount in token-decimal units (e.g. "25.00")'),
  token: z.string().optional().describe('Token symbol (default: USDC)'),
  chain: z.string().optional().describe('Chain (default: base)'),
  memo: z.string().optional().describe('Free-form memo recorded in the ledger'),
});
export type PayInputT = z.infer<typeof PayInputSchema>;

export const HoldCreateSchema = z.object({
  amount: z.string().describe('Hold amount in token-decimal units'),
  token: z.string().optional(),
  merchantId: z.string().optional(),
  purpose: z.string().optional(),
  durationHours: z.number().optional(),
});
export type HoldCreateT = z.infer<typeof HoldCreateSchema>;

export const HoldCaptureSchema = z.object({
  holdId: z.string(),
  amount: z.string().optional().describe('Partial capture amount (defaults to full hold)'),
});
export type HoldCaptureT = z.infer<typeof HoldCaptureSchema>;

export const HoldVoidSchema = z.object({
  holdId: z.string(),
});
export type HoldVoidT = z.infer<typeof HoldVoidSchema>;

export const BalanceSchema = z.object({
  token: z.string().optional().describe('Token symbol (default: USDC)'),
  chain: z.string().optional().describe('Chain to query'),
});
export type BalanceT = z.infer<typeof BalanceSchema>;

export const PolicyCheckSchema = z.object({
  amount: z.string(),
  merchant: z.string().optional(),
  category: z.string().optional(),
});
export type PolicyCheckT = z.infer<typeof PolicyCheckSchema>;

/* -------------------------------------------------------------------------- */
/* Provider config                                                             */
/* -------------------------------------------------------------------------- */

export interface CreateSardisOptions extends SardisClientOptions {
  /** Default wallet to act on. Required for tool execution. */
  walletId: string;
  /** Optional agent identifier passed to telemetry / audit. */
  agentId?: string;
  /** Hook called after every successful or failed tool invocation. */
  onTransaction?: (event: TransactionEvent) => void | Promise<void>;
  /** Customize the system prompt appended to the agent loop. */
  customInstructions?: string;
  /** Reuse an existing Sardis client instead of constructing a new one. */
  client?: Sardis;
}

export interface TransactionEvent {
  type: 'pay' | 'hold_create' | 'hold_capture' | 'hold_void' | 'balance' | 'policy_check';
  timestamp: string;
  input: Record<string, unknown>;
  output: unknown;
  success: boolean;
  error?: string;
  durationMs: number;
}

/**
 * Shape returned by `createSardis(...)`. The `tools` map is directly
 * compatible with Vercel AI SDK `generateText({ tools })` and
 * `streamText({ tools })`.
 *
 * `client` is the underlying Sardis instance — exposed so callers can drop
 * down to the full SDK surface (e.g. `provider.client.escrow.holds.create(...)`).
 */
export interface SardisProvider {
  readonly client: Sardis;
  readonly walletId: string;
  readonly tools: Record<string, AISDKTool>;
  readonly systemPrompt: string;
  pay(input: PayInputT): Promise<unknown>;
  balance(input?: BalanceT): Promise<unknown>;
}

/**
 * Vercel AI SDK `tool({ description, parameters, execute })` shape.
 *
 * The `ai` package isn't a hard dep — when present at runtime we just
 * return objects of this shape. `generateText` accepts duck-typed tools.
 */
export interface AISDKTool {
  description: string;
  parameters: z.ZodTypeAny;
  execute: (args: unknown) => Promise<unknown>;
}

const DEFAULT_SYSTEM_PROMPT = `You are an AI agent with access to a Sardis payment wallet.

Guidelines:
1. Check policy via sardis_check_policy before any payment over $50.
2. For uncertain amounts, create a hold first, then capture once the final amount is known. Void holds you no longer need.
3. Always report the transaction ID and status. If a payment fails, explain why and propose an alternative.
4. Never expose wallet IDs, API keys, or signing material.
5. Confirm the merchant and amount with the user for payments over $100.

Available tools:
- sardis_pay: Send a payment
- sardis_create_hold: Reserve funds
- sardis_capture_hold: Settle a hold
- sardis_void_hold: Cancel a hold
- sardis_get_balance: Read balance
- sardis_check_policy: Verify a payment is permitted`;

/* -------------------------------------------------------------------------- */
/* Factory                                                                     */
/* -------------------------------------------------------------------------- */

export function createSardis(opts: CreateSardisOptions): SardisProvider {
  const client = opts.client ?? new Sardis(opts);
  const walletId = opts.walletId;

  const wrap = async <I extends Record<string, unknown>, O>(
    type: TransactionEvent['type'],
    input: I,
    fn: () => Promise<O>,
  ): Promise<O> => {
    const start = Date.now();
    let output: unknown;
    let success = true;
    let error: string | undefined;
    try {
      output = await fn();
      return output as O;
    } catch (e) {
      success = false;
      error = e instanceof Error ? e.message : String(e);
      throw e;
    } finally {
      if (opts.onTransaction) {
        try {
          await opts.onTransaction({
            type,
            timestamp: new Date().toISOString(),
            input,
            output,
            success,
            error,
            durationMs: Date.now() - start,
          });
        } catch {
          // never let telemetry crash the agent loop
        }
      }
    }
  };

  const tools: Record<string, AISDKTool> = {
    sardis_pay: {
      description:
        'Execute a stablecoin payment from the configured wallet. Use for direct payments where the amount is known.',
      parameters: PayInputSchema,
      execute: async (args) => {
        const input = PayInputSchema.parse(args);
        return wrap('pay', input, () =>
          client.pay({
            from: walletId,
            to: input.to,
            amount: input.amount,
            ...(input.token ? { token: input.token as Token } : {}),
            ...(input.chain ? { chain: input.chain as Chain } : {}),
            ...(input.memo ? { memo: input.memo } : {}),
          }),
        );
      },
    },
    sardis_create_hold: {
      description: 'Reserve funds for a future payment. Use when the final amount is uncertain.',
      parameters: HoldCreateSchema,
      execute: async (args) => {
        const input = HoldCreateSchema.parse(args);
        return wrap('hold_create', input, () =>
          client.holds.create({
            wallet_id: walletId,
            amount: input.amount,
            ...(input.token ? { token: input.token as Token } : {}),
            ...(input.merchantId ? { merchant_id: input.merchantId } : {}),
            ...(input.purpose ? { purpose: input.purpose } : {}),
            ...(input.durationHours ? { duration_hours: input.durationHours } : {}),
          } as never),
        );
      },
    },
    sardis_capture_hold: {
      description: 'Capture a previously created hold, settling the payment.',
      parameters: HoldCaptureSchema,
      execute: async (args) => {
        const input = HoldCaptureSchema.parse(args);
        return wrap('hold_capture', input, () =>
          (client.holds as unknown as { capture: (id: string, body: Record<string, unknown>) => Promise<unknown> }).capture(
            input.holdId,
            input.amount ? { amount: input.amount } : {},
          ),
        );
      },
    },
    sardis_void_hold: {
      description: 'Cancel a hold and release the reserved funds.',
      parameters: HoldVoidSchema,
      execute: async (args) => {
        const input = HoldVoidSchema.parse(args);
        return wrap('hold_void', input, () =>
          (client.holds as unknown as { void: (id: string) => Promise<unknown> }).void(input.holdId),
        );
      },
    },
    sardis_get_balance: {
      description: 'Read the current balance of the configured wallet for a given token/chain.',
      parameters: BalanceSchema,
      execute: async (args) => {
        const input = BalanceSchema.parse(args);
        return wrap('balance', input, () =>
          (client.wallets as unknown as {
            getBalance: (id: string, params: Record<string, unknown>) => Promise<unknown>;
          }).getBalance(walletId, {
            ...(input.token ? { token: input.token } : {}),
            ...(input.chain ? { chain: input.chain } : {}),
          }),
        );
      },
    },
    sardis_check_policy: {
      description: 'Verify a prospective payment against the active spending policy.',
      parameters: PolicyCheckSchema,
      execute: async (args) => {
        const input = PolicyCheckSchema.parse(args);
        return wrap('policy_check', input, () =>
          (client.policies as unknown as {
            check: (body: Record<string, unknown>) => Promise<unknown>;
          }).check({
            amount: input.amount,
            ...(input.merchant ? { merchant: input.merchant } : {}),
            ...(input.category ? { category: input.category } : {}),
          }),
        );
      },
    },
  };

  const systemPrompt = opts.customInstructions
    ? `${DEFAULT_SYSTEM_PROMPT}\n\nAdditional instructions:\n${opts.customInstructions}`
    : DEFAULT_SYSTEM_PROMPT;

  return {
    client,
    walletId,
    tools,
    systemPrompt,
    pay: (input: PayInputT) => tools['sardis_pay']!.execute(input),
    balance: (input: BalanceT = {}) => tools['sardis_get_balance']!.execute(input),
  };
}

/**
 * Lazy default-provider helper. Mirrors the `openai` / `anthropic` defaults
 * exported by their respective Vercel AI SDK packages.
 *
 * Reads `SARDIS_API_KEY` and `SARDIS_WALLET_ID` from the environment.
 * Import has no side effects — construction is deferred to first call.
 */
export const sardisProvider = {
  default(): SardisProvider {
    const apiKey = process.env['SARDIS_API_KEY'];
    const walletId = process.env['SARDIS_WALLET_ID'];
    if (!apiKey || !walletId) {
      throw new Error(
        'sardisProvider.default() requires SARDIS_API_KEY and SARDIS_WALLET_ID env vars',
      );
    }
    return createSardis({ apiKey, walletId });
  },
};
