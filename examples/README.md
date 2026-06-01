# Examples

Small, single-concept, runnable scripts. Each shows **one** thing against the
real `sardis` v2 API (the `Sardis` client and `sardis.integrations.*`). For
larger end-to-end scenarios, see [`../demos/`](../demos/).

All Python examples target the published `sardis` package
(`pip install sardis`). Framework examples need an extra
(`pip install "sardis[langchain]"`, etc.) — each file's docstring lists its
prerequisites.

## Credential-free (run immediately, no API key)

These exercise in-process Sardis primitives — `python examples/<file>`:

| Example | Concept |
| --- | --- |
| [`budget_allocation_demo.py`](budget_allocation_demo.py) | Budget allocation across agents |
| [`event_webhooks.py`](event_webhooks.py) | EventBus pub/sub + webhook event routing |
| [`gas_optimizer_demo.py`](gas_optimizer_demo.py) | Multi-chain gas estimation / cheapest route |

## Require a Sardis API key

Set `export SARDIS_API_KEY=sk_live_...` (the `Sardis` client talks to a Sardis
deployment). Start here:

| Example | Concept |
| --- | --- |
| [`simple_payment.py`](simple_payment.py) | One policy-checked payment via `client.pay.execute` |
| [`quickstart_5min.py`](quickstart_5min.py) | Full flow: agent → wallet → policy → check → pay |
| [`agent_to_agent.py`](agent_to_agent.py) | Two agents; one pays the other (policy-enforced) |
| [`api_demo.py`](api_demo.py) | Drive the reference API + SDK end to end |
| [`alert_integration_example.py`](alert_integration_example.py) | Real-time alerts + WebSocket alert stream |

## Framework integrations (API key + framework deps)

Each uses the real `sardis.integrations.<name>` toolkit — no hand-rolled tools:

| Example | Framework | Install |
| --- | --- | --- |
| [`langchain_sardis_agent.py`](langchain_sardis_agent.py) | LangChain | `pip install "sardis[langchain]" langchain langchain-openai` |
| [`crewai_finance_team.py`](crewai_finance_team.py) | CrewAI | `pip install "sardis[crewai]" crewai` |
| [`openai_agents_payment.py`](openai_agents_payment.py) | OpenAI Agents SDK | `pip install "sardis[openai-agents]" openai-agents` |
| [`anthropic_agent_sdk.py`](anthropic_agent_sdk.py) | Anthropic SDK (Claude) | `pip install "sardis[anthropic]" anthropic` |
| [`google_adk_agent.py`](google_adk_agent.py) | Google ADK (Gemini) | `pip install "sardis[adk]" google-adk` |
| [`vercel_ai_payment.ts`](vercel_ai_payment.ts) | Vercel AI SDK (TS) | `npm install sardis ai @ai-sdk/openai` |

## Nested projects

Self-contained multi-file examples with their own README:

- [`langchain-payment-agent/`](langchain-payment-agent/) — LangChain agent, OpenAI-functions style
- [`crewai-procurement-team/`](crewai-procurement-team/) — CrewAI procurement crew
- [`openai-assistant-with-wallet/`](openai-assistant-with-wallet/) — OpenAI Assistant + wallet
- [`vercel-ai-chatbot/`](vercel-ai-chatbot/) — Vercel AI SDK chatbot (TS)

## Notes for contributors

- Examples must import from `sardis` / `sardis.integrations.<name>` — never the
  pre-consolidation `sardis_sdk`, `sardis_langchain`, `sardis_adk`, `@sardis/sdk`
  packages (those were merged into the three published packages in May 2026).
- One concept per file; keep them short and runnable.
- If an example needs an API key, fail fast with a clear message rather than a
  silent fake.
