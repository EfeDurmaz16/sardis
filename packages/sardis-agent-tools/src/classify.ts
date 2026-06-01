/**
 * Default Sardis action classifier.
 *
 * Decides the reversibility class for each verb BEFORE money is requested. This
 * is the client-side gate: it is NOT the backend's policy decision (that lives
 * behind the SDK / private backend and is mirrored, money-free, in
 * `@sardis/reference`'s policy simulator). It is the cheap, local guard that
 * keeps an agent from auto-firing an irreversible high-value spend.
 *
 *   give_wallet / set_budget          -> undoable
 *   check_*  / list_*                 -> undoable (read-only)
 *   freeze_card                       -> undoable (it IS a compensating action)
 *   issue_card                        -> compensatable (freeze undoes it)
 *   spend / pay_invoice  (< threshold) -> compensatable
 *   spend / pay_invoice  (>= threshold)-> approval_only
 *   unknown verb                      -> irreversible_blocked (fail-closed)
 */
import type { ReversibilityClass, SardisToolContext } from './types.js';
import { compareDecimalStrings, extractAmount } from './amount.js';

const DEFAULT_THRESHOLD = '50';

/** The set of verbs this classifier knows. Unknown verbs fail closed. */
export const KNOWN_VERBS = new Set([
  'sardis_give_wallet',
  'sardis_spend',
  'sardis_issue_card',
  'sardis_set_budget',
  'sardis_pay_invoice',
  'sardis_check_balance',
  'sardis_check_policy',
  'sardis_list_transactions',
  'sardis_freeze_card',
]);

export function classifyAction(
  toolName: string,
  args: unknown,
  ctx: SardisToolContext,
): ReversibilityClass {
  switch (toolName) {
    case 'sardis_give_wallet':
    case 'sardis_set_budget':
      return 'undoable';

    case 'sardis_check_balance':
    case 'sardis_check_policy':
    case 'sardis_list_transactions':
    case 'sardis_freeze_card':
      return 'undoable';

    case 'sardis_issue_card':
      return 'compensatable';

    case 'sardis_spend':
    case 'sardis_pay_invoice': {
      const threshold = ctx.approvalThreshold ?? DEFAULT_THRESHOLD;
      const amount = extractAmount(args);
      // No parseable amount -> be conservative and require approval.
      if (amount == null) return 'approval_only';
      // amount >= threshold -> approval_only ; else compensatable.
      return compareDecimalStrings(amount, threshold) >= 0 ? 'approval_only' : 'compensatable';
    }

    default:
      // Fail-closed for any verb we do not recognize.
      return 'irreversible_blocked';
  }
}
