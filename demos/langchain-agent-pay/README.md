# LangChain agent pay demo

30 seconds: a deterministic mock LLM drives a LangChain-style agent loop.
The agent receives a goal ("pay $20 to Anthropic for API credits"), calls
`sardis_check_policy` first, then `sardis_pay`. Sardis tools enforce wallet
spending limits — over-cap payments are halted before any transfer.

```python
from sardis.integrations.langchain import SardisPayTool, SardisPolicyCheckTool

tools = {
    "sardis_pay": SardisPayTool(client=client, wallet_id=wid, chain="base-sepolia"),
    "sardis_check_policy": SardisPolicyCheckTool(client=client, wallet_id=wid),
}
result = await tools["sardis_pay"]._arun(amount=20.0, merchant="Anthropic", ...)
```

## Run

```bash
make demo
```

## What's exercised

- `sardis.integrations.langchain.SardisPayTool` — `sardis_pay` LangChain tool
- `sardis.integrations.langchain.SardisPolicyCheckTool` — `sardis_check_policy`
- Mock `client.wallets` resource enforcing `limit_per_tx` policy
- Two scenarios: in-policy payment (APPROVE + ledger entry) and over-cap
  payment (BLOCKED before transfer)

No real LLM, no real Sardis API key — the agent and client are local stubs
so the full tool surface can be exercised offline.
