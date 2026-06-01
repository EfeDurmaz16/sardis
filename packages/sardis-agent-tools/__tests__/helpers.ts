import type { Sardis } from 'sardis';
import type { SardisToolContext } from '../src/types.js';

/** A call recorded by the mock client. */
export interface RecordedCall {
  method: string;
  args: unknown[];
}

/**
 * A mock Sardis client that records the method + args of every routed call and
 * returns a canned `{ ok: true, method }` response. No network. Methods can be
 * overridden to throw, to exercise the `blocked`-on-error path.
 */
export function mockSardis(overrides: Record<string, (...a: unknown[]) => unknown> = {}): {
  client: Sardis;
  calls: RecordedCall[];
} {
  const calls: RecordedCall[] = [];

  const record =
    (method: string) =>
    async (...args: unknown[]): Promise<unknown> => {
      calls.push({ method, args });
      if (overrides[method]) return overrides[method]!(...args);
      return { ok: true, method };
    };

  const client = {
    pay: record('pay'),
    wallets: {
      create: record('wallets.create'),
      getBalance: record('wallets.getBalance'),
    },
    cards: {
      issue: record('cards.issue'),
      freeze: record('cards.freeze'),
    },
    policies: {
      apply: record('policies.apply'),
      check: record('policies.check'),
    },
    payments: {
      executeMandate: record('payments.executeMandate'),
    },
    ledger: {
      listEntries: record('ledger.listEntries'),
    },
  } as unknown as Sardis;

  return { client, calls };
}

export function ctxFor(
  client: Sardis,
  extra: Partial<SardisToolContext> = {},
): SardisToolContext {
  return {
    client,
    walletId: 'wal_test',
    agentId: 'agt_test',
    approvalThreshold: '50',
    ...extra,
  };
}
