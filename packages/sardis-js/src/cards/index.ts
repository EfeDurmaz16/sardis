/**
 * `sardis/cards` — virtual card helpers + types.
 *
 * Thin façade over the `cards` resource of the Sardis client. Use the
 * full client (`sardis.cards.*`) for raw API access; import from this
 * subpath when you only need card types or the domain helpers below.
 */

export { CardsResource } from '../resources/cards.js';
export type {
  Card,
  CardStatus,
  CardTransaction,
  IssueCardInput,
  UpdateCardLimitsInput,
  SimulateCardPurchaseInput,
  SimulateCardPurchaseResponse,
} from '../types.js';

/**
 * Format a Lithic-style card status into a human-readable label.
 */
export function formatCardStatus(status: string): string {
  switch (status) {
    case 'active':
      return 'Active';
    case 'frozen':
      return 'Frozen';
    case 'cancelled':
      return 'Cancelled';
    case 'pending':
      return 'Pending activation';
    default:
      return status;
  }
}

/** Convert a token-decimal amount string to a Lithic-style minor-unit integer. */
export function amountToMinorUnits(amount: string, decimals = 2): number {
  const num = Number.parseFloat(amount);
  if (Number.isNaN(num)) throw new Error(`Invalid amount: ${amount}`);
  return Math.round(num * 10 ** decimals);
}
