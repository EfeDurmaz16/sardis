"""Sandbox/Playground API endpoints.

No-auth playground for developers to test Sardis features without signup.

Provides:
- Simulated payments with policy enforcement
- Policy testing and preview
- Demo wallet creation (in-memory)
- Virtual card issuance simulation
- Ledger exploration with pre-seeded demo data
- No API keys required, all data ephemeral

Designed for developer acquisition and onboarding.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sardis_v2_core import (
    SpendingPolicy,
    TrustLevel,
    SpendingScope,
    TimeWindowLimit,
    MerchantRule,
    create_default_policy,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# In-Memory Demo Data Store
# ============================================================================

@dataclass
class DemoAgent:
    agent_id: str
    name: str
    trust_level: TrustLevel
    kya_level: int
    created_at: datetime

@dataclass
class DemoWallet:
    wallet_id: str
    agent_id: str
    address: str
    balance: Decimal
    currency: str
    chain: str
    created_at: datetime

@dataclass
class DemoTransaction:
    tx_id: str
    wallet_id: str
    agent_id: str
    amount: Decimal
    merchant: str
    status: str
    policy_result: str
    created_at: datetime
    chain: str = "base_sepolia"
    token: str = "USDC"

@dataclass
class DemoLedgerEntry:
    entry_id: str
    tx_id: str
    agent_id: str
    event_type: str
    amount: Decimal
    merchant: str
    timestamp: datetime
    metadata: dict

@dataclass
class DemoCard:
    card_id: str
    agent_id: str
    last_four: str
    status: str
    spending_limit: Decimal
    created_at: datetime


class SandboxStore:
    """Ephemeral in-memory store for sandbox demo data."""

    def __init__(self):
        self.agents: dict[str, DemoAgent] = {}
        self.wallets: dict[str, DemoWallet] = {}
        self.transactions: list[DemoTransaction] = []
        self.ledger: list[DemoLedgerEntry] = []
        self.cards: dict[str, DemoCard] = {}
        self._seed_demo_data()

    def _seed_demo_data(self):
        """Pre-seed demo data for playground."""
        now = datetime.now(timezone.utc)

        # Create 3 demo agents
        agents_data = [
            ("agent_demo_001", "Marketing AI Agent", TrustLevel.LOW, 0),
            ("agent_demo_002", "Data Analytics Agent", TrustLevel.MEDIUM, 1),
            ("agent_demo_003", "Cloud Ops Agent", TrustLevel.HIGH, 2),
        ]

        for agent_id, name, trust, kya in agents_data:
            self.agents[agent_id] = DemoAgent(
                agent_id=agent_id,
                name=name,
                trust_level=trust,
                kya_level=kya,
                created_at=now - timedelta(days=30),
            )

        # Create wallets for each agent
        for idx, agent_id in enumerate(self.agents.keys()):
            wallet_id = f"wallet_demo_{idx+1:03d}"
            self.wallets[wallet_id] = DemoWallet(
                wallet_id=wallet_id,
                agent_id=agent_id,
                address=f"0x{uuid.uuid4().hex[:40]}",
                balance=Decimal("1000.00") * (idx + 1),
                currency="USDC",
                chain="base_sepolia",
                created_at=now - timedelta(days=30),
            )

        # Create 10 demo transactions
        merchants = [
            "OpenAI API", "AWS Compute", "Stripe Payment",
            "Google Cloud", "Anthropic API", "GitHub Premium",
            "Vercel Hosting", "MongoDB Atlas", "Sendgrid Email",
            "Cloudflare CDN"
        ]

        for i in range(10):
            wallet_id = list(self.wallets.keys())[i % 3]
            wallet = self.wallets[wallet_id]
            tx_id = f"tx_demo_{i+1:03d}"
            amount = Decimal("50.00") * (i + 1)
            merchant = merchants[i]

            tx = DemoTransaction(
                tx_id=tx_id,
                wallet_id=wallet_id,
                agent_id=wallet.agent_id,
                amount=amount,
                merchant=merchant,
                status="completed" if i % 5 != 4 else "denied",
                policy_result="approved" if i % 5 != 4 else "per_transaction_limit",
                created_at=now - timedelta(days=30-i),
            )
            self.transactions.append(tx)

            # Create ledger entry
            self.ledger.append(DemoLedgerEntry(
                entry_id=f"ledger_{i+1:03d}",
                tx_id=tx_id,
                agent_id=wallet.agent_id,
                event_type="payment_executed" if tx.status == "completed" else "payment_denied",
                amount=amount,
                merchant=merchant,
                timestamp=tx.created_at,
                metadata={
                    "policy_result": tx.policy_result,
                    "chain": tx.chain,
                    "token": tx.token,
                },
            ))

        # Create 2 demo cards
        for idx, agent_id in enumerate(list(self.agents.keys())[:2]):
            card_id = f"card_demo_{idx+1:03d}"
            self.cards[card_id] = DemoCard(
                card_id=card_id,
                agent_id=agent_id,
                last_four=f"{1000 + idx:04d}",
                status="active",
                spending_limit=Decimal("500.00"),
                created_at=now - timedelta(days=20),
            )

# Global sandbox store (ephemeral, resets on server restart)
_sandbox_store = SandboxStore()


# ============================================================================
# Request/Response Models
# ============================================================================

class SandboxPaymentRequest(BaseModel):
    """Request to simulate a payment."""
    agent_id: str = Field(default="agent_demo_001", description="Agent ID (use demo agent or create new)")
    amount: Decimal = Field(..., gt=0, description="Payment amount in USD")
    merchant: str = Field(..., description="Merchant name or domain")
    merchant_category: Optional[str] = Field(default=None, description="e.g., 'cloud', 'api', 'saas'")
    chain: str = Field(default="base_sepolia", description="Blockchain to simulate on")
    token: str = Field(default="USDC", description="Token to use")


class SandboxPaymentResponse(BaseModel):
    """Response from simulated payment."""
    success: bool
    tx_id: str
    amount: str
    merchant: str
    policy_result: str
    policy_reason: Optional[str] = None
    ledger_entry_id: Optional[str] = None
    simulated: bool = True


class PolicyCheckRequest(BaseModel):
    """Request to check if a payment would pass policy."""
    agent_id: str = Field(default="agent_demo_002", description="Agent ID")
    amount: Decimal = Field(..., gt=0)
    merchant: str
    policy_nl: Optional[str] = Field(
        default=None,
        description="Natural language policy to test (if not using agent's default)",
    )


class PolicyCheckResponse(BaseModel):
    """Response from policy check."""
    would_allow: bool
    reason: str
    policy_summary: str
    trust_level: str
    limits_summary: dict


class CreateDemoWalletRequest(BaseModel):
    """Request to create a demo wallet."""
    agent_id: Optional[str] = Field(default=None, description="Agent ID (auto-generated if not provided)")
    agent_name: Optional[str] = Field(default="Demo Agent", description="Agent display name")
    initial_balance: Decimal = Field(default=Decimal("100.00"), description="Initial testnet balance")
    trust_level: TrustLevel = Field(default=TrustLevel.MEDIUM)


class CreateDemoWalletResponse(BaseModel):
    """Response from wallet creation."""
    agent_id: str
    wallet_id: str
    address: str
    balance: str
    currency: str
    trust_level: str
    policy_summary: str


class IssueDemoCardRequest(BaseModel):
    """Request to issue a virtual card."""
    agent_id: str = Field(default="agent_demo_001")
    spending_limit: Decimal = Field(default=Decimal("500.00"))


class IssueDemoCardResponse(BaseModel):
    """Response from card issuance."""
    card_id: str
    agent_id: str
    last_four: str
    status: str
    spending_limit: str
    created_at: str


class DemoDataResponse(BaseModel):
    """All demo data for the playground."""
    agents: List[dict]
    wallets: List[dict]
    transactions: List[dict]
    cards: List[dict]


class LedgerEntryResponse(BaseModel):
    """A single ledger entry."""
    entry_id: str
    tx_id: str
    agent_id: str
    event_type: str
    amount: str
    merchant: str
    timestamp: str
    metadata: dict


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/payment", response_model=SandboxPaymentResponse, tags=["Sandbox"])
async def sandbox_payment(req: SandboxPaymentRequest):
    """
    Simulate a payment with policy enforcement.

    This endpoint demonstrates how Sardis enforces spending policies on payments.
    The payment is not real - no blockchain transaction occurs - but the policy
    evaluation logic is identical to production.

    Try different amounts and merchants to see how policies work!
    """
    # Get or create agent
    agent = _sandbox_store.agents.get(req.agent_id)
    if not agent:
        # Create ephemeral agent
        agent = DemoAgent(
            agent_id=req.agent_id,
            name="Sandbox Agent",
            trust_level=TrustLevel.MEDIUM,
            kya_level=1,
            created_at=datetime.now(timezone.utc),
        )
        _sandbox_store.agents[req.agent_id] = agent

    # Get or create wallet
    wallet = next(
        (w for w in _sandbox_store.wallets.values() if w.agent_id == req.agent_id),
        None
    )
    if not wallet:
        wallet = DemoWallet(
            wallet_id=f"wallet_{uuid.uuid4().hex[:8]}",
            agent_id=req.agent_id,
            address=f"0x{uuid.uuid4().hex[:40]}",
            balance=Decimal("1000.00"),
            currency="USDC",
            chain=req.chain,
            created_at=datetime.now(timezone.utc),
        )
        _sandbox_store.wallets[wallet.wallet_id] = wallet

    # Create policy for agent
    policy = create_default_policy(agent.trust_level)

    # Simulate policy evaluation
    policy_result = "approved"
    policy_reason = None
    success = True

    # Check amount validation
    if req.amount <= 0:
        policy_result = "invalid_amount"
        policy_reason = "Amount must be positive"
        success = False

    # Check per-transaction limit
    elif policy.limit_per_transaction and req.amount > policy.limit_per_transaction:
        policy_result = "per_transaction_limit"
        policy_reason = f"Exceeds per-transaction limit of ${policy.limit_per_transaction}"
        success = False

    # Check balance
    elif wallet.balance < req.amount:
        policy_result = "insufficient_balance"
        policy_reason = f"Wallet balance ${wallet.balance} < payment ${req.amount}"
        success = False

    # Check approval threshold
    elif policy.approval_threshold and req.amount >= policy.approval_threshold:
        policy_result = "requires_approval"
        policy_reason = f"Amount >= approval threshold of ${policy.approval_threshold}"
        success = True  # Still succeeds, but needs approval

    # Create transaction record
    tx_id = f"tx_{uuid.uuid4().hex[:8]}"
    tx = DemoTransaction(
        tx_id=tx_id,
        wallet_id=wallet.wallet_id,
        agent_id=req.agent_id,
        amount=req.amount,
        merchant=req.merchant,
        status="completed" if success and policy_result != "requires_approval" else "denied",
        policy_result=policy_result,
        created_at=datetime.now(timezone.utc),
        chain=req.chain,
        token=req.token,
    )
    _sandbox_store.transactions.append(tx)

    # Create ledger entry
    ledger_entry_id = f"ledger_{uuid.uuid4().hex[:8]}"
    ledger_entry = DemoLedgerEntry(
        entry_id=ledger_entry_id,
        tx_id=tx_id,
        agent_id=req.agent_id,
        event_type="payment_executed" if success else "payment_denied",
        amount=req.amount,
        merchant=req.merchant,
        timestamp=datetime.now(timezone.utc),
        metadata={
            "policy_result": policy_result,
            "policy_reason": policy_reason or "OK",
            "chain": req.chain,
            "token": req.token,
        },
    )
    _sandbox_store.ledger.append(ledger_entry)

    # Deduct from wallet if successful
    if success and policy_result == "approved":
        wallet.balance -= req.amount

    return SandboxPaymentResponse(
        success=success,
        tx_id=tx_id,
        amount=str(req.amount),
        merchant=req.merchant,
        policy_result=policy_result,
        policy_reason=policy_reason,
        ledger_entry_id=ledger_entry_id,
    )


@router.post("/policy-check", response_model=PolicyCheckResponse, tags=["Sandbox"])
async def sandbox_policy_check(req: PolicyCheckRequest):
    """
    Test if a hypothetical payment would pass policy.

    This is a dry-run - no payment is executed, but you can see exactly
    what would happen if the agent tried to make this payment.
    """
    agent = _sandbox_store.agents.get(req.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {req.agent_id} not found. Use /sandbox/demo-data to see available agents.",
        )

    # Create policy
    policy = create_default_policy(agent.trust_level)

    # Evaluate
    would_allow = True
    reason = "OK - payment would be allowed"

    if req.amount <= 0:
        would_allow = False
        reason = "Amount must be positive"
    elif policy.limit_per_transaction and req.amount > policy.limit_per_transaction:
        would_allow = False
        reason = f"Exceeds per-transaction limit of ${policy.limit_per_transaction}"
    elif policy.approval_threshold and req.amount >= policy.approval_threshold:
        reason = f"Would require approval (amount >= ${policy.approval_threshold})"

    # Build summary
    limits = {
        "per_transaction": str(policy.limit_per_transaction) if policy.limit_per_transaction else "unlimited",
        "total_lifetime": str(policy.limit_total) if policy.limit_total else "unlimited",
        "approval_threshold": str(policy.approval_threshold) if policy.approval_threshold else "none",
    }

    if policy.time_windows:
        for tw in policy.time_windows:
            limits[f"{tw.period}_limit"] = str(tw.max_amount)

    policy_summary = f"Trust Level: {agent.trust_level.value} | KYA Level: {agent.kya_level}"

    return PolicyCheckResponse(
        would_allow=would_allow,
        reason=reason,
        policy_summary=policy_summary,
        trust_level=agent.trust_level.value,
        limits_summary=limits,
    )


@router.post("/create-wallet", response_model=CreateDemoWalletResponse, tags=["Sandbox"])
async def sandbox_create_wallet(req: CreateDemoWalletRequest):
    """
    Create a demo wallet with simulated testnet funds.

    This wallet is ephemeral (in-memory only) and disappears on server restart.
    Perfect for testing the SDK and understanding wallet creation flow.
    """
    # Generate IDs
    agent_id = req.agent_id or f"agent_{uuid.uuid4().hex[:8]}"
    wallet_id = f"wallet_{uuid.uuid4().hex[:8]}"
    address = f"0x{uuid.uuid4().hex[:40]}"

    # Create agent if new
    if agent_id not in _sandbox_store.agents:
        _sandbox_store.agents[agent_id] = DemoAgent(
            agent_id=agent_id,
            name=req.agent_name or "Demo Agent",
            trust_level=req.trust_level,
            kya_level=0 if req.trust_level == TrustLevel.LOW else 1,
            created_at=datetime.now(timezone.utc),
        )

    # Create wallet
    wallet = DemoWallet(
        wallet_id=wallet_id,
        agent_id=agent_id,
        address=address,
        balance=req.initial_balance,
        currency="USDC",
        chain="base_sepolia",
        created_at=datetime.now(timezone.utc),
    )
    _sandbox_store.wallets[wallet_id] = wallet

    # Build policy summary
    policy = create_default_policy(req.trust_level)
    policy_summary = f"Per-tx: ${policy.limit_per_transaction or 'unlimited'}, Total: ${policy.limit_total or 'unlimited'}"

    logger.info(f"Created sandbox wallet: {wallet_id} for agent {agent_id}")

    return CreateDemoWalletResponse(
        agent_id=agent_id,
        wallet_id=wallet_id,
        address=address,
        balance=str(req.initial_balance),
        currency="USDC",
        trust_level=req.trust_level.value,
        policy_summary=policy_summary,
    )


@router.post("/issue-card", response_model=IssueDemoCardResponse, tags=["Sandbox"])
async def sandbox_issue_card(req: IssueDemoCardRequest):
    """
    Simulate virtual card issuance.

    This demonstrates how Sardis can issue virtual cards for AI agents.
    The card is simulated - no real Lithic/Stripe card is created.
    """
    agent = _sandbox_store.agents.get(req.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {req.agent_id} not found",
        )

    # Generate card
    card_id = f"card_{uuid.uuid4().hex[:8]}"
    last_four = f"{len(_sandbox_store.cards) + 1234:04d}"

    card = DemoCard(
        card_id=card_id,
        agent_id=req.agent_id,
        last_four=last_four,
        status="active",
        spending_limit=req.spending_limit,
        created_at=datetime.now(timezone.utc),
    )
    _sandbox_store.cards[card_id] = card

    logger.info(f"Issued sandbox card: {card_id} for agent {req.agent_id}")

    return IssueDemoCardResponse(
        card_id=card_id,
        agent_id=req.agent_id,
        last_four=last_four,
        status="active",
        spending_limit=str(req.spending_limit),
        created_at=card.created_at.isoformat(),
    )


@router.get("/demo-data", response_model=DemoDataResponse, tags=["Sandbox"])
async def sandbox_demo_data():
    """
    Get all pre-seeded demo data.

    Returns agents, wallets, transactions, and cards that you can use
    to explore the playground without creating your own data.
    """
    agents = [
        {
            "agent_id": a.agent_id,
            "name": a.name,
            "trust_level": a.trust_level.value,
            "kya_level": a.kya_level,
            "created_at": a.created_at.isoformat(),
        }
        for a in _sandbox_store.agents.values()
    ]

    wallets = [
        {
            "wallet_id": w.wallet_id,
            "agent_id": w.agent_id,
            "address": w.address,
            "balance": str(w.balance),
            "currency": w.currency,
            "chain": w.chain,
            "created_at": w.created_at.isoformat(),
        }
        for w in _sandbox_store.wallets.values()
    ]

    transactions = [
        {
            "tx_id": t.tx_id,
            "agent_id": t.agent_id,
            "amount": str(t.amount),
            "merchant": t.merchant,
            "status": t.status,
            "policy_result": t.policy_result,
            "chain": t.chain,
            "token": t.token,
            "created_at": t.created_at.isoformat(),
        }
        for t in _sandbox_store.transactions
    ]

    cards = [
        {
            "card_id": c.card_id,
            "agent_id": c.agent_id,
            "last_four": c.last_four,
            "status": c.status,
            "spending_limit": str(c.spending_limit),
            "created_at": c.created_at.isoformat(),
        }
        for c in _sandbox_store.cards.values()
    ]

    return DemoDataResponse(
        agents=agents,
        wallets=wallets,
        transactions=transactions,
        cards=cards,
    )


@router.get("/ledger", response_model=List[LedgerEntryResponse], tags=["Sandbox"])
async def sandbox_ledger(
    agent_id: Optional[str] = None,
    limit: int = 50,
):
    """
    View the demo ledger (audit trail).

    Shows all payment events with full context. Filter by agent_id to see
    one agent's activity, or leave blank to see everything.
    """
    entries = _sandbox_store.ledger

    if agent_id:
        entries = [e for e in entries if e.agent_id == agent_id]

    # Sort by timestamp descending
    entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)

    # Apply limit
    entries = entries[:limit]

    return [
        LedgerEntryResponse(
            entry_id=e.entry_id,
            tx_id=e.tx_id,
            agent_id=e.agent_id,
            event_type=e.event_type,
            amount=str(e.amount),
            merchant=e.merchant,
            timestamp=e.timestamp.isoformat(),
            metadata=e.metadata,
        )
        for e in entries
    ]


@router.delete("/reset", tags=["Sandbox"])
async def sandbox_reset():
    """
    Reset all sandbox data to initial state.

    Useful for starting fresh or after testing destructive operations.
    """
    global _sandbox_store
    _sandbox_store = SandboxStore()
    logger.info("Sandbox data reset to initial state")
    return {"status": "reset", "message": "Sandbox data has been reset to demo seed state"}
