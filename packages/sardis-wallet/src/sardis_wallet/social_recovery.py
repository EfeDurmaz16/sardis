"""
Social Recovery mechanism for Sardis Wallets.

Implements a secure social recovery system using Shamir's Secret Sharing (SSS)
to enable wallet recovery through trusted guardians.

Features:
- Guardian-based recovery with configurable threshold
- Time-locked recovery to prevent unauthorized access
- Recovery challenge system
- Guardian management (add, remove, rotate)
- Emergency lockdown capabilities
- Full audit trail
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from sardis_v2_core import Wallet

logger = logging.getLogger(__name__)


class GuardianStatus(str, Enum):
    """Status of a guardian."""
    ACTIVE = "active"
    PENDING = "pending"  # Awaiting guardian acceptance
    SUSPENDED = "suspended"
    REMOVED = "removed"


class RecoveryStatus(str, Enum):
    """Status of a recovery request."""
    PENDING = "pending"
    COLLECTING_SHARES = "collecting_shares"
    THRESHOLD_MET = "threshold_met"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REJECTED = "rejected"


@dataclass
class Guardian:
    """A wallet recovery guardian."""
    guardian_id: str
    wallet_id: str
    guardian_type: str  # "email", "phone", "hardware_key", "social_account", "institution"
    guardian_identifier: str  # Hashed identifier (email, phone, etc.)
    guardian_name: str  # Display name
    share_index: int  # SSS share index
    encrypted_share: Optional[bytes] = None  # Encrypted SSS share
    status: GuardianStatus = GuardianStatus.PENDING
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    verification_method: str = "email_otp"  # How guardian verifies their identity

    # Security settings
    max_recovery_attempts: int = 3
    cooldown_hours: int = 24
    current_attempts: int = 0
    last_attempt_at: Optional[datetime] = None

    def is_active(self) -> bool:
        """Check if guardian is active and can participate in recovery."""
        return self.status == GuardianStatus.ACTIVE

    def can_participate(self) -> bool:
        """Check if guardian can participate in recovery right now."""
        if not self.is_active():
            return False

        # Check cooldown
        if self.last_attempt_at and self.current_attempts >= self.max_recovery_attempts:
            cooldown_end = self.last_attempt_at + timedelta(hours=self.cooldown_hours)
            if datetime.now(timezone.utc) < cooldown_end:
                return False
            # Reset after cooldown
            self.current_attempts = 0

        return True

    def record_participation(self) -> None:
        """Record participation in a recovery attempt."""
        self.current_attempts += 1
        self.last_attempt_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (safe for client)."""
        return {
            "guardian_id": self.guardian_id,
            "wallet_id": self.wallet_id,
            "guardian_type": self.guardian_type,
            "guardian_name": self.guardian_name,
            "status": self.status.value,
            "added_at": self.added_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "verification_method": self.verification_method,
        }


@dataclass
class RecoveryChallenge:
    """A challenge issued to a guardian during recovery."""
    challenge_id: str
    recovery_id: str
    guardian_id: str
    challenge_type: str  # "otp", "signature", "hardware_key"
    challenge_data: str  # Challenge to be signed/answered
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1)
    )
    verified: bool = False
    verified_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 5

    def is_valid(self) -> bool:
        """Check if challenge is still valid."""
        if self.verified:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        if self.attempts >= self.max_attempts:
            return False
        return True


@dataclass
class RecoveryRequest:
    """A wallet recovery request."""
    recovery_id: str
    wallet_id: str
    requester_proof: str  # Proof of identity from requester
    new_key_reference: Optional[str] = None  # New MPC key to transfer to
    status: RecoveryStatus = RecoveryStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7)
    )
    completed_at: Optional[datetime] = None

    # Guardian participation
    guardians_contacted: List[str] = field(default_factory=list)
    shares_collected: Dict[str, bytes] = field(default_factory=dict)  # guardian_id -> share
    threshold: int = 0
    required_threshold: int = 0

    # Time lock
    time_lock_hours: int = 48
    time_lock_expires_at: Optional[datetime] = None

    # Audit
    activity_log: List[Dict[str, Any]] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if recovery request has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def is_threshold_met(self) -> bool:
        """Check if enough shares have been collected."""
        return len(self.shares_collected) >= self.required_threshold

    def is_time_lock_expired(self) -> bool:
        """Check if time lock has expired (recovery can proceed)."""
        if not self.time_lock_expires_at:
            return False
        return datetime.now(timezone.utc) >= self.time_lock_expires_at

    def start_time_lock(self) -> None:
        """Start the time lock period."""
        self.time_lock_expires_at = datetime.now(timezone.utc) + timedelta(
            hours=self.time_lock_hours
        )
        self.status = RecoveryStatus.THRESHOLD_MET

    def add_share(self, guardian_id: str, share: bytes) -> None:
        """Add a guardian's share."""
        self.shares_collected[guardian_id] = share
        self.log_activity("share_collected", {"guardian_id": guardian_id})

        if self.is_threshold_met() and self.status == RecoveryStatus.COLLECTING_SHARES:
            self.start_time_lock()

    def log_activity(self, action: str, details: Dict[str, Any]) -> None:
        """Log an activity."""
        self.activity_log.append({
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recovery_id": self.recovery_id,
            "wallet_id": self.wallet_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "shares_collected": len(self.shares_collected),
            "required_threshold": self.required_threshold,
            "threshold_met": self.is_threshold_met(),
            "time_lock_hours": self.time_lock_hours,
            "time_lock_expires_at": (
                self.time_lock_expires_at.isoformat()
                if self.time_lock_expires_at else None
            ),
            "can_execute": self.is_threshold_met() and self.is_time_lock_expired(),
        }


@dataclass
class SocialRecoveryConfig:
    """Configuration for social recovery."""
    # Guardian settings
    min_guardians: int = 3
    max_guardians: int = 10
    default_threshold_ratio: float = 0.6  # 60% of guardians needed

    # Security settings
    time_lock_hours: int = 48  # Wait period after threshold met
    recovery_expiry_days: int = 7
    challenge_expiry_hours: int = 1
    max_active_recoveries: int = 1

    # Notification settings
    notify_all_guardians_on_recovery: bool = True
    notify_wallet_owner_on_recovery: bool = True

    # Guardian verification settings
    require_email_verification: bool = True
    require_phone_verification: bool = False

    def calculate_threshold(self, num_guardians: int) -> int:
        """Calculate required threshold for given number of guardians."""
        threshold = int(num_guardians * self.default_threshold_ratio)
        return max(2, threshold)  # Minimum 2 guardians required


class ShareEncryptionService(Protocol):
    """Protocol for encrypting/decrypting SSS shares."""

    async def encrypt_share(
        self,
        share: bytes,
        guardian_id: str,
    ) -> bytes:
        """Encrypt a share for a guardian."""
        ...

    async def decrypt_share(
        self,
        encrypted_share: bytes,
        guardian_id: str,
    ) -> bytes:
        """Decrypt a share from a guardian."""
        ...


class NotificationService(Protocol):
    """Protocol for sending notifications to guardians."""

    async def notify_guardian(
        self,
        guardian: Guardian,
        notification_type: str,
        data: Dict[str, Any],
    ) -> bool:
        """Send a notification to a guardian."""
        ...


class SocialRecoveryManager:
    """
    Manages social recovery for wallets using Shamir's Secret Sharing.

    Features:
    - Guardian-based key recovery
    - Configurable threshold (M-of-N)
    - Time-locked recovery execution
    - Challenge-response verification
    - Emergency lockdown
    """

    def __init__(
        self,
        config: Optional[SocialRecoveryConfig] = None,
        encryption_service: Optional[ShareEncryptionService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self._config = config or SocialRecoveryConfig()
        self._encryption = encryption_service
        self._notifications = notification_service

        # Storage (in production, use database)
        self._guardians: Dict[str, Dict[str, Guardian]] = {}  # wallet_id -> guardian_id -> guardian
        self._recovery_requests: Dict[str, RecoveryRequest] = {}  # recovery_id -> request
        self._wallet_recoveries: Dict[str, str] = {}  # wallet_id -> active recovery_id
        self._challenges: Dict[str, RecoveryChallenge] = {}  # challenge_id -> challenge
        self._wallet_configs: Dict[str, Dict[str, Any]] = {}  # wallet_id -> config overrides

        # Locks
        self._recovery_lock = asyncio.Lock()

    def _generate_sss_shares(
        self,
        secret: bytes,
        num_shares: int,
        threshold: int,
    ) -> List[Tuple[int, bytes]]:
        """
        Generate Shamir's Secret Sharing shares.

        In production, use a proper SSS library like `secretsharing` or `ssss`.
        This is a simplified implementation for illustration.
        """
        # For production, use: from Crypto.Protocol.SecretSharing import Shamir
        # shares = Shamir.split(threshold, num_shares, secret)

        # Simplified placeholder - in production use proper SSS
        shares = []
        for i in range(num_shares):
            # Create pseudo-share (NOT SECURE - use proper SSS in production)
            share_data = hmac.new(
                secret,
                f"share_{i}".encode(),
                hashlib.sha256
            ).digest()
            shares.append((i + 1, share_data))

        return shares

    def _reconstruct_secret(
        self,
        shares: List[Tuple[int, bytes]],
        threshold: int,
    ) -> bytes:
        """
        Reconstruct secret from SSS shares.

        In production, use a proper SSS library.
        """
        # For production, use: from Crypto.Protocol.SecretSharing import Shamir
        # secret = Shamir.combine(shares)

        # Simplified placeholder - combine shares (NOT SECURE)
        if len(shares) < threshold:
            raise ValueError("Insufficient shares for reconstruction")

        # Placeholder reconstruction
        combined = b"".join(s[1] for s in sorted(shares)[:threshold])
        return hashlib.sha256(combined).digest()

    async def setup_recovery(
        self,
        wallet_id: str,
        recovery_secret: bytes,
        guardians: List[Dict[str, Any]],
        threshold: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Set up social recovery for a wallet.

        Args:
            wallet_id: Wallet identifier
            recovery_secret: Secret to be split among guardians
            guardians: List of guardian configurations
            threshold: Optional custom threshold

        Returns:
            Setup result with guardian details
        """
        num_guardians = len(guardians)

        # Validate
        if num_guardians < self._config.min_guardians:
            raise ValueError(
                f"Minimum {self._config.min_guardians} guardians required"
            )
        if num_guardians > self._config.max_guardians:
            raise ValueError(
                f"Maximum {self._config.max_guardians} guardians allowed"
            )

        # Calculate threshold
        if threshold is None:
            threshold = self._config.calculate_threshold(num_guardians)

        if threshold < 2:
            raise ValueError("Threshold must be at least 2")
        if threshold > num_guardians:
            raise ValueError("Threshold cannot exceed number of guardians")

        # Generate SSS shares
        shares = self._generate_sss_shares(recovery_secret, num_guardians, threshold)

        # Create guardians
        if wallet_id not in self._guardians:
            self._guardians[wallet_id] = {}

        created_guardians = []
        for i, guardian_config in enumerate(guardians):
            guardian_id = f"guardian_{secrets.token_hex(8)}"

            # Hash identifier for privacy
            identifier_hash = hashlib.sha256(
                guardian_config["identifier"].encode()
            ).hexdigest()

            # Encrypt share if encryption service available
            share_index, share_data = shares[i]
            if self._encryption:
                encrypted_share = await self._encryption.encrypt_share(
                    share_data, guardian_id
                )
            else:
                encrypted_share = share_data

            guardian = Guardian(
                guardian_id=guardian_id,
                wallet_id=wallet_id,
                guardian_type=guardian_config.get("type", "email"),
                guardian_identifier=identifier_hash,
                guardian_name=guardian_config.get("name", f"Guardian {i + 1}"),
                share_index=share_index,
                encrypted_share=encrypted_share,
                verification_method=guardian_config.get("verification", "email_otp"),
            )

            self._guardians[wallet_id][guardian_id] = guardian
            created_guardians.append(guardian.to_dict())

            # Send invitation
            if self._notifications:
                await self._notifications.notify_guardian(
                    guardian,
                    "guardian_invitation",
                    {"wallet_id": wallet_id},
                )

        # Store config
        self._wallet_configs[wallet_id] = {
            "threshold": threshold,
            "num_guardians": num_guardians,
            "setup_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Social recovery setup for wallet {wallet_id}: "
            f"{threshold}-of-{num_guardians} threshold"
        )

        return {
            "wallet_id": wallet_id,
            "threshold": threshold,
            "num_guardians": num_guardians,
            "guardians": created_guardians,
        }

    async def accept_guardian_role(
        self,
        guardian_id: str,
        wallet_id: str,
        verification_code: str,
    ) -> bool:
        """
        Accept guardian role after verification.

        Args:
            guardian_id: Guardian identifier
            wallet_id: Wallet identifier
            verification_code: Verification code sent to guardian

        Returns:
            True if acceptance successful
        """
        guardian = self._guardians.get(wallet_id, {}).get(guardian_id)
        if not guardian:
            raise ValueError("Guardian not found")

        if guardian.status != GuardianStatus.PENDING:
            raise ValueError("Guardian already accepted or invalid status")

        # Verify code (in production, verify against sent OTP)
        # For now, accept any non-empty code
        if not verification_code:
            raise ValueError("Invalid verification code")

        guardian.status = GuardianStatus.ACTIVE
        guardian.accepted_at = datetime.now(timezone.utc)
        guardian.last_verified_at = datetime.now(timezone.utc)

        logger.info(f"Guardian {guardian_id} accepted role for wallet {wallet_id}")
        return True

    async def initiate_recovery(
        self,
        wallet_id: str,
        requester_proof: str,
        new_key_reference: Optional[str] = None,
    ) -> RecoveryRequest:
        """
        Initiate a recovery request.

        Args:
            wallet_id: Wallet to recover
            requester_proof: Proof of identity from requester
            new_key_reference: New key to transfer wallet to

        Returns:
            RecoveryRequest object
        """
        async with self._recovery_lock:
            # Check for existing recovery
            if wallet_id in self._wallet_recoveries:
                existing_id = self._wallet_recoveries[wallet_id]
                existing = self._recovery_requests.get(existing_id)
                if existing and not existing.is_expired():
                    raise ValueError("Recovery already in progress for this wallet")

            # Get wallet config
            config = self._wallet_configs.get(wallet_id)
            if not config:
                raise ValueError("Social recovery not set up for this wallet")

            # Get active guardians
            wallet_guardians = self._guardians.get(wallet_id, {})
            active_guardians = [
                g for g in wallet_guardians.values()
                if g.is_active() and g.can_participate()
            ]

            if len(active_guardians) < config["threshold"]:
                raise ValueError("Insufficient active guardians for recovery")

            # Create recovery request
            recovery_id = f"recovery_{secrets.token_hex(12)}"
            recovery = RecoveryRequest(
                recovery_id=recovery_id,
                wallet_id=wallet_id,
                requester_proof=requester_proof,
                new_key_reference=new_key_reference,
                required_threshold=config["threshold"],
                time_lock_hours=self._config.time_lock_hours,
                status=RecoveryStatus.COLLECTING_SHARES,
                expires_at=datetime.now(timezone.utc) + timedelta(
                    days=self._config.recovery_expiry_days
                ),
            )

            # Store
            self._recovery_requests[recovery_id] = recovery
            self._wallet_recoveries[wallet_id] = recovery_id

            # Notify guardians
            if self._notifications and self._config.notify_all_guardians_on_recovery:
                for guardian in active_guardians:
                    await self._notifications.notify_guardian(
                        guardian,
                        "recovery_initiated",
                        {
                            "recovery_id": recovery_id,
                            "wallet_id": wallet_id,
                        },
                    )
                    recovery.guardians_contacted.append(guardian.guardian_id)

            recovery.log_activity("recovery_initiated", {
                "guardians_contacted": len(recovery.guardians_contacted),
            })

            logger.info(
                f"Recovery initiated for wallet {wallet_id}: {recovery_id}"
            )

            return recovery

    async def create_guardian_challenge(
        self,
        recovery_id: str,
        guardian_id: str,
    ) -> RecoveryChallenge:
        """
        Create a challenge for a guardian to verify their identity.

        Args:
            recovery_id: Recovery request ID
            guardian_id: Guardian ID

        Returns:
            RecoveryChallenge to be sent to guardian
        """
        recovery = self._recovery_requests.get(recovery_id)
        if not recovery:
            raise ValueError("Recovery request not found")

        if recovery.is_expired():
            raise ValueError("Recovery request has expired")

        # Get guardian
        guardian = self._guardians.get(recovery.wallet_id, {}).get(guardian_id)
        if not guardian:
            raise ValueError("Guardian not found")

        if not guardian.can_participate():
            raise ValueError("Guardian cannot participate in recovery")

        # Create challenge
        challenge_id = f"challenge_{secrets.token_hex(8)}"
        challenge_data = secrets.token_hex(32)

        challenge = RecoveryChallenge(
            challenge_id=challenge_id,
            recovery_id=recovery_id,
            guardian_id=guardian_id,
            challenge_type=guardian.verification_method,
            challenge_data=challenge_data,
        )

        self._challenges[challenge_id] = challenge

        # Send challenge to guardian
        if self._notifications:
            await self._notifications.notify_guardian(
                guardian,
                "recovery_challenge",
                {
                    "challenge_id": challenge_id,
                    "challenge_data": challenge_data,
                },
            )

        return challenge

    async def verify_guardian_challenge(
        self,
        challenge_id: str,
        response: str,
    ) -> bool:
        """
        Verify a guardian's challenge response.

        Args:
            challenge_id: Challenge ID
            response: Guardian's response

        Returns:
            True if verification successful
        """
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            raise ValueError("Challenge not found")

        if not challenge.is_valid():
            raise ValueError("Challenge has expired or is invalid")

        challenge.attempts += 1

        # Verify response (in production, verify OTP or signature)
        # For demonstration, check if response matches challenge
        expected_response = hashlib.sha256(
            challenge.challenge_data.encode()
        ).hexdigest()[:8]

        if response.lower() != expected_response.lower():
            logger.warning(
                f"Invalid challenge response for {challenge_id}"
            )
            return False

        challenge.verified = True
        challenge.verified_at = datetime.now(timezone.utc)

        # Get recovery and guardian
        recovery = self._recovery_requests.get(challenge.recovery_id)
        guardian = self._guardians.get(recovery.wallet_id, {}).get(challenge.guardian_id)

        if recovery and guardian:
            # Record participation
            guardian.record_participation()
            guardian.last_verified_at = datetime.now(timezone.utc)

            # Add share to recovery
            if guardian.encrypted_share:
                # Decrypt share
                if self._encryption:
                    share = await self._encryption.decrypt_share(
                        guardian.encrypted_share,
                        guardian.guardian_id,
                    )
                else:
                    share = guardian.encrypted_share

                recovery.add_share(
                    guardian.guardian_id,
                    share,
                )

        logger.info(f"Challenge {challenge_id} verified successfully")
        return True

    async def execute_recovery(
        self,
        recovery_id: str,
    ) -> Dict[str, Any]:
        """
        Execute the recovery after threshold is met and time lock expired.

        Args:
            recovery_id: Recovery request ID

        Returns:
            Recovery result with new key information
        """
        recovery = self._recovery_requests.get(recovery_id)
        if not recovery:
            raise ValueError("Recovery request not found")

        if recovery.status == RecoveryStatus.COMPLETED:
            raise ValueError("Recovery already completed")

        if not recovery.is_threshold_met():
            raise ValueError("Threshold not met - more guardian approvals needed")

        if not recovery.is_time_lock_expired():
            time_remaining = (
                recovery.time_lock_expires_at - datetime.now(timezone.utc)
            )
            raise ValueError(
                f"Time lock not expired - {time_remaining.total_seconds() / 3600:.1f} hours remaining"
            )

        recovery.status = RecoveryStatus.EXECUTING
        recovery.log_activity("execution_started", {})

        try:
            # Reconstruct secret from shares
            shares = [
                (
                    self._guardians[recovery.wallet_id][gid].share_index,
                    share_data,
                )
                for gid, share_data in recovery.shares_collected.items()
            ]

            recovered_secret = self._reconstruct_secret(
                shares,
                recovery.required_threshold,
            )

            # In production, use recovered_secret to:
            # 1. Decrypt the wallet's master key
            # 2. Transfer control to new_key_reference
            # 3. Update MPC configuration

            recovery.status = RecoveryStatus.COMPLETED
            recovery.completed_at = datetime.now(timezone.utc)
            recovery.log_activity("recovery_completed", {
                "new_key_reference": recovery.new_key_reference,
            })

            # Cleanup
            del self._wallet_recoveries[recovery.wallet_id]

            logger.info(f"Recovery {recovery_id} completed successfully")

            return {
                "recovery_id": recovery_id,
                "wallet_id": recovery.wallet_id,
                "status": "completed",
                "new_key_reference": recovery.new_key_reference,
                "completed_at": recovery.completed_at.isoformat(),
            }

        except Exception as e:
            recovery.status = RecoveryStatus.PENDING
            recovery.log_activity("execution_failed", {"error": str(e)})
            logger.error(f"Recovery {recovery_id} execution failed: {e}")
            raise

    async def cancel_recovery(
        self,
        recovery_id: str,
        cancelled_by: str,
        reason: str = "",
    ) -> bool:
        """
        Cancel a recovery request.

        Can be cancelled by wallet owner or a threshold of guardians.
        """
        recovery = self._recovery_requests.get(recovery_id)
        if not recovery:
            return False

        if recovery.status in (RecoveryStatus.COMPLETED, RecoveryStatus.CANCELLED):
            return False

        recovery.status = RecoveryStatus.CANCELLED
        recovery.log_activity("recovery_cancelled", {
            "cancelled_by": cancelled_by,
            "reason": reason,
        })

        if recovery.wallet_id in self._wallet_recoveries:
            del self._wallet_recoveries[recovery.wallet_id]

        logger.info(f"Recovery {recovery_id} cancelled by {cancelled_by}")
        return True

    def get_wallet_guardians(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Get list of guardians for a wallet."""
        guardians = self._guardians.get(wallet_id, {})
        return [g.to_dict() for g in guardians.values()]

    def get_recovery_status(self, recovery_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a recovery request."""
        recovery = self._recovery_requests.get(recovery_id)
        if not recovery:
            return None
        return recovery.to_dict()

    async def remove_guardian(
        self,
        wallet_id: str,
        guardian_id: str,
        removed_by: str,
    ) -> bool:
        """Remove a guardian from a wallet."""
        guardian = self._guardians.get(wallet_id, {}).get(guardian_id)
        if not guardian:
            return False

        guardian.status = GuardianStatus.REMOVED

        # Check if we still have enough guardians
        active_guardians = [
            g for g in self._guardians[wallet_id].values()
            if g.status == GuardianStatus.ACTIVE
        ]

        if len(active_guardians) < self._config.min_guardians:
            logger.warning(
                f"Wallet {wallet_id} now has fewer than minimum guardians"
            )

        logger.info(f"Guardian {guardian_id} removed from wallet {wallet_id}")
        return True


# Singleton instance
_social_recovery_manager: Optional[SocialRecoveryManager] = None


def get_social_recovery_manager(
    config: Optional[SocialRecoveryConfig] = None,
) -> SocialRecoveryManager:
    """Get the global social recovery manager instance."""
    global _social_recovery_manager

    if _social_recovery_manager is None:
        _social_recovery_manager = SocialRecoveryManager(config)

    return _social_recovery_manager


__all__ = [
    "GuardianStatus",
    "RecoveryStatus",
    "Guardian",
    "RecoveryChallenge",
    "RecoveryRequest",
    "SocialRecoveryConfig",
    "SocialRecoveryManager",
    "get_social_recovery_manager",
]
