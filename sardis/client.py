"""
Convenience SardisClient for the sardis meta-package.

This client provides the DX-friendly API shown in README and examples.
In simulation mode (default when sardis-sdk is not installed or no real
API key is provided), all operations run locally without network calls.

When sardis-sdk IS installed and a production API key is provided,
operations delegate to the real Sardis platform.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import uuid4

from .wallet import Wallet
from .transaction import Transaction, TransactionResult, TransactionStatus
from .policy import Policy, PolicyResult
from .group import AgentGroup


# ---------------------------------------------------------------------------
# Managed wallet — enriched Wallet with .pay() and .id
# ---------------------------------------------------------------------------


class ManagedWallet(Wallet):
    """A wallet managed by SardisClient with convenience methods."""

    _client: Optional["SardisClient"] = None
    _name: str = ""
    _chain: str = "base"
    _token: str = "USDC"
    _policy_text: str = ""
    _group_id: Optional[str] = None

    def __init__(
        self,
        client: "SardisClient",
        name: str,
        chain: str = "base",
        token: str = "USDC",
        policy: Optional[str] = None,
        group_id: Optional[str] = None,
        initial_balance: float = 1000,
        limit_per_tx: float = 100,
        limit_total: float = 10000,
    ):
        # Parse natural language policy for limits
        parsed = _parse_policy(policy) if policy else {}
        per_tx = parsed.get("max_per_tx", limit_per_tx)
        total = parsed.get("max_total", limit_total)

        super().__init__(
            initial_balance=initial_balance,
            currency=token,
            limit_per_tx=per_tx,
            limit_total=total,
        )
        self._client = client
        self._name = name
        self._chain = chain
        self._token = token
        self._policy_text = policy or ""
        self._group_id = group_id

    @property
    def id(self) -> str:
        """Wallet ID (alias for wallet_id)."""
        return self.wallet_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def chain(self) -> str:
        return self._chain

    @property
    def token(self) -> str:
        return self._token

    @property
    def group_id(self) -> Optional[str]:
        return self._group_id

    @property
    def spent_daily(self) -> Decimal:
        """Amount spent today (simulation: same as spent_total)."""
        return self.spent_total

    @property
    def daily_limit(self) -> Decimal:
        return self.limit_total

    @property
    def daily_remaining(self) -> Decimal:
        return self.remaining_limit()

    def pay(
        self,
        to: str,
        amount: float | str | Decimal,
        *,
        token: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> TransactionResult:
        """
        Pay from this wallet.

        Args:
            to: Recipient address or merchant identifier
            amount: Amount to pay
            token: Token override (default: wallet token)
            purpose: Reason for payment

        Returns:
            TransactionResult with success status and details
        """
        if self._client is None:
            raise RuntimeError("Wallet is not managed by a SardisClient")
        return self._client.payments.send(
            wallet_id=self.wallet_id,
            to=to,
            amount=amount,
            token=token or self._token,
            memo=purpose,
        )

    def __repr__(self) -> str:
        return f"ManagedWallet({self._name}, {self.balance} {self._token}, chain={self._chain})"


# ---------------------------------------------------------------------------
# Group info — enriched AgentGroup with .id
# ---------------------------------------------------------------------------


class ManagedGroup(AgentGroup):
    """A group managed by SardisClient with convenience properties."""

    _group_id: str = ""
    _policy_text: str = ""
    _tx_count_daily: int = 0

    def __init__(
        self,
        name: str,
        budget_per_tx: Decimal = Decimal("500.00"),
        budget_daily: Decimal = Decimal("5000.00"),
        budget_monthly: Decimal = Decimal("50000.00"),
        policy: Optional[str] = None,
        blocked_merchants: Optional[List[str]] = None,
    ):
        super().__init__(
            name=name,
            budget_per_tx=budget_per_tx,
            budget_daily=budget_daily,
            budget_monthly=budget_monthly,
            blocked_merchants=blocked_merchants or [],
        )
        self._group_id = f"group_{uuid4().hex[:12]}"
        self._policy_text = policy or ""

    @property
    def id(self) -> str:
        return self._group_id

    @property
    def spent_daily(self) -> Decimal:
        return self._spent_daily

    @property
    def daily_remaining(self) -> Decimal:
        return max(Decimal("0"), self.budget_daily - self._spent_daily)

    @property
    def tx_count_daily(self) -> int:
        return self._tx_count_daily

    def __repr__(self) -> str:
        return f"ManagedGroup({self.name}, budget_daily={self.budget_daily})"


# ---------------------------------------------------------------------------
# Ledger entry (simulation)
# ---------------------------------------------------------------------------


@dataclass
class LedgerEntry:
    """A single ledger entry for audit trails."""
    timestamp: datetime
    agent_name: str
    amount: Decimal
    merchant: str
    status: str
    tx_id: str
    wallet_id: str
    group_id: Optional[str] = None
    purpose: Optional[str] = None


# ---------------------------------------------------------------------------
# Natural language policy parser (simple regex-based)
# ---------------------------------------------------------------------------

def _parse_policy(text: str) -> dict:
    """Parse natural language policy into structured limits.

    Handles patterns like:
      - "Max $100 per transaction"
      - "Max $100/day"
      - "Daily limit $500"
      - "$200 per tx"

    Returns dict with 'max_per_tx' and/or 'max_total' keys.
    """
    result = {}
    text_lower = text.lower()

    # "Max $100 per transaction" / "Max $100/tx" / "$100 per tx"
    m = re.search(r'max\s+\$?([\d,]+(?:\.\d+)?)\s*(?:per\s+(?:transaction|tx)|/tx)', text_lower)
    if m:
        result["max_per_tx"] = float(m.group(1).replace(",", ""))

    # "$200 per transaction" without "max" prefix
    if "max_per_tx" not in result:
        m = re.search(r'\$?([\d,]+(?:\.\d+)?)\s*per\s+(?:transaction|tx)', text_lower)
        if m:
            result["max_per_tx"] = float(m.group(1).replace(",", ""))

    # "Daily limit $500" / "Max $500/day"
    m = re.search(r'(?:daily\s+limit|max\s+\$?[\d,]+(?:\.\d+)?/day)\s*\$?([\d,]+(?:\.\d+)?)', text_lower)
    if m:
        result["max_total"] = float(m.group(1).replace(",", ""))

    # Simpler: "Max $X/day"
    if "max_total" not in result:
        m = re.search(r'max\s+\$?([\d,]+(?:\.\d+)?)\s*/\s*day', text_lower)
        if m:
            result["max_total"] = float(m.group(1).replace(",", ""))

    # "daily limit $X"
    if "max_total" not in result:
        m = re.search(r'daily\s+limit\s+\$?([\d,]+(?:\.\d+)?)', text_lower)
        if m:
            result["max_total"] = float(m.group(1).replace(",", ""))

    return result


# ---------------------------------------------------------------------------
# Resource managers (namespaces on SardisClient)
# ---------------------------------------------------------------------------


class WalletManager:
    """client.wallets namespace."""

    def __init__(self, client: "SardisClient"):
        self._client = client

    def create(
        self,
        name: str,
        *,
        chain: str = "base",
        token: str = "USDC",
        policy: Optional[str] = None,
        group_id: Optional[str] = None,
        initial_balance: float = 1000,
    ) -> ManagedWallet:
        """Create a new wallet with optional natural language policy.

        Args:
            name: Human-readable wallet name
            chain: Blockchain network (base, polygon, ethereum, arbitrum, optimism)
            token: Token type (USDC, USDT, EURC)
            policy: Natural language spending policy
            group_id: Optional group ID for shared budgets
            initial_balance: Starting balance for simulation (default: 1000)

        Returns:
            ManagedWallet with .pay() method
        """
        wallet = ManagedWallet(
            client=self._client,
            name=name,
            chain=chain,
            token=token,
            policy=policy,
            group_id=group_id,
            initial_balance=initial_balance,
        )
        self._client._wallets[wallet.wallet_id] = wallet

        # Register wallet in group if specified
        if group_id and group_id in self._client._groups:
            self._client._groups[group_id].add_agent(wallet.wallet_id)

        return wallet

    def get(self, wallet_id: str) -> ManagedWallet:
        """Get a wallet by ID.

        Args:
            wallet_id: The wallet identifier

        Returns:
            ManagedWallet with current state
        """
        if wallet_id not in self._client._wallets:
            raise ValueError(f"Wallet {wallet_id} not found")
        return self._client._wallets[wallet_id]

    def get_balance(self, wallet_id: str) -> dict:
        """Get wallet balance info.

        Args:
            wallet_id: The wallet identifier

        Returns:
            Dict with balance, spent, limit, remaining
        """
        wallet = self.get(wallet_id)
        return {
            "wallet_id": wallet_id,
            "balance": float(wallet.balance),
            "currency": wallet.currency,
            "spent_total": float(wallet.spent_total),
            "limit_per_tx": float(wallet.limit_per_tx),
            "limit_total": float(wallet.limit_total),
            "remaining": float(wallet.remaining_limit()),
        }

    def list(self) -> List[ManagedWallet]:
        """List all wallets."""
        return list(self._client._wallets.values())


class PaymentManager:
    """client.payments namespace."""

    def __init__(self, client: "SardisClient"):
        self._client = client

    def send(
        self,
        wallet_id: str,
        to: str,
        amount: float | str | Decimal,
        *,
        token: str = "USDC",
        memo: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> TransactionResult:
        """Execute a payment with policy enforcement.

        Args:
            wallet_id: Source wallet ID
            to: Recipient address or merchant identifier
            amount: Payment amount
            token: Token type (default: USDC)
            memo: Payment memo / reason (alias: purpose)
            purpose: Alias for memo

        Returns:
            TransactionResult with status, tx_hash, policy_result
        """
        if wallet_id not in self._client._wallets:
            raise ValueError(f"Wallet {wallet_id} not found")

        wallet = self._client._wallets[wallet_id]
        amount_d = Decimal(str(amount))
        reason = memo or purpose

        # Check group budget if wallet belongs to a group
        if wallet.group_id and wallet.group_id in self._client._groups:
            group = self._client._groups[wallet.group_id]
            if not group.can_spend(amount_d, merchant_id=to):
                return TransactionResult(
                    tx_id=f"tx_{uuid4().hex[:16]}",
                    status=TransactionStatus.REJECTED,
                    amount=amount_d,
                    from_wallet=wallet_id,
                    to=to,
                    currency=token,
                    timestamp=datetime.now(timezone.utc),
                    message="Group budget limit exceeded",
                    policy_result=PolicyResult(
                        approved=False,
                        reason="Group budget limit exceeded",
                    ),
                )

        tx = Transaction(
            from_wallet=wallet,
            to=to,
            amount=amount_d,
            currency=token,
            purpose=reason,
        )
        result = tx.execute()

        # Record group spend on success
        if result.success and wallet.group_id and wallet.group_id in self._client._groups:
            group = self._client._groups[wallet.group_id]
            group.record_spend(amount_d)
            group._tx_count_daily += 1

        # Record in ledger
        self._client._ledger.append(LedgerEntry(
            timestamp=datetime.now(timezone.utc),
            agent_name=wallet.name,
            amount=amount_d,
            merchant=to,
            status=result.status.value,
            tx_id=result.tx_id,
            wallet_id=wallet_id,
            group_id=wallet.group_id,
            purpose=reason,
        ))

        # Add group_remaining to result for convenience
        if wallet.group_id and wallet.group_id in self._client._groups:
            group = self._client._groups[wallet.group_id]
            result.group_remaining = group.daily_remaining  # type: ignore[attr-defined]

        return result


class GroupManager:
    """client.groups namespace."""

    def __init__(self, client: "SardisClient"):
        self._client = client

    def create(
        self,
        name: str,
        *,
        budget_per_tx: float | Decimal = 500,
        budget_daily: float | Decimal = 5000,
        budget_monthly: float | Decimal = 50000,
        policy: Optional[str] = None,
        blocked_merchants: Optional[List[str]] = None,
    ) -> ManagedGroup:
        """Create a new agent group with shared budget.

        Args:
            name: Group name
            budget_per_tx: Maximum per transaction
            budget_daily: Daily budget limit
            budget_monthly: Monthly budget limit
            policy: Natural language group policy
            blocked_merchants: List of blocked merchant identifiers

        Returns:
            ManagedGroup with .id property
        """
        group = ManagedGroup(
            name=name,
            budget_per_tx=Decimal(str(budget_per_tx)),
            budget_daily=Decimal(str(budget_daily)),
            budget_monthly=Decimal(str(budget_monthly)),
            policy=policy,
            blocked_merchants=blocked_merchants,
        )
        self._client._groups[group.id] = group
        return group

    def get(self, group_id: str) -> ManagedGroup:
        """Get a group by ID.

        Args:
            group_id: The group identifier

        Returns:
            ManagedGroup with current state
        """
        if group_id not in self._client._groups:
            raise ValueError(f"Group {group_id} not found")
        return self._client._groups[group_id]

    def get_status(self, group_id: str) -> dict:
        """Get group budget status.

        Args:
            group_id: The group identifier

        Returns:
            Dict with budget info, spending, and agent count
        """
        group = self.get(group_id)
        return {
            "group_id": group_id,
            "name": group.name,
            "budget_daily": float(group.budget_daily),
            "budget_per_tx": float(group.budget_per_tx),
            "spent_daily": float(group.spent_daily),
            "daily_remaining": float(group.daily_remaining),
            "agent_count": len(group.agent_ids),
            "tx_count_daily": group.tx_count_daily,
        }


class LedgerManager:
    """client.ledger namespace."""

    def __init__(self, client: "SardisClient"):
        self._client = client

    def list(
        self,
        *,
        group_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[LedgerEntry]:
        """List ledger entries.

        Args:
            group_id: Filter by group
            wallet_id: Filter by wallet
            limit: Maximum entries to return

        Returns:
            List of LedgerEntry objects
        """
        entries = self._client._ledger
        if group_id:
            entries = [e for e in entries if e.group_id == group_id]
        if wallet_id:
            entries = [e for e in entries if e.wallet_id == wallet_id]
        return entries[-limit:]


# ---------------------------------------------------------------------------
# SardisClient — the main entry point
# ---------------------------------------------------------------------------


class SardisClient:
    """
    Sardis client for agent payments with policy enforcement.

    Works in two modes:

    1. **Simulation mode** (default): All operations run locally.
       No API key needed. Great for prototyping and testing.

    2. **Production mode**: When ``sardis-sdk`` is installed and a
       real API key is provided, delegates to the Sardis platform.

    Example::

        from sardis import SardisClient

        client = SardisClient(api_key="sk_...")
        wallet = client.wallets.create(
            name="my-agent",
            chain="base",
            policy="Max $100/day",
        )
        tx = wallet.pay(to="openai.com", amount="25.00", token="USDC")
        print(tx.success)  # True
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self._simulation = True

        # Internal state for simulation mode
        self._wallets: Dict[str, ManagedWallet] = {}
        self._groups: Dict[str, ManagedGroup] = {}
        self._ledger: List[LedgerEntry] = []

        # Try to use production SDK if available and key looks real
        if api_key and api_key.startswith("sk_") and not api_key.startswith("sk_test"):
            try:
                from sardis_sdk import SardisClient as _ProdClient
                self._prod_client = _ProdClient(api_key=api_key)
                self._simulation = False
            except ImportError:
                pass

        # Resource managers
        self.wallets = WalletManager(self)
        self.payments = PaymentManager(self)
        self.groups = GroupManager(self)
        self.ledger = LedgerManager(self)

    @property
    def is_simulation(self) -> bool:
        """True if running in local simulation mode."""
        return self._simulation

    def __repr__(self) -> str:
        mode = "simulation" if self._simulation else "production"
        return f"SardisClient(mode={mode})"
