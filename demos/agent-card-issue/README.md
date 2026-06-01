# agent card issue demo

Issue a virtual card to an AI agent, attach a natural-language spending policy
(per-tx cap + blocked MCC categories), then inject Lithic/Stripe-style ASA
(Authorization Stream Access) requests and watch the **server's** policy engine
approve/decline each one in real time — the same path production card auth takes.

This is a public-surface demo: it talks to a hosted Sardis deployment through the
`sardis` client SDK. No local engine, no card-provider keys, no PCI flow runs in
this process.

```python
from sardis import Sardis

client = Sardis(api_key="sk_live_...")
agent = client.agents.create(name="research-bot")
wallet = client.wallets.create(agent_id=agent.id, currency="USDC")
client.policies.apply(
    agent_id=agent.id,
    natural_language="Allow up to $250 per transaction. Block gambling and pawn shops.",
)
card = client.cards.issue(wallet_id=wallet.id, card_type="multi_use")
resp = client.cards.simulate_purchase(card.card_id, amount="42.50", mcc_code="7372")
print(resp.transaction.status, resp.policy)
```

## Run

```bash
export SARDIS_API_KEY=sk_live_...
# optional: export SARDIS_API_URL=https://your-sardis-api.example.com
make demo
```

## What's exercised

- `client.agents.create` / `client.wallets.create` — agent + funding wallet
- `client.policies.apply` — natural-language spending policy (per-tx cap +
  blocked MCCs), parsed and enforced server-side
- `client.cards.issue` — virtual card issuance with on-card limits
- `client.cards.simulate_purchase` — inject an ASA authorization; the response's
  `transaction.status` + `policy` carry the server-side APPROVE/DECLINE decision
