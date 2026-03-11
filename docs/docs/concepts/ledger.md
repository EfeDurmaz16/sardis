# Ledger & Audit Trail

Immutable, double-entry ledger for complete transaction history and compliance reporting.

## Overview

Every transaction through Sardis is recorded in an **append-only audit ledger**. This provides:

- Complete transaction history
- Cryptographic proof of all operations
- Compliance audit trail
- Dispute resolution evidence
- Regulatory reporting data

**Key principle:** The ledger cannot be modified or deleted. It's immutable and cryptographically verifiable.

## Ledger Architecture

```
Transaction Request
       ↓
Policy Validation
       ↓
MPC Signing
       ↓
Blockchain Execution
       ↓
┌──────────────────────┐
│   Ledger Entry       │
│  • Transaction hash  │
│  • Policy applied    │
│  • Trust score       │
│  • Timestamp         │
│  • Signatures        │
└──────────────────────┘
       ↓
Append-Only Storage
(PostgreSQL + S3)
```

## Double-Entry Accounting

Sardis uses **double-entry bookkeeping** - every transaction creates two ledger entries:

```python
# Payment from Agent A to Merchant B

# Debit Entry (Agent A)
{
  "entry_id": "ledger_001",
  "wallet_id": "wallet_agent_a",
  "type": "debit",
  "amount": "-50.00",
  "token": "USDC",
  "balance_after": "450.00"
}

# Credit Entry (Merchant B)
{
  "entry_id": "ledger_002",
  "wallet_id": "wallet_merchant_b",
  "type": "credit",
  "amount": "+50.00",
  "token": "USDC",
  "balance_after": "550.00"
}
```

This ensures:
- All transactions balance (sum of debits = sum of credits)
- No "lost" funds
- Easy reconciliation

## Viewing Ledger Entries

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_...")

# Get ledger entries for a wallet
entries = client.ledger.list(wallet_id="wallet_abc123")

for entry in entries:
    print(f"{entry.timestamp}: {entry.type} {entry.amount} {entry.token}")
```

## Ledger Entry Structure

```python
entry = client.ledger.get("ledger_xyz789")

# Core fields
entry.id                    # "ledger_xyz789"
entry.wallet_id             # "wallet_abc123"
entry.type                  # "debit" | "credit"
entry.amount                # "-50.00" or "+50.00"
entry.token                 # "USDC"
entry.balance_after         # "450.00"

# Transaction details
entry.tx_hash               # "0xabcd..."
entry.payment_id            # "payment_123"
entry.recipient             # "0x1234..." or "merchant@example.com"
entry.purpose               # "API credits"

# Policy & compliance
entry.policy_applied        # "Max $500/day, SaaS only"
entry.policy_result         # "approved"
entry.trust_score_at_time   # 85
entry.compliance_checks     # ["sanctions_clear", "kyc_verified"]

# Metadata
entry.timestamp             # "2026-02-21T10:30:00Z"
entry.block_number          # 12345678
entry.gas_used              # "0.0002"
entry.signature             # "0xsig..."

# Immutability proof
entry.previous_entry_hash   # SHA256 of previous entry (blockchain-style)
entry.merkle_root           # Merkle tree root for batch
```

## Ledger Queries

### By Date Range

```python
entries = client.ledger.list(
    wallet_id="wallet_abc123",
    start_date="2026-02-01",
    end_date="2026-02-28"
)
```

### By Transaction Type

```python
# Only debits (outgoing payments)
debits = client.ledger.list(
    wallet_id="wallet_abc123",
    type="debit"
)

# Only credits (incoming funds)
credits = client.ledger.list(
    wallet_id="wallet_abc123",
    type="credit"
)
```

### By Token

```python
usdc_entries = client.ledger.list(
    wallet_id="wallet_abc123",
    token="USDC"
)
```

### By Status

```python
# Successful transactions
successful = client.ledger.list(
    wallet_id="wallet_abc123",
    status="success"
)

# Failed transactions
failed = client.ledger.list(
    wallet_id="wallet_abc123",
    status="failed"
)

# Pending transactions
pending = client.ledger.list(
    wallet_id="wallet_abc123",
    status="pending"
)
```

## Reconciliation

Generate reconciliation reports:

```python
# Daily reconciliation
report = client.ledger.reconcile(
    wallet_id="wallet_abc123",
    date="2026-02-21"
)

print(f"Opening balance: {report.opening_balance}")
print(f"Total debits: {report.total_debits}")
print(f"Total credits: {report.total_credits}")
print(f"Closing balance: {report.closing_balance}")

# Verify: opening + credits - debits = closing
assert report.opening_balance + report.total_credits - report.total_debits == report.closing_balance
```

## Compliance Exports

Export ledger data for compliance/auditing:

```python
# Export as CSV
csv_data = client.ledger.export(
    wallet_id="wallet_abc123",
    format="csv",
    start_date="2026-01-01",
    end_date="2026-12-31"
)

# Export as JSON
json_data = client.ledger.export(
    wallet_id="wallet_abc123",
    format="json"
)

# Export for specific regulations
irs_report = client.ledger.export(
    wallet_id="wallet_abc123",
    format="irs_1099"  # Tax reporting
)

aml_report = client.ledger.export(
    wallet_id="wallet_abc123",
    format="aml_sar"  # Suspicious Activity Report
)
```

## Cryptographic Verification

Verify ledger integrity:

```python
# Verify entire ledger chain
is_valid = client.ledger.verify(wallet_id="wallet_abc123")

if not is_valid:
    print("WARNING: Ledger integrity compromised!")

# Verify specific entry
entry = client.ledger.get("ledger_xyz789")
is_valid = client.ledger.verify_entry(entry.id)

# Verify against blockchain
blockchain_verify = client.ledger.verify_on_chain(entry.id)
print(f"Blockchain confirmed: {blockchain_verify.confirmed}")
print(f"Block: {blockchain_verify.block_number}")
```

## Ledger Events

Every ledger entry triggers an event:

```python
# Subscribe to ledger events
client.webhooks.create(
    url="https://your-app.com/ledger-webhook",
    events=[
        "ledger.entry.created",
        "ledger.reconciliation.complete",
        "ledger.export.ready"
    ]
)
```

Webhook payload:

```json
{
  "event": "ledger.entry.created",
  "entry": {
    "id": "ledger_xyz789",
    "wallet_id": "wallet_abc123",
    "type": "debit",
    "amount": "-50.00",
    "token": "USDC",
    "tx_hash": "0xabcd...",
    "timestamp": "2026-02-21T10:30:00Z"
  }
}
```

## Audit Reports

Generate audit reports for specific purposes:

### Financial Audit

```python
audit = client.ledger.audit_report(
    wallet_id="wallet_abc123",
    type="financial",
    period="2026-Q1"
)

print(audit.total_transactions)
print(audit.total_volume_usd)
print(audit.policy_violations)
print(audit.reconciliation_errors)  # Should be 0
```

### Compliance Audit

```python
compliance = client.ledger.audit_report(
    wallet_id="wallet_abc123",
    type="compliance",
    period="2026-Q1"
)

print(compliance.kyc_checks_performed)
print(compliance.sanctions_screenings)
print(compliance.flagged_transactions)
print(compliance.sar_filed)  # Suspicious Activity Reports
```

### Security Audit

```python
security = client.ledger.audit_report(
    wallet_id="wallet_abc123",
    type="security",
    period="2026-Q1"
)

print(security.anomalies_detected)
print(security.policy_violations)
print(security.wallet_freezes)
print(security.trust_score_changes)
```

## Retention Policy

Ledger data retention:

- **Active wallets:** Indefinite retention
- **Closed wallets:** 7 years (regulatory requirement)
- **Exports:** Available on-demand
- **Backups:** Encrypted, geo-redundant

```python
# Check retention policy
retention = client.ledger.retention_policy(wallet_id)

print(f"Retention period: {retention.years} years")
print(f"Last backup: {retention.last_backup}")
print(f"Backup location: {retention.backup_region}")
```

## Real-Time Monitoring

Monitor ledger activity in real-time:

```python
# Stream ledger entries (WebSocket)
async for entry in client.ledger.stream(wallet_id="wallet_abc123"):
    print(f"New entry: {entry.type} {entry.amount} {entry.token}")

    # Alert on large transactions
    if abs(float(entry.amount)) > 1000:
        send_alert(f"Large transaction: {entry.amount} {entry.token}")
```

## Dispute Resolution

Use ledger entries as evidence:

```python
# Get cryptographic proof for a transaction
proof = client.ledger.get_proof("ledger_xyz789")

print(proof.entry_hash)          # SHA256 of entry
print(proof.signature)           # Cryptographic signature
print(proof.merkle_proof)        # Merkle tree inclusion proof
print(proof.blockchain_tx)       # On-chain transaction hash

# Verify proof independently
from sardis import verify_ledger_proof

is_valid = verify_ledger_proof(
    entry_data=entry,
    proof=proof,
    public_key=client.public_key
)
```

## Performance

The Sardis ledger is optimized for:

- **Write throughput:** 10,000+ entries/second
- **Query latency:** <100ms for recent entries
- **Storage:** Compressed, deduplicated
- **Indexes:** Wallet ID, timestamp, tx hash, token

```python
# Bulk queries are efficient
entries = client.ledger.list(
    wallet_id="wallet_abc123",
    limit=10000  # Returns in <1 second
)
```

## Best Practices

1. **Regular reconciliation** - Daily or weekly
2. **Export monthly** - Keep offline backups
3. **Monitor for anomalies** - Set up alerts
4. **Verify cryptographically** - Periodically check integrity
5. **Document policy changes** - Track why policies were updated
6. **Archive old exports** - For long-term compliance
7. **Test verification** - Ensure you can prove transactions

## Integration Examples

### Accounting Integration (QuickBooks)

```python
# Export ledger to QuickBooks format
qb_export = client.ledger.export(
    wallet_id="wallet_abc123",
    format="quickbooks",
    start_date="2026-02-01",
    end_date="2026-02-28"
)

# Import into QuickBooks API
quickbooks.import_journal_entries(qb_export)
```

### Tax Reporting (IRS)

```python
# Generate 1099 forms for all merchants paid
tax_report = client.ledger.tax_report(
    wallet_id="wallet_abc123",
    year=2026,
    form="1099-MISC"
)

for merchant, total in tax_report.items():
    print(f"{merchant}: ${total} paid in 2026")
```

### Bank Reconciliation

```python
# Compare Sardis ledger to bank statement
bank_statement = load_bank_statement("statement.csv")
sardis_ledger = client.ledger.list(wallet_id="wallet_abc123")

discrepancies = reconcile(bank_statement, sardis_ledger)

if discrepancies:
    print(f"Found {len(discrepancies)} discrepancies")
```

## Next Steps

- [Spending Policies](policies.md) - Policy enforcement
- [KYA Trust Scoring](kya.md) - Behavioral monitoring
- [Webhooks](../api/webhooks.md) - Real-time events
- [API Reference](../api/rest.md) - Complete ledger API
