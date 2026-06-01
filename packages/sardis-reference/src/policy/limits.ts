/**
 * Time-window limit logic — mirrors `TimeWindowLimit` (reset/can_spend).
 *
 * Pure: the rolling reset is computed from an injectable `now` (epoch ms) and
 * the caller-supplied `windowStartMs`, never a global clock.
 */
import type { TimeWindowLimit, WindowType } from '../types/policy.js';
import type { Money } from '../types/money.js';
import { add, gt } from '../types/money.js';

const DAY_MS = 24 * 60 * 60 * 1000;

function windowDurationMs(windowType: WindowType): number {
  switch (windowType) {
    case 'daily':
      return DAY_MS;
    case 'weekly':
      return 7 * DAY_MS;
    case 'monthly':
      return 30 * DAY_MS; // mirrors Python timedelta(days=30)
  }
}

/** The effective spent amount in the window at `now` (0 if the window expired). */
export function effectiveSpent(win: TimeWindowLimit, now: number): Money {
  const duration = windowDurationMs(win.windowType);
  if (now >= win.windowStartMs + duration) {
    return { minor: 0n, currency: win.currentSpent.currency };
  }
  return win.currentSpent;
}

/**
 * Whether `totalCost` can be spent in this window. Mirrors
 * `TimeWindowLimit.can_spend`: rolling reset, then
 * `current_spent + amount > limit` → deny.
 */
export function canSpend(
  win: TimeWindowLimit,
  totalCost: Money,
  now: number,
): { ok: boolean; reason: string } {
  const spent = effectiveSpent(win, now);
  if (gt(add(spent, totalCost), win.limit)) {
    return { ok: false, reason: 'time_window_limit' };
  }
  return { ok: true, reason: 'OK' };
}
