/**
 * governedToolCall — the governance middleware.
 *
 * Ported from the Aspendos NemoClaw `governedToolCall`, rebranded to Sardis and
 * extended so the result carries the simulator-aligned authority outcome
 * (`allow | requires_approval | deny`). Flow:
 *
 *   1. classify the action (default classifier, fail-closed for unknown verbs);
 *   2. if `irreversible_blocked` -> return `blocked` / `deny` WITHOUT executing;
 *   3. compute the canonical `sardis_<hash>` commit;
 *   4. if `approval_only` -> return `awaiting_approval` / `requires_approval`,
 *      WITHOUT executing (the money path is never touched until approved);
 *   5. otherwise execute (route to the Sardis SDK) and return `executed` /
 *      `allow`, capturing any thrown error as `blocked`.
 */
import type {
  GovernedResult,
  ReversibilityClass,
  SardisToolContext,
} from './types.js';
import { BADGE, outcomeForClass } from './types.js';
import { createCommitHash } from './canonical.js';
import { classifyAction } from './classify.js';

export type ClassifyFn = (
  toolName: string,
  args: unknown,
  ctx: SardisToolContext,
) => ReversibilityClass;

export async function governedToolCall(
  toolName: string,
  args: unknown,
  ctx: SardisToolContext,
  executeFn: (args: unknown, ctx: SardisToolContext) => Promise<unknown>,
  classifyFn: ClassifyFn = classifyAction,
): Promise<GovernedResult> {
  const cls = classifyFn(toolName, args, ctx);

  if (cls === 'irreversible_blocked') {
    return {
      status: 'blocked',
      outcome: 'deny',
      commitHash: '',
      reversibilityClass: cls,
      badge: BADGE[cls],
      error: `Action "${toolName}" blocked by governance policy (fail-closed)`,
    };
  }

  const commitHash = await createCommitHash(toolName, args, ctx, cls);

  if (cls === 'approval_only') {
    return {
      status: 'awaiting_approval',
      outcome: 'requires_approval',
      commitHash,
      reversibilityClass: cls,
      badge: BADGE[cls],
    };
  }

  try {
    const result = await executeFn(args, ctx);
    return {
      status: 'executed',
      outcome: outcomeForClass(cls),
      commitHash,
      reversibilityClass: cls,
      badge: BADGE[cls],
      result,
    };
  } catch (e) {
    return {
      status: 'blocked',
      outcome: 'deny',
      commitHash,
      reversibilityClass: cls,
      badge: BADGE[cls],
      error: e instanceof Error ? e.message : String(e),
    };
  }
}
