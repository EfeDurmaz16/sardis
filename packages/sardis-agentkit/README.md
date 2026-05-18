# sardis-agentkit

Status: experimental

Coinbase AgentKit integration layer for exposing Sardis payment-authority actions to AgentKit-compatible agents.

## Why This Exists

AgentKit can give agents wallet and on-chain capabilities. Sardis should sit above those capabilities as the authority layer: mandate, policy, approval, idempotency, and evidence before an action can spend or sign.

## Install

```bash
pip install sardis-agentkit
```

For local development from this monorepo:

```bash
uv run pytest packages/sardis-agentkit/tests -q
```

## Security Notes

This package must not let AgentKit tools call wallet or payment operations directly without a Sardis authority check. Any live-money example must clearly separate sandbox credentials from production credentials.

## Contribution Notes

Before promoting this package from experimental to supported:

- refresh it against current Coinbase AgentKit docs
- add smoke tests for provider registration and action execution
- document the exact public tool/action names
- add examples that run without production credentials
