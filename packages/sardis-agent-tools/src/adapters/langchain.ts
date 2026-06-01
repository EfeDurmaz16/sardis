/**
 * `@sardis/agent-tools/langchain` — reshape the Sardis verbs into LangChain.js
 * structured tools, following the `sardis/langchain` precedent: a `safe()`
 * wrapper returns JSON so the agent loop never throws, and `@langchain/core` is
 * an OPTIONAL peer dep (lazily imported only in `createLangChainTools`).
 *
 * Unlike the raw SDK tools, every invocation goes through the governance gate
 * (`runGoverned`), so the returned JSON carries the authority decision
 * (`status` / `outcome` / `reversibilityClass` / `commitHash`). An at/above-
 * threshold spend returns `awaiting_approval` and is NOT executed.
 */
import type { z } from 'zod';
import type { SardisToolContext } from '../types.js';
import { ALL_VERBS } from '../tools/verbs.js';
import { buildRegistry, runGoverned } from '../index.js';

export interface LangChainStructuredTool {
  name: string;
  description: string;
  schema: z.ZodTypeAny;
  invoke: (input: unknown) => Promise<string>;
}

/**
 * Build LangChain structured tools from a Sardis context. Synchronous; returns
 * plain objects with the LangChain `StructuredTool` shape.
 */
export function createSardisLangChainTools(ctx: SardisToolContext): LangChainStructuredTool[] {
  const registry = buildRegistry();
  return ALL_VERBS.map((tool) => ({
    name: tool.name,
    description: tool.description,
    schema: tool.schema,
    invoke: async (input: unknown): Promise<string> => {
      const result = await runGoverned(tool.name, input, ctx, { registry });
      return JSON.stringify(result);
    },
  }));
}

/**
 * Optional: wrap the structured tools in `DynamicStructuredTool` instances from
 * `@langchain/core/tools`. Throws a helpful error if the peer dep is missing.
 */
export async function createLangChainTools(ctx: SardisToolContext): Promise<unknown[]> {
  const tools = createSardisLangChainTools(ctx);
  let core: { DynamicStructuredTool: new (cfg: Record<string, unknown>) => unknown };
  try {
    core = (await import('@langchain/core/tools')) as never;
  } catch {
    throw new Error(
      'createLangChainTools() requires `@langchain/core` as a peer dependency. Install it or use createSardisLangChainTools() to get the structured-tool objects directly.',
    );
  }
  return tools.map(
    (t) =>
      new core.DynamicStructuredTool({
        name: t.name,
        description: t.description,
        schema: t.schema,
        func: async (input: unknown) => t.invoke(input),
      }),
  );
}
