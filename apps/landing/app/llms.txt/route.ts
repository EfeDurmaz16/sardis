export function GET() {
  const content = `# Sardis

> The Payment OS for the Agent Economy. Non-custodial MPC wallets with natural language spending policies for AI agents.

Sardis enables AI agents to make real financial transactions safely. Define spending rules in plain English. Agents pay within guardrails. Every transaction is audited with cryptographic proof.

## Docs

- [Getting Started](https://sardis.sh/docs): Quick start guide for Sardis SDK
- [API Reference](https://sardis.sh/docs/api): Complete REST API documentation
- [Python SDK](https://sardis.sh/docs/sdk/python): pip install sardis
- [TypeScript SDK](https://sardis.sh/docs/sdk/typescript): npm install @sardis/sdk
- [MCP Server](https://sardis.sh/docs/mcp): 52 tools for Claude Desktop, Cursor
- [Spending Policies](https://sardis.sh/docs/policies): Natural language policy engine
- [Supported Chains](https://sardis.sh/docs/chains): Base, Polygon, Ethereum, Arbitrum, Optimism
- [Runtime Guardrails](https://sardis.sh/docs/runtime-guardrails): Policy Firewall documentation
- [Provider Diligence](https://sardis.sh/docs/provider-diligence): Infrastructure security

## Integrations

- [Browser Use](https://sardis.sh/docs/integrations/browser-use): pip install sardis-browser-use
- [CrewAI](https://sardis.sh/docs/integrations/crewai): pip install sardis-crewai
- [OpenAI Agents](https://sardis.sh/docs/integrations/openai): pip install sardis-openai-agents
- [Vercel AI SDK](https://sardis.sh/docs/integrations/vercel-ai): npm install @sardis/ai-sdk
- [LangChain](https://sardis.sh/docs/integrations/langchain): pip install sardis-langchain
- [Activepieces](https://sardis.sh/docs/integrations/activepieces): Workflow automation
- [n8n](https://sardis.sh/docs/integrations/n8n): npm install n8n-nodes-sardis

## Protocols

- [AP2 (Agent Payment Protocol)](https://sardis.sh/docs/protocols/ap2): Google, PayPal, Mastercard, Visa consortium standard
- [TAP (Trust Anchor Protocol)](https://sardis.sh/docs/protocols/tap): Agent identity verification
- [x402](https://sardis.sh/docs/protocols/x402): HTTP 402 Payment Required standard
- [A2A (Agent-to-Agent)](https://sardis.sh/docs/protocols/a2a): Google's agent interoperability protocol

## Pricing

- Free tier with simulation mode (no API key needed)
- 0% merchant fee on USDC stablecoin checkout
- Usage-based pricing for production
- Enterprise plans available

## Company

- Founded: 2024, Delaware C-corp (Sardis Labs, Inc.)
- Founder: Efe Baran Durmaz
- Website: https://sardis.sh
- GitHub: https://github.com/EfeDurmaz16/sardis
- X/Twitter: https://x.com/sardisHQ
- npm: @sardis/sdk, @sardis/mcp-server
- PyPI: sardis, sardis-sdk
`;

  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=86400",
    },
  });
}
