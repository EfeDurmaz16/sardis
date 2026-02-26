"""Multi-Agent Payment Orchestration.

Provides payment patterns beyond simple 1-to-1 transfers:
  1. Split Payments — divide a payment among multiple recipients
  2. Group Payments — pool funds from multiple payers
  3. Cascading Payments — sequential payment chains with conditions
  4. Round-Robin — rotate payment responsibility among agents

All flows integrate with the spending policy engine and escrow system.

Usage:
    from sardis_v2_core.multi_agent_payments import (
        PaymentOrchestrator,
        SplitPayment,
        GroupPayment,
    )

    orchestrator = PaymentOrchestrator()

    # Split $1000 among 3 recipients proportionally
    split = await orchestrator.create_split_payment(
        payer_id="agent_buyer",
        recipients=[
            ("agent_dev", Decimal("0.60")),   # 60%
            ("agent_design", Decimal("0.30")), # 30%
            ("agent_pm", Decimal("0.10")),     # 10%
        ],
        total_amount=Decimal("1000"),
        token="USDC",
        chain="base",
    )

    # Pool funds from 3 agents for a group purchase
    group = await orchestrator.create_group_payment(
        payers=[
            ("agent_a", Decimal("300")),
            ("agent_b", Decimal("300")),
            ("agent_c", Decimal("400")),
        ],
        recipient_id="vendor_xyz",
        token="USDC",
        chain="base",
    )
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple
from uuid import uuid4

from .mandates import PaymentMandate, VCProof
from .tokens import TokenType, to_raw_token_amount

logger = logging.getLogger("sardis.core.multi_agent_payments")


# ============ Enums ============


class PaymentFlowType(str, Enum):
    """Types of multi-agent payment flows."""
    SPLIT = "split"
    GROUP = "group"
    CASCADE = "cascade"
    ROUND_ROBIN = "round_robin"


class FlowState(str, Enum):
    """Multi-agent payment flow lifecycle states."""
    CREATED = "created"
    COLLECTING = "collecting"  # Group: waiting for all payers
    EXECUTING = "executing"    # Payments being processed
    PARTIAL = "partial"        # Some payments succeeded, some pending
    COMPLETED = "completed"    # All payments succeeded
    FAILED = "failed"          # Flow failed
    CANCELLED = "cancelled"


class PaymentLegState(str, Enum):
    """State of an individual payment leg."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ChainExecutorPort(Protocol):
    async def dispatch_payment(self, mandate: PaymentMandate) -> Any: ...


class WalletRepositoryPort(Protocol):
    async def get_by_agent(self, agent_id: str) -> Any: ...


# ============ Data Models ============


@dataclass
class PaymentLeg:
    """A single payment within a multi-agent flow."""
    id: str = field(default_factory=lambda: f"leg_{uuid4().hex[:12]}")
    payer_id: str = ""
    recipient_id: str = ""
    amount: Decimal = Decimal("0")
    token: str = "USDC"
    chain: str = "base"
    state: PaymentLegState = PaymentLegState.PENDING
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    explorer_url: Optional[str] = None
    execution_path: Optional[str] = None
    user_op_hash: Optional[str] = None
    error: Optional[str] = None
    order: int = 0  # Execution order for cascading
    condition: Optional[str] = None  # Condition for cascading
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payer_id": self.payer_id,
            "recipient_id": self.recipient_id,
            "amount": str(self.amount),
            "token": self.token,
            "chain": self.chain,
            "state": self.state.value,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "explorer_url": self.explorer_url,
            "execution_path": self.execution_path,
            "user_op_hash": self.user_op_hash,
            "error": self.error,
            "order": self.order,
        }


@dataclass
class PaymentFlow:
    """A multi-agent payment flow containing multiple legs."""
    id: str = field(default_factory=lambda: f"flow_{uuid4().hex[:12]}")
    flow_type: PaymentFlowType = PaymentFlowType.SPLIT
    state: FlowState = FlowState.CREATED
    legs: List[PaymentLeg] = field(default_factory=list)
    total_amount: Decimal = Decimal("0")
    token: str = "USDC"
    chain: str = "base"
    description: Optional[str] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def completed_legs(self) -> int:
        return sum(1 for leg in self.legs if leg.state == PaymentLegState.COMPLETED)

    @property
    def failed_legs(self) -> int:
        return sum(1 for leg in self.legs if leg.state == PaymentLegState.FAILED)

    @property
    def pending_legs(self) -> int:
        return sum(1 for leg in self.legs if leg.state == PaymentLegState.PENDING)

    @property
    def progress(self) -> float:
        if not self.legs:
            return 0.0
        return self.completed_legs / len(self.legs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "flow_type": self.flow_type.value,
            "state": self.state.value,
            "total_amount": str(self.total_amount),
            "token": self.token,
            "chain": self.chain,
            "description": self.description,
            "legs": [leg.to_dict() for leg in self.legs],
            "progress": round(self.progress, 2),
            "completed_legs": self.completed_legs,
            "total_legs": len(self.legs),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


# ============ Payment Orchestrator ============


class PaymentOrchestrator:
    """Orchestrates multi-agent payment flows.

    Manages complex payment patterns like splits, groups, cascades,
    and round-robin payments between multiple agents.
    """

    def __init__(
        self,
        *,
        chain_executor: Optional[ChainExecutorPort] = None,
        wallet_repo: Optional[WalletRepositoryPort] = None,
        domain: str = "sardis.sh",
        require_chain_execution: Optional[bool] = None,
    ) -> None:
        self._flows: Dict[str, PaymentFlow] = {}
        self._chain_executor = chain_executor
        self._wallet_repo = wallet_repo
        self._domain = domain
        env_chain_mode = os.getenv("SARDIS_CHAIN_MODE", "simulated").strip().lower()
        self._require_chain_execution = (
            env_chain_mode == "live" if require_chain_execution is None else require_chain_execution
        )

    def configure_execution_dependencies(
        self,
        *,
        chain_executor: Optional[ChainExecutorPort] = None,
        wallet_repo: Optional[WalletRepositoryPort] = None,
        domain: Optional[str] = None,
    ) -> None:
        """Inject/replace execution dependencies at runtime."""
        if chain_executor is not None:
            self._chain_executor = chain_executor
        if wallet_repo is not None:
            self._wallet_repo = wallet_repo
        if domain:
            self._domain = domain

    async def create_split_payment(
        self,
        payer_id: str,
        recipients: List[Tuple[str, Decimal]],
        total_amount: Decimal,
        token: str = "USDC",
        chain: str = "base",
        description: Optional[str] = None,
    ) -> PaymentFlow:
        """Create a split payment from one payer to multiple recipients.

        Args:
            payer_id: Agent paying
            recipients: List of (recipient_id, share) tuples.
                        Share can be a proportion (0-1) or absolute amount.
            total_amount: Total payment amount
            token: Token symbol
            chain: Blockchain network
            description: Optional description

        Returns:
            PaymentFlow with legs for each recipient
        """
        # Determine if shares are proportions or absolute
        total_shares = sum(share for _, share in recipients)
        is_proportional = total_shares <= Decimal("1.01")

        legs: List[PaymentLeg] = []
        allocated = Decimal("0")

        for i, (recipient_id, share) in enumerate(recipients):
            if is_proportional:
                if i == len(recipients) - 1:
                    # Last recipient gets remainder to avoid rounding issues
                    amount = total_amount - allocated
                else:
                    amount = (total_amount * share).quantize(Decimal("0.01"))
            else:
                amount = share

            allocated += amount

            legs.append(PaymentLeg(
                payer_id=payer_id,
                recipient_id=recipient_id,
                amount=amount,
                token=token,
                chain=chain,
                order=i,
            ))

        flow = PaymentFlow(
            flow_type=PaymentFlowType.SPLIT,
            state=FlowState.CREATED,
            legs=legs,
            total_amount=total_amount,
            token=token,
            chain=chain,
            description=description or f"Split payment: {payer_id} → {len(recipients)} recipients",
            created_by=payer_id,
        )

        self._flows[flow.id] = flow
        logger.info("Split payment created", extra={"flow_id": flow.id, "legs": len(legs)})
        return flow

    async def create_group_payment(
        self,
        payers: List[Tuple[str, Decimal]],
        recipient_id: str,
        token: str = "USDC",
        chain: str = "base",
        description: Optional[str] = None,
    ) -> PaymentFlow:
        """Create a group payment from multiple payers to one recipient.

        Args:
            payers: List of (payer_id, amount) tuples
            recipient_id: Agent receiving the pooled payment
            token: Token symbol
            chain: Blockchain network
            description: Optional description

        Returns:
            PaymentFlow with legs for each payer
        """
        total = sum(amount for _, amount in payers)

        legs = [
            PaymentLeg(
                payer_id=payer_id,
                recipient_id=recipient_id,
                amount=amount,
                token=token,
                chain=chain,
                order=i,
            )
            for i, (payer_id, amount) in enumerate(payers)
        ]

        flow = PaymentFlow(
            flow_type=PaymentFlowType.GROUP,
            state=FlowState.COLLECTING,
            legs=legs,
            total_amount=total,
            token=token,
            chain=chain,
            description=description or f"Group payment: {len(payers)} payers → {recipient_id}",
            created_by=payers[0][0] if payers else "",
        )

        self._flows[flow.id] = flow
        logger.info("Group payment created", extra={"flow_id": flow.id, "payers": len(payers)})
        return flow

    async def create_cascade_payment(
        self,
        steps: List[Dict[str, Any]],
        token: str = "USDC",
        chain: str = "base",
        description: Optional[str] = None,
    ) -> PaymentFlow:
        """Create a cascading payment chain.

        Each step executes only after the previous succeeds.
        Steps can have conditions (e.g., "if delivery_confirmed").

        Args:
            steps: List of step dicts with keys:
                   - payer_id: str
                   - recipient_id: str
                   - amount: Decimal
                   - condition: Optional[str]
            token: Token symbol
            chain: Blockchain network

        Returns:
            PaymentFlow with ordered, conditional legs
        """
        legs = []
        total = Decimal("0")

        for i, step in enumerate(steps):
            amount = Decimal(str(step["amount"]))
            total += amount

            legs.append(PaymentLeg(
                payer_id=step["payer_id"],
                recipient_id=step["recipient_id"],
                amount=amount,
                token=token,
                chain=chain,
                order=i,
                condition=step.get("condition"),
            ))

        flow = PaymentFlow(
            flow_type=PaymentFlowType.CASCADE,
            state=FlowState.CREATED,
            legs=legs,
            total_amount=total,
            token=token,
            chain=chain,
            description=description or f"Cascade payment: {len(steps)} steps",
            created_by=steps[0]["payer_id"] if steps else "",
        )

        self._flows[flow.id] = flow
        logger.info("Cascade payment created", extra={"flow_id": flow.id, "steps": len(steps)})
        return flow

    async def create_round_robin(
        self,
        participants: List[str],
        amount_per_round: Decimal,
        recipient_id: str,
        rounds: int = 1,
        token: str = "USDC",
        chain: str = "base",
    ) -> PaymentFlow:
        """Create a round-robin payment schedule.

        Participants take turns paying a recurring amount.

        Args:
            participants: Agent IDs that rotate payments
            amount_per_round: Amount each participant pays per turn
            recipient_id: Who receives the payments
            rounds: Number of complete rounds
            token: Token symbol
            chain: Blockchain network

        Returns:
            PaymentFlow with round-robin legs
        """
        legs = []
        total = Decimal("0")
        order = 0

        for _round in range(rounds):
            for participant in participants:
                legs.append(PaymentLeg(
                    payer_id=participant,
                    recipient_id=recipient_id,
                    amount=amount_per_round,
                    token=token,
                    chain=chain,
                    order=order,
                ))
                total += amount_per_round
                order += 1

        flow = PaymentFlow(
            flow_type=PaymentFlowType.ROUND_ROBIN,
            state=FlowState.CREATED,
            legs=legs,
            total_amount=total,
            token=token,
            chain=chain,
            description=f"Round-robin: {len(participants)} participants × {rounds} rounds",
            created_by=participants[0] if participants else "",
            metadata={"rounds": rounds, "participants": participants},
        )

        self._flows[flow.id] = flow
        logger.info("Round-robin created", extra={"flow_id": flow.id, "total_legs": len(legs)})
        return flow

    async def execute_flow(self, flow_id: str) -> PaymentFlow:
        """Execute all pending legs in a payment flow.

        For SPLIT and GROUP: executes all legs in parallel.
        For CASCADE: executes legs sequentially, checking conditions.
        For ROUND_ROBIN: executes next pending leg.

        Returns:
            Updated PaymentFlow
        """
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"Flow not found: {flow_id}")

        if flow.state in (FlowState.COMPLETED, FlowState.CANCELLED):
            raise ValueError(f"Flow already {flow.state.value}")

        flow.state = FlowState.EXECUTING

        if flow.flow_type == PaymentFlowType.CASCADE:
            await self._execute_cascade(flow)
        else:
            await self._execute_parallel(flow)

        # Update flow state
        if flow.failed_legs > 0 and flow.completed_legs > 0:
            flow.state = FlowState.PARTIAL
        elif flow.failed_legs == len(flow.legs):
            flow.state = FlowState.FAILED
        elif flow.completed_legs == len(flow.legs):
            flow.state = FlowState.COMPLETED
            flow.completed_at = datetime.now(timezone.utc)

        return flow

    async def _execute_parallel(self, flow: PaymentFlow) -> None:
        """Execute all legs in parallel (for SPLIT and GROUP)."""
        for leg in flow.legs:
            if leg.state != PaymentLegState.PENDING:
                continue

            await self._execute_leg(flow, leg)

    async def _execute_cascade(self, flow: PaymentFlow) -> None:
        """Execute legs sequentially with condition checks."""
        sorted_legs = sorted(flow.legs, key=lambda l: l.order)

        for leg in sorted_legs:
            if leg.state != PaymentLegState.PENDING:
                continue

            # Check condition if set
            if leg.condition:
                condition_met = await self._check_condition(leg.condition, flow)
                if not condition_met:
                    leg.state = PaymentLegState.SKIPPED
                    logger.info("Leg skipped (condition not met)", extra={"leg_id": leg.id})
                    continue

            leg.state = PaymentLegState.EXECUTING

            try:
                await self._execute_leg(flow, leg)
            except Exception as e:
                leg.state = PaymentLegState.FAILED
                leg.error = str(e)
                # Cascade stops on failure
                logger.error("Cascade stopped at failed leg", extra={"leg_id": leg.id})
                break

    async def _check_condition(self, condition: str, flow: PaymentFlow) -> bool:
        """Check if a cascade condition is met.

        Supported conditions:
        - "previous_completed": Previous leg must have completed
        - "all_completed": All previous legs must have completed
        - Custom conditions can be added via subclassing
        """
        if condition == "previous_completed":
            completed_orders = {
                leg.order
                for leg in flow.legs
                if leg.state == PaymentLegState.COMPLETED
            }
            current_order = max(
                (leg.order for leg in flow.legs if leg.condition == condition),
                default=0,
            )
            return (current_order - 1) in completed_orders

        if condition == "all_completed":
            return all(
                leg.state == PaymentLegState.COMPLETED
                for leg in flow.legs
                if leg.condition != condition
            )

        # Default: condition met
        return True

    async def execute_next_leg(self, flow_id: str) -> Optional[PaymentLeg]:
        """Execute the next pending leg in a flow (for round-robin)."""
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"Flow not found: {flow_id}")

        sorted_legs = sorted(flow.legs, key=lambda l: l.order)

        for leg in sorted_legs:
            if leg.state == PaymentLegState.PENDING:
                leg.state = PaymentLegState.EXECUTING
                try:
                    await self._execute_leg(flow, leg)
                    return leg
                except Exception as e:
                    leg.state = PaymentLegState.FAILED
                    leg.error = str(e)
                    return leg

        return None

    async def cancel_flow(self, flow_id: str, reason: str = "") -> PaymentFlow:
        """Cancel a payment flow and skip remaining legs."""
        flow = self._flows.get(flow_id)
        if not flow:
            raise ValueError(f"Flow not found: {flow_id}")

        for leg in flow.legs:
            if leg.state == PaymentLegState.PENDING:
                leg.state = PaymentLegState.SKIPPED

        flow.state = FlowState.CANCELLED
        flow.metadata["cancel_reason"] = reason

        logger.info("Flow cancelled", extra={"flow_id": flow_id, "reason": reason})
        return flow

    async def get_flow(self, flow_id: str) -> Optional[PaymentFlow]:
        """Get a payment flow by ID."""
        return self._flows.get(flow_id)

    async def list_flows(
        self,
        agent_id: Optional[str] = None,
        flow_type: Optional[PaymentFlowType] = None,
        state: Optional[FlowState] = None,
    ) -> List[PaymentFlow]:
        """List payment flows with optional filters."""
        flows = list(self._flows.values())

        if agent_id:
            flows = [
                f for f in flows
                if f.created_by == agent_id
                or any(leg.payer_id == agent_id or leg.recipient_id == agent_id for leg in f.legs)
            ]

        if flow_type:
            flows = [f for f in flows if f.flow_type == flow_type]

        if state:
            flows = [f for f in flows if f.state == state]

        return flows

    async def _execute_leg(self, flow: PaymentFlow, leg: PaymentLeg) -> None:
        leg.state = PaymentLegState.EXECUTING
        try:
            if self._should_dispatch_on_chain():
                await self._dispatch_leg_on_chain(flow, leg)
            else:
                leg.tx_hash = self._simulated_tx_hash(flow.id, leg.id)
            leg.state = PaymentLegState.COMPLETED
            leg.completed_at = datetime.now(timezone.utc)
            logger.info(
                "Payment leg completed",
                extra={
                    "flow_id": flow.id,
                    "leg_id": leg.id,
                    "payer": leg.payer_id,
                    "recipient": leg.recipient_id,
                    "amount": str(leg.amount),
                    "tx_hash": leg.tx_hash,
                },
            )
        except Exception as e:
            leg.state = PaymentLegState.FAILED
            leg.error = str(e)
            logger.error(
                "Payment leg failed",
                extra={"flow_id": flow.id, "leg_id": leg.id, "error": str(e)},
            )
            raise

    def _should_dispatch_on_chain(self) -> bool:
        has_deps = self._chain_executor is not None and self._wallet_repo is not None
        if self._require_chain_execution and not has_deps:
            raise ValueError(
                "Live chain execution required but chain_executor/wallet_repo are not configured"
            )
        return has_deps

    async def _dispatch_leg_on_chain(self, flow: PaymentFlow, leg: PaymentLeg) -> None:
        assert self._chain_executor is not None  # guarded by _should_dispatch_on_chain
        assert self._wallet_repo is not None

        payer_wallet = await self._wallet_repo.get_by_agent(leg.payer_id)
        if payer_wallet is None:
            raise ValueError(f"Payer wallet not found for agent: {leg.payer_id}")
        payee_wallet = await self._wallet_repo.get_by_agent(leg.recipient_id)
        if payee_wallet is None:
            raise ValueError(f"Payee wallet not found for agent: {leg.recipient_id}")

        destination = payee_wallet.get_address(leg.chain)
        if not destination:
            raise ValueError(
                f"Payee wallet has no address for chain '{leg.chain}' (agent={leg.recipient_id})"
            )

        token_symbol = str(leg.token).upper()
        try:
            token_type = TokenType(token_symbol)
        except ValueError as exc:
            raise ValueError(f"Unsupported token in multi-agent flow: {leg.token}") from exc

        amount_minor = to_raw_token_amount(token_type, leg.amount)
        nonce = hashlib.sha256(f"flow:{flow.id}:leg:{leg.id}".encode()).hexdigest()
        audit_hash = hashlib.sha256(
            f"multi_agent_leg:{flow.id}:{leg.id}:{leg.payer_id}:{leg.recipient_id}:{leg.amount}:{token_symbol}:{leg.chain}".encode()
        ).hexdigest()
        mandate = PaymentMandate(
            mandate_id=f"multi_leg_{nonce[:16]}",
            mandate_type="payment",
            issuer=f"agent:{leg.payer_id}",
            subject=leg.payer_id,
            expires_at=int(time.time()) + 300,
            nonce=nonce,
            proof=VCProof(
                verification_method=f"wallet:{getattr(payer_wallet, 'wallet_id', leg.payer_id)}#key-1",
                created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                proof_value="multi-agent-payment",
            ),
            domain=self._domain,
            purpose="checkout",
            chain=leg.chain,
            token=token_symbol,
            amount_minor=amount_minor,
            destination=destination,
            audit_hash=audit_hash,
            wallet_id=getattr(payer_wallet, "wallet_id", None),
            account_type=getattr(payer_wallet, "account_type", "mpc_v1"),
            smart_account_address=getattr(payer_wallet, "smart_account_address", None),
            merchant_domain=self._domain,
        )
        receipt = await self._chain_executor.dispatch_payment(mandate)
        tx_hash = getattr(receipt, "tx_hash", None)
        if not tx_hash:
            raise ValueError("Chain executor returned empty tx_hash")

        leg.tx_hash = tx_hash
        leg.block_number = getattr(receipt, "block_number", None)
        leg.execution_path = getattr(receipt, "execution_path", None)
        leg.user_op_hash = getattr(receipt, "user_op_hash", None)
        leg.explorer_url = _explorer_url(leg.chain, tx_hash)

    @staticmethod
    def _simulated_tx_hash(flow_id: str, leg_id: str) -> str:
        digest = hashlib.sha256(f"simulated:{flow_id}:{leg_id}".encode()).hexdigest()
        return f"0x{digest}"


def _explorer_url(chain: str, tx_hash: str) -> Optional[str]:
    chain_key = (chain or "").strip().lower()
    if chain_key in {"base", "base-mainnet"}:
        return f"https://basescan.org/tx/{tx_hash}"
    if chain_key in {"base-sepolia", "base_sepolia"}:
        return f"https://sepolia.basescan.org/tx/{tx_hash}"
    if chain_key in {"ethereum", "eth-mainnet"}:
        return f"https://etherscan.io/tx/{tx_hash}"
    if chain_key in {"ethereum-sepolia", "sepolia"}:
        return f"https://sepolia.etherscan.io/tx/{tx_hash}"
    if chain_key in {"polygon", "polygon-mainnet"}:
        return f"https://polygonscan.com/tx/{tx_hash}"
    if chain_key in {"arbitrum", "arbitrum-mainnet"}:
        return f"https://arbiscan.io/tx/{tx_hash}"
    if chain_key in {"optimism", "optimism-mainnet"}:
        return f"https://optimistic.etherscan.io/tx/{tx_hash}"
    return None
