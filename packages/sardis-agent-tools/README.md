# @sardis/agent-tools

**Sardis as a TOOL for AI agents.** Give an agent five verbs — give-wallet,
spend, issue-card, set-budget, pay-invoice — that route to the
[Sardis SDK](https://www.npmjs.com/package/sardis), wrapped in a fail-closed
governance gate so an agent can earn a wallet, move money, and get a card
without ever holding a key or auto-firing an irreversible high-value spend.

```ts
import { Sardis } from 'sardis';
import { runGoverned } from '@sardis/agent-tools';

const client = new Sardis({ apiKey: process.env.SARDIS_API_KEY! });
const ctx = { client, walletId: 'wal_abc', agentId: 'agt_abc', approvalThreshold: '50' };

const res = await runGoverned('sardis_spend', { to: 'openai.com', amount: '12.50' }, ctx);
// { status: 'executed', outcome: 'allow', commitHash: 'sardis_…', result: { … } }

const big = await runGoverned('sardis_spend', { to: 'vendor', amount: '5000' }, ctx);
// { status: 'awaiting_approval', outcome: 'requires_approval', commitHash: 'sardis_…' }
// — the money path is NEVER touched until approved.
```

## The verbs

| Verb | Routes to (`sardis`) | Class |
|------|----------------------|-------|
| `sardis_give_wallet` | `wallets.create({ agent_id, … })` | undoable |
| `sardis_spend` | `pay({ from, to, amount, … })` | compensatable / approval_only* |
| `sardis_issue_card` | `cards.issue({ wallet_id, … })` | compensatable |
| `sardis_set_budget` | `policies.apply(policy, agentId)` | undoable |
| `sardis_pay_invoice` | `payments.executeMandate(mandate)` or `pay(…)` | compensatable / approval_only* |
| `sardis_check_balance` | `wallets.getBalance(walletId, chain, token)` | undoable (read) |
| `sardis_check_policy` | `policies.check({ agent_id, amount, … })` | undoable (read) |
| `sardis_list_transactions` | `ledger.listEntries({ wallet_id, limit })` | undoable (read) |
| `sardis_freeze_card` | `cards.freeze(cardId)` | undoable (compensates issue-card) |

\* at/above `approvalThreshold` (default `"50"`), `spend` and `pay_invoice`
classify `approval_only`: the gate returns `awaiting_approval` and does **not**
call the SDK.

The adapters **never re-implement money movement, signing, or the backend
policy decision** — they delegate to the SDK, which talks to the private
backend. The local classification mirrors the
[`@sardis/reference`](https://www.npmjs.com/package/@sardis/reference) policy
simulator's `allow | requires_approval | deny` outcome contract, so an agent
sees the same authority view everywhere.

## Governance gate

`governedToolCall` (and the registry-resolved `runGoverned`):

1. **classify** the action — unknown verbs **fail closed** to `irreversible_blocked`;
2. `irreversible_blocked` → `blocked` / `deny`, no execution;
3. compute a deterministic `sardis_<sha256[:40]>` commit over the canonical action;
4. `approval_only` → `awaiting_approval` / `requires_approval`, no execution;
5. otherwise execute and return `executed` / `allow` (or `blocked` / `deny` on error).

## Framework adapters

Each reshapes the same verbs; the framework is an **optional peer dep**, lazily
imported only by the wrapping helper.

```ts
import { createSardisLangChainTools } from '@sardis/agent-tools/langchain';
import { createVercelAiTools }        from '@sardis/agent-tools/vercel-ai';
import { createMcpTools }             from '@sardis/agent-tools/mcp';

const lcTools  = createSardisLangChainTools(ctx); // StructuredTool[] (governed JSON results)
const aiTools  = createVercelAiTools(ctx);         // { [name]: { description, parameters, execute } }
const { definitions, handlers } = createMcpTools(ctx); // sardis-mcp-server shape
```

## License

MIT — see `LICENSE`.
