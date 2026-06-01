/**
 * `@sardis/agent-tools/vercel-ai` — reshape the Sardis verbs into Vercel AI SDK
 * tools (`{ description, parameters, execute }`). `ai` is an OPTIONAL peer dep;
 * we build the tool objects WITHOUT importing it (the shape is structural), and
 * only the optional `createVercelAiToolSet` helper lazily resolves `ai`'s
 * `tool()` wrapper.
 *
 * Every `execute` runs through the governance gate, so the tool's return value
 * carries the authority decision (`status` / `outcome` / `commitHash`). An
 * at/above-threshold spend returns `awaiting_approval` and is NOT executed.
 */
import type { z } from 'zod';
import type { GovernedResult, SardisToolContext } from '../types.js';
import { ALL_VERBS } from '../tools/verbs.js';
import { buildRegistry, runGoverned } from '../index.js';

/** A Vercel AI SDK tool shape (structural — we do not import `ai`). */
export interface VercelAiTool {
  description: string;
  parameters: z.ZodTypeAny;
  execute: (args: unknown) => Promise<GovernedResult>;
}

/**
 * Build a Vercel AI tool set keyed by verb name. Pass the result straight into
 * `generateText({ tools })`.
 */
export function createVercelAiTools(ctx: SardisToolContext): Record<string, VercelAiTool> {
  const registry = buildRegistry();
  const out: Record<string, VercelAiTool> = {};
  for (const tool of ALL_VERBS) {
    out[tool.name] = {
      description: tool.description,
      parameters: tool.schema,
      execute: (args: unknown) => runGoverned(tool.name, args, ctx, { registry }),
    };
  }
  return out;
}

/**
 * Optional: wrap each tool with the Vercel AI SDK `tool()` helper for
 * first-class typing. Throws if the `ai` peer dep is missing.
 */
export async function createVercelAiToolSet(ctx: SardisToolContext): Promise<Record<string, unknown>> {
  let aiSdk: { tool: (cfg: Record<string, unknown>) => unknown };
  try {
    aiSdk = (await import('ai')) as never;
  } catch {
    throw new Error(
      "createVercelAiToolSet() requires `ai` (Vercel AI SDK) as a peer dependency. Install it or use createVercelAiTools() to get the plain tool objects directly.",
    );
  }
  const plain = createVercelAiTools(ctx);
  const out: Record<string, unknown> = {};
  for (const [name, t] of Object.entries(plain)) {
    out[name] = aiSdk.tool({
      description: t.description,
      parameters: t.parameters,
      execute: t.execute,
    });
  }
  return out;
}
