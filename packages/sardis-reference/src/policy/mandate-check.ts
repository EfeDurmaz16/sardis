/**
 * checkMandate — mirrors `SpendingMandate.check_payment` exactly.
 *
 * Check order and `MANDATE_*` error codes are reproduced verbatim:
 *   lifecycle → per-tx → total → merchant scope (blocked / not-allowed w/ `*`
 *   wildcard) → rail → chain → token → approval mode.
 *
 * Pure: lifecycle uses an injectable `now` (epoch ms) instead of a wall clock.
 */
import type { Mandate, MandateCheckResult, ApprovalMode } from '../types/mandate.js';
import type { Money } from '../types/money.js';
import type { Rail } from '../types/spend.js';
import { gt } from '../types/money.js';

export interface MandateSpend {
  amount: Money;
  merchant?: string;
  rail?: Rail;
  chain?: string;
  token?: string;
  purpose?: string;
}

/** Mirrors `SpendingMandate.is_active`. */
function isActive(mandate: Mandate, now: number): boolean {
  if (mandate.status !== 'active') return false;
  if (mandate.validFromMs != null && now < mandate.validFromMs) return false;
  if (mandate.expiresAtMs != null && now > mandate.expiresAtMs) return false;
  return true;
}

/** Mirrors `remaining_total`. */
function remainingTotal(mandate: Mandate): Money | null {
  if (!mandate.amountTotal) return null;
  return { minor: mandate.amountTotal.minor - mandate.spentTotal.minor, currency: mandate.amountTotal.currency };
}

/** Mirrors the wildcard match: `*.foo.com` → endsWith("foo.com"), else exact. */
function merchantMatchesAllowed(merchant: string, allowed: string[]): boolean {
  if (allowed.includes(merchant)) return true;
  return allowed.some((a) => (a.startsWith('*') ? merchant.endsWith(a.replace(/^\*+/, '')) : merchant === a));
}

export function checkMandate(
  mandate: Mandate,
  spend: MandateSpend,
  opts: { now?: number } = {},
): MandateCheckResult {
  const now = opts.now ?? 0;
  const amount = spend.amount;

  // Lifecycle
  if (!isActive(mandate, now)) {
    return {
      approved: false,
      reason: `Mandate is ${mandate.status}`,
      errorCode: 'MANDATE_NOT_ACTIVE',
      requiresApproval: false,
    };
  }

  // Per-transaction limit
  if (mandate.amountPerTx && gt(amount, mandate.amountPerTx)) {
    return {
      approved: false,
      reason: `Amount exceeds per-transaction limit`,
      errorCode: 'MANDATE_AMOUNT_EXCEEDED',
      requiresApproval: false,
    };
  }

  // Total remaining budget
  if (mandate.amountTotal) {
    const remaining = remainingTotal(mandate)!;
    if (gt(amount, remaining)) {
      return {
        approved: false,
        reason: `Amount exceeds remaining mandate budget`,
        errorCode: 'MANDATE_BUDGET_EXHAUSTED',
        requiresApproval: false,
      };
    }
  }

  // Merchant scope
  if (spend.merchant && (mandate.merchantScope.allowed || mandate.merchantScope.blocked)) {
    const allowed = mandate.merchantScope.allowed;
    const blocked = mandate.merchantScope.blocked ?? [];
    if (blocked.includes(spend.merchant)) {
      return {
        approved: false,
        reason: `Merchant ${spend.merchant} is blocked by mandate`,
        errorCode: 'MANDATE_MERCHANT_BLOCKED',
        requiresApproval: false,
      };
    }
    if (allowed && allowed.length > 0 && !merchantMatchesAllowed(spend.merchant, allowed)) {
      return {
        approved: false,
        reason: `Merchant ${spend.merchant} not in mandate allowed list`,
        errorCode: 'MANDATE_MERCHANT_NOT_ALLOWED',
        requiresApproval: false,
      };
    }
  }

  // Rail
  if (spend.rail && !mandate.allowedRails.includes(spend.rail)) {
    return {
      approved: false,
      reason: `Rail ${spend.rail} not permitted by mandate`,
      errorCode: 'MANDATE_RAIL_NOT_ALLOWED',
      requiresApproval: false,
    };
  }

  // Chain
  if (spend.chain && mandate.allowedChains && mandate.allowedChains.length > 0 && !mandate.allowedChains.includes(spend.chain)) {
    return {
      approved: false,
      reason: `Chain ${spend.chain} not permitted by mandate`,
      errorCode: 'MANDATE_CHAIN_NOT_ALLOWED',
      requiresApproval: false,
    };
  }

  // Token
  if (spend.token && mandate.allowedTokens && mandate.allowedTokens.length > 0 && !mandate.allowedTokens.includes(spend.token)) {
    return {
      approved: false,
      reason: `Token ${spend.token} not permitted by mandate`,
      errorCode: 'MANDATE_TOKEN_NOT_ALLOWED',
      requiresApproval: false,
    };
  }

  // Approval mode
  let requiresApproval = false;
  const mode: ApprovalMode = mandate.approvalMode;
  if (mode === 'always_human') {
    requiresApproval = true;
  } else if (mode === 'threshold' && mandate.approvalThreshold) {
    if (gt(amount, mandate.approvalThreshold)) {
      requiresApproval = true;
    }
  }

  return {
    approved: true,
    reason: 'Mandate check passed',
    requiresApproval,
    mandateId: mandate.id,
  };
}
