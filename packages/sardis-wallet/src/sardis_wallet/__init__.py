"""
Sardis Wallet - Production-grade wallet orchestration for AI agents.

This package provides comprehensive wallet management with:
- MPC key rotation for secure key lifecycle management
- Social recovery using Shamir's Secret Sharing
- HD wallet path customization (BIP-32/44/84)
- Encrypted backup and restore
- Multi-signature transaction support
- Granular spending limits
- Real-time activity monitoring
- Secure session management
- Tamper-evident audit logging
- Comprehensive health checks

Example usage:
    from sardis_wallet import (
        WalletManager,
        EnhancedWalletManager,
        PolicyEvaluation,
        # Key Rotation
        MPCKeyRotationManager,
        MPCKeyRotationPolicy,
        # Social Recovery
        SocialRecoveryManager,
        Guardian,
        # HD Wallet
        HDWalletManager,
        HDPath,
        # Backup
        WalletBackupManager,
        # Multi-sig
        MultisigManager,
        # Spending Limits
        SpendingLimitsManager,
        # Activity Monitoring
        ActivityMonitor,
        Alert,
        # Session Management
        SessionManager,
        Session,
        # Audit Logging
        AuditLogger,
        AuditCategory,
        # Health Checks
        HealthChecker,
        WalletHealthReport,
    )
"""

# Core manager
from .manager import (
    WalletManager,
    EnhancedWalletManager,
    PolicyEvaluation,
    PolicyStore,
)

# Key Rotation
from .key_rotation import (
    MPCKeyStatus,
    RotationReason,
    MPCKeyInfo,
    KeyRotationEvent,
    MPCKeyRotationPolicy,
    MPCSignerPort,
    KeyRotationCallback,
    MPCKeyRotationManager,
    get_mpc_key_rotation_manager,
)

# Social Recovery
from .social_recovery import (
    GuardianStatus,
    RecoveryStatus,
    Guardian,
    RecoveryChallenge,
    RecoveryRequest,
    SocialRecoveryConfig,
    SocialRecoveryManager,
    get_social_recovery_manager,
)

# HD Wallet
from .hd_wallet import (
    HDPathPurpose,
    CoinType,
    HDPathComponent,
    HDPath,
    HDPathTemplate,
    DerivedAddress,
    HDWalletConfig,
    HDWalletManager,
    STANDARD_TEMPLATES,
    CHAIN_COIN_TYPES,
    get_hd_wallet_manager,
)

# Backup and Restore
from .backup_restore import (
    BackupType,
    BackupStatus,
    RestoreStatus,
    BackupMetadata,
    BackupRecord,
    RestoreRequest,
    BackupConfig,
    WalletBackupManager,
    get_backup_manager,
)

# Multi-signature
from .multisig import (
    SignerRole,
    TransactionType,
    ApprovalStatus,
    MultisigSigner,
    ApprovalThreshold,
    TransactionApproval,
    PendingTransaction,
    MultisigConfig,
    MultisigManager,
    get_multisig_manager,
)

# Spending Limits
from .spending_limits import (
    LimitType,
    LimitScope,
    LimitAction,
    VelocityCheckType,
    SpendingLimit,
    VelocityRule,
    DynamicLimitAdjustment,
    ComplianceLimit,
    SpendingLimitsConfig,
    SpendingLimitsManager,
    get_spending_limits_manager,
)

# Activity Monitoring
from .activity_monitor import (
    AlertSeverity,
    AlertType,
    ActivityType,
    WalletActivity,
    Alert,
    WatchlistEntry,
    ActivityPattern,
    MonitoringConfig,
    ActivityMonitor,
    get_activity_monitor,
)

# Session Management
from .session_manager import (
    SessionStatus,
    SessionAction,
    MFAMethod,
    DeviceInfo,
    Session,
    MFAChallenge,
    SessionPolicy,
    SessionAuditEvent,
    SessionManager,
    get_session_manager,
)

# Audit Logging
from .audit_log import (
    AuditCategory,
    AuditLevel,
    AuditAction,
    AuditEntry,
    AuditQuery,
    AuditStats,
    RetentionPolicy,
    AuditLogger,
    get_audit_logger,
)

# Health Checks
from .health_check import (
    HealthStatus,
    CheckCategory,
    HealthCheckResult,
    WalletHealthReport,
    HealthCheckConfig,
    HealthChecker,
    get_health_checker,
)


__all__ = [
    # Core Manager
    "WalletManager",
    "EnhancedWalletManager",
    "PolicyEvaluation",
    "PolicyStore",

    # Key Rotation
    "MPCKeyStatus",
    "RotationReason",
    "MPCKeyInfo",
    "KeyRotationEvent",
    "MPCKeyRotationPolicy",
    "MPCSignerPort",
    "KeyRotationCallback",
    "MPCKeyRotationManager",
    "get_mpc_key_rotation_manager",

    # Social Recovery
    "GuardianStatus",
    "RecoveryStatus",
    "Guardian",
    "RecoveryChallenge",
    "RecoveryRequest",
    "SocialRecoveryConfig",
    "SocialRecoveryManager",
    "get_social_recovery_manager",

    # HD Wallet
    "HDPathPurpose",
    "CoinType",
    "HDPathComponent",
    "HDPath",
    "HDPathTemplate",
    "DerivedAddress",
    "HDWalletConfig",
    "HDWalletManager",
    "STANDARD_TEMPLATES",
    "CHAIN_COIN_TYPES",
    "get_hd_wallet_manager",

    # Backup and Restore
    "BackupType",
    "BackupStatus",
    "RestoreStatus",
    "BackupMetadata",
    "BackupRecord",
    "RestoreRequest",
    "BackupConfig",
    "WalletBackupManager",
    "get_backup_manager",

    # Multi-signature
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

    # Spending Limits
    "LimitType",
    "LimitScope",
    "LimitAction",
    "VelocityCheckType",
    "SpendingLimit",
    "VelocityRule",
    "DynamicLimitAdjustment",
    "ComplianceLimit",
    "SpendingLimitsConfig",
    "SpendingLimitsManager",
    "get_spending_limits_manager",

    # Activity Monitoring
    "AlertSeverity",
    "AlertType",
    "ActivityType",
    "WalletActivity",
    "Alert",
    "WatchlistEntry",
    "ActivityPattern",
    "MonitoringConfig",
    "ActivityMonitor",
    "get_activity_monitor",

    # Session Management
    "SessionStatus",
    "SessionAction",
    "MFAMethod",
    "DeviceInfo",
    "Session",
    "MFAChallenge",
    "SessionPolicy",
    "SessionAuditEvent",
    "SessionManager",
    "get_session_manager",

    # Audit Logging
    "AuditCategory",
    "AuditLevel",
    "AuditAction",
    "AuditEntry",
    "AuditQuery",
    "AuditStats",
    "RetentionPolicy",
    "AuditLogger",
    "get_audit_logger",

    # Health Checks
    "HealthStatus",
    "CheckCategory",
    "HealthCheckResult",
    "WalletHealthReport",
    "HealthCheckConfig",
    "HealthChecker",
    "get_health_checker",
]
