"""
Sardis Ledger - Production-grade ledger with full transaction support.

This package provides:
- Append-only ledger with Merkle tree receipts
- Row-level locking for concurrent transactions
- Batch transaction processing with atomic commits
- Balance snapshots for point-in-time queries
- Blockchain reconciliation
- Currency conversion
- Comprehensive audit trail

Example usage:

    from sardis_ledger import LedgerStore, ChainReceipt, LedgerEngine

    # Create a ledger store
    ledger = LedgerStore("sqlite:///ledger.db")

    # Or use the engine for advanced operations
    from sardis_ledger.engine import LedgerEngine, LockManager
    engine = LedgerEngine(lock_manager=LockManager())

    # Create entries with locking
    entry = engine.create_entry(
        account_id="acc_123",
        amount=Decimal("100.50"),
        entry_type=LedgerEntryType.CREDIT,
    )

    # Batch processing
    batch = engine.create_batch([
        {"account_id": "acc_123", "amount": "50.00", "entry_type": "debit"},
        {"account_id": "acc_456", "amount": "50.00", "entry_type": "credit"},
    ])

    # Rollback if needed
    engine.rollback_batch(batch.batch_id, reason="Customer requested refund")
"""
from .records import LedgerStore, ChainReceipt, PendingReconciliation

from .models import (
    # Constants
    DECIMAL_PRECISION,
    DECIMAL_SCALE,
    DECIMAL_QUANTIZE,
    # Utilities
    to_ledger_decimal,
    validate_amount,
    # Enums
    LedgerEntryType,
    LedgerEntryStatus,
    ReconciliationStatus,
    AuditAction,
    # Models
    LedgerEntry,
    BalanceSnapshot,
    AuditLog,
    ReconciliationRecord,
    BatchTransaction,
    CurrencyRate,
    LockRecord,
)

from .engine import (
    # Exceptions
    LedgerError,
    LockAcquisitionError,
    LockTimeoutError,
    ConcurrencyError,
    InsufficientBalanceError,
    BatchProcessingError,
    RollbackError,
    ValidationError,
    # Lock Manager
    LockManager,
    # Engine
    LedgerEngine,
)

from .reconciliation import (
    # Types
    DiscrepancyType,
    ResolutionStrategy,
    ChainTransaction,
    Discrepancy,
    # Providers
    ChainProvider,
    MockChainProvider,
    # Engines
    ReconciliationEngine,
    CurrencyConverter,
    ReconciliationScheduler,
)

# Immutable audit trail (optional - requires immudb-py)
try:
    from .immutable import (
        # Config
        ImmutableConfig,
        # Errors
        ImmutableStoreError,
        VerificationError,
        ConsistencyError,
        AnchoringError,
        # Enums
        VerificationStatus,
        # Models
        MerkleProof,
        ImmutableReceipt,
        VerificationResult,
        AuditEntry,
        # Services
        ImmutableAuditTrail,
        BlockchainAnchor,
        # Factory
        create_audit_trail,
    )
    IMMUDB_AVAILABLE = True
except ImportError:
    IMMUDB_AVAILABLE = False

# Hybrid ledger (PostgreSQL + immudb)
try:
    from .hybrid import (
        # Config
        HybridConfig,
        # Errors
        HybridLedgerError,
        DualWriteError,
        # Models
        HybridReceipt,
        ConsistencyReport,
        # Service
        HybridLedger,
        # Factory
        create_hybrid_ledger,
    )
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False

__version__ = "0.3.0"

__all__ = [
    # Version
    "__version__",
    # Feature flags
    "IMMUDB_AVAILABLE",
    "HYBRID_AVAILABLE",
    # Core store
    "LedgerStore",
    "ChainReceipt",
    "PendingReconciliation",
    # Constants
    "DECIMAL_PRECISION",
    "DECIMAL_SCALE",
    "DECIMAL_QUANTIZE",
    # Utilities
    "to_ledger_decimal",
    "validate_amount",
    # Enums
    "LedgerEntryType",
    "LedgerEntryStatus",
    "ReconciliationStatus",
    "AuditAction",
    # Models
    "LedgerEntry",
    "BalanceSnapshot",
    "AuditLog",
    "ReconciliationRecord",
    "BatchTransaction",
    "CurrencyRate",
    "LockRecord",
    # Exceptions
    "LedgerError",
    "LockAcquisitionError",
    "LockTimeoutError",
    "ConcurrencyError",
    "InsufficientBalanceError",
    "BatchProcessingError",
    "RollbackError",
    "ValidationError",
    # Lock Manager
    "LockManager",
    # Engine
    "LedgerEngine",
    # Reconciliation types
    "DiscrepancyType",
    "ResolutionStrategy",
    "ChainTransaction",
    "Discrepancy",
    # Reconciliation providers
    "ChainProvider",
    "MockChainProvider",
    # Reconciliation engines
    "ReconciliationEngine",
    "CurrencyConverter",
    "ReconciliationScheduler",
]

# Add immutable audit trail exports if available
if IMMUDB_AVAILABLE:
    __all__.extend([
        # Config
        "ImmutableConfig",
        # Errors
        "ImmutableStoreError",
        "VerificationError",
        "ConsistencyError",
        "AnchoringError",
        # Enums
        "VerificationStatus",
        # Models
        "MerkleProof",
        "ImmutableReceipt",
        "VerificationResult",
        "AuditEntry",
        # Services
        "ImmutableAuditTrail",
        "BlockchainAnchor",
        # Factory
        "create_audit_trail",
    ])

# Add hybrid ledger exports if available
if HYBRID_AVAILABLE:
    __all__.extend([
        # Config
        "HybridConfig",
        # Errors
        "HybridLedgerError",
        "DualWriteError",
        # Models
        "HybridReceipt",
        "ConsistencyReport",
        # Service
        "HybridLedger",
        # Factory
        "create_hybrid_ledger",
    ])
