# OpenAI Assistant with Wallet

OpenAI function calling agent with Sardis payment capabilities.

## Setup

```bash
pip install sardis-openai openai
```

## Run

```bash
export SARDIS_API_KEY="sk_..."
export OPENAI_API_KEY="sk-..."
python main.py
```

## Tools Available

- `sardis_pay` - Execute USDC payment
- `sardis_check_balance` - Check wallet balance
- `sardis_check_policy` - Validate spending policy
- `sardis_issue_card` - Create virtual card
- `sardis_get_spending_summary` - Spending analytics
