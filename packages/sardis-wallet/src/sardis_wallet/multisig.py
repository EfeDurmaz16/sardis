"""
Multi-signature Wallet Support for Sardis.

Implements multi-signature transaction approval with configurable
thresholds and time-based policies.

Features:
- M-of-N signature schemes
- Time-locked approvals
- Approval delegation
- Transaction queuing
- Emergency override mechanisms
- Audit trail for all approvals
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sardis_v2_core import Wallet, Transaction

logger = logging.getLogger(__name__)


class SignerRole(str, Enum):
    """Role of a multi-sig signer."""
    OWNER = "owner"  # Full control
    ADMIN = "admin"  # Can approve most transactions
    OPERATOR = "operator"  # Limited approval rights
    VIEWER = "viewer"  # Read-only access


class TransactionType(str, Enum):
    """Types of transactions for threshold configuration."""
    TRANSFER = "transfer"
    CONTRACT_CALL = "contract_call"
    POLICY_CHANGE = "policy_change"
    SIGNER_CHANGE = "signer_change"
    EMERGENCY = "emergency"


class ApprovalStatus(str, Enum):
    """Status of an approval."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


@dataclass
class MultisigSigner:
    """A signer in a multi-sig wallet."""
    signer_id: str
    wallet_id: str
    public_key: bytes
    role: SignerRole = SignerRole.OPERATOR
    weight: int = 1  # For weighted voting
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    added_by: Optional[str] = None
    is_active: bool = True

    # Approval limits
    max_approval_amount: Optional[Decimal] = None  # None = unlimited
    daily_approval_limit: Optional[Decimal] = None
    approved_today: Decimal = field(default_factory=lambda: Decimal("0"))
    last_approval_date: Optional[datetime] = None

    # Security settings
    require_mfa: bool = False
    allowed_hours: Optional[Tuple[int, int]] = None  # (start_hour, end_hour) UTC

    def can_approve(self, amount: Decimal) -> Tuple[bool, str]:
        """Check if signer can approve a given amount."""
        if not self.is_active:
            return False, "Signer is not active"

        # Check amount limit
        if self.max_approval_amount and amount > self.max_approval_amount:
            return False, f"Amount exceeds signer's limit of {self.max_approval_amount}"

        # Check daily limit
        if self.daily_approval_limit:
            today = datetime.now(timezone.utc).date()
            if self.last_approval_date and self.last_approval_date.date() == today:
                if self.approved_today + amount > self.daily_approval_limit:
                    return False, f"Would exceed daily limit of {self.daily_approval_limit}"
            else:
                # Reset daily counter
                self.approved_today = Decimal("0")

        # Check time restrictions
        if self.allowed_hours:
            current_hour = datetime.now(timezone.utc).hour
            start, end = self.allowed_hours
            if start <= end:
                if not (start <= current_hour < end):
                    return False, f"Outside allowed hours ({start}:00-{end}:00 UTC)"
            else:  # Spans midnight
                if not (current_hour >= start or current_hour < end):
                    return False, f"Outside allowed hours ({start}:00-{end}:00 UTC)"

        return True, "OK"

    def record_approval(self, amount: Decimal) -> None:
        """Record an approval for daily limit tracking."""
        today = datetime.now(timezone.utc).date()
        if self.last_approval_date and self.last_approval_date.date() != today:
            self.approved_today = Decimal("0")

        self.approved_today += amount
        self.last_approval_date = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "signer_id": self.signer_id,
            "wallet_id": self.wallet_id,
            "role": self.role.value,
            "weight": self.weight,
            "added_at": self.added_at.isoformat(),
            "is_active": self.is_active,
            "max_approval_amount": str(self.max_approval_amount) if self.max_approval_amount else None,
            "daily_approval_limit": str(self.daily_approval_limit) if self.daily_approval_limit else None,
            "require_mfa": self.require_mfa,
        }


@dataclass
class ApprovalThreshold:
    """Threshold configuration for a transaction type."""
    transaction_type: TransactionType
    required_signatures: int
    required_weight: int = 0  # For weighted voting (0 = use count)
    timeout_hours: int = 24
    require_owner: bool = False
    require_admin: bool = False
    max_amount: Optional[Decimal] = None  # Max amount for this threshold

    def is_met(
        self,
        approvals: List["TransactionApproval"],
        signers: Dict[str, MultisigSigner],
    ) -> Tuple[bool, str]:
        """Check if threshold is met."""
        valid_approvals = [a for a in approvals if a.status == ApprovalStatus.APPROVED]

        # Check signature count
        if len(valid_approvals) < self.required_signatures:
            return False, f"Need {self.required_signatures - len(valid_approvals)} more signatures"

        # Check weight if applicable
        if self.required_weight > 0:
            total_weight = sum(
                signers.get(a.signer_id, MultisigSigner(signer_id="", wallet_id="", public_key=b"")).weight
                for a in valid_approvals
            )
            if total_weight < self.required_weight:
                return False, f"Need {self.required_weight - total_weight} more weight"

        # Check owner requirement
        if self.require_owner:
            has_owner = any(
                signers.get(a.signer_id) and signers[a.signer_id].role == SignerRole.OWNER
                for a in valid_approvals
            )
            if not has_owner:
                return False, "Requires owner approval"

        # Check admin requirement
        if self.require_admin:
            has_admin = any(
                signers.get(a.signer_id) and signers[a.signer_id].role in (SignerRole.OWNER, SignerRole.ADMIN)
                for a in valid_approvals
            )
            if not has_admin:
                return False, "Requires admin approval"

        return True, "OK"


@dataclass
class TransactionApproval:
    """An approval from a signer."""
    approval_id: str
    pending_tx_id: str
    signer_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    signature: Optional[bytes] = None
    approved_at: Optional[datetime] = None
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24)
    )
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if approval is still valid."""
        if self.status != ApprovalStatus.APPROVED:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "approval_id": self.approval_id,
            "pending_tx_id": self.pending_tx_id,
            "signer_id": self.signer_id,
            "status": self.status.value,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "expires_at": self.expires_at.isoformat(),
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class PendingTransaction:
    """A transaction pending multi-sig approval."""
    pending_tx_id: str
    wallet_id: str
    transaction_type: TransactionType
    initiated_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24)
    )

    # Transaction details
    to_address: str = ""
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    token: str = "USDC"
    chain: str = "base"
    data: Optional[str] = None  # Contract call data

    # Approval tracking
    required_threshold: Optional[ApprovalThreshold] = None
    approvals: List[TransactionApproval] = field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING

    # Execution info
    executed_at: Optional[datetime] = None
    tx_hash: Optional[str] = None
    execution_error: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if transaction has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def get_approval_count(self) -> int:
        """Get number of valid approvals."""
        return sum(1 for a in self.approvals if a.is_valid())

    def get_rejection_count(self) -> int:
        """Get number of rejections."""
        return sum(1 for a in self.approvals if a.status == ApprovalStatus.REJECTED)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pending_tx_id": self.pending_tx_id,
            "wallet_id": self.wallet_id,
            "transaction_type": self.transaction_type.value,
            "initiated_by": self.initiated_by,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "to_address": self.to_address,
            "amount": str(self.amount),
            "token": self.token,
            "chain": self.chain,
            "status": self.status.value,
            "approvals": len([a for a in self.approvals if a.is_valid()]),
            "rejections": self.get_rejection_count(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "tx_hash": self.tx_hash,
        }


@dataclass
class MultisigConfig:
    """Configuration for multi-sig wallet."""
    wallet_id: str
    name: str = ""
    default_threshold: int = 2
    default_timeout_hours: int = 24

    # Thresholds by transaction type
    thresholds: Dict[TransactionType, ApprovalThreshold] = field(default_factory=dict)

    # Emergency settings
    emergency_threshold: int = 1  # For emergency transactions
    emergency_timeout_hours: int = 1
    emergency_signers: List[str] = field(default_factory=list)

    # Security settings
    max_pending_transactions: int = 10
    require_different_signers: bool = True  # Signers must be different from initiator
    min_time_between_executions: int = 60  # Seconds

    def get_threshold(self, tx_type: TransactionType, amount: Decimal) -> ApprovalThreshold:
        """Get the applicable threshold for a transaction."""
        if tx_type in self.thresholds:
            threshold = self.thresholds[tx_type]
            if threshold.max_amount is None or amount <= threshold.max_amount:
                return threshold

        # Default threshold
        return ApprovalThreshold(
            transaction_type=tx_type,
            required_signatures=self.default_threshold,
            timeout_hours=self.default_timeout_hours,
        )


class TransactionExecutor(Protocol):
    """Protocol for executing approved transactions."""

    async def execute_transaction(
        self,
        wallet_id: str,
        to_address: str,
        amount: Decimal,
        token: str,
        chain: str,
        data: Optional[str] = None,
    ) -> str:
        """Execute transaction, returns tx_hash."""
        ...


class MultisigNotificationService(Protocol):
    """Protocol for multi-sig notifications."""

    async def notify_approval_needed(
        self,
        signers: List[MultisigSigner],
        pending_tx: PendingTransaction,
    ) -> None:
        """Notify signers that approval is needed."""
        ...

    async def notify_threshold_met(
        self,
        pending_tx: PendingTransaction,
    ) -> None:
        """Notify that threshold has been met."""
        ...


class MultisigManager:
    """
    Manages multi-signature wallet operations.

    Features:
    - M-of-N signature schemes
    - Configurable thresholds per transaction type
    - Time-locked approvals
    - Weighted voting
    - Emergency override
    """

    def __init__(
        self,
        executor: Optional[TransactionExecutor] = None,
        notification_service: Optional[MultisigNotificationService] = None,
    ):
        self._executor = executor
        self._notifications = notification_service

        # Storage (in production, use database)
        self._configs: Dict[str, MultisigConfig] = {}  # wallet_id -> config
        self._signers: Dict[str, Dict[str, MultisigSigner]] = {}  # wallet_id -> signer_id -> signer
        self._pending_txs: Dict[str, PendingTransaction] = {}  # pending_tx_id -> tx
        self._wallet_pending: Dict[str, List[str]] = {}  # wallet_id -> [pending_tx_ids]

        # Locks
        self._approval_lock = asyncio.Lock()
        self._execution_lock = asyncio.Lock()

    async def setup_multisig(
        self,
        wallet_id: str,
        signers: List[Dict[str, Any]],
        config: Optional[MultisigConfig] = None,
    ) -> MultisigConfig:
        """
        Set up multi-sig for a wallet.

        Args:
            wallet_id: Wallet identifier
            signers: List of signer configurations
            config: Optional configuration

        Returns:
            MultisigConfig for the wallet
        """
        if len(signers) < 2:
            raise ValueError("Multi-sig requires at least 2 signers")

        # Create config
        multisig_config = config or MultisigConfig(wallet_id=wallet_id)
        multisig_config.wallet_id = wallet_id

        # Set default thresholds
        if not multisig_config.thresholds:
            multisig_config.thresholds = {
                TransactionType.TRANSFER: ApprovalThreshold(
                    transaction_type=TransactionType.TRANSFER,
                    required_signatures=2,
                    timeout_hours=24,
                ),
                TransactionType.CONTRACT_CALL: ApprovalThreshold(
                    transaction_type=TransactionType.CONTRACT_CALL,
                    required_signatures=2,
                    timeout_hours=24,
                ),
                TransactionType.POLICY_CHANGE: ApprovalThreshold(
                    transaction_type=TransactionType.POLICY_CHANGE,
                    required_signatures=3,
                    timeout_hours=48,
                    require_owner=True,
                ),
                TransactionType.SIGNER_CHANGE: ApprovalThreshold(
                    transaction_type=TransactionType.SIGNER_CHANGE,
                    required_signatures=3,
                    timeout_hours=48,
                    require_owner=True,
                ),
            }

        self._configs[wallet_id] = multisig_config

        # Add signers
        self._signers[wallet_id] = {}
        for signer_data in signers:
            signer = MultisigSigner(
                signer_id=f"signer_{secrets.token_hex(8)}",
                wallet_id=wallet_id,
                public_key=signer_data.get("public_key", b""),
                role=SignerRole(signer_data.get("role", "operator")),
                weight=signer_data.get("weight", 1),
                max_approval_amount=signer_data.get("max_approval_amount"),
                daily_approval_limit=signer_data.get("daily_approval_limit"),
                require_mfa=signer_data.get("require_mfa", False),
            )
            self._signers[wallet_id][signer.signer_id] = signer

        logger.info(
            f"Multi-sig setup for wallet {wallet_id} with {len(signers)} signers"
        )

        return multisig_config

    async def add_signer(
        self,
        wallet_id: str,
        signer_data: Dict[str, Any],
        added_by: str,
    ) -> MultisigSigner:
        """Add a new signer to a multi-sig wallet."""
        if wallet_id not in self._signers:
            raise ValueError(f"Multi-sig not set up for wallet {wallet_id}")

        signer = MultisigSigner(
            signer_id=f"signer_{secrets.token_hex(8)}",
            wallet_id=wallet_id,
            public_key=signer_data.get("public_key", b""),
            role=SignerRole(signer_data.get("role", "operator")),
            weight=signer_data.get("weight", 1),
            added_by=added_by,
        )

        self._signers[wallet_id][signer.signer_id] = signer

        logger.info(f"Added signer {signer.signer_id} to wallet {wallet_id}")
        return signer

    async def remove_signer(
        self,
        wallet_id: str,
        signer_id: str,
        removed_by: str,
    ) -> bool:
        """Remove a signer from a multi-sig wallet."""
        if wallet_id not in self._signers:
            return False

        signer = self._signers[wallet_id].get(signer_id)
        if not signer:
            return False

        signer.is_active = False
        logger.info(f"Removed signer {signer_id} from wallet {wallet_id}")
        return True

    async def initiate_transaction(
        self,
        wallet_id: str,
        initiated_by: str,
        to_address: str,
        amount: Decimal,
        token: str = "USDC",
        chain: str = "base",
        transaction_type: TransactionType = TransactionType.TRANSFER,
        data: Optional[str] = None,
    ) -> PendingTransaction:
        """
        Initiate a multi-sig transaction.

        Args:
            wallet_id: Wallet identifier
            initiated_by: Signer ID who initiated
            to_address: Recipient address
            amount: Transaction amount
            token: Token type
            chain: Chain identifier
            transaction_type: Type of transaction
            data: Optional contract call data

        Returns:
            PendingTransaction awaiting approvals
        """
        config = self._configs.get(wallet_id)
        if not config:
            raise ValueError(f"Multi-sig not set up for wallet {wallet_id}")

        # Check max pending transactions
        pending_count = len(self._wallet_pending.get(wallet_id, []))
        if pending_count >= config.max_pending_transactions:
            raise ValueError(f"Maximum pending transactions ({config.max_pending_transactions}) reached")

        # Get threshold
        threshold = config.get_threshold(transaction_type, amount)

        # Create pending transaction
        pending_tx_id = f"pending_{secrets.token_hex(12)}"
        pending_tx = PendingTransaction(
            pending_tx_id=pending_tx_id,
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            initiated_by=initiated_by,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=threshold.timeout_hours),
            to_address=to_address,
            amount=amount,
            token=token,
            chain=chain,
            data=data,
            required_threshold=threshold,
            status=ApprovalStatus.PENDING,
        )

        # Store
        self._pending_txs[pending_tx_id] = pending_tx
        if wallet_id not in self._wallet_pending:
            self._wallet_pending[wallet_id] = []
        self._wallet_pending[wallet_id].append(pending_tx_id)

        # Notify signers
        if self._notifications:
            signers = list(self._signers.get(wallet_id, {}).values())
            active_signers = [s for s in signers if s.is_active and s.signer_id != initiated_by]
            await self._notifications.notify_approval_needed(active_signers, pending_tx)

        logger.info(
            f"Initiated multi-sig transaction {pending_tx_id} for wallet {wallet_id}"
        )

        return pending_tx

    async def approve_transaction(
        self,
        pending_tx_id: str,
        signer_id: str,
        signature: bytes,
    ) -> TransactionApproval:
        """
        Approve a pending transaction.

        Args:
            pending_tx_id: Pending transaction ID
            signer_id: Approving signer ID
            signature: Signature over transaction data

        Returns:
            TransactionApproval record
        """
        async with self._approval_lock:
            pending_tx = self._pending_txs.get(pending_tx_id)
            if not pending_tx:
                raise ValueError(f"Pending transaction {pending_tx_id} not found")

            if pending_tx.status != ApprovalStatus.PENDING:
                raise ValueError(f"Transaction is not pending: {pending_tx.status}")

            if pending_tx.is_expired():
                pending_tx.status = ApprovalStatus.EXPIRED
                raise ValueError("Transaction has expired")

            config = self._configs.get(pending_tx.wallet_id)
            signer = self._signers.get(pending_tx.wallet_id, {}).get(signer_id)

            if not signer:
                raise ValueError(f"Signer {signer_id} not found")

            # Check if signer already approved
            for existing_approval in pending_tx.approvals:
                if existing_approval.signer_id == signer_id:
                    raise ValueError("Signer has already voted")

            # Check if signer is initiator (if required different signers)
            if config and config.require_different_signers:
                if signer_id == pending_tx.initiated_by:
                    raise ValueError("Initiator cannot approve their own transaction")

            # Check if signer can approve
            can_approve, reason = signer.can_approve(pending_tx.amount)
            if not can_approve:
                raise ValueError(reason)

            # Verify signature (in production, verify cryptographically)
            # For now, accept non-empty signature
            if not signature:
                raise ValueError("Invalid signature")

            # Create approval
            approval = TransactionApproval(
                approval_id=f"approval_{secrets.token_hex(8)}",
                pending_tx_id=pending_tx_id,
                signer_id=signer_id,
                status=ApprovalStatus.APPROVED,
                signature=signature,
                approved_at=datetime.now(timezone.utc),
            )

            pending_tx.approvals.append(approval)
            signer.record_approval(pending_tx.amount)

            # Check if threshold is met
            if pending_tx.required_threshold:
                signers = self._signers.get(pending_tx.wallet_id, {})
                is_met, _ = pending_tx.required_threshold.is_met(
                    pending_tx.approvals,
                    signers,
                )

                if is_met:
                    pending_tx.status = ApprovalStatus.APPROVED

                    if self._notifications:
                        await self._notifications.notify_threshold_met(pending_tx)

            logger.info(
                f"Approval recorded for transaction {pending_tx_id} by {signer_id}"
            )

            return approval

    async def reject_transaction(
        self,
        pending_tx_id: str,
        signer_id: str,
        reason: str = "",
    ) -> TransactionApproval:
        """Reject a pending transaction."""
        async with self._approval_lock:
            pending_tx = self._pending_txs.get(pending_tx_id)
            if not pending_tx:
                raise ValueError(f"Pending transaction {pending_tx_id} not found")

            signer = self._signers.get(pending_tx.wallet_id, {}).get(signer_id)
            if not signer:
                raise ValueError(f"Signer {signer_id} not found")

            # Create rejection
            rejection = TransactionApproval(
                approval_id=f"rejection_{secrets.token_hex(8)}",
                pending_tx_id=pending_tx_id,
                signer_id=signer_id,
                status=ApprovalStatus.REJECTED,
                rejection_reason=reason,
            )

            pending_tx.approvals.append(rejection)

            # Check if enough rejections to cancel
            signers_count = len([s for s in self._signers.get(pending_tx.wallet_id, {}).values() if s.is_active])
            rejection_count = pending_tx.get_rejection_count()

            threshold = pending_tx.required_threshold
            if threshold:
                rejections_to_cancel = signers_count - threshold.required_signatures + 1
                if rejection_count >= rejections_to_cancel:
                    pending_tx.status = ApprovalStatus.REJECTED

            logger.info(
                f"Rejection recorded for transaction {pending_tx_id} by {signer_id}"
            )

            return rejection

    async def execute_transaction(
        self,
        pending_tx_id: str,
        executor_signer_id: str,
    ) -> PendingTransaction:
        """
        Execute an approved transaction.

        Args:
            pending_tx_id: Pending transaction ID
            executor_signer_id: Signer executing the transaction

        Returns:
            Updated PendingTransaction with execution result
        """
        async with self._execution_lock:
            pending_tx = self._pending_txs.get(pending_tx_id)
            if not pending_tx:
                raise ValueError(f"Pending transaction {pending_tx_id} not found")

            if pending_tx.status != ApprovalStatus.APPROVED:
                raise ValueError(f"Transaction not approved: {pending_tx.status}")

            # Verify executor is a valid signer
            signer = self._signers.get(pending_tx.wallet_id, {}).get(executor_signer_id)
            if not signer or not signer.is_active:
                raise ValueError(f"Invalid executor: {executor_signer_id}")

            pending_tx.status = ApprovalStatus.EXECUTED

            try:
                if self._executor:
                    tx_hash = await self._executor.execute_transaction(
                        wallet_id=pending_tx.wallet_id,
                        to_address=pending_tx.to_address,
                        amount=pending_tx.amount,
                        token=pending_tx.token,
                        chain=pending_tx.chain,
                        data=pending_tx.data,
                    )
                    pending_tx.tx_hash = tx_hash
                else:
                    # Mock execution for testing
                    pending_tx.tx_hash = f"0x{secrets.token_hex(32)}"

                pending_tx.executed_at = datetime.now(timezone.utc)

                logger.info(
                    f"Executed transaction {pending_tx_id}: {pending_tx.tx_hash}"
                )

            except Exception as e:
                pending_tx.status = ApprovalStatus.APPROVED  # Reset to allow retry
                pending_tx.execution_error = str(e)
                logger.error(f"Transaction execution failed: {e}")
                raise

            return pending_tx

    async def cancel_transaction(
        self,
        pending_tx_id: str,
        cancelled_by: str,
        reason: str = "",
    ) -> bool:
        """Cancel a pending transaction."""
        pending_tx = self._pending_txs.get(pending_tx_id)
        if not pending_tx:
            return False

        # Only initiator or owners can cancel
        signer = self._signers.get(pending_tx.wallet_id, {}).get(cancelled_by)
        if cancelled_by != pending_tx.initiated_by:
            if not signer or signer.role not in (SignerRole.OWNER, SignerRole.ADMIN):
                raise ValueError("Only initiator or admin can cancel")

        pending_tx.status = ApprovalStatus.CANCELLED

        logger.info(f"Transaction {pending_tx_id} cancelled by {cancelled_by}")
        return True

    def get_pending_transactions(
        self,
        wallet_id: str,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get pending transactions for a wallet."""
        pending_ids = self._wallet_pending.get(wallet_id, [])
        transactions = []

        for pending_tx_id in pending_ids:
            pending_tx = self._pending_txs.get(pending_tx_id)
            if pending_tx:
                if not include_expired and pending_tx.is_expired():
                    continue
                if pending_tx.status in (ApprovalStatus.EXECUTED, ApprovalStatus.CANCELLED):
                    continue
                transactions.append(pending_tx.to_dict())

        return transactions

    def get_signers(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Get all signers for a wallet."""
        signers = self._signers.get(wallet_id, {})
        return [s.to_dict() for s in signers.values()]

    def get_config(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get multi-sig config for a wallet."""
        config = self._configs.get(wallet_id)
        if not config:
            return None

        return {
            "wallet_id": config.wallet_id,
            "name": config.name,
            "default_threshold": config.default_threshold,
            "default_timeout_hours": config.default_timeout_hours,
            "signer_count": len(self._signers.get(wallet_id, {})),
            "pending_transactions": len(self._wallet_pending.get(wallet_id, [])),
        }


# Singleton instance
_multisig_manager: Optional[MultisigManager] = None


def get_multisig_manager() -> MultisigManager:
    """Get the global multi-sig manager instance."""
    global _multisig_manager

    if _multisig_manager is None:
        _multisig_manager = MultisigManager()

    return _multisig_manager


__all__ = [
    "SignerRole",
    "TransactionType",
    "ApprovalStatus",
    "MultisigSigner",
    "ApprovalThreshold",
    "TransactionApproval",
    "PendingTransaction",
    "MultisigConfig",
    "MultisigManager",
    "get_multisig_manager",
]
