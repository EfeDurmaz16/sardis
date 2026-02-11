# sardis-ledger

[![PyPI version](https://badge.fury.io/py/sardis-ledger.svg)](https://badge.fury.io/py/sardis-ledger)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-grade append-only ledger with row-level locking, batch processing, and blockchain reconciliation.

## Overview

`sardis-ledger` provides an immutable audit and settlement ledger for financial operations:

- **Append-Only Records**: Immutable ledger entries with Merkle tree receipts
- **Row-Level Locking**: Concurrent transaction support with deadlock prevention
- **Batch Processing**: Atomic multi-entry commits with rollback support
- **Blockchain Reconciliation**: Automated chain state reconciliation
- **Balance Snapshots**: Point-in-time balance queries
- **Hybrid Storage**: PostgreSQL + immudb for verified immutability

## Installation

```bash
pip install sardis-ledger
```

### Optional Dependencies

```bash
# PostgreSQL async support
pip install sardis-ledger[postgres]

# immudb for verified immutability
pip install sardis-ledger[immudb]

# Blockchain anchoring
pip install sardis-ledger[anchoring]

# All optional dependencies
pip install sardis-ledger[all]
```

## Quick Start

```python
from sardis_ledger import LedgerEngine, LedgerEntryType
from decimal import Decimal

# Initialize the ledger
engine = LedgerEngine(database_url="postgresql://...")

# Create a ledger entry
entry = await engine.create_entry(
    account_id="acc_123",
    amount=Decimal("100.50"),
    entry_type=LedgerEntryType.CREDIT,
    reference="payment_456",
)

print(f"Entry ID: {entry.entry_id}")
print(f"Balance: {entry.running_balance}")
print(f"Merkle Root: {entry.merkle_root}")
```

## Features

### Ledger Operations

```python
from sardis_ledger import LedgerEngine, LedgerEntryType
from decimal import Decimal

engine = LedgerEngine(database_url="postgresql://...")

# Credit an account
credit = await engine.create_entry(
    account_id="acc_123",
    amount=Decimal("500.00"),
    entry_type=LedgerEntryType.CREDIT,
    reference="deposit_789",
    metadata={"source": "bank_transfer"},
)

# Debit an account
debit = await engine.create_entry(
    account_id="acc_123",
    amount=Decimal("100.00"),
    entry_type=LedgerEntryType.DEBIT,
    reference="withdrawal_012",
)

# Get current balance
balance = await engine.get_balance("acc_123")
print(f"Current balance: {balance}")
```

### Batch Processing

```python
from sardis_ledger import LedgerEngine

engine = LedgerEngine(database_url="postgresql://...")

# Create a batch of entries (atomic commit)
batch = await engine.create_batch([
    {
        "account_id": "acc_sender",
        "amount": "500.00",
        "entry_type": "debit",
        "reference": "transfer_123",
    },
    {
        "account_id": "acc_receiver",
        "amount": "500.00",
        "entry_type": "credit",
        "reference": "transfer_123",
    },
])

print(f"Batch ID: {batch.batch_id}")
print(f"Entries: {len(batch.entries)}")

# Rollback if needed
await engine.rollback_batch(
    batch_id=batch.batch_id,
    reason="Customer requested refund",
)
```

### Row-Level Locking

```python
from sardis_ledger import LedgerEngine, LockManager

lock_manager = LockManager()
engine = LedgerEngine(lock_manager=lock_manager)

# Acquire lock for concurrent safety
async with engine.lock_account("acc_123"):
    balance = await engine.get_balance("acc_123")
    if balance >= amount:
        await engine.create_entry(
            account_id="acc_123",
            amount=amount,
            entry_type=LedgerEntryType.DEBIT,
        )
```

### Blockchain Reconciliation

```python
from sardis_ledger import ReconciliationEngine, ChainProvider

reconciler = ReconciliationEngine(
    ledger=engine,
    chain_provider=ChainProvider(chain="base"),
)

# Run reconciliation
report = await reconciler.reconcile(
    start_block=1000000,
    end_block=1001000,
)

print(f"Matched: {report.matched_count}")
print(f"Discrepancies: {len(report.discrepancies)}")

for disc in report.discrepancies:
    print(f"  {disc.type}: {disc.description}")
```

### Immutable Audit Trail (with immudb)

```python
from sardis_ledger import create_audit_trail, ImmutableConfig

# Create immutable audit trail
audit = create_audit_trail(
    config=ImmutableConfig(
        host="localhost",
        port=3322,
        database="sardis_audit",
    )
)

# Write an audit entry
receipt = await audit.write(
    entry_id=entry.entry_id,
    data=entry.to_dict(),
)

print(f"Verified at: {receipt.timestamp}")
print(f"Merkle proof: {receipt.merkle_proof}")

# Verify an entry
verification = await audit.verify(entry.entry_id)
assert verification.status == VerificationStatus.VERIFIED
```

### Hybrid Ledger (PostgreSQL + immudb)

```python
from sardis_ledger import create_hybrid_ledger, HybridConfig

# Create hybrid ledger for best of both worlds
ledger = create_hybrid_ledger(
    config=HybridConfig(
        postgres_url="postgresql://...",
        immudb_host="localhost",
        immudb_port=3322,
    )
)

# Entries are written to both stores
entry = await ledger.create_entry(
    account_id="acc_123",
    amount=Decimal("100.00"),
    entry_type=LedgerEntryType.CREDIT,
)

# Get hybrid receipt with both proofs
print(f"PostgreSQL ID: {entry.receipt.pg_id}")
print(f"immudb TX: {entry.receipt.immudb_tx}")
```

## Architecture

```
sardis-ledger/
├── models.py         # Data models and enums
├── records.py        # Core ledger store
├── engine.py         # Ledger engine with locking
├── reconciliation.py # Blockchain reconciliation
├── immutable.py      # immudb integration
└── hybrid.py         # Hybrid storage
```

## Requirements

- Python 3.11+
- sardis-core >= 0.1.0
- sqlalchemy >= 2.0

## Documentation

Full documentation is available at [docs.sardis.sh/ledger](https://docs.sardis.sh/ledger).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.
