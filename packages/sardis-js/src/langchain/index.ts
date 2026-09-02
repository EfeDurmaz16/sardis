/**
 * `sardis/langchain` — LangChain.js integration.
 *
 * Mirrors the Python toolkit in
 * `packages/sardis-langchain/src/sardis_langchain/tools.py` — 5 tools that
 * wrap the Sardis client and report errors as structured JSON so the agent
 * loop never crashes.
 *
 * `@langchain/core` is an *optional* peer dep — importing this module
 * lazily resolves it at runtime so the v2 SDK can ship without forcing the
 * heavy LangChain dep on every consumer.
 *
 * ```ts
 * import { createSardisTools } from "sardis/langchain";
 *
 * const tools = await createSardisTools({
 *   apiKey: process.env.SARDIS_API_KEY!,
 *   walletId: "wallet_abc",
 * });
 *
 * const agent = createToolCallingAgent({ llm, tools, prompt });
 * ```
 */

import { z } from 'zod';
import { Sardis } from '../index.js';
import type { SardisClientOptions } from '../core/types.js';
import type { Chain, Token } from '../types.js';

export interface CreateSardisToolsOptions extends SardisClientOptions {
  walletId: string;
  agentId?: string;
  /** Reuse an existing Sardis client instead of constructing a new one. */
  client?: Sardis;
}

// Minimal subset of the `@langchain/core` Tool / StructuredTool surface.
// We don't import the real type — it lives behind an optional peer dep.
export interface LangChainStructuredTool {
  name: string;
  description: string;
  schema: z.ZodTypeAny;
  invoke: (input: unknown) => Promise<string>;
}

const PaySchema = z.object({
  to: z.string().describe('Recipient wallet address or merchant identifier (e.g. "openai.com")'),
  amount: z.string().describe('Payment amount in token units (e.g. "25.00")'),
  token: z.string().optional().describe('Stablecoin: USDC, USDT, PYUSD, EURC (default USDC)'),
  chain: z.string().optional().describe('Chain: base, polygon, ethereum, arbitrum, optimism (default base)'),
  purpose: z.string().optional().describe('Reason for the payment (audit memo)'),
});

const CheckBalanceSchema = z.object({
  token: z.string().optional().describe('Token to check (default USDC)'),
  chain: z.string().optional().describe('Chain to query (default base)'),
});

const CheckPolicySchema = z.object({
  to: z.string().describe('Recipient address or merchant identifier'),
  amount: z.string().describe('Amount to validate'),
  token: z.string().optional(),
});

const SetPolicySchema = z.object({
  policy: z.string().describe('Natural-language spending policy, e.g. "Allow up to $50/day on AI APIs"'),
});

const ListTransactionsSchema = z.object({
  limit: z.number().optional().describe('Max number of results (default 20)'),
});

/**
 * Build a LangChain tool array from a Sardis configuration.
 *
 * Synchronous — returns plain objects with the LangChain `StructuredTool`
 * shape. `@langchain/core` is not imported, so consumers can wrap these via
 * `DynamicStructuredTool` if they want first-class LangChain behavior.
 */
export function createSardisTools(opts: CreateSardisToolsOptions): LangChainStructuredTool[] {
  const client = opts.client ?? new Sardis(opts);
  const walletId = opts.walletId;

  const safe = async (fn: () => Promise<unknown>): Promise<string> => {
    try {
      const out = await fn();
      return JSON.stringify({ success: true, data: out });
    } catch (e) {
      return JSON.stringify({
        success: false,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  };

  return [
    {
      name: 'sardis_pay',
      description:
        'Execute a stablecoin payment from the configured Sardis wallet. Use when the recipient and exact amount are known.',
      schema: PaySchema,
      invoke: (input) => {
        const parsed = PaySchema.parse(input);
        return safe(() =>
          client.pay({
            from: walletId,
            to: parsed.to,
            amount: parsed.amount,
            ...(parsed.token ? { token: parsed.token as Token } : {}),
            ...(parsed.chain ? { chain: parsed.chain as Chain } : {}),
            ...(parsed.purpose ? { memo: parsed.purpose } : {}),
          }),
        );
      },
    },
    {
      name: 'sardis_check_balance',
      description: 'Read the configured wallet balance for a given token + chain.',
      schema: CheckBalanceSchema,
      invoke: (input) => {
        const parsed = CheckBalanceSchema.parse(input);
        return safe(() =>
          client.wallets.getBalance(walletId, parsed.chain ?? 'base', parsed.token ?? 'USDC'),
        );
      },
    },
    {
      name: 'sardis_check_policy',
      description:
        'Verify a prospective payment against the active spending policy. Call before sardis_pay for amounts above the trust threshold.',
      schema: CheckPolicySchema,
      invoke: (input) => {
        const parsed = CheckPolicySchema.parse(input);
        return safe(() =>
          client.policies.check({
            agent_id: opts.agentId ?? '',
            amount: parsed.amount,
            ...(parsed.to ? { merchant_id: parsed.to } : {}),
          }),
        );
      },
    },
    {
      name: 'sardis_set_policy',
      description:
        'Apply a natural-language spending policy to the agent. Use sparingly — policy changes are recorded in the audit ledger.',
      schema: SetPolicySchema,
      invoke: (input) => {
        const parsed = SetPolicySchema.parse(input);
        return safe(() =>
          client.policies.apply(parsed.policy, opts.agentId ?? ''),
        );
      },
    },
    {
      name: 'sardis_list_transactions',
      description: 'List recent payments for the configured wallet.',
      schema: ListTransactionsSchema,
      invoke: (input) => {
        const parsed = ListTransactionsSchema.parse(input);
        return safe(() =>
          client.ledger.listEntries({ wallet_id: walletId, limit: parsed.limit ?? 20 }),
        );
      },
    },
  ];
}

/**
 * Optional: wrap the structured tools in `DynamicStructuredTool` instances
 * from `@langchain/core/tools`. Throws a helpful error if the peer dep is
 * missing.
 */
export async function createLangChainTools(opts: CreateSardisToolsOptions): Promise<unknown[]> {
  const tools = createSardisTools(opts);
  let LangChainCore: { DynamicStructuredTool: new (cfg: Record<string, unknown>) => unknown };
  try {
    LangChainCore = (await import('@langchain/core/tools')) as never;
  } catch {
    throw new Error(
      'createLangChainTools() requires `@langchain/core` as a peer dependency. Install it or use createSardisTools() to get the structured-tool objects directly.',
    );
  }
  return tools.map(
    (t) =>
      new LangChainCore.DynamicStructuredTool({
        name: t.name,
        description: t.description,
        schema: t.schema,
        func: async (input: unknown) => t.invoke(input),
      }),
  );
}
