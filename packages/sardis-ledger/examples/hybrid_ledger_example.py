#!/usr/bin/env python3
"""
Example: Using the Hybrid Ledger (PostgreSQL + immudb)

This example demonstrates:
1. Setting up the hybrid ledger
2. Creating entries with dual-write
3. Verifying entries cryptographically
4. Generating audit proofs for compliance
5. Checking consistency between stores

Prerequisites:
1. Install dependencies:
   pip install sardis-ledger[immudb,anchoring]

2. Start immudb:
   docker-compose -f docker-compose.immudb.yml up -d

Run:
   python examples/hybrid_ledger_example.py
"""
import asyncio
from decimal import Decimal
from datetime import datetime

from sardis_ledger import (
    # Hybrid ledger
    HybridConfig,
    HybridLedger,
    create_hybrid_ledger,
    # Models
    LedgerEntryType,
    # Verification
    VerificationStatus,
)


async def main():
    print("=" * 60)
    print("Sardis Hybrid Ledger Example")
    print("PostgreSQL + immudb for Immutable Financial Transactions")
    print("=" * 60)

    # 1. Configure the hybrid ledger
    config = HybridConfig(
        # PostgreSQL (in-memory for this example)
        enable_postgresql=True,
        snapshot_interval=100,
        enable_pg_audit=True,

        # immudb
        enable_immudb=True,
        immudb_host="localhost",
        immudb_port=3322,
        immudb_user="immudb",
        immudb_password="immudb",
        immudb_database="sardis_example",

        # Blockchain anchoring (disabled for example)
        enable_anchoring=False,
        anchor_chain="base",

        # Consistency settings
        require_dual_write=True,
        async_immudb_write=False,
    )

    # 2. Create and connect
    print("\n[1] Connecting to hybrid ledger...")
    ledger = HybridLedger(config)

    try:
        await ledger.connect()
        print("    ✓ Connected to PostgreSQL (in-memory)")
        print("    ✓ Connected to immudb")
    except Exception as e:
        print(f"    ✗ Connection failed: {e}")
        print("\n    Make sure immudb is running:")
        print("    docker-compose -f docker-compose.immudb.yml up -d")
        return

    # 3. Health check
    print("\n[2] Health check...")
    health = await ledger.health_check()
    print(f"    Status: {health['status']}")
    for store, info in health.get("stores", {}).items():
        status = info.get("status", "unknown")
        print(f"    - {store}: {status}")

    # 4. Create some transactions
    print("\n[3] Creating transactions...")

    # Agent wallet receives funds
    receipt1 = await ledger.create_entry(
        account_id="agent_wallet_001",
        amount=Decimal("1000.00"),
        entry_type=LedgerEntryType.CREDIT,
        currency="USDC",
        chain="base",
        chain_tx_hash="0xabc123...",
        block_number=12345678,
        actor_id="user_alice",
        metadata={"source": "deposit", "agent": "shopping_agent"},
    )
    print(f"    ✓ Credit $1000 to agent_wallet_001")
    print(f"      Entry ID: {receipt1.entry_id}")
    print(f"      Merkle Root: {receipt1.immudb_receipt.merkle_proof.root_hash[:32]}...")

    # Agent makes a purchase
    receipt2 = await ledger.create_entry(
        account_id="agent_wallet_001",
        amount=Decimal("150.00"),
        entry_type=LedgerEntryType.DEBIT,
        currency="USDC",
        chain="base",
        chain_tx_hash="0xdef456...",
        block_number=12345680,
        actor_id="shopping_agent",
        metadata={"purchase": "electronics", "merchant": "amazon"},
    )
    print(f"    ✓ Debit $150 from agent_wallet_001 (purchase)")
    print(f"      Entry ID: {receipt2.entry_id}")

    # Transaction fee
    receipt3 = await ledger.create_entry(
        account_id="agent_wallet_001",
        amount=Decimal("0.50"),
        entry_type=LedgerEntryType.FEE,
        currency="USDC",
        actor_id="system",
        metadata={"fee_type": "network"},
    )
    print(f"    ✓ Fee $0.50 from agent_wallet_001")

    # 5. Check balance
    print("\n[4] Checking balance...")
    balance = ledger.get_balance("agent_wallet_001", "USDC")
    print(f"    Current balance: ${balance:.2f} USDC")

    # 6. Verify a transaction
    print("\n[5] Verifying transaction cryptographically...")
    verification = await ledger.verify_entry(receipt1.entry_id)
    print(f"    Entry: {receipt1.entry_id}")
    print(f"    Status: {verification.status.value}")
    print(f"    immudb verified: {verification.immudb_verified}")
    print(f"    Merkle verified: {verification.merkle_verified}")
    if verification.merkle_root:
        print(f"    Merkle root: {verification.merkle_root[:32]}...")

    # 7. Generate audit proof (for compliance)
    print("\n[6] Generating audit proof for compliance...")
    proof = await ledger.get_audit_proof(receipt1.entry_id)
    print(f"    Proof version: {proof['version']}")
    print(f"    Generated at: {proof['generated_at']}")
    print(f"    Stores included: {list(proof['stores'].keys())}")
    print(f"    Consistency verified: {proof['consistency']['verified']}")

    # Show Merkle proof details
    immudb_proof = proof['stores']['immudb']
    if 'merkle_proof' in immudb_proof:
        mp = immudb_proof['merkle_proof']
        print(f"    Merkle proof:")
        print(f"      - Transaction ID: {mp['tx_id']}")
        print(f"      - Tree size: {mp['tree_size']}")
        print(f"      - Proof nodes: {len(mp['proof_nodes'])}")

    # 8. Check consistency between stores
    print("\n[7] Checking consistency between PostgreSQL and immudb...")
    report = await ledger.check_consistency(sample_size=10)
    print(f"    Entries checked: {report.total_checked}")
    print(f"    Consistent: {report.consistent}")
    print(f"    Inconsistent: {report.inconsistent}")
    print(f"    Is fully consistent: {report.is_consistent}")

    # 9. List recent entries
    print("\n[8] Recent entries for agent_wallet_001...")
    entries = ledger.get_entries("agent_wallet_001", limit=5)
    for entry in entries:
        print(f"    - {entry.entry_type.value}: ${entry.amount:.2f} {entry.currency}")

    # 10. Cleanup
    print("\n[9] Disconnecting...")
    await ledger.disconnect()
    print("    ✓ Disconnected")

    print("\n" + "=" * 60)
    print("Summary:")
    print("- Transactions stored in PostgreSQL for fast queries")
    print("- Transactions immutably stored in immudb with Merkle proofs")
    print("- Every entry has cryptographic verification")
    print("- Audit proofs available for compliance/legal purposes")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
