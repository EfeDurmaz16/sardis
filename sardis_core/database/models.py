from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, Numeric, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DBOrganization(Base):
    """Organization database model."""
    __tablename__ = "organizations"

    org_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    admin_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agents: Mapped[List["DBAgent"]] = relationship(back_populates="organization")


class DBAgent(Base):
    """Agent database model."""
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[str] = mapped_column(String, nullable=False)
    organization_id: Mapped[Optional[str]] = mapped_column(ForeignKey("organizations.org_id"), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wallet_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Linked manually or via relationship
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization: Mapped[Optional["DBOrganization"]] = relationship(back_populates="agents")
    wallet: Mapped[Optional["DBWallet"]] = relationship(back_populates="agent", uselist=False)


class DBWallet(Base):
    """Wallet database model."""
    __tablename__ = "wallets"

    wallet_id: Mapped[str] = mapped_column(String, primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.agent_id"), nullable=False)
    
    # Balances (stored as JSON for multi-token support)
    # Structure: {"USDC": "100.00", "ETH": "1.5"}
    balances: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Primary currency settings
    currency: Mapped[str] = mapped_column(String, default="USDC")
    
    # Limits
    limit_per_tx: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), default=0)
    limit_total: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), default=0)
    spent_total: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), default=0)
    
    # Virtual Card (stored as JSON)
    virtual_card: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent: Mapped["DBAgent"] = relationship(back_populates="wallet")


class DBTransaction(Base):
    """Transaction database model."""
    __tablename__ = "transactions"

    tx_id: Mapped[str] = mapped_column(String, primary_key=True)
    from_wallet: Mapped[str] = mapped_column(String, nullable=False, index=True)
    to_wallet: Mapped[str] = mapped_column(String, nullable=False, index=True)
    
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), default=0)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    
    purpose: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # pending, completed, failed
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
