# n8n-nodes-sardis

n8n community node for [Sardis](https://sardis.sh) — policy-controlled payments for AI agents and workflows.

## Installation

In your n8n instance, go to **Settings > Community Nodes** and install:

```
n8n-nodes-sardis
```

Or install manually via npm in your n8n data directory:

```bash
npm install n8n-nodes-sardis
```

## Credentials

Create a **Sardis API** credential with:

- **API Key** — your Sardis key (starts with `sk_`), from https://sardis.sh/dashboard
- **Base URL** — defaults to `https://api.sardis.sh` (change for self-hosted)

## Operations

### Send Payment

Executes a policy-checked on-chain stablecoin transfer.

| Field     | Description                          |
|-----------|--------------------------------------|
| Wallet ID | Sardis wallet ID                     |
| Amount    | Payment amount in USD                |
| Merchant  | Destination address or identifier    |
| Purpose   | Optional memo / reason for payment   |
| Token     | USDC, USDT, PYUSD, or EURC          |
| Chain     | Base, Ethereum, Polygon, Arbitrum, Optimism |

### Check Balance

Returns current balance and spending limits for a wallet.

| Field     | Description                          |
|-----------|--------------------------------------|
| Wallet ID | Sardis wallet ID                     |
| Token     | Token to query                       |
| Chain     | Chain to query                       |

### Check Policy

Pre-flight check — returns whether a given amount/merchant combination would be approved by the wallet's spending policy without executing a transaction.

| Field     | Description                          |
|-----------|--------------------------------------|
| Wallet ID | Sardis wallet ID                     |
| Amount    | Proposed payment amount              |
| Merchant  | Proposed recipient                   |

## Example Workflow

1. Trigger node (e.g. Schedule, Webhook, or AI Agent output)
2. **Sardis** node — operation: `Check Policy`
3. IF node — branch on `{{ $json.allowed }}`
4. **Sardis** node — operation: `Send Payment`
5. Slack / Email node — notify on completion

## Links

- Website: https://sardis.sh
- Docs: https://sardis.sh/docs
- GitHub: https://github.com/EfeDurmaz16/sardis
