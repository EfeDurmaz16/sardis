/**
 * SpendObject — the proposed spend, the pure input to the policy simulator.
 *
 * The money-free analogue of "a payment the agent wants to make". Mirrors the
 * arguments of `SpendingPolicy.evaluate(amount, fee, ...)` /
 * `validate_payment(...)`.
 */
import type { Money } from './money.js';

export type Rail = 'card' | 'usdc' | 'bank';

export type SpendingScope =
  | 'all'
  | 'retail'
  | 'digital'
  | 'services'
  | 'compute'
  | 'data'
  | 'agent_to_agent';

export interface SpendObject {
  /** Payment amount only (the fee is separate, mirroring evaluate(amount, fee)). */
  amount: Money;
  /** Gas/tx fee; included in the per-tx, total and window limit checks. Default 0. */
  fee?: Money;
  merchantId?: string;
  /** Category name, e.g. "cloud" | "gambling". */
  merchantCategory?: string;
  /** 4-digit Merchant Category Code. */
  mccCode?: string;
  /** Spending scope. Default "all". */
  scope?: SpendingScope;
  rail?: Rail;
  /** Chain id string, e.g. "base" (execution-context guard). */
  chain?: string;
  /** Token symbol, e.g. "USDC" (execution-context guard). */
  token?: string;
  /** Destination address, e.g. "0x..." (execution-context guard). */
  destination?: string;
  /** Goal-drift score 0.0–1.0 (optional). */
  driftScore?: number;
}
