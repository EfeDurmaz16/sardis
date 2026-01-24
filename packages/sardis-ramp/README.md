# Sardis Fiat Ramp

Bridge crypto wallets to traditional banking. Fund agent wallets from bank accounts, withdraw to banks, and pay merchants in USD.

## Installation

```bash
pip install sardis-ramp
```

## Quick Start

```python
from sardis_ramp import SardisFiatRamp, BankAccount

# Initialize
ramp = SardisFiatRamp(
    sardis_api_key="sk_...",
    bridge_api_key="bridge_..."
)

# Fund wallet from bank
result = await ramp.fund_wallet(
    wallet_id="wallet_123",
    amount_usd=100.00,
    method="bank"
)
print(f"Send ACH to: {result.ach_instructions.routing_number}")

# Withdraw to bank
withdrawal = await ramp.withdraw_to_bank(
    wallet_id="wallet_123",
    amount_usd=50.00,
    bank_account=BankAccount(
        account_holder_name="John Doe",
        account_number="1234567890",
        routing_number="021000021"
    )
)
print(f"Payout ID: {withdrawal.payout_id}")
```

## Features

- **On-Ramp**: Fund wallets via ACH, wire, or card (via Bridge/Stripe)
- **Off-Ramp**: Withdraw to bank accounts in USD
- **Merchant Payments**: Pay merchants in USD from crypto wallets
- **Policy Enforcement**: All operations respect Sardis spending policies

## Funding Methods

| Method | Settlement | Fee |
|--------|------------|-----|
| ACH | 1-3 days | 0.5% |
| Wire | Same day | $15 flat |
| Card | Instant | 2.5% |
| Crypto | ~15 min | Gas only |

## Architecture

```
User Bank → Bridge → USDC → Sardis Wallet → Virtual Card / Crypto / Fiat Payout
```

All funds flow through the Sardis wallet as USDC, enabling:
- Unified policy enforcement
- Single balance view
- Flexible payout options

## Documentation

- [Full Documentation](https://sardis.sh/docs/fiat-ramp)
- [API Reference](https://sardis.sh/docs/reference/api)
- [Bridge Integration Guide](https://sardis.sh/docs/guides/bridge)

## License

Apache 2.0
