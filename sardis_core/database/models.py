"""
SQLAlchemy Database Models for Sardis

These models represent the production database schema for
persistent storage of all Sardis data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    JSON,
    Index,
    Enum as SQLEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum


Base = declarative_base()


# ============ Enums ============

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class LedgerEntryType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    FEE = "fee"
    REFUND = "refund"
    HOLD = "hold"
    RELEASE = "release"
    SETTLEMENT = "settlement"
    MINT = "mint"
    BURN = "burn"


class HoldStatus(str, enum.Enum):
    ACTIVE = "active"
    CAPTURED = "captured"
    VOIDED = "voided"
    EXPIRED = "expired"


class TrustLevel(str, enum.Enum):
    NEW = "new"
    BASIC = "basic"
    VERIFIED = "verified"
    TRUSTED = "trusted"


# ============ Agent Model ============

class AgentDB(Base):
    """AI Agent entity."""
    
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    trust_level = Column(SQLEnum(TrustLevel), default=TrustLevel.NEW)
    
    # Blockchain
    on_chain_wallet = Column(String(42))  # Ethereum address
    chain = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    wallet = relationship("WalletDB", back_populates="agent", uselist=False)
    transactions = relationship("TransactionDB", back_populates="agent")
    spending_policy = relationship("SpendingPolicyDB", back_populates="agent", uselist=False)
    
    __table_args__ = (
        Index("ix_agents_owner_active", "owner_id", "is_active"),
    )


# ============ Wallet Model ============

class WalletDB(Base):
    """Agent wallet for holding funds."""
    
    __tablename__ = "wallets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(String(100), unique=True, nullable=False, index=True)
    agent_id = Column(String(100), ForeignKey("agents.agent_id"), unique=True)
    
    # Balances (stored as strings for precision)
    balance = Column(Numeric(24, 6), default=0)
    held_balance = Column(Numeric(24, 6), default=0)
    currency = Column(String(10), default="USDC")
    
    # Limits
    limit_per_tx = Column(Numeric(24, 6), default=100)
    limit_daily = Column(Numeric(24, 6), default=1000)
    limit_total = Column(Numeric(24, 6), default=10000)
    
    # Daily tracking
    spent_today = Column(Numeric(24, 6), default=0)
    last_reset_date = Column(DateTime, default=datetime.utcnow)
    
    # Blockchain
    on_chain_address = Column(String(42))
    chain = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("AgentDB", back_populates="wallet")
    
    __table_args__ = (
        Index("ix_wallets_chain", "chain"),
    )


# ============ Transaction Model ============

class TransactionDB(Base):
    """Payment transaction record."""
    
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tx_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Parties
    agent_id = Column(String(100), ForeignKey("agents.agent_id"), index=True)
    from_wallet_id = Column(String(100), index=True)
    to_wallet_id = Column(String(100), index=True)
    merchant_id = Column(String(100), ForeignKey("merchants.merchant_id"), index=True)
    
    # Amount
    amount = Column(Numeric(24, 6), nullable=False)
    fee = Column(Numeric(24, 6), default=0)
    currency = Column(String(10), default="USDC")
    
    # Status
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, index=True)
    purpose = Column(Text)
    idempotency_key = Column(String(100), unique=True)
    
    # Blockchain
    on_chain_tx_hash = Column(String(66))
    block_number = Column(Integer)
    chain = Column(String(50))
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    
    # Relationships
    agent = relationship("AgentDB", back_populates="transactions")
    merchant = relationship("MerchantDB", back_populates="transactions")
    
    __table_args__ = (
        Index("ix_transactions_agent_status", "agent_id", "status"),
        Index("ix_transactions_created", "created_at"),
        Index("ix_transactions_chain_block", "chain", "block_number"),
    )


# ============ Ledger Entry Model ============

class LedgerEntryDB(Base):
    """Append-only ledger entry for double-entry bookkeeping."""
    
    __tablename__ = "ledger_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(String(100), unique=True, nullable=False, index=True)
    transaction_id = Column(String(100), index=True)
    
    # Entry details
    entry_type = Column(SQLEnum(LedgerEntryType), nullable=False, index=True)
    account_id = Column(String(100), nullable=False, index=True)
    amount = Column(Numeric(24, 6), nullable=False)
    currency = Column(String(10), default="USDC")
    
    # Balances after this entry
    balance_before = Column(Numeric(24, 6))
    balance_after = Column(Numeric(24, 6))
    
    # Reference
    reference = Column(Text)
    metadata = Column(JSONB)
    
    # Timestamp (immutable)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Checksum for integrity
    checksum = Column(String(64))
    
    __table_args__ = (
        Index("ix_ledger_account_type", "account_id", "entry_type"),
        Index("ix_ledger_created", "created_at"),
        Index("ix_ledger_transaction", "transaction_id"),
    )


# ============ Merchant Model ============

class MerchantDB(Base):
    """Merchant entity that receives payments."""
    
    __tablename__ = "merchants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    
    # Wallet
    wallet_id = Column(String(100))
    on_chain_address = Column(String(42))
    
    # Webhooks
    webhook_url = Column(String(500))
    webhook_secret = Column(String(100))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    risk_score = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = relationship("TransactionDB", back_populates="merchant")
    
    __table_args__ = (
        Index("ix_merchants_category", "category"),
    )


# ============ Hold Model ============

class HoldDB(Base):
    """Pre-authorization hold on funds."""
    
    __tablename__ = "holds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hold_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Parties
    agent_id = Column(String(100), index=True)
    wallet_id = Column(String(100), index=True)
    merchant_id = Column(String(100), index=True)
    
    # Amount
    amount = Column(Numeric(24, 6), nullable=False)
    captured_amount = Column(Numeric(24, 6), default=0)
    currency = Column(String(10), default="USDC")
    
    # Status
    status = Column(SQLEnum(HoldStatus), default=HoldStatus.ACTIVE, index=True)
    purpose = Column(Text)
    
    # Blockchain (if on-chain hold)
    on_chain_hold_id = Column(String(66))
    on_chain_tx_hash = Column(String(66))
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
    captured_at = Column(DateTime)
    voided_at = Column(DateTime)
    
    # Related transaction
    transaction_id = Column(String(100))
    
    __table_args__ = (
        Index("ix_holds_agent_status", "agent_id", "status"),
        Index("ix_holds_expires", "expires_at"),
    )


# ============ Spending Policy Model ============

class SpendingPolicyDB(Base):
    """Spending controls and limits for an agent."""
    
    __tablename__ = "spending_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(String(100), unique=True, nullable=False, index=True)
    agent_id = Column(String(100), ForeignKey("agents.agent_id"), unique=True)
    
    # Limits
    limit_per_tx = Column(Numeric(24, 6), default=100)
    limit_daily = Column(Numeric(24, 6), default=1000)
    limit_weekly = Column(Numeric(24, 6))
    limit_monthly = Column(Numeric(24, 6))
    limit_total = Column(Numeric(24, 6))
    
    # Merchant controls
    allowed_merchants = Column(JSONB, default=list)  # List of merchant IDs
    denied_merchants = Column(JSONB, default=list)
    allowed_categories = Column(JSONB, default=list)
    denied_categories = Column(JSONB, default=list)
    
    # Mode
    use_allowlist = Column(Boolean, default=False)
    
    # Trust
    trust_level = Column(SQLEnum(TrustLevel), default=TrustLevel.NEW)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("AgentDB", back_populates="spending_policy")


# ============ Webhook Model ============

class WebhookDB(Base):
    """Webhook endpoint registration."""
    
    __tablename__ = "webhooks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Target
    url = Column(String(500), nullable=False)
    secret = Column(String(100))
    
    # Events to subscribe
    events = Column(JSONB, default=list)  # List of event types
    
    # Owner
    owner_id = Column(String(100), index=True)
    owner_type = Column(String(50))  # "agent", "merchant", "system"
    
    # Status
    is_active = Column(Boolean, default=True)
    last_delivery_at = Column(DateTime)
    failure_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_webhooks_owner", "owner_id", "owner_type"),
    )


# ============ Webhook Event Model ============

class WebhookEventDB(Base):
    """Record of webhook delivery attempts."""
    
    __tablename__ = "webhook_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(100), unique=True, nullable=False, index=True)
    webhook_id = Column(String(100), ForeignKey("webhooks.webhook_id"), index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB)
    
    # Delivery status
    delivered = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime)
    response_code = Column(Integer)
    response_body = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_webhook_events_type", "event_type"),
        Index("ix_webhook_events_delivered", "delivered"),
    )


# ============ Checkpoint Model ============

class LedgerCheckpointDB(Base):
    """Daily ledger checkpoint for reconciliation."""
    
    __tablename__ = "ledger_checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checkpoint_id = Column(String(100), unique=True, nullable=False)
    
    # Checkpoint data
    checkpoint_date = Column(DateTime, nullable=False, index=True)
    total_entries = Column(Integer)
    total_volume = Column(Numeric(24, 6))
    
    # Account balances at checkpoint
    account_balances = Column(JSONB)  # Dict of account_id -> balance
    
    # Integrity
    checksum = Column(String(64))
    verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("checkpoint_date", name="uq_checkpoint_date"),
    )

