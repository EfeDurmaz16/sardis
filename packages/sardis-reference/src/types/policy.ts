/**
 * SpendingPolicy — the decision-engine state, mirroring the Python dataclass.
 *
 * Window/total state is caller-supplied (no IO here): the simulator reads
 * `spentTotal` and each `TimeWindowLimit.currentSpent` exactly as the Python
 * in-memory fallback path does.
 */
import type { Money } from './money.js';
import type { SpendingScope } from './spend.js';

export type TrustLevel = 'low' | 'medium' | 'high' | 'unlimited';
export type MerchantRuleType = 'allow' | 'deny';
export type WindowType = 'daily' | 'weekly' | 'monthly';

export interface TimeWindowLimit {
  windowType: WindowType;
  limit: Money;
  /** Caller-supplied window state (the simulator does no IO). */
  currentSpent: Money;
  /** Epoch ms when the current window started (for rolling reset). */
  windowStartMs: number;
}

export interface MerchantRule {
  ruleId: string;
  ruleType: MerchantRuleType;
  merchantId?: string;
  category?: string;
  maxPerTx?: Money;
  dailyLimit?: Money;
  /** Epoch ms; rule is inactive once `now > expiresAtMs`. */
  expiresAtMs?: number;
}

export interface SpendingPolicy {
  policyId: string;
  agentId: string;
  trustLevel: TrustLevel;
  limitPerTx: Money;
  limitTotal: Money;
  /** Caller-supplied cumulative spend state. */
  spentTotal: Money;
  daily?: TimeWindowLimit;
  weekly?: TimeWindowLimit;
  monthly?: TimeWindowLimit;
  merchantRules: MerchantRule[];
  /** Default ["all"]. */
  allowedScopes: SpendingScope[];
  blockedMerchantCategories: string[];
  allowedChains: string[];
  allowedTokens: string[];
  allowedDestinations: string[];
  blockedDestinations: string[];
  approvalThreshold?: Money;
  /** Default 0.5 (mirrors `max_drift_score`). */
  maxDriftScore?: number;
}
