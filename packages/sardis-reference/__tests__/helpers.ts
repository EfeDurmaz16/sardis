/** Test helpers: deserialize golden-vector JSON (minor as string) into TS types. */
import type { Money } from '../src/types/money.js';
import type { SpendingPolicy, TimeWindowLimit, MerchantRule } from '../src/types/policy.js';
import type { SpendObject } from '../src/types/spend.js';

interface MoneyJson {
  minor: string;
  currency: string;
}

export function money(j: MoneyJson | undefined): Money | undefined {
  if (!j) return undefined;
  return { minor: BigInt(j.minor), currency: j.currency };
}

function reqMoney(j: MoneyJson): Money {
  return { minor: BigInt(j.minor), currency: j.currency };
}

function window(j: Record<string, unknown> | undefined): TimeWindowLimit | undefined {
  if (!j) return undefined;
  return {
    windowType: j.windowType as TimeWindowLimit['windowType'],
    limit: reqMoney(j.limit as MoneyJson),
    currentSpent: reqMoney(j.currentSpent as MoneyJson),
    windowStartMs: j.windowStartMs as number,
  };
}

function merchantRule(j: Record<string, unknown>): MerchantRule {
  return {
    ruleId: j.ruleId as string,
    ruleType: j.ruleType as MerchantRule['ruleType'],
    merchantId: j.merchantId as string | undefined,
    category: j.category as string | undefined,
    maxPerTx: money(j.maxPerTx as MoneyJson | undefined),
    dailyLimit: money(j.dailyLimit as MoneyJson | undefined),
    expiresAtMs: j.expiresAtMs as number | undefined,
  };
}

export function deserializePolicy(j: Record<string, unknown>): SpendingPolicy {
  return {
    policyId: j.policyId as string,
    agentId: j.agentId as string,
    trustLevel: j.trustLevel as SpendingPolicy['trustLevel'],
    limitPerTx: reqMoney(j.limitPerTx as MoneyJson),
    limitTotal: reqMoney(j.limitTotal as MoneyJson),
    spentTotal: reqMoney(j.spentTotal as MoneyJson),
    daily: window(j.daily as Record<string, unknown> | undefined),
    weekly: window(j.weekly as Record<string, unknown> | undefined),
    monthly: window(j.monthly as Record<string, unknown> | undefined),
    merchantRules: ((j.merchantRules as Record<string, unknown>[]) ?? []).map(merchantRule),
    allowedScopes: (j.allowedScopes as SpendingPolicy['allowedScopes']) ?? ['all'],
    blockedMerchantCategories: (j.blockedMerchantCategories as string[]) ?? [],
    allowedChains: (j.allowedChains as string[]) ?? [],
    allowedTokens: (j.allowedTokens as string[]) ?? [],
    allowedDestinations: (j.allowedDestinations as string[]) ?? [],
    blockedDestinations: (j.blockedDestinations as string[]) ?? [],
    approvalThreshold: money(j.approvalThreshold as MoneyJson | undefined),
    maxDriftScore: j.maxDriftScore as number | undefined,
  };
}

export function deserializeSpend(j: Record<string, unknown>): SpendObject {
  return {
    amount: reqMoney(j.amount as MoneyJson),
    fee: money(j.fee as MoneyJson | undefined),
    merchantId: j.merchantId as string | undefined,
    merchantCategory: j.merchantCategory as string | undefined,
    mccCode: j.mccCode as string | undefined,
    scope: j.scope as SpendObject['scope'],
    rail: j.rail as SpendObject['rail'],
    chain: j.chain as string | undefined,
    token: j.token as string | undefined,
    destination: j.destination as string | undefined,
    driftScore: j.driftScore as number | undefined,
  };
}
