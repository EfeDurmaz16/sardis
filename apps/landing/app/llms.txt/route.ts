export function GET() {
  const content = `# Sardis

> Payment OS for the Agent Economy

## What is Sardis?

Sardis is infrastructure that enables AI agents to make real financial transactions safely. It provides non-custodial MPC wallets with natural language spending policies, compliance guardrails, and cryptographic audit trails.

## Key Features

- Natural language spending policies (e.g. "max $100/tx, only approved merchants")
- Non-custodial MPC wallets via Turnkey
- Multi-chain stablecoin settlement (Base, Tempo, Polygon, Arbitrum, Optimism)
- KYC/AML compliance (Persona, Elliptic)
- AP2 (Agent Payment Protocol) verification
- Python and TypeScript SDKs
- MCP server for Claude, Cursor, Windsurf
- Framework integrations: CrewAI, LangChain, Vercel AI SDK, AutoGPT, Activepieces

## Links

- Website: https://sardis.sh
- Dashboard: https://app.sardis.sh
- Documentation: https://docs.sardis.sh
- API: https://api.sardis.sh/api/v2/docs

## Quick Start

\`\`\`python
pip install sardis

from sardis import Sardis
client = Sardis(api_key="sk_...")
agent = client.agents.create(name="My Agent", chain="base")
\`\`\`

## Pricing

- Free: $0/mo — Sandbox, 1 agent
- Dev: $49/mo — Testnet, 2 agents, 100 tx/mo
- Starter: $199/mo — Production, 25 agents, unlimited tx
- Growth: $499/mo — KYB, PEP screening, 100 agents
- Enterprise: Custom — White-glove, unlimited
`;

  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
