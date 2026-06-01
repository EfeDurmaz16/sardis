import type { SardisToolContext } from '@sardis/agent-tools';

/**
 * NemoClaw secures the *container*; Sardis governs the *spend*. The NemoClaw
 * context carries the sandbox the agent is running in, plus an optional user
 * id, so every governed commit is bound to the sandbox that produced it.
 */
export interface SardisNemoContext extends SardisToolContext {
  /** The sandbox / container id the agent runs in. Bound into every commit. */
  sandboxId: string;
  /** Optional acting user id (bound into the commit alongside the sandbox). */
  userId?: string;
}
