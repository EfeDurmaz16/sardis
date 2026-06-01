/**
 * SardisToolRegistry — ported from the Aspendos core tool registry, adapted to
 * `SardisToolDefinition`. The key behavior is preserved: an unknown tool
 * **fails closed** to `irreversible_blocked` so a typo or an injected verb can
 * never auto-execute a money action.
 */
import type { ReversibilityClass, SardisToolContext, SardisToolDefinition } from './types.js';

export class SardisToolRegistry {
  private tools = new Map<string, SardisToolDefinition>();

  register(tool: SardisToolDefinition): this {
    this.tools.set(tool.name, tool);
    return this;
  }

  get(name: string): SardisToolDefinition | undefined {
    return this.tools.get(name);
  }

  has(name: string): boolean {
    return this.tools.has(name);
  }

  /** Classify a (possibly unknown) tool — fail-closed for unknown names. */
  classify(name: string, args: unknown, ctx: SardisToolContext): ReversibilityClass {
    const tool = this.tools.get(name);
    if (!tool) {
      // Unknown tool -> blocked by default (fail-closed).
      return 'irreversible_blocked';
    }
    return tool.classify(args, ctx);
  }

  list(): SardisToolDefinition[] {
    return Array.from(this.tools.values());
  }

  names(): string[] {
    return Array.from(this.tools.keys());
  }
}
