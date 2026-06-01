/**
 * verifyChainStructure — AP2 Intent → Cart → Payment chain verification, mirror
 * of `MandateVerifier.verify_chain` for the STRUCTURAL + SEMANTIC checks.
 *
 * Deliberately omits the server-owned layers (replay cache, rate limiter,
 * per-mandate signature verification, identity-registry binding) — those depend
 * on live state and a key registry the reference package never touches. Every
 * other check is reproduced in the exact same order with the exact same reason
 * codes, so a structurally-valid chain here is structurally valid server-side.
 *
 * For callers that own a public-key resolver, `verifyChain(bundle, resolveKey)`
 * is left as a documented extension point (signature verification is delegated
 * to a pure, caller-supplied resolver) — not implemented here to avoid pulling
 * in an identity registry.
 */
import type { MandateBundle, MandateChainVerification, IntentMandate, CartMandate, PaymentMandate } from '../types/ap2.js';
import { computeDrift } from './drift.js';
import { sha256Hex } from '../crypto/hmac.js';

function deny(reason: string, driftScore = 0.0, driftReasons?: string[]): MandateChainVerification {
  return { accepted: false, reason, driftScore, driftReasons };
}

/** Mirrors `is_expired()` at a given `now` (epoch seconds). */
function isExpired(expiresAt: number, now: number): boolean {
  return now >= expiresAt;
}

export function verifyChainStructure(
  bundle: MandateBundle,
  opts: { now?: number } = {},
): MandateChainVerification {
  const now = opts.now ?? 0;
  const intent: IntentMandate = bundle.intent;
  const cart: CartMandate = bundle.cart;
  const payment: PaymentMandate = bundle.payment;

  // Type/purpose per stage.
  if (intent.mandateType !== 'intent' || intent.purpose !== 'intent') {
    return deny('intent_invalid_type');
  }
  if (cart.mandateType !== 'cart' || cart.purpose !== 'cart') {
    return deny('cart_invalid_type');
  }
  if (payment.mandateType !== 'payment' || payment.purpose !== 'checkout') {
    return deny('payment_invalid_type');
  }

  // AI agent presence + modality.
  if (payment.aiAgentPresence !== true) {
    return deny('payment_agent_presence_required');
  }
  if (
    payment.transactionModality !== 'human_present' &&
    payment.transactionModality !== 'human_not_present'
  ) {
    return deny('payment_invalid_modality');
  }

  // Expiry of each mandate.
  for (const m of [intent, cart, payment]) {
    if (isExpired(m.expiresAt, now)) {
      return deny('mandate_expired');
    }
  }

  // Subject match across the chain.
  if (new Set([intent.subject, cart.subject, payment.subject]).size !== 1) {
    return deny('subject_mismatch');
  }

  // Merchant domain presence + cart↔payment match.
  if (!payment.merchantDomain) {
    return deny('payment_missing_merchant_domain');
  }
  if (cart.merchantDomain !== payment.merchantDomain) {
    return deny('merchant_domain_mismatch');
  }

  // Payment must not exceed cart total (subtotal + taxes).
  const cartTotal = cart.subtotalMinor + cart.taxesMinor;
  if (payment.amountMinor > cartTotal) {
    return deny('payment_exceeds_cart_total');
  }

  // Payment must not exceed intent's requested amount (if bounded).
  if (intent.requestedAmount != null && payment.amountMinor > intent.requestedAmount) {
    return deny('payment_exceeds_intent_amount');
  }

  // Goal drift.
  const drift = computeDrift(intent, payment);
  if (drift.driftScore >= 1.0) {
    return deny('goal_drift_scope_mismatch', drift.driftScore, drift.driftReasons);
  }

  // Origin binding: action_description_hash == sha256(natural_language_description).
  if (intent.naturalLanguageDescription && intent.actionDescriptionHash) {
    const expected = sha256Hex(intent.naturalLanguageDescription);
    if (intent.actionDescriptionHash !== expected) {
      return deny('action_description_hash_mismatch', drift.driftScore, drift.driftReasons.length ? drift.driftReasons : undefined);
    }
  }

  return {
    accepted: true,
    driftScore: drift.driftScore,
    driftReasons: drift.driftReasons.length ? drift.driftReasons : undefined,
  };
}
