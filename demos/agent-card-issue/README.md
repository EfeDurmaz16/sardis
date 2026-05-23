# agent card issue demo

30 seconds: issue a virtual card to an AI agent, attach a spending policy
(per-tx cap + blocked MCC categories), and simulate Lithic-style ASA
authorization requests. The policy approves/declines each transaction in
real time, just like the production card auth path.

```python
from sardis.cards import CardService, CardType
from sardis.cards.providers.mock import MockProvider

service = CardService(provider=MockProvider())
card = await service.issue_card(
    wallet_id="wallet_agent_research_bot_001",
    card_type=CardType.MULTI_USE,
    limit_per_tx=Decimal("250.00"),
)
```

## Run

```bash
make demo
```

## What's exercised

- `sardis.cards.CardService` — high-level card issuance + lifecycle
- `sardis.cards.providers.mock.MockProvider` — in-memory issuer (no Lithic
  / Stripe Issuing keys required)
- Inline spending policy stand-in for `ASAHandler.policy_check`: per-tx
  amount cap + blocked MCC list
