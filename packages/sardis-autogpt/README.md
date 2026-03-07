# sardis-autogpt

Sardis payment blocks for [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) (180k+ stars). Gives AutoGPT agents policy-controlled access to real financial transactions via non-custodial MPC wallets.

## Install

```bash
pip install sardis-autogpt
```

## Quickstart

```python
from sardis_autogpt import SardisPayBlock, SardisPayBlockInput

# Execute a payment (uses SARDIS_API_KEY + SARDIS_WALLET_ID env vars)
input_data = SardisPayBlockInput(
    amount=25.0,
    merchant="acme-software",
    purpose="Monthly SaaS subscription",
    token="USDC",
)

for result in SardisPayBlock.run(input_data):
    print(result.status)   # APPROVED or BLOCKED
    print(result.tx_id)    # on-chain transaction ID
    print(result.message)
```

## Blocks

### `SardisPayBlock`
Execute a policy-controlled stablecoin payment from a Sardis wallet.

| Input | Type | Description |
|-------|------|-------------|
| `amount` | float | Payment amount in USD |
| `merchant` | str | Merchant or recipient identifier |
| `purpose` | str | Reason for payment (default: "Payment") |
| `token` | str | Token to use (default: "USDC") |
| `api_key` | str | Sardis API key (or `SARDIS_API_KEY` env var) |
| `wallet_id` | str | Wallet ID (or `SARDIS_WALLET_ID` env var) |

| Output | Type | Description |
|--------|------|-------------|
| `status` | str | `APPROVED`, `BLOCKED`, or `ERROR` |
| `tx_id` | str | On-chain transaction ID |
| `message` | str | Human-readable status |
| `amount` | float | Actual amount processed |

---

### `SardisBalanceBlock`
Check wallet balance and remaining spending limits.

| Output | Type | Description |
|--------|------|-------------|
| `balance` | float | Current token balance |
| `remaining` | float | Remaining spending limit for period |
| `token` | str | Token type checked |

---

### `SardisPolicyCheckBlock`
Dry-run policy check before executing a payment. Use this to guard against blocked transactions.

| Output | Type | Description |
|--------|------|-------------|
| `allowed` | bool | Whether the payment would be approved |
| `reason` | str | Explanation |

## Environment Variables

```bash
SARDIS_API_KEY=sk_...          # Your Sardis API key
SARDIS_WALLET_ID=wallet_...    # Agent wallet ID
```

## AutoGPT Integration

Register all blocks via the `BLOCKS` registry:

```python
from sardis_autogpt import BLOCKS

# BLOCKS = [SardisPayBlock, SardisBalanceBlock, SardisPolicyCheckBlock]
for block_cls in BLOCKS:
    autogpt_registry.register(block_cls)
```

## Links

- [Sardis Docs](https://sardis.sh/docs)
- [AutoGPT Blocks Guide](https://docs.agpt.co/forge/blocks)
- [GitHub](https://github.com/sardis-sh/sardis)
