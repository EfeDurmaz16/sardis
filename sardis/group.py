"""Simple agent group for local simulation."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional


@dataclass
class AgentGroup:
    """A group of agents with shared budget (local simulation).

    Example:
        >>> from sardis import AgentGroup
        >>> group = AgentGroup(name="engineering", budget_daily=Decimal("1000"))
        >>> group.add_agent("agent_abc")
        >>> group.can_spend(Decimal("100"))
        True
    """

    name: str
    budget_per_tx: Decimal = Decimal("500.00")
    budget_daily: Decimal = Decimal("5000.00")
    budget_monthly: Decimal = Decimal("50000.00")
    budget_total: Decimal = Decimal("500000.00")
    blocked_merchants: List[str] = field(default_factory=list)
    agent_ids: List[str] = field(default_factory=list)
    _spent_daily: Decimal = field(default=Decimal("0"), repr=False)
    _spent_monthly: Decimal = field(default=Decimal("0"), repr=False)
    _spent_total: Decimal = field(default=Decimal("0"), repr=False)

    def add_agent(self, agent_id: str) -> None:
        """Add an agent to this group."""
        if agent_id not in self.agent_ids:
            self.agent_ids.append(agent_id)

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from this group."""
        if agent_id in self.agent_ids:
            self.agent_ids.remove(agent_id)

    def can_spend(
        self,
        amount: Decimal,
        merchant_id: Optional[str] = None,
    ) -> bool:
        """Check if a spend is allowed under group policy."""
        if amount > self.budget_per_tx:
            return False
        if self._spent_daily + amount > self.budget_daily:
            return False
        if self._spent_monthly + amount > self.budget_monthly:
            return False
        if self._spent_total + amount > self.budget_total:
            return False
        if merchant_id and merchant_id.lower() in [m.lower() for m in self.blocked_merchants]:
            return False
        return True

    def record_spend(self, amount: Decimal) -> None:
        """Record a successful spend against group budget."""
        self._spent_daily += amount
        self._spent_monthly += amount
        self._spent_total += amount
