# sardis-mpp

Policy-governed [Machine Payments Protocol](https://mpp.dev) client for AI agents. Built on [pympp](https://pypi.org/project/pympp/) (co-authored by Stripe and Tempo).

Every HTTP 402 payment challenge passes through the Sardis policy pipeline before funds move.

## Installation

```bash
pip install sardis-mpp
```

Requires `pympp >= 0.4.0` and `httpx >= 0.27`.

## Quick Start

```python
import asyncio
from sardis_mpp import SardisMPPClient
from mpp.methods.tempo import tempo, TempoAccount, ChargeIntent

# Set up Tempo payment method
account = TempoAccount.from_key("0x<your-private-key>")
tempo_method = tempo(
    account=account,
    intents={"charge": ChargeIntent(chain_id=4217)},  # Tempo mainnet
)

# Create Sardis-governed MPP client
client = SardisMPPClient(
    methods=[tempo_method],
    policy_checker=my_policy_fn,  # (amount, merchant, ...) -> (bool, str)
)

# Agent accesses a paid API — 402 handled automatically with policy check
async def main():
    response = await client.get("https://api.example.com/premium-data")
    print(response.json())
    await client.close()

asyncio.run(main())
```

## Payment Methods

### Tempo (Crypto)

Pay with pathUSD or USDC on Tempo mainnet/testnet:

```python
from mpp.methods.tempo import tempo, TempoAccount, ChargeIntent

account = TempoAccount.from_key("0x...")
tempo_method = tempo(
    account=account,
    intents={"charge": ChargeIntent(chain_id=4217)},  # mainnet
)
```

### Stripe (Fiat)

Pay with cards/wallets via Shared Payment Tokens (SPT):

```python
from sardis_mpp import SardisStripeMPPMethod

stripe_method = SardisStripeMPPMethod(
    api_key="sk_...",
    mandate_id="mandate_abc123",
)
```

### Combined

Use both payment methods together:

```python
client = SardisMPPClient(
    methods=[tempo_method, stripe_method],
    policy_checker=policy_fn,
)
```

## Policy Enforcement

The `policy_checker` is an async function that receives payment details and returns `(allowed: bool, reason: str)`:

```python
async def my_policy(amount, merchant, payment_type, currency, network):
    if amount > 100:
        return False, "Amount exceeds $100 limit"
    return True, "Within policy"

client = SardisMPPClient(
    methods=[tempo_method],
    policy_checker=my_policy,
)
```

When a policy denies a payment, `MPPPaymentDenied` is raised:

```python
from sardis_mpp import MPPPaymentDenied

try:
    response = await client.get("https://expensive-api.com/data")
except MPPPaymentDenied as e:
    print(f"Blocked: {e}")
```

## Audit Trail

Track all payments for compliance:

```python
client = SardisMPPClient(
    methods=[tempo_method],
    policy_checker=policy_fn,
    on_payment=lambda record: print(f"{record.policy_result}: {record.amount} {record.currency}"),
)

# After making requests:
for record in client.payment_records:
    print(f"{record.url} — {record.amount} {record.currency} — {record.policy_result}")

print(f"Total spent: {client.total_spent}")
```

## x402 Auto-Pay (Laso Virtual Cards)

Issue virtual prepaid cards via Laso Finance. The x402 micro-payment ($0.001 USDC) is handled automatically:

```python
from sardis_mpp.services.laso import LasoMPPService

laso = LasoMPPService(
    tempo_private_key="0x...",
    policy_checker=policy_fn,
)

card = await laso.issue_card(amount=50)  # $50 virtual Visa card
print(card.card_number, card.cvv, card.expiry)

await laso.close()
```

## Session Management

Map Sardis spending mandates to MPP session parameters:

```python
from sardis_mpp import MPPSessionManager

session_mgr = MPPSessionManager(policy_checker=policy_fn)

# Convert mandate to MPP session params
params = session_mgr.mandate_to_session_params(mandate)
# -> {"maxDeposit": "500", "dailyLimit": "5000", ...}

# Track payments for anomaly detection
session_mgr.track_payment("session_123", amount)
if session_mgr.check_anomaly("session_123", amount):
    await session_mgr.force_close("session_123", "Anomalous spend detected")
```

## Constants

From pympp defaults:

| Constant | Value |
|----------|-------|
| Tempo Mainnet Chain ID | `4217` |
| Tempo Testnet Chain ID | `42431` |
| pathUSD | `0x20c0000000000000000000000000000000000000` |
| USDC (bridged) | `0x20C000000000000000000000b9537d11c60E8b50` |

## Exports

- `SardisMPPClient` — Main client with policy enforcement
- `SardisPolicyTransport` — httpx transport for 402 interception
- `MPPPaymentDenied` — Raised when policy blocks a payment
- `MPPPaymentRecord` — Audit record for each payment
- `MPPSessionManager` — Mandate-to-session mapping + anomaly detection
- `SardisStripeMPPMethod` — Stripe SPT payment method

## License

MIT
