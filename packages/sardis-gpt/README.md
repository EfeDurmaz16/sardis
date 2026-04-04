# Sardis GPT — ChatGPT Custom GPT Actions

Enable ChatGPT to make policy-controlled payments via Sardis.

## Setup

1. Go to [ChatGPT](https://chatgpt.com) > Explore GPTs > Create
2. Paste `instructions.md` as the system prompt
3. Add Actions > Import `openapi-actions.yaml`
4. Configure authentication:
   - Type: **API Key**
   - Auth Type: **Custom**
   - Header: `X-API-Key`
   - Value: Your Sardis API key (`sk_...`)

## Available Actions

| Action | Description |
|--------|-------------|
| `sendPayment` | Execute a policy-controlled payment |
| `getBalance` | Check wallet balance |
| `getWallet` | Get wallet info and spending limits |

## Links

- [Sardis Docs](https://sardis.sh/docs)
- [API Reference](https://sardis.sh/docs/api)
