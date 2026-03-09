# PR: Add Sardis payment blocks

## Target Repo
`Significant-Gravitas/AutoGPT`

## Branch
`feat/add-sardis-payment-blocks`

## Files
```
autogpt_platform/backend/backend/blocks/sardis/
  __init__.py
  _api.py
  _auth.py
  payment.py
  balance.py
  policy.py
```

Also requires adding `SARDIS = "sardis"` to `ProviderName` enum in
`autogpt_platform/backend/backend/integrations/providers.py`
(optional -- the `_missing_` method on ProviderName accepts any string).

## PR Title
feat: add Sardis payment blocks for policy-controlled agent payments

## PR Body

### Summary
Adds Sardis payment blocks so AutoGPT agents can make real stablecoin payments with spending policy guardrails.

**3 blocks:**
| Block | Description |
|-------|-------------|
| **Sardis Pay** | Execute a policy-controlled payment from a Sardis wallet |
| **Sardis Balance** | Check wallet balance and remaining spending limits |
| **Sardis Policy Check** | Pre-validate a payment against spending policy without moving funds |

### What is Sardis?
Sardis is the Payment OS for the Agent Economy. Each agent gets a non-custodial MPC wallet with spending policies you define in plain English. The agent proposes a payment, deterministic policy decides, full audit trail.

- 25k+ organic SDK installs
- Live on Base, Polygon, Ethereum, Arbitrum, Optimism
- Supports USDC, USDT, EURC, PYUSD
- Website: https://sardis.sh
- PyPI: https://pypi.org/project/sardis/

### Implementation
- Follows the provider pattern (see `_auth.py`, `_api.py`)
- Uses `APIKeyCredentials` via `ProviderName.SARDIS`
- Async `run()` methods with proper `BlockOutput` yields
- Test inputs, outputs, and mocks included for all 3 blocks
- Uses `backend.util.request.Requests` for HTTP calls

### Testing
All blocks include `test_input`, `test_output`, and `test_mock` configurations.
```bash
poetry run pytest backend/blocks/sardis/ -xvs
```

### Prerequisites
- Sardis API key (free sandbox at https://sardis.sh)
- Wallet ID (created via API or dashboard)
