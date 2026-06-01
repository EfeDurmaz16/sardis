# @sardis/hermes

Hermes governance-middleware adapter for **Sardis as a TOOL**. Wrap any agent
tool execution so it is **classified and hash-committed before money is
requested**, with an optional approval hook — and get the five Sardis verbs
pre-wrapped.

```ts
import { Sardis } from 'sardis';
import { createGovernanceMiddleware } from '@sardis/hermes';

const client = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });

const mw = createGovernanceMiddleware({
  context: { client, walletId: 'wal_abc', agentId: 'agt_abc', approvalThreshold: '50' },
  onBlocked: (tool, r) => console.warn('blocked', tool, r.reversibilityClass),
  onApprovalNeeded: async (tool, r) => {
    // ask a human / second factor; return true to let it execute.
    return await askForApproval(tool, r.commitHash);
  },
});

const tools = mw.tools();
await tools.sardis_spend({ to: 'openai.com', amount: '12.50' });
// { status: 'executed', outcome: 'allow', commitHash: 'sardis_…' }

// Wrap an arbitrary execute fn too:
const governed = mw.wrap('sardis_spend', (args, ctx) => ctx.client.pay({ from: ctx.walletId!, ...args }));
```

## What it adds over the bare gate

Classification, the canonical `sardis_<hash>` commit, and the fail-closed gate
all come from [`@sardis/agent-tools`](https://www.npmjs.com/package/@sardis/agent-tools).
Hermes adds:

- **`wrap(name, executeFn)`** — a decorator that returns a governed fn;
- **`onBlocked`** — fired when an action fails closed;
- **`onApprovalNeeded`** — the one behavioral difference from the bare gate: if
  it resolves `true`, an `approval_only` action executes anyway (a human or
  second factor approved); the record still carries the true `approval_only`
  reversibility class.

The adapter never re-implements money movement — it delegates to the Sardis SDK
via the wrapped execute functions.

## Provenance

A TS re-implementation of the Aspendos Hermes `GovernanceMiddleware.wrap`
pattern (the Python original was studied, not copied; no Aspendos/YULA/fides/agit
naming or memory-layer logic survives).

## License

MIT — see `LICENSE`.
