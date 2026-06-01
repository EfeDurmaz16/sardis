/**
 * Canonical commit hash for a governed action.
 *
 * Ported from the Aspendos NemoClaw middleware (`normalizeForHash` +
 * `canonicalJson` + `sha256Hex`), rebranded to Sardis (`nemo_` -> `sardis_`).
 * Deterministic and order-independent: object keys are sorted recursively so
 * the same logical action always commits to the same hash, regardless of key
 * insertion order. Uses Web Crypto (`crypto.subtle`) — available on Node 18+,
 * all browsers, and edge runtimes — so the core stays dependency-free.
 */
import type { ReversibilityClass, SardisToolContext } from './types.js';

/** Recursively sort object keys so the hash is insertion-order-independent. */
export function normalizeForHash(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(normalizeForHash);
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, entry]) => [key, normalizeForHash(entry)]),
    );
  }
  return value;
}

/** Stable JSON of a value (sorted keys, no whitespace control beyond JSON). */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(normalizeForHash(value));
}

/** Hex SHA-256 of a UTF-8 payload via Web Crypto. */
export async function sha256Hex(payload: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(payload));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Compute the `sardis_<hash[:40]>` commit hash binding the tool name, args,
 * classification, and the identifying context fields.
 */
export async function createCommitHash(
  toolName: string,
  args: unknown,
  ctx: SardisToolContext,
  reversibilityClass: ReversibilityClass,
): Promise<string> {
  const payload = canonicalJson({
    actionId: ctx.actionId ?? null,
    agentId: ctx.agentId ?? null,
    args,
    reversibilityClass,
    toolName,
    walletId: ctx.walletId ?? null,
  });
  const digest = await sha256Hex(payload);
  return `sardis_${digest.slice(0, 40)}`;
}
