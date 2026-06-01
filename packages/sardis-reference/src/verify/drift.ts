/**
 * Goal-drift detection — verbatim port of `MandateVerifier._compute_drift`,
 * `_SCOPE_DOMAINS`, and `_HIGH_RISK_DOMAINS`.
 *
 * Pure: drift is a deterministic function of (intent, payment).
 */
import type { IntentMandate, PaymentMandate } from '../types/ap2.js';

export const SCOPE_DOMAINS: Record<string, string[]> = {
  cloud: ['aws.amazon.com', 'cloud.google.com', 'azure.microsoft.com', 'digitalocean.com', 'vercel.com', 'netlify.com', 'heroku.com'],
  compute: ['aws.amazon.com', 'cloud.google.com', 'azure.microsoft.com', 'digitalocean.com', 'linode.com', 'vultr.com'],
  ai: ['openai.com', 'anthropic.com', 'cohere.com', 'replicate.com', 'huggingface.co', 'together.ai'],
  saas: ['slack.com', 'notion.so', 'github.com', 'atlassian.com', 'figma.com', 'linear.app'],
  data: ['snowflake.com', 'databricks.com', 'mongodb.com', 'elastic.co', 'supabase.com'],
  hosting: ['vercel.com', 'netlify.com', 'heroku.com', 'fly.io', 'railway.app', 'render.com'],
};

export const HIGH_RISK_DOMAINS: string[] = [
  'bet365.com',
  'draftkings.com',
  'fanduel.com',
  'pokerstars.com',
  'casino.com',
  '888casino.com',
  'bovada.lv',
];

export interface DriftResult {
  driftScore: number;
  driftReasons: string[];
}

/** Mirrors `_compute_drift`. driftScore ≥ 1.0 ⇒ goal_drift_scope_mismatch. */
export function computeDrift(intent: IntentMandate, payment: PaymentMandate): DriftResult {
  let driftScore = 0.0;
  const driftReasons: string[] = [];

  // Amount deviation.
  const requested = intent.requestedAmount;
  if (requested != null && requested > 0) {
    const deviation = Math.abs(payment.amountMinor - requested) / requested;
    if (deviation > 0.1) {
      const amountDrift = Math.min(deviation, 1.0);
      driftScore = Math.max(driftScore, amountDrift * 0.5);
      driftReasons.push(`amount_deviation:${deviation.toFixed(2)}`);
    }
  }

  // Scope drift.
  if (intent.scope && intent.scope.length > 0 && payment.merchantDomain) {
    const merchantDomain = payment.merchantDomain.toLowerCase();
    let scopeMatched = false;
    for (const scopeName of intent.scope) {
      const scopeLower = scopeName.toLowerCase();
      const knownDomains = SCOPE_DOMAINS[scopeLower] ?? [];
      if (knownDomains.some((d) => merchantDomain.includes(d))) {
        scopeMatched = true;
        break;
      }
      if (merchantDomain.includes(scopeLower)) {
        scopeMatched = true;
        break;
      }
    }
    if (!scopeMatched) {
      driftScore = Math.max(driftScore, 0.8);
      driftReasons.push(`scope_mismatch:intent=${JSON.stringify(intent.scope)},merchant=${merchantDomain}`);
    }
    if (HIGH_RISK_DOMAINS.some((d) => merchantDomain.includes(d))) {
      driftScore = 1.0;
      driftReasons.push(`high_risk_domain:${merchantDomain}`);
    }
  }

  return { driftScore, driftReasons };
}
