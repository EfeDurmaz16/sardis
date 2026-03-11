# Sardis Documentation

**Payment OS for the Agent Economy**

Sardis is infrastructure that enables AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.

## Why Sardis?

AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.

- **Non-Custodial**: Agent wallets powered by Turnkey MPC - you control the keys
- **Policy Enforcement**: Natural language spending rules ("Max $100/day, only for API credits")
- **Multi-Chain**: Base, Polygon, Ethereum, Arbitrum, Optimism
- **Fiat Rails**: Stripe Treasury + Issuing for real-world payments
- **Framework Agnostic**: Works with OpenAI, LangChain, CrewAI, Gemini, Claude, and more
- **Compliance Built-in**: KYA verification, sanctions screening, full audit trail
- **Strict Live Controls**: Replay/idempotency proof gates, fail-closed runtime security policies, and DR evidence artifacts

## Quick Start

=== "Python"

    ```bash
    pip install sardis-sdk
    ```

    ```python
    from sardis import SardisClient

    client = SardisClient(api_key="sk_...")
    wallet = client.wallets.create(
        name="my-agent",
        chain="base",
        policy="Max $100/day"
    )

    result = client.payments.execute(
        wallet_id=wallet.id,
        to="0x...",
        amount=50,
        token="USDC",
    )
    ```

=== "TypeScript"

    ```bash
    npm install @sardis/sdk
    ```

    ```typescript
    import { SardisClient } from '@sardis/sdk';

    const client = new SardisClient({ apiKey: 'sk_...' });
    const wallet = await client.wallets.create({
      name: 'my-agent',
      chain: 'base',
      policy: 'Max $100/day',
    });

    const result = await client.payments.execute({
      walletId: wallet.id,
      to: '0x...',
      amount: 50,
      token: 'USDC',
    });
    ```

=== "CLI"

    ```bash
    pip install sardis-cli
    sardis init
    sardis wallets create --name my-agent --chain base --policy "Max \$100/day"
    sardis payments execute --wallet wallet_abc --to 0x... --amount 50 --token USDC
    ```

## Architecture

```
Agent → Sardis Policy Engine → MPC Wallet (Turnkey) → Blockchain
                                    ↓
                              Audit Ledger
```

Sardis never holds funds. Crypto stays in Turnkey MPC wallets (non-custodial), fiat flows through Stripe (their license), and KYC data lives with Veriff/Persona (their responsibility).

## Current Ops Posture (v0.9.5)

- Runtime security policy endpoints for checkout, ASA, and A2A trust lanes
- Provider readiness endpoint for Stripe/Lithic/Rain/Bridge certification tracking
- Release gates for webhook replay protection and payment idempotency
- SLO + pager alerting and DR runbook evidence automation

## Integrations

| Framework | Package | Install |
|-----------|---------|---------|
| OpenAI | `sardis-openai` | `pip install sardis-openai` |
| LangChain | `sardis-langchain` | `pip install sardis-langchain` |
| CrewAI | `sardis-crewai` | `pip install sardis-crewai` |
| Google ADK | `sardis-adk` | `pip install sardis-adk` |
| Claude | `sardis-agent-sdk` | `pip install sardis-agent-sdk` |
| Vercel AI SDK | `@sardis/ai-sdk` | `npm install @sardis/ai-sdk` |
| MCP Server | `@sardis/mcp-server` | `npm install @sardis/mcp-server` |
| OpenClaw | `sardis-openclaw` | `pip install sardis-openclaw` |

## Links

- [Website](https://sardis.sh)
- [GitHub](https://github.com/sardis-labs/sardis)
- [API Reference](https://sardis.sh/api/v2/docs)
- [Blog](https://sardis.sh/blog)
