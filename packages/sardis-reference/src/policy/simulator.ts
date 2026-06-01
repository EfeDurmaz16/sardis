/**
 * simulateSpend — the showcase: "would Sardis allow this?", offline, money-free.
 *
 * Pure mirror of `SpendingPolicy.validate_payment` (the synchronous, IO-free
 * subset of `evaluate`). It runs the SAME checks in the SAME order and returns
 * the SAME reason codes. The async/port-gated checks are omitted EXACTLY as
 * `validate_payment` omits them:
 *
 *   Check 7  (on-chain balance)   → WalletPort        — skipped
 *   Check 10 (merchant trust)     → MerchantTrustPort — skipped
 *   Check 12 (KYA attestation)    → KyaPort           — skipped
 *
 * Cumulative/window state is read from the caller-supplied `policy.spentTotal`
 * and each `TimeWindowLimit.currentSpent` — the in-memory fallback path Python
 * uses when no `policy_store` is injected. `now` is injectable for determinism.
 */
import type { SpendingPolicy, MerchantRule } from '../types/policy.js';
import type { SpendObject } from '../types/spend.js';
import type { Money } from '../types/money.js';
import { add, gt, zero } from '../types/money.js';
import { canSpend } from './limits.js';
import { categoriesMatch } from './category-match.js';
import { getMccInfo, isBlockedCategory } from './mcc.js';

export type Outcome = 'allow' | 'requires_approval' | 'deny';

export interface PolicyDecision {
  outcome: Outcome;
  /** Exact reason code from the Python engine. */
  reason: string;
  /** 1..12 for debuggability (the check that produced the outcome). */
  checkFailed?: number;
}

function ruleActive(rule: MerchantRule, now: number): boolean {
  return rule.expiresAtMs == null || now <= rule.expiresAtMs;
}

function ruleMatchesMerchant(
  rule: MerchantRule,
  merchantId: string,
  merchantCategory: string | undefined,
  now: number,
): boolean {
  if (!ruleActive(rule, now)) return false;
  // Case-insensitive matching prevents bypass via casing tricks.
  if (rule.merchantId && rule.merchantId.toLowerCase() === merchantId.toLowerCase()) {
    return true;
  }
  return Boolean(
    rule.category && merchantCategory && rule.category.toLowerCase() === merchantCategory.toLowerCase(),
  );
}

/** Mirrors `_get_effective_per_tx_limit`. */
function effectivePerTxLimit(policy: SpendingPolicy, spend: SpendObject, now: number): Money {
  if (policy.merchantRules.length === 0) {
    return policy.limitPerTx;
  }
  let resolvedCategory = spend.merchantCategory;
  if (!resolvedCategory && spend.mccCode) {
    const info = getMccInfo(spend.mccCode);
    if (info) resolvedCategory = info.category;
  }
  if (resolvedCategory) {
    for (const rule of policy.merchantRules) {
      if (!ruleActive(rule, now) || !rule.maxPerTx) continue;
      const matchField = rule.category || rule.merchantId;
      if (matchField && categoriesMatch(matchField, resolvedCategory)) {
        return rule.maxPerTx;
      }
    }
  }
  return policy.limitPerTx;
}

/** Mirrors `_check_merchant_rules`. */
function checkMerchantRules(
  policy: SpendingPolicy,
  merchantId: string,
  merchantCategory: string | undefined,
  amount: Money,
  now: number,
): { ok: boolean; reason: string } {
  for (const rule of policy.merchantRules) {
    if (rule.ruleType === 'deny' && ruleMatchesMerchant(rule, merchantId, merchantCategory, now)) {
      return { ok: false, reason: 'merchant_denied' };
    }
  }
  const allowRules = policy.merchantRules.filter((r) => r.ruleType === 'allow');
  if (allowRules.length > 0) {
    const match = allowRules.find((r) => ruleMatchesMerchant(r, merchantId, merchantCategory, now));
    if (!match) {
      return { ok: false, reason: 'merchant_not_allowlisted' };
    }
    if (match.maxPerTx && gt(amount, match.maxPerTx)) {
      return { ok: false, reason: 'merchant_cap_exceeded' };
    }
  }
  return { ok: true, reason: 'OK' };
}

/** Mirrors `_check_mcc_policy`. */
function checkMccPolicy(policy: SpendingPolicy, mccCode: string): { ok: boolean; reason: string } {
  if (policy.blockedMerchantCategories.length > 0 && isBlockedCategory(mccCode, policy.blockedMerchantCategories)) {
    const info = getMccInfo(mccCode);
    const categoryName = info ? info.category : 'unknown';
    return { ok: false, reason: `merchant_category_blocked:${categoryName}` };
  }
  const info = getMccInfo(mccCode);
  if (info && info.defaultBlocked) {
    return { ok: false, reason: `high_risk_merchant:${info.description}` };
  }
  return { ok: true, reason: 'OK' };
}

/**
 * Run the policy decision for a proposed spend. Pure; deterministic given `now`.
 */
export function simulateSpend(
  policy: SpendingPolicy,
  spend: SpendObject,
  opts: { now?: number } = {},
): PolicyDecision {
  const now = opts.now ?? 0;
  const amount = spend.amount;
  const fee = spend.fee ?? zero(amount.currency);
  const scope = spend.scope ?? 'all';

  // ── Check 1: Amount validation ──
  if (amount.minor <= 0n) {
    return { outcome: 'deny', reason: 'amount_must_be_positive', checkFailed: 1 };
  }
  if (fee.minor < 0n) {
    return { outcome: 'deny', reason: 'fee_must_be_non_negative', checkFailed: 1 };
  }
  const totalCost = add(amount, fee);

  // ── Check 2: Scope ──
  if (!policy.allowedScopes.includes('all') && !policy.allowedScopes.includes(scope)) {
    return { outcome: 'deny', reason: 'scope_not_allowed', checkFailed: 2 };
  }

  // ── Check 3: MCC ──
  if (spend.mccCode) {
    const mcc = checkMccPolicy(policy, spend.mccCode);
    if (!mcc.ok) {
      return { outcome: 'deny', reason: mcc.reason, checkFailed: 3 };
    }
  }

  // ── Check 4: Per-transaction limit ──
  const perTx = effectivePerTxLimit(policy, spend, now);
  if (gt(totalCost, perTx)) {
    return { outcome: 'deny', reason: 'per_transaction_limit', checkFailed: 4 };
  }

  // ── Check 5: Total lifetime limit (in-memory state) ──
  if (gt(add(policy.spentTotal, totalCost), policy.limitTotal)) {
    return { outcome: 'deny', reason: 'total_limit_exceeded', checkFailed: 5 };
  }

  // ── Check 6: Time-window limits ──
  // NOTE: in the in-memory path (no policy_store), Python returns the raw
  // `can_spend` reason ("time_window_limit") and short-circuits — it does NOT
  // emit "{daily,weekly,monthly}_limit_exceeded" (those only arise on the
  // DB-backed `policy_store` path, which is port-gated and omitted here).
  for (const win of [policy.daily, policy.weekly, policy.monthly]) {
    if (!win) continue;
    const res = canSpend(win, totalCost, now);
    if (!res.ok) {
      return { outcome: 'deny', reason: res.reason, checkFailed: 6 };
    }
  }

  // ── Check 7: on-chain balance — port-gated (WalletPort), skipped ──

  // ── Check 8: Merchant rules ──
  if (spend.merchantId) {
    const res = checkMerchantRules(policy, spend.merchantId, spend.merchantCategory, amount, now);
    if (!res.ok) {
      return { outcome: 'deny', reason: res.reason, checkFailed: 8 };
    }
  }

  // ── Check 9: Goal drift ──
  if (spend.driftScore != null && policy.maxDriftScore != null) {
    if (spend.driftScore > policy.maxDriftScore) {
      return { outcome: 'deny', reason: 'goal_drift_exceeded', checkFailed: 9 };
    }
  }

  // ── Check 10: merchant trust — port-gated (MerchantTrustPort), skipped ──

  // ── Check 11: Approval threshold ──
  if (policy.approvalThreshold != null && gt(amount, policy.approvalThreshold)) {
    return { outcome: 'requires_approval', reason: 'requires_approval', checkFailed: 11 };
  }

  // ── Check 12: KYA attestation — port-gated (KyaPort), skipped ──

  return { outcome: 'allow', reason: 'OK' };
}

/**
 * Deterministic execution guard. Mirrors `validate_execution_context`:
 * chain/token/destination allow/block-list checks with case normalization
 * (chain lower, token upper, destination lower).
 */
export function checkExecutionContext(policy: SpendingPolicy, spend: SpendObject): PolicyDecision {
  const norm = (v: string | undefined, mode: 'lower' | 'upper'): string => {
    const s = (v ?? '').trim();
    return mode === 'lower' ? s.toLowerCase() : s.toUpperCase();
  };
  const chainNorm = norm(spend.chain, 'lower');
  const tokenNorm = norm(spend.token, 'upper');
  const destNorm = norm(spend.destination, 'lower');

  const allowedChains = new Set(policy.allowedChains.map((c) => norm(c, 'lower')).filter(Boolean));
  const allowedTokens = new Set(policy.allowedTokens.map((t) => norm(t, 'upper')).filter(Boolean));
  const allowedDest = new Set(policy.allowedDestinations.map((d) => norm(d, 'lower')).filter(Boolean));
  const blockedDest = new Set(policy.blockedDestinations.map((d) => norm(d, 'lower')).filter(Boolean));

  if (allowedChains.size > 0 && !allowedChains.has(chainNorm)) {
    return { outcome: 'deny', reason: 'chain_not_allowlisted' };
  }
  if (allowedTokens.size > 0 && !allowedTokens.has(tokenNorm)) {
    return { outcome: 'deny', reason: 'token_not_allowlisted' };
  }
  if (destNorm) {
    if (blockedDest.has(destNorm)) {
      return { outcome: 'deny', reason: 'destination_blocked' };
    }
    if (allowedDest.size > 0 && !allowedDest.has(destNorm)) {
      return { outcome: 'deny', reason: 'destination_not_allowlisted' };
    }
  } else if (allowedDest.size > 0) {
    return { outcome: 'deny', reason: 'destination_required_for_allowlist' };
  }
  return { outcome: 'allow', reason: 'OK' };
}
