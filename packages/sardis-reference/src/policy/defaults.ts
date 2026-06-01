/**
 * DEFAULT_LIMITS, createDefaultPolicy, and the KYA ↔ TrustLevel maps.
 *
 * Mirrors `spending_policy.py` `DEFAULT_LIMITS`, `create_default_policy`,
 * `KYA_TO_TRUST`, `TRUST_TO_KYA`. Limits are expressed in minor units using the
 * default 2-decimal USD-style precision the Python presets imply ($50 = 5000).
 */
import type { SpendingPolicy, TrustLevel, TimeWindowLimit, WindowType } from '../types/policy.js';
import type { Currency, Money } from '../types/money.js';

export interface TierLimits {
  perTx: bigint;
  daily: bigint | null;
  weekly: bigint | null;
  monthly: bigint | null;
  total: bigint;
}

/** Minor units at 2 decimals (e.g. $50.00 → 5000n). */
export const DEFAULT_LIMITS: Record<TrustLevel, TierLimits> = {
  low: { perTx: 5_000n, daily: 10_000n, weekly: 50_000n, monthly: 100_000n, total: 500_000n },
  medium: { perTx: 50_000n, daily: 100_000n, weekly: 500_000n, monthly: 1_000_000n, total: 5_000_000n },
  high: { perTx: 500_000n, daily: 1_000_000n, weekly: 5_000_000n, monthly: 10_000_000n, total: 50_000_000n },
  unlimited: { perTx: 99_999_999_900n, daily: null, weekly: null, monthly: null, total: 99_999_999_900n },
};

export const KYA_TO_TRUST: Record<string, TrustLevel> = {
  none: 'low',
  basic: 'low',
  verified: 'medium',
  attested: 'high',
};

export const TRUST_TO_KYA: Record<TrustLevel, string> = {
  low: 'basic',
  medium: 'verified',
  high: 'attested',
  unlimited: 'attested',
};

export function trustLevelForKya(kyaLevel: string): TrustLevel {
  return KYA_TO_TRUST[kyaLevel.toLowerCase()] ?? 'low';
}

export function kyaLevelForTrust(trustLevel: TrustLevel): string {
  return TRUST_TO_KYA[trustLevel] ?? 'basic';
}

function window(windowType: WindowType, limit: bigint, currency: Currency, now: number): TimeWindowLimit {
  return {
    windowType,
    limit: { minor: limit, currency },
    currentSpent: { minor: 0n, currency },
    windowStartMs: now,
  };
}

/**
 * Build a SpendingPolicy with preset limits for a trust level.
 * Mirrors `create_default_policy`. `now` seeds the window starts (default 0 for
 * determinism in fixtures).
 */
export function createDefaultPolicy(
  agentId: string,
  trustLevel: TrustLevel = 'low',
  opts: { currency?: Currency; now?: number; kyaLevel?: string } = {},
): SpendingPolicy {
  const currency = opts.currency ?? 'USDC';
  const now = opts.now ?? 0;
  const level = opts.kyaLevel != null ? trustLevelForKya(opts.kyaLevel) : trustLevel;
  const tier = DEFAULT_LIMITS[level];
  const m = (minor: bigint): Money => ({ minor, currency });

  const policy: SpendingPolicy = {
    policyId: `policy_ref_${agentId}`,
    agentId,
    trustLevel: level,
    limitPerTx: m(tier.perTx),
    limitTotal: m(tier.total),
    spentTotal: m(0n),
    merchantRules: [],
    allowedScopes: ['all'],
    blockedMerchantCategories: [],
    allowedChains: [],
    allowedTokens: [],
    allowedDestinations: [],
    blockedDestinations: [],
    maxDriftScore: 0.5,
  };
  if (tier.daily != null) policy.daily = window('daily', tier.daily, currency, now);
  if (tier.weekly != null) policy.weekly = window('weekly', tier.weekly, currency, now);
  if (tier.monthly != null) policy.monthly = window('monthly', tier.monthly, currency, now);
  return policy;
}
