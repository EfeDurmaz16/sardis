"""
Transaction execution for agent payments.

Transactions represent payments from one wallet to a destination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from .errors import ErrorCode, _get_suggestion
from .policy import Policy, PolicyResult
from .wallet import Wallet


class TransactionStatus(str, Enum):
    """Transaction status."""
    PENDING = "pending"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    FAILED = "failed"
    REJECTED = "rejected"


# Map policy check failure names to error codes
_POLICY_CHECK_TO_ERROR: dict[str, str] = {
    "amount_limit": ErrorCode.POLICY_AMOUNT_EXCEEDED,
    "token_allowed": ErrorCode.POLICY_TOKEN_NOT_ALLOWED,
    "destination_blocked": ErrorCode.POLICY_MERCHANT_BLOCKED,
    "destination_allowed": ErrorCode.POLICY_MERCHANT_NOT_ALLOWED,
    "purpose_required": ErrorCode.POLICY_PURPOSE_REQUIRED,
    "wallet_limit": ErrorCode.POLICY_WALLET_LIMIT,
}


@dataclass
class TransactionResult:
    """Result of a transaction execution.

    On failure, ``error_code`` and ``suggestion`` provide actionable
    guidance for fixing the issue::

        result = wallet.pay(to="openai.com", amount=500)
        if not result.success:
            print(result.error_code)   # "POLICY_AMOUNT_EXCEEDED"
            print(result.suggestion)   # "Reduce amount below $100..."
    """
    tx_id: str
    status: TransactionStatus
    amount: Decimal
    from_wallet: str
    to: str
    currency: str
    timestamp: datetime
    tx_hash: str | None = None  # On-chain hash (simulated in demo)
    message: str | None = None
    policy_result: PolicyResult | None = None
    approval_id: str | None = None
    error_code: str | None = None
    suggestion: str | None = None

    @property
    def success(self) -> bool:
        return self.status == TransactionStatus.EXECUTED

    def __repr__(self) -> str:
        status_icon = "✓" if self.success else "✗"
        return f"TransactionResult({status_icon} {self.amount} {self.currency} → {self.to})"


@dataclass
class Transaction:
    """
    A payment transaction from a wallet to a destination.

    Example:
        >>> wallet = Wallet(initial_balance=100)
        >>> tx = Transaction(from_wallet=wallet, to="openai:api", amount=5)
        >>> result = tx.execute()
        >>> print(result.success)  # True
        >>> print(wallet.balance)  # 95.00
    """

    from_wallet: Wallet
    to: str  # Destination (address, agent ID, or merchant identifier)
    amount: Decimal
    currency: str = "USDC"
    purpose: str | None = None
    policy: Policy | None = None
    tx_id: str = field(default_factory=lambda: f"tx_{uuid4().hex[:16]}")

    def __init__(
        self,
        from_wallet: Wallet,
        to: str,
        amount: float | Decimal,
        *,
        currency: str = "USDC",
        purpose: str | None = None,
        policy: Policy | None = None,
    ):
        """
        Create a new transaction.

        Args:
            from_wallet: Source wallet
            to: Destination identifier (address, agent, or merchant)
            amount: Amount to transfer
            currency: Token type (default: USDC)
            purpose: Optional description
            policy: Optional policy to enforce
        """
        self.from_wallet = from_wallet
        self.to = to
        self.amount = Decimal(str(amount))
        self.currency = currency
        self.purpose = purpose
        self.policy = policy or Policy()
        self.tx_id = f"tx_{uuid4().hex[:16]}"

    def execute(self) -> TransactionResult:
        """
        Execute the transaction.

        Checks policy, deducts from wallet, and returns result.
        In production, this triggers on-chain settlement.
        """
        timestamp = datetime.now(UTC)

        # Check policy
        policy_result = self.policy.check(
            amount=self.amount,
            wallet=self.from_wallet,
            destination=self.to,
        )

        if not policy_result.approved:
            # Resolve error code from the first failed policy check
            failed_check = policy_result.checks_failed[0] if policy_result.checks_failed else ""
            error_code = _POLICY_CHECK_TO_ERROR.get(failed_check, ErrorCode.TRANSACTION_FAILED)
            return TransactionResult(
                tx_id=self.tx_id,
                status=TransactionStatus.REJECTED,
                amount=self.amount,
                from_wallet=self.from_wallet.wallet_id,
                to=self.to,
                currency=self.currency,
                timestamp=timestamp,
                message=policy_result.reason,
                policy_result=policy_result,
                error_code=error_code,
                suggestion=_get_suggestion(error_code),
            )

        # Check if human approval is required
        if policy_result.requires_approval:
            approval_id = f"appr_{uuid4().hex[:16]}"
            return TransactionResult(
                tx_id=self.tx_id,
                status=TransactionStatus.PENDING_APPROVAL,
                amount=self.amount,
                from_wallet=self.from_wallet.wallet_id,
                to=self.to,
                currency=self.currency,
                timestamp=timestamp,
                message=policy_result.approval_reason or "Awaiting human approval",
                policy_result=policy_result,
                approval_id=approval_id,
                error_code=ErrorCode.APPROVAL_REQUIRED,
                suggestion=_get_suggestion(ErrorCode.APPROVAL_REQUIRED),
            )

        # Attempt to spend from wallet
        if not self.from_wallet.spend(self.amount):
            return TransactionResult(
                tx_id=self.tx_id,
                status=TransactionStatus.FAILED,
                amount=self.amount,
                from_wallet=self.from_wallet.wallet_id,
                to=self.to,
                currency=self.currency,
                timestamp=timestamp,
                message="Insufficient funds or limit exceeded",
                policy_result=policy_result,
                error_code=ErrorCode.INSUFFICIENT_FUNDS,
                suggestion=_get_suggestion(ErrorCode.INSUFFICIENT_FUNDS),
            )

        # Generate simulated tx hash (in production, this is real on-chain hash)
        tx_hash = f"0x{uuid4().hex}"

        return TransactionResult(
            tx_id=self.tx_id,
            status=TransactionStatus.EXECUTED,
            amount=self.amount,
            from_wallet=self.from_wallet.wallet_id,
            to=self.to,
            currency=self.currency,
            timestamp=timestamp,
            tx_hash=tx_hash,
            message="Transaction executed successfully",
            policy_result=policy_result,
        )

    def __repr__(self) -> str:
        return f"Transaction({self.amount} {self.currency} → {self.to})"






