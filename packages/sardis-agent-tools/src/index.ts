/**
 * @sardis/agent-tools — Sardis as a TOOL for AI agents.
 *
 * A framework-agnostic core: five agent verbs (give-wallet, spend, issue-card,
 * set-budget, pay-invoice) plus supporting read/compensating verbs, each routing
 * to the Sardis SDK (`sardis`), wrapped in a fail-closed governance gate
 * (classify -> canonical commit hash -> allow / requires_approval / deny). The
 * generic LangChain / Vercel-AI / MCP adapters live in subpath modules
 * (`@sardis/agent-tools/{langchain,vercel-ai,mcp}`).
 *
 * The verbs never re-implement money movement — they delegate to the client,
 * which talks to the private backend. The local classification mirrors the
 * `@sardis/reference` policy simulator's outcome contract so an agent sees the
 * same `allow | requires_approval | deny` view everywhere.
 */
import type { GovernedResult, SardisToolContext, SardisToolDefinition } from './types.js';
import { governedToolCall, type ClassifyFn } from './governed.js';
import { SardisToolRegistry } from './registry.js';
import { ALL_VERBS } from './tools/verbs.js';

export * from './types.js';
export * from './canonical.js';
export * from './classify.js';
export * from './amount.js';
export { SardisToolRegistry } from './registry.js';
export { governedToolCall, type ClassifyFn } from './governed.js';
export * from './tools/verbs.js';

/** Options for building the Sardis agent tool set. */
export type CreateSardisAgentToolsOptions = SardisToolContext;

/**
 * Return all Sardis verbs as `SardisToolDefinition`s. Framework adapters reshape
 * these into their native tool type.
 */
export function createSardisAgentTools(_opts?: CreateSardisAgentToolsOptions): SardisToolDefinition[] {
  return [...ALL_VERBS];
}

/** Build a fail-closed registry pre-loaded with every Sardis verb. */
export function buildRegistry(): SardisToolRegistry {
  const registry = new SardisToolRegistry();
  for (const tool of ALL_VERBS) registry.register(tool);
  return registry;
}

/**
 * Run a named Sardis verb through the governance gate, resolving the verb from
 * the registry so an unknown name fails closed. This is the one-call entry
 * point an adapter or a scaffold's `/agent/execute` route uses.
 */
export async function runGoverned(
  toolName: string,
  args: unknown,
  ctx: SardisToolContext,
  opts?: { registry?: SardisToolRegistry; classify?: ClassifyFn },
): Promise<GovernedResult> {
  const registry = opts?.registry ?? buildRegistry();
  const tool = registry.get(toolName);
  const classify: ClassifyFn =
    opts?.classify ?? ((name, a, c) => registry.classify(name, a, c));

  const execute = async (a: unknown, c: SardisToolContext): Promise<unknown> => {
    if (!tool) {
      // Should be unreachable (unknown -> irreversible_blocked before execute),
      // but keep it explicit and fail-closed.
      throw new Error(`Unknown tool "${toolName}"`);
    }
    return tool.execute(a, c);
  };

  return governedToolCall(toolName, args, ctx, execute, classify);
}
