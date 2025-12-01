"""Payment orchestration tying mandates, policies, compliance, and execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sardis_v2_core.mandates import MandateChain, PaymentMandate


@dataclass(slots=True)
class PaymentResult:
    mandate_id: str
    ledger_tx_id: str
    chain_tx_hash: str
    chain: str
    audit_anchor: str
    status: str = "submitted"
    compliance_provider: str | None = None
    compliance_rule: str | None = None


class PaymentExecutionError(Exception):
    """Raised when a mandate fails to execute."""


class WalletPolicyEngine(Protocol):
    def validate_policies(self, mandate: PaymentMandate) -> "PolicyEvaluation": ...


class CompliancePort(Protocol):
    def preflight(self, mandate: PaymentMandate) -> "ComplianceResult": ...


class ChainExecutorPort(Protocol):
    async def dispatch_payment(self, mandate: PaymentMandate) -> "ChainReceipt": ...


class LedgerPort(Protocol):
    def append(self, payment_mandate: PaymentMandate, chain_receipt: "ChainReceipt") -> "Transaction": ...


class PaymentOrchestrator:
    """Executes verified mandate chains against policies, compliance, and chain executors."""

    def __init__(
        self,
        *,
        wallet_manager: WalletPolicyEngine,
        compliance: CompliancePort,
        chain_executor: ChainExecutorPort,
        ledger: LedgerPort,
    ) -> None:
        self._wallet_manager = wallet_manager
        self._compliance = compliance
        self._chain_executor = chain_executor
        self._ledger = ledger

    async def execute_chain(self, chain: MandateChain) -> PaymentResult:
        payment = chain.payment
        policy = self._wallet_manager.validate_policies(payment)
        if not policy.allowed:
            raise PaymentExecutionError(policy.reason or "policy_denied")

        compliance = self._compliance.preflight(payment)
        if not compliance.allowed:
            raise PaymentExecutionError(compliance.reason or "compliance_denied")

        receipt = await self._chain_executor.dispatch_payment(payment)
        ledger_tx = self._ledger.append(payment, receipt)

        return PaymentResult(
            mandate_id=payment.mandate_id,
            ledger_tx_id=ledger_tx.tx_id,
            chain_tx_hash=receipt.tx_hash,
            chain=receipt.chain,
            audit_anchor=receipt.audit_anchor,
            compliance_provider=compliance.provider,
            compliance_rule=compliance.rule_id,
        )
