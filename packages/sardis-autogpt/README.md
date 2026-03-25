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
    amount="25.00",           # Always use str for money (never float)
    merchant="acme-software",
    purpose="Monthly SaaS subscription",
    token="USDC",
    chain="base",
)

for result in SardisPayBlock.run(input_data):
    print(result.status)   # APPROVED, BLOCKED, PENDING, FAILED, or ERROR
    print(result.tx_id)    # on-chain transaction ID
    print(result.message)
```

## Blocks

### `SardisPayBlock`
Execute a policy-controlled stablecoin payment from a Sardis wallet.

| Input | Type | Description |
|-------|------|-------------|
| `amount` | str | Payment amount as decimal string (e.g. `"25.00"`) |
| `merchant` | str | Merchant or recipient identifier |
| `destination` | str | On-chain hex address `0x...` (optional) |
| `purpose` | str | Reason for payment (default: `"Payment"`) |
| `token` | Literal | `"USDC"`, `"USDT"`, `"EURC"`, or `"PYUSD"` |
| `chain` | Literal | `"base"`, `"ethereum"`, `"polygon"`, `"arbitrum"`, `"optimism"`, `"tempo"` |
| `api_key` | str | Sardis API key (or `SARDIS_API_KEY` env var) |
| `wallet_id` | str | Wallet ID `wal_...` (or `SARDIS_WALLET_ID` env var) |

| Output | Type | Description |
|--------|------|-------------|
| `status` | str | `APPROVED`, `BLOCKED`, `PENDING`, `FAILED`, or `ERROR` |
| `tx_id` | str | On-chain transaction ID |
| `message` | str | Human-readable status |
| `amount` | str | Actual amount processed (decimal string) |

---

### `SardisBalanceBlock`
Check wallet balance and remaining spending limits. Category: `DATA`.

| Output | Type | Description |
|--------|------|-------------|
| `balance` | str | Current token balance (decimal string) |
| `remaining` | str | Remaining spending limit for period (decimal string) |
| `token` | str | Token type checked |

---

### `SardisPolicyCheckBlock`
Dry-run policy check before executing a payment. Category: `DATA`.

| Output | Type | Description |
|--------|------|-------------|
| `allowed` | bool | Whether the payment would be approved |
| `reason` | str | Explanation |

## Input Validation

All inputs are validated at the Pydantic schema level:

- **`wallet_id`**: Must match `wal_<alphanumeric>` (regex: `^wal_[a-zA-Z0-9]+$`)
- **`destination`**: Must be a valid hex address (regex: `^0x[a-fA-F0-9]{40}$`)
- **`amount`**: Must be a positive decimal string with at most 6 decimal places
- **`token`**: Must be one of `USDC`, `USDT`, `EURC`, `PYUSD`
- **`chain`**: Must be one of `base`, `ethereum`, `polygon`, `arbitrum`, `optimism`, `tempo`

## Environment Variables

```bash
SARDIS_API_KEY=sk_...          # Your Sardis API key
SARDIS_WALLET_ID=wal_...       # Agent wallet ID
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
