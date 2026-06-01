import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { verifyChainStructure } from '../src/verify/ap2.js';
import { computeDrift } from '../src/verify/drift.js';
import type { MandateBundle } from '../src/types/ap2.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface Ap2Vectors {
  chains: Array<{ name: string; chain: MandateBundle; now: number; expected: { accepted: boolean; reason: string | null } }>;
  drift: Array<{
    name: string;
    intentAmount: number;
    scope: string[];
    payAmount: number;
    merchant: string;
    expected: { score: number; reasons: string[] };
  }>;
}

const vec: Ap2Vectors = JSON.parse(readFileSync(join(__dirname, 'vectors', 'ap2-chains.json'), 'utf8'));

describe('verifyChainStructure — AP2 chain (vs Python verify_chain structural path)', () => {
  for (const c of vec.chains) {
    it(`${c.name} → accepted=${c.expected.accepted} reason=${c.expected.reason ?? '(none)'}`, () => {
      const res = verifyChainStructure(c.chain, { now: c.now });
      expect(res.accepted).toBe(c.expected.accepted);
      expect(res.reason ?? null).toBe(c.expected.reason);
    });
  }
});

describe('computeDrift — authoritative scores from Python _compute_drift', () => {
  for (const d of vec.drift) {
    it(`${d.name} → score ${d.expected.score}`, () => {
      const res = computeDrift(
        { mandateId: 'i', mandateType: 'intent', subject: 's', purpose: 'intent', expiresAt: 0, scope: d.scope, requestedAmount: d.intentAmount },
        { mandateId: 'p', mandateType: 'payment', subject: 's', purpose: 'checkout', expiresAt: 0, amountMinor: d.payAmount, merchantDomain: d.merchant },
      );
      // The decision-relevant drift SCORE must match Python exactly.
      expect(res.driftScore).toBeCloseTo(d.expected.score, 10);
      // Reason count must match (string formatting of the scope list differs by
      // language — Python repr vs JSON — but the set of reasons is identical).
      expect(res.driftReasons.length).toBe(d.expected.reasons.length);
    });
  }
});
