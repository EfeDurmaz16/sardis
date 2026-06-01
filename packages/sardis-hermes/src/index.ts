/**
 * @sardis/hermes — governance-middleware adapter.
 *
 * A TS port of the Aspendos Hermes `GovernanceMiddleware.wrap` pattern (the
 * Python original is re-implemented, not copied; all YULA/Aspendos/fides/agit
 * naming and the memory-layer logic are dropped). The idea Hermes contributes:
 * **wrap any tool execution so it is classified and hash-committed before money
 * is requested**, with an optional approval hook that can let an
 * `approval_only` action through after a human / second factor says yes.
 *
 * It is built ON TOP of `@sardis/agent-tools`: classification, the canonical
 * `sardis_<hash>` commit, and the fail-closed gate all come from the core. This
 * adapter adds the decorator surface (`wrap`) + lifecycle callbacks
 * (`onBlocked` / `onApprovalNeeded`) and pre-wraps the five Sardis verbs.
 */
import {
  governedToolCall,
  classifyAction,
  createCommitHash,
  type ClassifyFn,
  type GovernedResult,
  type ReversibilityClass,
  type SardisToolContext,
  type SardisToolDefinition,
  ALL_VERBS,
} from '@sardis/agent-tools';

export interface HermesOptions {
  /** Shared Sardis tool context (client, walletId, agentId, approvalThreshold). */
  context: SardisToolContext;
  /** Custom classifier; defaults to the Sardis classifier. */
  classify?: ClassifyFn;
  /** Called when an action is blocked (fail-closed). */
  onBlocked?: (toolName: string, result: GovernedResult) => void;
  /**
   * Called when an action needs approval. Return (or resolve) `true` to let it
   * execute anyway (a human / second factor approved); `false`/absent keeps it
   * `awaiting_approval`. This is the one place Hermes differs from the bare
   * gate: an approval hook can downgrade `approval_only` to execution.
   */
  onApprovalNeeded?: (
    toolName: string,
    result: GovernedResult,
  ) => boolean | Promise<boolean>;
}

/** A governed tool execution function. */
export type GovernedFn<TArgs = unknown> = (args: TArgs) => Promise<GovernedResult>;

export class GovernanceMiddleware {
  private readonly ctx: SardisToolContext;
  private readonly classify: ClassifyFn;
  private readonly onBlocked?: HermesOptions['onBlocked'];
  private readonly onApprovalNeeded?: HermesOptions['onApprovalNeeded'];

  constructor(opts: HermesOptions) {
    this.ctx = opts.context;
    this.classify = opts.classify ?? classifyAction;
    this.onBlocked = opts.onBlocked;
    this.onApprovalNeeded = opts.onApprovalNeeded;
  }

  /**
   * Wrap an execute function as a governed tool. The returned fn classifies +
   * commits before calling `executeFn`, fires the lifecycle callbacks, and (if
   * `onApprovalNeeded` approves) executes an otherwise approval-gated action.
   */
  wrap<TArgs = unknown>(
    toolName: string,
    executeFn: (args: TArgs, ctx: SardisToolContext) => Promise<unknown>,
  ): GovernedFn<TArgs> {
    return async (args: TArgs): Promise<GovernedResult> => {
      const cls: ReversibilityClass = this.classify(toolName, args, this.ctx);

      // approval_only + an approval hook that says yes -> execute anyway.
      if (cls === 'approval_only' && this.onApprovalNeeded) {
        const commitHash = await createCommitHash(toolName, args, this.ctx, cls);
        const pending: GovernedResult = {
          status: 'awaiting_approval',
          outcome: 'requires_approval',
          commitHash,
          reversibilityClass: cls,
          badge: 'APPROVAL_REQUIRED',
        };
        const approved = await this.onApprovalNeeded(toolName, pending);
        if (approved) {
          // Force the compensatable path through the gate so it executes while
          // keeping the (true) reversibility class on the record.
          const result = await governedToolCall(
            toolName,
            args,
            this.ctx,
            (a, c) => executeFn(a as TArgs, c),
            () => 'compensatable',
          );
          return { ...result, reversibilityClass: cls, badge: 'APPROVAL_REQUIRED' };
        }
        return pending;
      }

      const result = await governedToolCall(
        toolName,
        args,
        this.ctx,
        (a, c) => executeFn(a as TArgs, c),
        () => cls,
      );

      if (result.status === 'blocked' && result.reversibilityClass === 'irreversible_blocked') {
        this.onBlocked?.(toolName, result);
      }
      return result;
    };
  }

  /**
   * The five Sardis verbs, each pre-wrapped as a governed fn. Call e.g.
   * `tools.sardis_spend({ to, amount })`.
   */
  tools(): Record<string, GovernedFn> {
    const out: Record<string, GovernedFn> = {};
    for (const def of ALL_VERBS as SardisToolDefinition[]) {
      out[def.name] = this.wrap(def.name, (a, c) => def.execute(a, c));
    }
    return out;
  }
}

/** Convenience factory mirroring the langchain/vercel-ai `create*` style. */
export function createGovernanceMiddleware(opts: HermesOptions): GovernanceMiddleware {
  return new GovernanceMiddleware(opts);
}

export type { GovernedResult, SardisToolContext, ReversibilityClass } from '@sardis/agent-tools';
