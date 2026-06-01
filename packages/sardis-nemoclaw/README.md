# @sardis/nemoclaw

NemoClaw governance layer for **Sardis as a TOOL**. NemoClaw secures the
*container*; Sardis governs the *spend*. This adapter governs an agent's Sardis
verbs and **binds the `sandboxId` (and optional `userId`) into every governance
commit**, so a spend is traceable to the exact sandbox that produced it.

```ts
import { Sardis } from 'sardis';
import { governedSpend, createNemoTools } from '@sardis/nemoclaw';

const client = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });
const ctx = { client, walletId: 'wal_abc', agentId: 'agt_abc', approvalThreshold: '50', sandboxId: 'sbx_42' };

const res = await governedSpend(ctx, { to: 'openai.com', amount: '12.50' });
// { status: 'executed', outcome: 'allow', commitHash: 'sardis_…' } — bound to sbx_42

const tools = createNemoTools(ctx); // all five verbs, sandbox-bound
await tools.sardis_give_wallet({ currency: 'USDC' });
```

The same action from two different sandboxes produces two different
`commitHash`es; the same action from the same sandbox is stable. The sandbox
envelope is folded into the canonical hash only — it never leaks into the money
call, which routes through the Sardis SDK with the real args.

## What it adds over the bare gate

Classification, the canonical commit, and the fail-closed gate come from
[`@sardis/agent-tools`](https://www.npmjs.com/package/@sardis/agent-tools). This
adapter adds the sandbox-bound commit and exposes `governedSpend`,
`governedToolCall`, and `createNemoTools` keyed by a `SardisNemoContext`.

## Provenance

A direct TS port of the Aspendos NemoClaw adapter, rebranded to Sardis
(`nemo_` → `sardis_`; no Aspendos/YULA/fides/agit naming or memory-layer logic
survives).

## License

MIT — see `LICENSE`.
