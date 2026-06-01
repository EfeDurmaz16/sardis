/**
 * @sardis/nemoclaw — NemoClaw governance layer.
 *
 * The closest 1:1 port of the Aspendos NemoClaw adapter, rebranded to Sardis
 * (`nemo_` -> `sardis_`; all YULA/Aspendos/fides/agit naming and the
 * container-sandbox specifics that are not Sardis's concern are dropped). The
 * distinctive NemoClaw trait kept here: a `sandboxId` (and optional `userId`)
 * is **bound into every governance commit**, so a Sardis spend is traceable to
 * the exact sandbox that produced it.
 *
 * It is built on `@sardis/agent-tools`: classification, the canonical commit,
 * and the fail-closed gate come from the core. This adapter binds the sandbox
 * identity into the committed envelope and exposes a `governedToolCall` and a
 * pre-wrapped verb set keyed by sandbox.
 */
import {
  governedToolCall as coreGovernedToolCall,
  classifyAction,
  type ClassifyFn,
  type GovernedResult,
  type SardisToolContext,
  ALL_VERBS,
  type SardisToolDefinition,
} from '@sardis/agent-tools';
import type { SardisNemoContext } from './types.js';

const defaultClassify: ClassifyFn = classifyAction;

export type { SardisNemoContext } from './types.js';
export type { GovernedResult, ReversibilityClass } from '@sardis/agent-tools';

/**
 * Fold the sandbox identity into the args envelope so it is bound into the
 * canonical `sardis_<hash>` commit (the core hashes the args). The wrapped
 * verbs strip this envelope back off before routing to the SDK, so the sandbox
 * id influences the commit without leaking into the money call.
 */
const SANDBOX_KEY = '__sardisSandbox';

interface SandboxEnvelope {
  [SANDBOX_KEY]: { sandboxId: string; userId?: string };
  args: unknown;
}

function wrapArgs(ctx: SardisNemoContext, args: unknown): SandboxEnvelope {
  return {
    [SANDBOX_KEY]: { sandboxId: ctx.sandboxId, ...(ctx.userId ? { userId: ctx.userId } : {}) },
    args,
  };
}

function unwrapArgs(value: unknown): unknown {
  if (value && typeof value === 'object' && SANDBOX_KEY in (value as object)) {
    return (value as SandboxEnvelope).args;
  }
  return value;
}

/**
 * Govern a single tool call inside a sandbox. Same gate as the core, but the
 * commit hash is bound to `sandboxId` (+ `userId`). `classifyFn` still sees the
 * REAL tool args (not the envelope) so thresholds work unchanged.
 */
export async function governedToolCall(
  toolName: string,
  args: unknown,
  ctx: SardisNemoContext,
  executeFn: (args: unknown, ctx: SardisToolContext) => Promise<unknown>,
  classifyFn?: ClassifyFn,
): Promise<GovernedResult> {
  const envelope = wrapArgs(ctx, args);
  const classify: ClassifyFn = (name, _wrapped, c) =>
    (classifyFn ?? defaultClassify)(name, args, c);

  return coreGovernedToolCall(
    toolName,
    envelope,
    ctx,
    (wrapped, c) => executeFn(unwrapArgs(wrapped), c),
    classify,
  );
}

/**
 * Govern a Sardis spend inside a sandbox — the headline NemoClaw verb.
 */
export function governedSpend(
  ctx: SardisNemoContext,
  spend: { to: string; amount: string; token?: string; chain?: string; purpose?: string },
): Promise<GovernedResult> {
  const spendDef = (ALL_VERBS as SardisToolDefinition[]).find((t) => t.name === 'sardis_spend')!;
  return governedToolCall('sardis_spend', spend, ctx, (a, c) => spendDef.execute(a, c));
}

/** All five Sardis verbs as governed fns bound to one sandbox context. */
export function createNemoTools(
  ctx: SardisNemoContext,
): Record<string, (args: unknown) => Promise<GovernedResult>> {
  const out: Record<string, (args: unknown) => Promise<GovernedResult>> = {};
  for (const def of ALL_VERBS as SardisToolDefinition[]) {
    out[def.name] = (args: unknown) =>
      governedToolCall(def.name, args, ctx, (a, c) => def.execute(a, c));
  }
  return out;
}
