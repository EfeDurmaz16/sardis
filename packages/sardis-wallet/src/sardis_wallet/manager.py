"""
Enhanced Wallet Manager for Sardis.

Production-grade wallet orchestration with comprehensive security features:
- MPC key rotation
- Social recovery
- HD wallet path customization
- Backup and restore
- Multi-signature support
- Spending limits
- Activity monitoring
- Session management
- Audit logging
- Health checks
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING

from sardis_v2_core import (
    SardisSettings,
    PaymentMandate,
    SpendingPolicy,
    SpendingScope,
    create_default_policy,
    Wallet,
)

# Import all new modules
from .key_rotation import (
    MPCKeyRotationManager,
    MPCKeyRotationPolicy,
    MPCKeyInfo,
    KeyRotationEvent,
    get_mpc_key_rotation_manager,
)
from .social_recovery import (
    SocialRecoveryManager,
    SocialRecoveryConfig,
    Guardian,
    RecoveryRequest,
    get_social_recovery_manager,
)
from .hd_wallet import (
    HDWalletManager,
    HDWalletConfig,
    HDPath,
    DerivedAddress,
    get_hd_wallet_manager,
)
from .backup_restore import (
    WalletBackupManager,
    BackupConfig,
    BackupRecord,
    RestoreRequest as BackupRestoreRequest,
    get_backup_manager,
)
from .multisig import (
    MultisigManager,
    MultisigConfig,
    MultisigSigner,
    PendingTransaction,
    get_multisig_manager,
)
from .spending_limits import (
    SpendingLimitsManager,
    SpendingLimitsConfig,
    SpendingLimit,
    get_spending_limits_manager,
)
from .activity_monitor import (
    ActivityMonitor,
    MonitoringConfig,
    WalletActivity,
    Alert,
    get_activity_monitor,
)
from .session_manager import (
    SessionManager,
    SessionPolicy,
    Session,
    DeviceInfo,
    get_session_manager,
)
from .audit_log import (
    AuditLogger,
    AuditCategory,
    AuditAction,
    AuditLevel,
    AuditEntry,
    get_audit_logger,
)
from .health_check import (
    HealthChecker,
    HealthCheckConfig,
    WalletHealthReport,
    get_health_checker,
)


@dataclass
class PolicyEvaluation:
    """Result of policy evaluation."""
    allowed: bool
    reason: str | None = None
    warnings: List[str] | None = None
    risk_score: float = 0.0
    required_approvals: int = 0


class PolicyStore(Protocol):
    """Protocol for policy storage."""
    def fetch_policy(self, agent_id: str) -> SpendingPolicy | None: ...


class EnhancedWalletManager:
    """
    Production-grade wallet manager with comprehensive security features.

    This class orchestrates all wallet operations including:
    - Policy validation
    - Key management
    - Recovery options
    - Security monitoring
    - Compliance checks
    """

    def __init__(
        self,
        settings: SardisSettings,
        policy_store: PolicyStore | None = None,
        # Optional component overrides
        key_rotation_manager: MPCKeyRotationManager | None = None,
        recovery_manager: SocialRecoveryManager | None = None,
        hd_manager: HDWalletManager | None = None,
        backup_manager: WalletBackupManager | None = None,
        multisig_manager: MultisigManager | None = None,
        spending_limits_manager: SpendingLimitsManager | None = None,
        activity_monitor: ActivityMonitor | None = None,
        session_manager: SessionManager | None = None,
        audit_logger: AuditLogger | None = None,
        health_checker: HealthChecker | None = None,
    ):
        self._settings = settings
        self._policy_store = policy_store

        # Initialize all managers (use provided or get global instances)
        self._key_rotation = key_rotation_manager or get_mpc_key_rotation_manager()
        self._recovery = recovery_manager or get_social_recovery_manager()
        self._hd_wallet = hd_manager or get_hd_wallet_manager()
        self._backup = backup_manager or get_backup_manager()
        self._multisig = multisig_manager or get_multisig_manager()
        self._spending_limits = spending_limits_manager or get_spending_limits_manager()
        self._activity_monitor = activity_monitor or get_activity_monitor()
        self._session = session_manager or get_session_manager()
        self._audit = audit_logger or get_audit_logger()
        self._health = health_checker or get_health_checker()

    # =========================================================================
    # Policy Validation
    # =========================================================================

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
        wallet: Wallet,
        mandate: PaymentMandate,
        chain: str,
        token: Any,
        rpc_client: Optional[Any] = None,
        session_id: Optional[str] = None,
    ) -> PolicyEvaluation:
        """
        Comprehensive async policy evaluation with all security checks.

        Args:
            wallet: Wallet instance
            mandate: Payment mandate
            chain: Chain identifier
            token: Token type
            rpc_client: RPC client for balance queries
            session_id: Session ID for validation

        Returns:
            PolicyEvaluation result with full analysis
        """
        warnings = []
        risk_score = 0.0

        # Validate session if provided
        if session_id:
            valid, reason, session = await self._session.validate_session(
                session_id,
                action=None,  # Will check specific action based on amount
            )
            if not valid:
                return PolicyEvaluation(
                    allowed=False,
                    reason=f"Session validation failed: {reason}",
                )

        # Get spending policy
        policy = self._policy_store.fetch_policy(mandate.subject) if self._policy_store else None
        if not policy:
            policy = create_default_policy(mandate.subject)

        amount = Decimal(mandate.amount_minor) / Decimal(10**2)

        # Check spending policy
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

        if not ok:
            return PolicyEvaluation(allowed=False, reason=reason)

        # Check spending limits
        limits_ok, limit_results = await self._spending_limits.check_transaction(
            wallet_id=wallet.wallet_id,
            amount=amount,
            token=str(token),
            chain=chain,
            merchant_id=mandate.domain,
        )

        if not limits_ok:
            failed_limits = [r for r in limit_results if not r.get("allowed", True)]
            return PolicyEvaluation(
                allowed=False,
                reason=failed_limits[0].get("reason", "Spending limit exceeded"),
                warnings=[r.get("reason") for r in limit_results if r.get("reason") != "OK"],
            )

        # Calculate risk score from activity monitor
        for result in limit_results:
            utilization = result.get("utilization", 0)
            if utilization > 80:
                warnings.append(f"{result.get('limit_type', 'Limit')} at {utilization:.1f}% utilization")
                risk_score += 10

        # Check if multi-sig approval is required
        required_approvals = 0
        multisig_config = self._multisig.get_config(wallet.wallet_id)
        if multisig_config:
            threshold = multisig_config.get("default_threshold", 1)
            if threshold > 1:
                required_approvals = threshold

        return PolicyEvaluation(
            allowed=True,
            reason=None,
            warnings=warnings if warnings else None,
            risk_score=risk_score,
            required_approvals=required_approvals,
        )

    # =========================================================================
    # Key Management
    # =========================================================================

    async def rotate_wallet_key(
        self,
        wallet_id: str,
        reason: str = "scheduled",
        initiated_by: str = "system",
    ) -> KeyRotationEvent:
        """Rotate the MPC key for a wallet."""
        event = await self._key_rotation.rotate_key(
            wallet_id=wallet_id,
            new_public_key=b"",  # Will be generated by MPC provider
            reason=reason,
            initiated_by=initiated_by,
        )

        # Audit log
        await self._audit.log(
            wallet_id=wallet_id,
            category=AuditCategory.KEY_MANAGEMENT,
            action=AuditAction.KEY_ROTATED,
            actor_id=initiated_by,
            resource_type="key",
            resource_id=event.new_key_id,
            details={"reason": reason, "old_key_id": event.old_key_id},
        )

        return event

    async def emergency_key_rotation(
        self,
        wallet_id: str,
        reason: str,
        initiated_by: str,
    ) -> KeyRotationEvent:
        """Emergency key rotation with immediate revocation."""
        event = await self._key_rotation.emergency_rotate(
            wallet_id=wallet_id,
            reason=reason,
            initiated_by=initiated_by,
        )

        # Audit log - security event
        await self._audit.log_security_event(
            wallet_id=wallet_id,
            action=AuditAction.KEY_ROTATED,
            threat_level="high",
            actor_id=initiated_by,
            details={"emergency": True, "reason": reason},
        )

        return event

    # =========================================================================
    # Social Recovery
    # =========================================================================

    async def setup_social_recovery(
        self,
        wallet_id: str,
        guardians: List[Dict[str, Any]],
        recovery_secret: bytes,
        threshold: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Set up social recovery for a wallet."""
        result = await self._recovery.setup_recovery(
            wallet_id=wallet_id,
            recovery_secret=recovery_secret,
            guardians=guardians,
            threshold=threshold,
        )

        await self._audit.log(
            wallet_id=wallet_id,
            category=AuditCategory.RECOVERY,
            action=AuditAction.GUARDIAN_ADDED,
            details={
                "guardian_count": len(guardians),
                "threshold": result["threshold"],
            },
        )

        return result

    async def initiate_recovery(
        self,
        wallet_id: str,
        requester_proof: str,
    ) -> RecoveryRequest:
        """Initiate wallet recovery process."""
        recovery = await self._recovery.initiate_recovery(
            wallet_id=wallet_id,
            requester_proof=requester_proof,
        )

        await self._audit.log_security_event(
            wallet_id=wallet_id,
            action=AuditAction.RECOVERY_INITIATED,
            threat_level="medium",
            details={"recovery_id": recovery.recovery_id},
        )

        return recovery

    # =========================================================================
    # HD Wallet
    # =========================================================================

    async def derive_address(
        self,
        wallet_id: str,
        master_key_ref: str,
        chain: str,
        account: int = 0,
        label: Optional[str] = None,
    ) -> DerivedAddress:
        """Derive a new address for a wallet."""
        address = await self._hd_wallet.derive_address(
            wallet_id=wallet_id,
            master_key_ref=master_key_ref,
            chain=chain,
            account=account,
            label=label,
        )

        await self._audit.log(
            wallet_id=wallet_id,
            category=AuditCategory.KEY_MANAGEMENT,
            action=AuditAction.KEY_CREATED,
            resource_type="address",
            resource_id=address.address,
            details={"chain": chain, "path": address.path},
        )

        return address

    # =========================================================================
    # Backup and Restore
    # =========================================================================

    async def create_backup(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
        password: str,
        recovery_hint: str = "",
    ) -> BackupRecord:
        """Create an encrypted wallet backup."""
        record = await self._backup.create_backup(
            wallet_id=wallet_id,
            wallet_data=wallet_data,
            password=password,
            recovery_hint=recovery_hint,
        )

        await self._audit.log(
            wallet_id=wallet_id,
            category=AuditCategory.KEY_MANAGEMENT,
            action=AuditAction.BACKUP_CREATED,
            resource_type="backup",
            resource_id=record.metadata.backup_id,
        )

        return record

    async def restore_backup(
        self,
        backup_id: str,
        password: str,
    ) -> BackupRestoreRequest:
        """Restore a wallet from backup."""
        restore = await self._backup.restore_backup(
            backup_id=backup_id,
            password=password,
        )

        await self._audit.log(
            wallet_id=restore.wallet_id,
            category=AuditCategory.RECOVERY,
            action=AuditAction.BACKUP_RESTORED,
            resource_type="backup",
            resource_id=backup_id,
        )

        return restore

    # =========================================================================
    # Multi-Signature
    # =========================================================================

    async def setup_multisig(
        self,
        wallet_id: str,
        signers: List[Dict[str, Any]],
        config: Optional[MultisigConfig] = None,
    ) -> MultisigConfig:
        """Set up multi-signature for a wallet."""
        multisig_config = await self._multisig.setup_multisig(
            wallet_id=wallet_id,
            signers=signers,
            config=config,
        )

        await self._audit.log(
            wallet_id=wallet_id,
            category=AuditCategory.CONFIGURATION,
            action=AuditAction.SETTING_CHANGED,
            details={
                "setting": "multisig",
                "signer_count": len(signers),
                "threshold": multisig_config.default_threshold,
            },
        )

        return multisig_config

    async def approve_multisig_transaction(
        self,
        pending_tx_id: str,
        signer_id: str,
        signature: bytes,
    ) -> Dict[str, Any]:
        """Approve a pending multi-sig transaction."""
        approval = await self._multisig.approve_transaction(
            pending_tx_id=pending_tx_id,
            signer_id=signer_id,
            signature=signature,
        )

        # Get pending transaction for audit
        pending_tx = self._multisig._pending_txs.get(pending_tx_id)

        await self._audit.log_transaction(
            wallet_id=pending_tx.wallet_id if pending_tx else "",
            action=AuditAction.TRANSACTION_APPROVED,
            actor_id=signer_id,
            details={"pending_tx_id": pending_tx_id},
        )

        return approval.to_dict()

    # =========================================================================
    # Spending Limits
    # =========================================================================

    async def setup_spending_limits(
        self,
        wallet_id: str,
        config: Optional[SpendingLimitsConfig] = None,
    ) -> SpendingLimitsConfig:
        """Set up spending limits for a wallet."""
        return await self._spending_limits.setup_default_limits(
            wallet_id=wallet_id,
            config=config,
        )

    async def update_spending_limit(
        self,
        wallet_id: str,
        limit_id: str,
        limit_amount: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[SpendingLimit]:
        """Update a spending limit."""
        limit = await self._spending_limits.update_limit(
            wallet_id=wallet_id,
            limit_id=limit_id,
            limit_amount=limit_amount,
            is_active=is_active,
        )

        if limit:
            await self._audit.log(
                wallet_id=wallet_id,
                category=AuditCategory.POLICY,
                action=AuditAction.LIMIT_UPDATED,
                resource_type="spending_limit",
                resource_id=limit_id,
                old_value=str(limit.limit_amount) if limit_amount else None,
                new_value=str(limit_amount) if limit_amount else None,
            )

        return limit

    # =========================================================================
    # Activity Monitoring
    # =========================================================================

    async def record_activity(
        self,
        activity: WalletActivity,
    ) -> tuple[WalletActivity, List[Alert]]:
        """Record and analyze wallet activity."""
        return await self._activity_monitor.record_activity(activity)

    def get_activity_summary(
        self,
        wallet_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get activity summary for a wallet."""
        return self._activity_monitor.get_activity_summary(wallet_id, days)

    # =========================================================================
    # Session Management
    # =========================================================================

    async def create_session(
        self,
        wallet_id: str,
        user_id: str,
        device_info: Optional[DeviceInfo] = None,
        ip_address: Optional[str] = None,
    ) -> Session:
        """Create a new wallet access session."""
        session = await self._session.create_session(
            wallet_id=wallet_id,
            user_id=user_id,
            device_info=device_info,
            ip_address=ip_address,
        )

        await self._audit.log_auth_event(
            wallet_id=wallet_id,
            action=AuditAction.SESSION_CREATED,
            actor_id=user_id,
            session_id=session.session_id,
            ip_address=ip_address,
            device_id=device_info.device_id if device_info else None,
        )

        return session

    async def validate_session(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
    ) -> tuple[bool, str, Optional[Session]]:
        """Validate a session."""
        return await self._session.validate_session(
            session_id=session_id,
            ip_address=ip_address,
        )

    async def revoke_session(
        self,
        session_id: str,
        reason: str = "",
    ) -> bool:
        """Revoke a session."""
        session = self._session._sessions.get(session_id)
        result = await self._session.revoke_session(session_id, reason)

        if result and session:
            await self._audit.log_auth_event(
                wallet_id=session.wallet_id,
                action=AuditAction.SESSION_REVOKED,
                session_id=session_id,
                details={"reason": reason},
            )

        return result

    # =========================================================================
    # Health Checks
    # =========================================================================

    async def check_wallet_health(
        self,
        wallet_id: str,
        wallet_data: Dict[str, Any],
        deep_check: bool = False,
    ) -> WalletHealthReport:
        """Perform comprehensive health check on a wallet."""
        return await self._health.check_wallet_health(
            wallet_id=wallet_id,
            wallet_data=wallet_data,
            deep_check=deep_check,
        )

    # =========================================================================
    # Audit
    # =========================================================================

    async def get_audit_log(
        self,
        wallet_id: str,
        limit: int = 100,
        categories: Optional[List[AuditCategory]] = None,
    ) -> List[Dict[str, Any]]:
        """Get audit log for a wallet."""
        from .audit_log import AuditQuery

        query = AuditQuery(
            wallet_id=wallet_id,
            categories=categories,
            limit=limit,
        )

        return await self._audit.query(query)


# Backwards-compatible alias
class WalletManager(EnhancedWalletManager):
    """Backwards-compatible WalletManager class."""
    pass


__all__ = [
    "WalletManager",
    "EnhancedWalletManager",
    "PolicyEvaluation",
    "PolicyStore",
]
