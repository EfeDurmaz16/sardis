import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { checkMandate, type MandateSpend } from '../src/policy/mandate-check.js';
import { money } from './helpers.js';
import type { Mandate, MerchantScope } from '../src/types/mandate.js';
import type { Rail } from '../src/types/spend.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface MandateVector {
  name: string;
  mandate: Record<string, unknown>;
  spend: Record<string, unknown>;
  now: number;
  expected: { approved: boolean; errorCode: string | null; requiresApproval: boolean };
}

const vectors: MandateVector[] = JSON.parse(
  readFileSync(join(__dirname, 'vectors', 'mandate-checks.json'), 'utf8'),
);

function deserializeMandate(j: Record<string, unknown>): Mandate {
  return {
    id: j.id as string,
    status: j.status as Mandate['status'],
    validFromMs: j.validFromMs as number | undefined,
    expiresAtMs: j.expiresAtMs as number | undefined,
    merchantScope: (j.merchantScope as MerchantScope) ?? {},
    purposeScope: j.purposeScope as string | undefined,
    amountPerTx: money(j.amountPerTx as never),
    amountTotal: money(j.amountTotal as never),
    spentTotal: money(j.spentTotal as never)!,
    currency: j.currency as string,
    allowedRails: (j.allowedRails as Rail[]) ?? ['card', 'usdc', 'bank'],
    allowedChains: j.allowedChains as string[] | undefined,
    allowedTokens: j.allowedTokens as string[] | undefined,
    approvalThreshold: money(j.approvalThreshold as never),
    approvalMode: j.approvalMode as Mandate['approvalMode'],
  };
}

function deserializeSpend(j: Record<string, unknown>): MandateSpend {
  return {
    amount: money(j.amount as never)!,
    merchant: j.merchant as string | undefined,
    rail: j.rail as Rail | undefined,
    chain: j.chain as string | undefined,
    token: j.token as string | undefined,
    purpose: j.purpose as string | undefined,
  };
}

describe('checkMandate — golden vectors (vs Python SpendingMandate.check_payment)', () => {
  for (const v of vectors) {
    it(`${v.name} → approved=${v.expected.approved} code=${v.expected.errorCode}`, () => {
      const mandate = deserializeMandate(v.mandate);
      const spend = deserializeSpend(v.spend);
      const res = checkMandate(mandate, spend, { now: v.now });
      expect(res.approved).toBe(v.expected.approved);
      expect(res.errorCode ?? null).toBe(v.expected.errorCode);
      expect(res.requiresApproval).toBe(v.expected.requiresApproval);
    });
  }

  it('covers all MANDATE_* error codes', () => {
    const codes = new Set(vectors.map((v) => v.expected.errorCode).filter(Boolean));
    for (const expected of [
      'MANDATE_NOT_ACTIVE',
      'MANDATE_AMOUNT_EXCEEDED',
      'MANDATE_BUDGET_EXHAUSTED',
      'MANDATE_MERCHANT_BLOCKED',
      'MANDATE_MERCHANT_NOT_ALLOWED',
      'MANDATE_RAIL_NOT_ALLOWED',
      'MANDATE_CHAIN_NOT_ALLOWED',
      'MANDATE_TOKEN_NOT_ALLOWED',
    ]) {
      expect(codes.has(expected)).toBe(true);
    }
  });
});
