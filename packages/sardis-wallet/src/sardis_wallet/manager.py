"""Wallet and policy orchestration for Sardis."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from sardis_v2_core import (
    SardisSettings,
    PaymentMandate,
    SpendingPolicy,
    SpendingScope,
    create_default_policy,
)


@dataclass
class PolicyEvaluation:
    allowed: bool
    reason: str | None = None


class PolicyStore(Protocol):
    def fetch_policy(self, agent_id: str) -> SpendingPolicy | None: ...


class WalletManager:
    def __init__(self, settings: SardisSettings, policy_store: PolicyStore | None = None):
        self._settings = settings
        self._policy_store = policy_store

    def validate_policies(self, mandate: PaymentMandate) -> PolicyEvaluation:
        """Synchronous validation (for backwards compatibility)."""
        policy = self._policy_store.fetch_policy(mandate.subject) if self._policy_store else None
        if not policy:
            policy = create_default_policy(mandate.subject)
        amount = Decimal(mandate.amount_minor) / Decimal(10**2)
        ok, reason = policy.validate_payment(
            amount,
            Decimal("0"),
            merchant_id=mandate.domain,
            scope=SpendingScope.ALL,
        )
        return PolicyEvaluation(allowed=ok, reason=None if ok else reason)
    
    async def evaluate_policies(
        self,
        wallet: "Wallet",  # Forward reference
        mandate: PaymentMandate,
        chain: str,
        token: "TokenType",  # Forward reference
        rpc_client: Optional[Any] = None,
    ) -> PolicyEvaluation:
        """
        Async policy evaluation with on-chain balance check (non-custodial).
        
        Args:
            wallet: Wallet instance
            mandate: Payment mandate
            chain: Chain identifier
            token: Token type
            rpc_client: RPC client for balance queries
            
        Returns:
            PolicyEvaluation result
        """
        policy = self._policy_store.fetch_policy(mandate.subject) if self._policy_store else None
        if not policy:
            policy = create_default_policy(mandate.subject)
        amount = Decimal(mandate.amount_minor) / Decimal(10**2)
        ok, reason = await policy.evaluate(
            wallet=wallet,
            amount=amount,
            fee=Decimal("0"),
            chain=chain,
            token=token,
            merchant_id=mandate.domain,
            scope=SpendingScope.ALL,
            rpc_client=rpc_client,
        )
        return PolicyEvaluation(allowed=ok, reason=None if ok else reason)