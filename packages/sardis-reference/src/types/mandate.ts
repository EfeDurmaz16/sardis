/**
 * Mandate — the decision surface of `SpendingMandate.check_payment`.
 *
 * Reason codes are mirrored exactly (the `MANDATE_*` codes).
 */
import type { Money, Currency } from './money.js';
import type { Rail } from './spend.js';

export type MandateStatus =
  | 'draft'
  | 'active'
  | 'suspended'
  | 'revoked'
  | 'expired'
  | 'consumed';

export type ApprovalMode = 'auto' | 'threshold' | 'always_human';

export interface MerchantScope {
  /** Allowed merchants/domains. `*.foo.com` wildcard supported (mirrors Python `*`-prefix). */
  allowed?: string[];
  blocked?: string[];
}

export interface Mandate {
  id: string;
  status: MandateStatus;
  validFromMs?: number;
  expiresAtMs?: number;
  merchantScope: MerchantScope;
  purposeScope?: string;
  amountPerTx?: Money;
  amountTotal?: Money;
  spentTotal: Money;
  currency: Currency;
  /** Default ["card","usdc","bank"]. */
  allowedRails: Rail[];
  allowedChains?: string[];
  allowedTokens?: string[];
  approvalThreshold?: Money;
  approvalMode: ApprovalMode;
}

export interface MandateCheckResult {
  approved: boolean;
  reason: string;
  /** Mirrors the MANDATE_* error codes exactly. */
  errorCode?: string;
  requiresApproval: boolean;
  mandateId?: string;
}
