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

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sardis_v2_core import (
    TrustLevel,
    create_default_policy,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# Constants
# ============================================================================

DEMO_NAMESPACE = "__demo__"
MAX_NAMESPACES = 1000
NAMESPACE_TTL_HOURS = 24
RATE_LIMIT_MAX = 60
RATE_LIMIT_WINDOW_SECONDS = 60

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
        self.created_at: datetime = datetime.now(UTC)
        self.last_accessed: datetime = datetime.now(UTC)
        self._seed_demo_data()

    def touch(self) -> None:
        """Update last_accessed timestamp."""
        self.last_accessed = datetime.now(UTC)

    def is_expired(self) -> bool:
        """Return True if the store has not been accessed within TTL."""
        return datetime.now(UTC) - self.last_accessed > timedelta(hours=NAMESPACE_TTL_HOURS)

    def _seed_demo_data(self):
        """Pre-seed demo data for playground."""
        now = datetime.now(UTC)

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


# ============================================================================
# SandboxStoreManager — per-namespace isolation with LRU eviction
# ============================================================================

class SandboxStoreManager:
    """Manages per-namespace SandboxStore instances with LRU eviction and rate limiting."""

    def __init__(self) -> None:
        self._stores: dict[str, SandboxStore] = {}
        # namespace -> list of request timestamps (float, epoch seconds)
        self._rate_limits: dict[str, list[float]] = {}

    def get_store(self, namespace: str) -> SandboxStore:
        """Return the SandboxStore for *namespace*, creating it if needed.

        Evicts expired stores and enforces the MAX_NAMESPACES cap before
        creating a new store.
        """
        self._evict_expired()

        if namespace not in self._stores:
            if len(self._stores) >= MAX_NAMESPACES:
                self._evict_lru()
            self._stores[namespace] = SandboxStore()
            # Only initialise rate-limit tracking if not already present (e.g.
            # check_rate_limit may have already seeded it for this namespace).
            if namespace not in self._rate_limits:
                self._rate_limits[namespace] = []

        store = self._stores[namespace]
        store.touch()
        return store

    def reset_namespace(self, namespace: str) -> None:
        """Replace the store for *namespace* with a fresh seeded instance."""
        self._stores[namespace] = SandboxStore()
        self._rate_limits[namespace] = []

    def check_rate_limit(self, namespace: str) -> bool:
        """Return True if request is allowed, False if rate limit exceeded.

        Allows up to RATE_LIMIT_MAX requests per RATE_LIMIT_WINDOW_SECONDS.
        """
        now = time.monotonic()
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        timestamps = self._rate_limits.get(namespace, [])
        # Drop timestamps outside the window
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= RATE_LIMIT_MAX:
            self._rate_limits[namespace] = timestamps
            return False
        timestamps.append(now)
        self._rate_limits[namespace] = timestamps
        return True

    # ------------------------------------------------------------------
    # Internal eviction helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        """Remove stores that have not been accessed within their TTL."""
        expired = [ns for ns, store in self._stores.items() if store.is_expired()]
        for ns in expired:
            del self._stores[ns]
            self._rate_limits.pop(ns, None)

    def _evict_lru(self) -> None:
        """Remove the least-recently-used namespace to make room."""
        if not self._stores:
            return
        lru_ns = min(self._stores, key=lambda ns: self._stores[ns].last_accessed)
        del self._stores[lru_ns]
        self._rate_limits.pop(lru_ns, None)


# Module-level manager (replaces the old global _sandbox_store)
_manager = SandboxStoreManager()


# ============================================================================
# Namespace helpers
# ============================================================================

def _get_namespace_from_request(request: Request) -> str:
    """Extract namespace from auth header if present, else return demo namespace.

    Uses a truncated SHA-256 of the raw token so we never store credentials.
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return f"ns_{hashlib.sha256(token.encode()).hexdigest()[:16]}"
    return DEMO_NAMESPACE


def _get_store_for_request(request: Request) -> SandboxStore:
    """Resolve the namespace, enforce rate limit, return the store."""
    namespace = _get_namespace_from_request(request)
    if not _manager.check_rate_limit(namespace):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: max 60 sandbox requests per minute per namespace.",
        )
    return _manager.get_store(namespace)


# ============================================================================
# Request/Response Models
# ============================================================================

class SandboxPaymentRequest(BaseModel):
    """Request to simulate a payment."""
    agent_id: str = Field(default="agent_demo_001", description="Agent ID (use demo agent or create new)")
    amount: Decimal = Field(..., gt=0, description="Payment amount in USD")
    merchant: str = Field(..., description="Merchant name or domain")
    merchant_category: str | None = Field(default=None, description="e.g., 'cloud', 'api', 'saas'")
    chain: str = Field(default="base_sepolia", description="Blockchain to simulate on")
    token: str = Field(default="USDC", description="Token to use")


class SandboxPaymentResponse(BaseModel):
    """Response from simulated payment."""
    success: bool
    tx_id: str
    amount: str
    merchant: str
    policy_result: str
    policy_reason: str | None = None
    ledger_entry_id: str | None = None
    simulated: bool = True


class PolicyCheckRequest(BaseModel):
    """Request to check if a payment would pass policy."""
    agent_id: str = Field(default="agent_demo_002", description="Agent ID")
    amount: Decimal = Field(..., gt=0)
    merchant: str
    policy_nl: str | None = Field(
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
    agent_id: str | None = Field(default=None, description="Agent ID (auto-generated if not provided)")
    agent_name: str | None = Field(default="Demo Agent", description="Agent display name")
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
    agents: list[dict]
    wallets: list[dict]
    transactions: list[dict]
    cards: list[dict]


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
async def sandbox_payment(req: SandboxPaymentRequest, request: Request):
    """
    Simulate a payment with policy enforcement.

    This endpoint demonstrates how Sardis enforces spending policies on payments.
    The payment is not real - no blockchain transaction occurs - but the policy
    evaluation logic is identical to production.

    Try different amounts and merchants to see how policies work!
    """
    store = _get_store_for_request(request)

    # Get or create agent
    agent = store.agents.get(req.agent_id)
    if not agent:
        # Create ephemeral agent
        agent = DemoAgent(
            agent_id=req.agent_id,
            name="Sandbox Agent",
            trust_level=TrustLevel.MEDIUM,
            kya_level=1,
            created_at=datetime.now(UTC),
        )
        store.agents[req.agent_id] = agent

    # Get or create wallet
    wallet = next(
        (w for w in store.wallets.values() if w.agent_id == req.agent_id),
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
            created_at=datetime.now(UTC),
        )
        store.wallets[wallet.wallet_id] = wallet

    # Create policy for agent
    policy = create_default_policy(agent.agent_id, agent.trust_level)

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
    elif policy.limit_per_tx and req.amount > policy.limit_per_tx:
        policy_result = "per_transaction_limit"
        policy_reason = f"Exceeds per-transaction limit of ${policy.limit_per_tx}"
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
        created_at=datetime.now(UTC),
        chain=req.chain,
        token=req.token,
    )
    store.transactions.append(tx)

    # Create ledger entry
    ledger_entry_id = f"ledger_{uuid.uuid4().hex[:8]}"
    ledger_entry = DemoLedgerEntry(
        entry_id=ledger_entry_id,
        tx_id=tx_id,
        agent_id=req.agent_id,
        event_type="payment_executed" if success else "payment_denied",
        amount=req.amount,
        merchant=req.merchant,
        timestamp=datetime.now(UTC),
        metadata={
            "policy_result": policy_result,
            "policy_reason": policy_reason or "OK",
            "chain": req.chain,
            "token": req.token,
        },
    )
    store.ledger.append(ledger_entry)

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
async def sandbox_policy_check(req: PolicyCheckRequest, request: Request):
    """
    Test if a hypothetical payment would pass policy.

    This is a dry-run - no payment is executed, but you can see exactly
    what would happen if the agent tried to make this payment.
    """
    store = _get_store_for_request(request)

    agent = store.agents.get(req.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {req.agent_id} not found. Use /sandbox/demo-data to see available agents.",
        )

    # Create policy
    policy = create_default_policy(agent.agent_id, agent.trust_level)

    # Evaluate
    would_allow = True
    reason = "OK - payment would be allowed"

    if req.amount <= 0:
        would_allow = False
        reason = "Amount must be positive"
    elif policy.limit_per_tx and req.amount > policy.limit_per_tx:
        would_allow = False
        reason = f"Exceeds per-transaction limit of ${policy.limit_per_tx}"
    elif policy.approval_threshold and req.amount >= policy.approval_threshold:
        reason = f"Would require approval (amount >= ${policy.approval_threshold})"

    # Build summary
    limits = {
        "per_transaction": str(policy.limit_per_tx) if policy.limit_per_tx else "unlimited",
        "total_lifetime": str(policy.limit_total) if policy.limit_total else "unlimited",
        "approval_threshold": str(policy.approval_threshold) if policy.approval_threshold else "none",
    }

    if hasattr(policy, 'daily_limit') and policy.daily_limit:
        limits["daily_limit"] = str(policy.daily_limit.limit_amount)
    if hasattr(policy, 'weekly_limit') and policy.weekly_limit:
        limits["weekly_limit"] = str(policy.weekly_limit.limit_amount)
    if hasattr(policy, 'monthly_limit') and policy.monthly_limit:
        limits["monthly_limit"] = str(policy.monthly_limit.limit_amount)

    policy_summary = f"Trust Level: {agent.trust_level.value} | KYA Level: {agent.kya_level}"

    return PolicyCheckResponse(
        would_allow=would_allow,
        reason=reason,
        policy_summary=policy_summary,
        trust_level=agent.trust_level.value,
        limits_summary=limits,
    )


@router.post("/create-wallet", response_model=CreateDemoWalletResponse, tags=["Sandbox"])
async def sandbox_create_wallet(req: CreateDemoWalletRequest, request: Request):
    """
    Create a demo wallet with simulated testnet funds.

    This wallet is ephemeral (in-memory only) and disappears on server restart.
    Perfect for testing the SDK and understanding wallet creation flow.
    """
    store = _get_store_for_request(request)

    # Generate IDs
    agent_id = req.agent_id or f"agent_{uuid.uuid4().hex[:8]}"
    wallet_id = f"wallet_{uuid.uuid4().hex[:8]}"
    address = f"0x{uuid.uuid4().hex[:40]}"

    # Create agent if new
    if agent_id not in store.agents:
        store.agents[agent_id] = DemoAgent(
            agent_id=agent_id,
            name=req.agent_name or "Demo Agent",
            trust_level=req.trust_level,
            kya_level=0 if req.trust_level == TrustLevel.LOW else 1,
            created_at=datetime.now(UTC),
        )

    # Create wallet
    wallet = DemoWallet(
        wallet_id=wallet_id,
        agent_id=agent_id,
        address=address,
        balance=req.initial_balance,
        currency="USDC",
        chain="base_sepolia",
        created_at=datetime.now(UTC),
    )
    store.wallets[wallet_id] = wallet

    # Build policy summary
    policy = create_default_policy(agent_id, req.trust_level)
    policy_summary = f"Per-tx: ${policy.limit_per_tx or 'unlimited'}, Total: ${policy.limit_total or 'unlimited'}"

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
async def sandbox_issue_card(req: IssueDemoCardRequest, request: Request):
    """
    Simulate virtual card issuance.

    This demonstrates how Sardis can issue virtual cards for AI agents.
    The card is simulated - no real Lithic/Stripe card is created.
    """
    store = _get_store_for_request(request)

    agent = store.agents.get(req.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {req.agent_id} not found",
        )

    # Generate card
    card_id = f"card_{uuid.uuid4().hex[:8]}"
    last_four = f"{len(store.cards) + 1234:04d}"

    card = DemoCard(
        card_id=card_id,
        agent_id=req.agent_id,
        last_four=last_four,
        status="active",
        spending_limit=req.spending_limit,
        created_at=datetime.now(UTC),
    )
    store.cards[card_id] = card

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
async def sandbox_demo_data(request: Request):
    """
    Get all pre-seeded demo data.

    Returns agents, wallets, transactions, and cards that you can use
    to explore the playground without creating your own data.
    """
    store = _get_store_for_request(request)

    agents = [
        {
            "agent_id": a.agent_id,
            "name": a.name,
            "trust_level": a.trust_level.value,
            "kya_level": a.kya_level,
            "created_at": a.created_at.isoformat(),
        }
        for a in store.agents.values()
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
        for w in store.wallets.values()
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
        for t in store.transactions
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
        for c in store.cards.values()
    ]

    return DemoDataResponse(
        agents=agents,
        wallets=wallets,
        transactions=transactions,
        cards=cards,
    )


@router.get("/ledger", response_model=list[LedgerEntryResponse], tags=["Sandbox"])
async def sandbox_ledger(
    request: Request,
    agent_id: str | None = None,
    limit: int = 50,
):
    """
    View the demo ledger (audit trail).

    Shows all payment events with full context. Filter by agent_id to see
    one agent's activity, or leave blank to see everything.
    """
    store = _get_store_for_request(request)
    entries = store.ledger

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
@router.post("/reset", tags=["Sandbox"])
async def sandbox_reset(request: Request):
    """
    Reset sandbox data to initial state.

    When authenticated, only resets the caller's isolated namespace.
    When unauthenticated, resets the shared demo namespace.

    Useful for starting fresh or after testing destructive operations.
    """
    namespace = _get_namespace_from_request(request)
    _manager.reset_namespace(namespace)
    logger.info(f"Sandbox namespace '{namespace}' reset to initial state")
    return {"status": "reset", "message": "Sandbox data has been reset to demo seed state"}
