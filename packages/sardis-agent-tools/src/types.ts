/**
 * Core contracts for the Sardis agent-tool surface.
 *
 * A `SardisToolDefinition` is one agent verb (give-wallet, spend, issue-card,
 * set-budget, pay-invoice, ...). It carries a zod schema (like the existing
 * `sardis/langchain` adapter), a `classify()` that decides the reversibility
 * class BEFORE money is requested, and an `execute()` that routes to the Sardis
 * SDK (`sardis`). Adapters never re-implement money movement — they delegate to
 * the client, which talks to the private backend.
 *
 * The governance shape (`ReversibilityClass`, `GovernedResult`, the canonical
 * commit hash) is the Sardis re-spelling of the Aspendos NemoClaw middleware,
 * rebranded (`nemo_` -> `sardis_`) with all YULA/Aspendos/memory-layer naming
 * dropped.
 */
import type { z } from 'zod';
import type { Sardis } from 'sardis';

/**
 * How reversible an action is — the gate the governance layer keys off.
 *   - undoable            : trivially reversible (create a wallet, set a budget)
 *   - cancelable_window   : reversible within a window
 *   - compensatable       : reversible by a compensating action (freeze a card)
 *   - approval_only       : must NOT auto-execute; needs a human / second factor
 *   - irreversible_blocked: fail-closed; never executed
 */
export type ReversibilityClass =
  | 'undoable'
  | 'cancelable_window'
  | 'compensatable'
  | 'approval_only'
  | 'irreversible_blocked';

/** Stable text badge per class (no emoji — Sardis design rule). */
export const BADGE: Record<ReversibilityClass, string> = {
  undoable: 'UNDOABLE',
  cancelable_window: 'CANCELABLE',
  compensatable: 'COMPENSATABLE',
  approval_only: 'APPROVAL_REQUIRED',
  irreversible_blocked: 'BLOCKED',
};

/** The authority decision an agent sees, aligned with the policy simulator. */
export type AuthorityOutcome = 'allow' | 'requires_approval' | 'deny';

/** Map a reversibility class to the simulator-style authority outcome. */
export function outcomeForClass(cls: ReversibilityClass): AuthorityOutcome {
  if (cls === 'irreversible_blocked') return 'deny';
  if (cls === 'approval_only') return 'requires_approval';
  return 'allow';
}

/** Execution context shared by every Sardis tool. */
export interface SardisToolContext {
  /** The Sardis SDK client — the ONLY money path. */
  client: Sardis;
  /** Default source wallet for spend / card / balance verbs. */
  walletId?: string;
  /** Acting agent id (used by give-wallet / set-budget). */
  agentId?: string;
  /**
   * Amount (in token-major units, e.g. "50") at/above which spend & pay-invoice
   * classify `approval_only` instead of auto-executing. Default "50".
   */
  approvalThreshold?: string;
  /** Optional correlation id bound into the commit hash. */
  actionId?: string;
}

/** A single agent verb. */
export interface SardisToolDefinition {
  /** e.g. "sardis_spend". */
  name: string;
  description: string;
  /** zod schema for the tool arguments (matches the langchain adapter shape). */
  schema: z.ZodTypeAny;
  /** Decide the reversibility class from the args + context, before executing. */
  classify(args: unknown, ctx: SardisToolContext): ReversibilityClass;
  /** Route to the Sardis SDK. Never re-implements money movement. */
  execute(args: unknown, ctx: SardisToolContext): Promise<unknown>;
}

/**
 * The governed result of a tool call — ported from the NemoClaw middleware,
 * with the authority outcome added so it lines up with the policy simulator's
 * `{ outcome: allow | requires_approval | deny }` contract.
 */
export interface GovernedResult {
  status: 'executed' | 'blocked' | 'awaiting_approval';
  /** allow / requires_approval / deny — the simulator-aligned view of status. */
  outcome: AuthorityOutcome;
  /** `sardis_<sha256[:40]>` commit over the canonical action, or '' if blocked pre-hash. */
  commitHash: string;
  reversibilityClass: ReversibilityClass;
  badge: string;
  result?: unknown;
  error?: string;
}
