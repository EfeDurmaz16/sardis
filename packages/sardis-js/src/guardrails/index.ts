/**
 * `sardis/guardrails` — natural-language policy DSL + simulation helpers.
 *
 * Re-exports the `policies` and `kill-switch` resources, plus a small
 * builder for composing structured policies in code (alternative to the
 * natural-language path).
 */

export { PoliciesResource } from '../resources/policies.js';
export { KillSwitchResource } from '../resources/kill-switch.js';
export type {
  ParsedPolicy,
  PolicySpendingLimit,
  PolicyPreviewResponse,
  ApplyPolicyFromNLResponse,
  PolicyCheckResponse,
} from '../types.js';

export interface StructuredPolicyInput {
  /** Daily ceiling in token-decimal units (e.g. "200.00"). */
  dailyLimit?: string;
  /** Monthly ceiling. */
  monthlyLimit?: string;
  /** Per-transaction ceiling. */
  perTransactionLimit?: string;
  /** Threshold above which manual approval is required. */
  approvalThreshold?: string;
  /** Allowed merchant categories (whitelist). */
  allowCategories?: string[];
  /** Blocked merchants. */
  blockMerchants?: string[];
}

/**
 * Compose a Sardis-shaped policy object from a structured input.
 *
 * Returns the wire shape (snake_case) ready to POST to
 * `/api/v2/policies` or pass to `sardis.policies.preview()`.
 */
export function buildPolicy(input: StructuredPolicyInput): Record<string, unknown> {
  const policy: Record<string, unknown> = {};
  if (input.dailyLimit) policy['global_daily_limit'] = input.dailyLimit;
  if (input.monthlyLimit) policy['global_monthly_limit'] = input.monthlyLimit;
  if (input.perTransactionLimit) policy['per_transaction_limit'] = input.perTransactionLimit;
  if (input.approvalThreshold) policy['requires_approval_above'] = input.approvalThreshold;
  if (input.allowCategories) policy['allowed_categories'] = input.allowCategories;
  if (input.blockMerchants) policy['blocked_merchants'] = input.blockMerchants;
  return policy;
}
