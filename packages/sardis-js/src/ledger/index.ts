/**
 * `sardis/ledger` — audit log + Merkle proof helpers.
 *
 * Thin façade over the `ledger` resource of the Sardis client.
 */

export { LedgerResource } from '../resources/ledger.js';
export type { LedgerEntry } from '../types.js';

/**
 * Compose a stable, sortable key for a ledger entry. Useful for
 * idempotent client-side caches and dedupe.
 */
export function ledgerKey(entry: { tx_id: string; created_at: string }): string {
  return `${entry.created_at}|${entry.tx_id}`;
}
