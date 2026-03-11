# CLI Reference

Command-line interface for Sardis Payment OS.

## Installation

```bash
pip install sardis-cli
```

Or install with the full SDK:

```bash
pip install sardis[cli]
```

## Initialization

Set up your API key:

```bash
sardis init
```

This creates `~/.sardis/config.yaml`:

```yaml
api_key: sk_...
environment: production
default_chain: base
```

Or set via environment variable:

```bash
export SARDIS_API_KEY="sk_..."
```

## Commands

### Wallets

#### Create Wallet

```bash
sardis wallets create --name my-agent --chain base --policy "Max $500/day"
```

Output:
```
Wallet created successfully!
ID: wallet_abc123
Address: 0x1234567890abcdef1234567890abcdef12345678
Chain: base
Policy: Max $500/day
Trust Score: 75
```

With metadata:

```bash
sardis wallets create \
  --name my-agent \
  --chain base \
  --policy "Max $500/day" \
  --metadata '{"department": "engineering", "cost_center": "CC-1234"}'
```

#### List Wallets

```bash
sardis wallets list
```

Output:
```
ID              Name            Chain   Status  Trust Score
wallet_abc123   my-agent        base    active  85
wallet_def456   test-agent      polygon active  72
```

With filters:

```bash
sardis wallets list --status active --limit 50
```

#### Get Wallet

```bash
sardis wallets get wallet_abc123
```

Output:
```
Wallet: wallet_abc123
Name: my-agent
Address: 0x1234567890abcdef1234567890abcdef12345678
Chain: base
Policy: Max $500/day
Trust Score: 85/100 (Good)
Status: active

Balances:
  USDC: 1500.00
  EURC: 200.00

Created: 2026-02-21 10:00:00
```

#### Update Policy

```bash
sardis wallets update-policy wallet_abc123 --policy "Max $1000/day, SaaS only"
```

#### Freeze/Unfreeze

```bash
# Freeze
sardis wallets freeze wallet_abc123 --reason "Suspected compromise"

# Unfreeze
sardis wallets unfreeze wallet_abc123
```

#### Delete Wallet

```bash
sardis wallets delete wallet_abc123
```

With confirmation:

```bash
sardis wallets delete wallet_abc123 --confirm
```

### Payments

#### Execute Payment

```bash
sardis payments execute \
  --wallet wallet_abc123 \
  --to 0x1234567890abcdef1234567890abcdef12345678 \
  --amount 50 \
  --token USDC \
  --purpose "API credits"
```

Output:
```
Payment executed successfully!
Payment ID: payment_xyz789
TX Hash: 0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
Status: success
Block: 12345678
Gas Used: 0.0002 ETH
```

#### Get Payment

```bash
sardis payments get payment_xyz789
```

#### List Payments

```bash
sardis payments list --wallet wallet_abc123
```

With filters:

```bash
sardis payments list \
  --wallet wallet_abc123 \
  --status success \
  --start-date 2026-02-01 \
  --end-date 2026-02-28 \
  --limit 100
```

Output as JSON:

```bash
sardis payments list --wallet wallet_abc123 --format json
```

#### Simulate Payment

Test without executing:

```bash
sardis payments simulate \
  --wallet wallet_abc123 \
  --to 0x1234... \
  --amount 5000 \
  --token USDC
```

Output:
```
Simulation Result: FAIL
Violation: daily_limit_exceeded
Message: Daily limit of $500 exceeded
Attempted: $5000
Limit: $500
```

#### Estimate Gas

```bash
sardis payments estimate-gas \
  --wallet wallet_abc123 \
  --to 0x1234... \
  --amount 50 \
  --token USDC
```

Output:
```
Gas Estimate:
  Gas Price: 15.5 gwei
  Gas Limit: 21000
  Total Cost (ETH): 0.0003255
  Total Cost (USD): $0.98
```

### Balances

#### Get Balance

```bash
sardis balances get wallet_abc123 --token USDC
```

Output:
```
Balance: 1500.00 USDC
```

#### Get All Balances

```bash
sardis balances get-all wallet_abc123
```

Output:
```
Wallet: wallet_abc123
Balances:
  USDC: 1500.00
  EURC: 200.00
  USDT: 0.00
```

### Trust & KYA

#### Get Trust Score

```bash
sardis kya trust-score wallet_abc123
```

Output:
```
Trust Score: 85/100 (Good)

Breakdown:
  Transaction History: 40/40
  Behavioral Consistency: 28/30
  Identity Attestation: 15/20
  External Signals: 2/10

Risk Factors:
  - new_merchant_frequency

Recommendations:
  - Add merchant allowlist to policy
```

#### Trust History

```bash
sardis kya trust-history wallet_abc123 --days 30
```

Output:
```
Date        Score  Change  Reason
2026-02-21  85     +2      5 days clean behavior
2026-02-15  83     -5      Anomaly detected: spending spike
2026-02-10  88     +3      100+ successful payments
```

#### KYA Analysis

```bash
sardis kya analyze wallet_abc123
```

### Ledger

#### List Entries

```bash
sardis ledger list --wallet wallet_abc123
```

With filters:

```bash
sardis ledger list \
  --wallet wallet_abc123 \
  --type debit \
  --token USDC \
  --start-date 2026-02-01 \
  --end-date 2026-02-28
```

Output:
```
Timestamp           Type    Amount      Token  Balance After  TX Hash
2026-02-21 10:30    debit   -50.00      USDC   1450.00        0xabcd...
2026-02-21 09:15    credit  +100.00     USDC   1500.00        0x1234...
```

#### Reconcile

```bash
sardis ledger reconcile --wallet wallet_abc123 --date 2026-02-21
```

Output:
```
Reconciliation Report: 2026-02-21
Wallet: wallet_abc123

Opening Balance: 1500.00 USDC
Total Credits:   100.00 USDC
Total Debits:    150.00 USDC
Closing Balance: 1450.00 USDC

✓ Verified (balances match)
```

#### Export

```bash
sardis ledger export \
  --wallet wallet_abc123 \
  --format csv \
  --start-date 2026-01-01 \
  --end-date 2026-12-31 \
  --output ledger-2026.csv
```

Supported formats: `csv`, `json`, `quickbooks`, `irs_1099`

### Webhooks

#### Create Webhook

```bash
sardis webhooks create \
  --url https://your-app.com/sardis-webhook \
  --events wallet.payment.success wallet.payment.failed \
  --secret whsec_example_placeholder  # nosecret
```

#### List Webhooks

```bash
sardis webhooks list
```

Output:
```
ID               URL                                 Events                    Status
webhook_abc123   https://your-app.com/sardis-webhook 2 events                  active
```

#### Delete Webhook

```bash
sardis webhooks delete webhook_abc123
```

#### Test Webhook

```bash
sardis webhooks test webhook_abc123 --event wallet.payment.success
```

### Status

Check API status and account info:

```bash
sardis status
```

Output:
```
Sardis CLI v0.4.0
API: https://api.sardis.sh/v2
Status: Operational
Rate Limit: 45/60 requests remaining

Account:
  Wallets: 3
  Total Volume (30d): $12,500.00
  API Key: sk_...abc123 (ends in abc123)
```

## Global Options

Available on all commands:

```bash
--api-key sk_...          # Override API key
--environment production  # production or testnet
--format json             # Output format: text, json, table
--quiet                   # Suppress non-essential output
--verbose                 # Show detailed logs
```

Examples:

```bash
# Use testnet
sardis wallets list --environment testnet

# JSON output
sardis wallets get wallet_abc123 --format json

# Quiet mode
sardis payments execute --wallet wallet_abc123 --to 0x... --amount 50 --token USDC --quiet
```

## Output Formats

### Text (default)

Human-readable output:

```bash
sardis wallets get wallet_abc123
```

### JSON

Machine-readable:

```bash
sardis wallets get wallet_abc123 --format json
```

Output:
```json
{
  "id": "wallet_abc123",
  "name": "my-agent",
  "address": "0x1234...",
  "chain": "base",
  "policy": "Max $500/day",
  "trust_score": 85,
  "status": "active"
}
```

### Table

Tabular format:

```bash
sardis payments list --wallet wallet_abc123 --format table
```

## Configuration

Config file: `~/.sardis/config.yaml`

```yaml
api_key: sk_...
environment: production
default_chain: base
default_token: USDC
timeout: 30
max_retries: 3
```

View config:

```bash
sardis config show
```

Update config:

```bash
sardis config set default_chain polygon
sardis config set default_token EURC
```

## Scripting

Use CLI in scripts:

```bash
#!/bin/bash

# Create wallet
WALLET_ID=$(sardis wallets create \
  --name script-wallet \
  --chain base \
  --format json | jq -r '.id')

echo "Created wallet: $WALLET_ID"

# Fund wallet (manual step)
echo "Send USDC to: $(sardis wallets get $WALLET_ID --format json | jq -r '.address')"
read -p "Press enter when funded..."

# Execute payment
sardis payments execute \
  --wallet $WALLET_ID \
  --to 0x1234... \
  --amount 50 \
  --token USDC \
  --format json | jq '.tx_hash'
```

## Interactive Mode

Launch interactive shell:

```bash
sardis shell
```

```
sardis> wallets list
sardis> payments execute --wallet wallet_abc123 --to 0x... --amount 50 --token USDC
sardis> exit
```

## Autocomplete

Enable shell autocomplete:

```bash
# Bash
sardis completion bash >> ~/.bashrc

# Zsh
sardis completion zsh >> ~/.zshrc

# Fish
sardis completion fish > ~/.config/fish/completions/sardis.fish
```

## Troubleshooting

### Check API Connection

```bash
sardis status
```

### View Logs

```bash
sardis --verbose wallets list
```

### Reset Configuration

```bash
sardis config reset
sardis init
```

## Examples

### Daily Reconciliation Script

```bash
#!/bin/bash

YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

for WALLET in $(sardis wallets list --format json | jq -r '.[].id'); do
  echo "Reconciling $WALLET for $YESTERDAY"
  sardis ledger reconcile --wallet $WALLET --date $YESTERDAY
done
```

### Monthly Export

```bash
#!/bin/bash

MONTH=$(date +%Y-%m)

for WALLET in $(sardis wallets list --format json | jq -r '.[].id'); do
  sardis ledger export \
    --wallet $WALLET \
    --format csv \
    --start-date ${MONTH}-01 \
    --end-date ${MONTH}-31 \
    --output exports/${WALLET}_${MONTH}.csv
done
```

### Batch Payments

```bash
#!/bin/bash

# payments.csv format: wallet_id,to,amount,token,purpose
while IFS=, read -r wallet to amount token purpose; do
  echo "Processing: $purpose"
  sardis payments execute \
    --wallet $wallet \
    --to $to \
    --amount $amount \
    --token $token \
    --purpose "$purpose"
done < payments.csv
```

## Next Steps

- [Python SDK](python.md) - SDK reference
- [TypeScript SDK](typescript.md) - SDK reference
- [API Reference](../api/rest.md) - Raw HTTP API
