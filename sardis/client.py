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
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .agent import Agent
from .wallet import Wallet
from .transaction import Transaction, TransactionResult, TransactionStatus
from .policy import PolicyResult
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
    def group_id(self) -> str:
        """Compatibility alias for SDK-style group identifier."""
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
    currency: str = "USDC"
    group_id: Optional[str] = None
    purpose: Optional[str] = None

    @property
    def created_at(self) -> datetime:
        """Compatibility alias used by examples."""
        return self.timestamp

    @property
    def to_wallet(self) -> str:
        """Compatibility alias used by examples."""
        return self.merchant


class _AttrDict(dict):
    """Dictionary with attribute-style access for backward compatibility."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


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


class AgentManager:
    """client.agents namespace."""

    def __init__(self, client: "SardisClient"):
        self._client = client

    def create(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Agent:
        """Create an agent identity."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.agents.create(
                name=name,
                description=description,
                metadata=metadata,
            )
        agent = Agent(name=name, description=description)
        self._client._agents[agent.agent_id] = agent
        return agent

    def get(self, agent_id: str) -> Agent:
        """Get an agent by id."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.agents.get(agent_id)
        if agent_id not in self._client._agents:
            raise ValueError(f"Agent {agent_id} not found")
        return self._client._agents[agent_id]

    def list(self, *, limit: int = 100, offset: Optional[int] = None) -> List[Agent]:
        """List agents."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.agents.list(limit=limit, offset=offset)
        agents = list(self._client._agents.values())
        start = offset or 0
        return agents[start:start + limit]

    def update(
        self,
        agent_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Agent:
        """Update mutable agent fields."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.agents.update(
                agent_id,
                name=name,
                description=description,
                metadata=metadata,
            )
        agent = self.get(agent_id)
        if name is not None:
            agent.name = name
        if description is not None:
            agent.description = description
        if metadata is not None:
            setattr(agent, "metadata", metadata)
        return agent


class WalletManager:
    """client.wallets namespace."""

    def __init__(self, client: "SardisClient"):
        self._client = client

    def create(
        self,
        name: Optional[str] = None,
        *,
        agent_id: Optional[str] = None,
        mpc_provider: str = "local",
        account_type: str = "mpc_v1",
        chain: str = "base",
        currency: Optional[str] = None,
        token: Optional[str] = None,
        policy: Optional[str] = None,
        group_id: Optional[str] = None,
        initial_balance: float = 1000,
        limit_per_tx: float | Decimal = 100,
        limit_total: float | Decimal = 10000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Create a wallet in simulation mode or delegate to production SDK."""
        token_value = token or currency or "USDC"
        chain_value = chain or "base"

        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            if not agent_id:
                raise ValueError("agent_id is required in production mode")
            return self._client._prod_client.wallets.create(
                agent_id=agent_id,
                mpc_provider=mpc_provider,
                account_type=account_type,
                currency=token_value,
                chain=chain_value,
                limit_per_tx=Decimal(str(limit_per_tx)),
                limit_total=Decimal(str(limit_total)),
                metadata=metadata,
            )

        wallet_name = name
        if wallet_name is None and agent_id and agent_id in self._client._agents:
            wallet_name = self._client._agents[agent_id].name
        wallet_name = wallet_name or f"wallet-{uuid4().hex[:8]}"

        wallet = ManagedWallet(
            client=self._client,
            name=wallet_name,
            chain=chain_value,
            token=token_value,
            policy=policy,
            group_id=group_id,
            initial_balance=initial_balance,
            limit_per_tx=float(limit_per_tx),
            limit_total=float(limit_total),
        )
        wallet.agent_id = agent_id
        self._client._wallets[wallet.wallet_id] = wallet

        if group_id and group_id in self._client._groups:
            self._client._groups[group_id].add_agent(agent_id or wallet.wallet_id)
        return wallet

    def get(self, wallet_id: str) -> Any:
        """Get a wallet by ID."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.wallets.get(wallet_id)
        if wallet_id not in self._client._wallets:
            raise ValueError(f"Wallet {wallet_id} not found")
        return self._client._wallets[wallet_id]

    def get_balance(
        self,
        wallet_id: str,
        *,
        chain: str = "base",
        token: str = "USDC",
    ) -> Any:
        """Get wallet balance info."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.wallets.get_balance(
                wallet_id,
                chain=chain,
                token=token,
            )
        wallet = self.get(wallet_id)
        return _AttrDict({
            "wallet_id": wallet_id,
            "chain": chain,
            "token": token,
            "currency": wallet.currency,
            "balance": float(wallet.balance),
            "spent_total": float(wallet.spent_total),
            "limit_per_tx": float(wallet.limit_per_tx),
            "limit_total": float(wallet.limit_total),
            "remaining": float(wallet.remaining_limit()),
        })

    def list(self, *, agent_id: Optional[str] = None, limit: int = 100) -> List[Any]:
        """List wallets."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.wallets.list(agent_id=agent_id, limit=limit)
        wallets = list(self._client._wallets.values())
        if agent_id:
            wallets = [wallet for wallet in wallets if wallet.agent_id == agent_id]
        return wallets[:limit]

    def transfer(
        self,
        wallet_id: str,
        *,
        destination: str,
        amount: float | str | Decimal,
        token: str = "USDC",
        chain: str = "base_sepolia",
        domain: str = "localhost",
        memo: Optional[str] = None,
    ) -> Any:
        """Transfer stablecoins from a wallet."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.wallets.transfer(
                wallet_id,
                destination=destination,
                amount=Decimal(str(amount)),
                token=token,
                chain=chain,
                domain=domain,
                memo=memo,
            )
        result = self._client.payments.send(
            wallet_id=wallet_id,
            to=destination,
            amount=amount,
            token=token,
            memo=memo,
        )
        # SDK compatibility fields expected by examples/docs.
        result.token = token  # type: ignore[attr-defined]
        result.chain = chain  # type: ignore[attr-defined]
        return result


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
            currency=token,
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
        budget: Optional[Dict[str, Any]] = None,
        budget_per_tx: float | Decimal = 500,
        budget_daily: float | Decimal = 5000,
        budget_monthly: float | Decimal = 50000,
        merchant_policy: Optional[Dict[str, Any]] = None,
        policy: Optional[str] = None,
        blocked_merchants: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Create a new agent group with shared budget."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            payload_budget = budget
            if payload_budget is None:
                payload_budget = {
                    "per_transaction": str(budget_per_tx),
                    "daily": str(budget_daily),
                    "monthly": str(budget_monthly),
                }
            return self._client._prod_client.groups.create(
                name=name,
                budget=payload_budget,
                merchant_policy=merchant_policy,
                metadata=metadata,
            )

        if budget:
            budget_per_tx = budget.get("per_transaction", budget_per_tx)
            budget_daily = budget.get("daily", budget_daily)
            budget_monthly = budget.get("monthly", budget_monthly)
        blocked = list(blocked_merchants or [])
        if merchant_policy and merchant_policy.get("blocked_categories"):
            blocked.extend([str(item) for item in merchant_policy.get("blocked_categories", [])])

        group = ManagedGroup(
            name=name,
            budget_per_tx=Decimal(str(budget_per_tx)),
            budget_daily=Decimal(str(budget_daily)),
            budget_monthly=Decimal(str(budget_monthly)),
            policy=policy,
            blocked_merchants=blocked,
        )
        self._client._groups[group.id] = group
        return group

    def get(self, group_id: str) -> Any:
        """Get a group by ID."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.groups.get(group_id)
        if group_id not in self._client._groups:
            raise ValueError(f"Group {group_id} not found")
        return self._client._groups[group_id]

    def add_agent(self, group_id: str, agent_id: str) -> Any:
        """Attach an agent to a group."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.groups.add_agent(group_id, agent_id)
        group = self.get(group_id)
        group.add_agent(agent_id)
        return group

    def remove_agent(self, group_id: str, agent_id: str) -> Any:
        """Detach an agent from a group."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.groups.remove_agent(group_id, agent_id)
        group = self.get(group_id)
        group.remove_agent(agent_id)
        return group

    def get_spending(self, group_id: str) -> Dict[str, Any]:
        """Return spending summary for a group."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.groups.get_spending(group_id)
        group = self.get(group_id)
        return {
            "group_id": group_id,
            "name": group.name,
            "budget": {
                "daily": str(group.budget_daily),
                "per_transaction": str(group.budget_per_tx),
                "monthly": str(group.budget_monthly),
            },
            "spending": {
                "daily": str(group.spent_daily),
            },
            "daily_remaining": str(group.daily_remaining),
            "agent_count": len(group.agent_ids or []),
            "tx_count_daily": group.tx_count_daily,
        }

    def get_status(self, group_id: str) -> Dict[str, Any]:
        """Backward-compatible alias for group status."""
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self.get_spending(group_id)
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
    ) -> List[Any]:
        """List ledger entries.

        Args:
            group_id: Filter by group
            wallet_id: Filter by wallet
            limit: Maximum entries to return

        Returns:
            List of LedgerEntry objects
        """
        if not self._client._simulation and hasattr(self._client, "_prod_client"):
            return self._client._prod_client.ledger.list(
                group_id=group_id,
                wallet_id=wallet_id,
                limit=limit,
            )

        entries = self._client._ledger
        if group_id:
            entries = [e for e in entries if e.group_id == group_id]
        if wallet_id:
            entries = [e for e in entries if e.wallet_id == wallet_id]
        return entries[-limit:]

    def list_entries(
        self,
        *,
        group_id: Optional[str] = None,
        wallet_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Any]:
        """Compatibility alias used by framework examples."""
        return self.list(group_id=group_id, wallet_id=wallet_id, limit=limit)


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
        self._agents: Dict[str, Agent] = {}
        self._wallets: Dict[str, ManagedWallet] = {}
        self._groups: Dict[str, ManagedGroup] = {}
        self._ledger: List[LedgerEntry] = []

        # Try to use production SDK if available and key looks real
        if api_key and api_key.startswith("sk_") and not api_key.startswith(("sk_test", "sk_demo")):
            try:
                from sardis_sdk import SardisClient as _ProdClient
                client_kwargs: Dict[str, Any] = {"api_key": api_key}
                if base_url:
                    client_kwargs["base_url"] = base_url
                self._prod_client = _ProdClient(**client_kwargs)
                self._simulation = False
            except ImportError:
                pass

        # Resource managers
        self.agents = AgentManager(self)
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
