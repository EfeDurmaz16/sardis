"""
MPC Wallet Key Rotation mechanism for Sardis.

Provides secure key rotation for MPC-backed wallets with:
- Scheduled automatic rotation
- Grace periods for old keys
- Emergency rotation procedures
- Audit trail for all rotation events
- Support for multiple MPC providers (Turnkey, Fireblocks)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from sardis_v2_core import Wallet

logger = logging.getLogger(__name__)


class MPCKeyStatus(str, Enum):
    """Status of an MPC wallet key."""
    ACTIVE = "active"
    ROTATING = "rotating"
    PENDING_ACTIVATION = "pending_activation"
    REVOKED = "revoked"
    COMPROMISED = "compromised"
    EXPIRED = "expired"


class RotationReason(str, Enum):
    """Reason for key rotation."""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    SECURITY_INCIDENT = "security_incident"
    COMPLIANCE = "compliance"
    KEY_EXPIRY = "key_expiry"
    PROVIDER_MIGRATION = "provider_migration"


@dataclass
class MPCKeyInfo:
    """Information about an MPC wallet key."""
    key_id: str
    wallet_id: str
    mpc_provider: str
    mpc_key_reference: str  # Provider-specific key identifier
    algorithm: str = "ecdsa-secp256k1"  # Default for EVM chains
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    status: MPCKeyStatus = MPCKeyStatus.ACTIVE

    # Rotation tracking
    previous_key_id: Optional[str] = None
    rotation_started_at: Optional[datetime] = None
    rotation_completed_at: Optional[datetime] = None

    # Security metadata
    key_fingerprint: Optional[str] = None
    last_used_at: Optional[datetime] = None
    use_count: int = 0

    @property
    def is_valid(self) -> bool:
        """Check if key is valid for signing."""
        if self.status not in (MPCKeyStatus.ACTIVE, MPCKeyStatus.ROTATING):
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def is_in_grace_period(self) -> bool:
        """Check if key is in rotation grace period."""
        return self.status == MPCKeyStatus.ROTATING

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Get days until key expires."""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    def record_use(self) -> None:
        """Record key usage."""
        self.last_used_at = datetime.now(timezone.utc)
        self.use_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key_id": self.key_id,
            "wallet_id": self.wallet_id,
            "mpc_provider": self.mpc_provider,
            "mpc_key_reference": self.mpc_key_reference,
            "algorithm": self.algorithm,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "previous_key_id": self.previous_key_id,
            "key_fingerprint": self.key_fingerprint,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "use_count": self.use_count,
            "days_until_expiry": self.days_until_expiry,
        }


@dataclass
class KeyRotationEvent:
    """Audit event for key rotation."""
    event_id: str
    wallet_id: str
    old_key_id: str
    new_key_id: str
    reason: RotationReason
    initiated_at: datetime
    initiated_by: str  # "system", "user", "security"
    completed_at: Optional[datetime] = None
    status: str = "in_progress"  # "in_progress", "completed", "failed", "cancelled"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "wallet_id": self.wallet_id,
            "old_key_id": self.old_key_id,
            "new_key_id": self.new_key_id,
            "reason": self.reason.value,
            "initiated_at": self.initiated_at.isoformat(),
            "initiated_by": self.initiated_by,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class MPCKeyRotationPolicy:
    """Policy configuration for MPC key rotation."""
    # Automatic rotation settings
    rotation_interval_days: int = 90
    grace_period_hours: int = 48  # Longer grace period for MPC wallets
    max_key_age_days: int = 180

    # Notification settings
    notification_threshold_days: int = 14
    send_expiry_warnings: bool = True

    # Security settings
    require_mfa_for_rotation: bool = True
    allow_emergency_rotation: bool = True
    max_concurrent_rotations: int = 1

    # Provider-specific settings
    turnkey_settings: Dict[str, Any] = field(default_factory=dict)
    fireblocks_settings: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        """Validate policy configuration."""
        errors = []
        if self.rotation_interval_days < 30:
            errors.append("Rotation interval must be at least 30 days")
        if self.grace_period_hours < 24:
            errors.append("Grace period must be at least 24 hours")
        if self.max_key_age_days <= self.rotation_interval_days:
            errors.append("Max key age must be greater than rotation interval")
        return errors


class MPCSignerPort(Protocol):
    """Protocol for MPC signing providers."""

    async def create_key(
        self,
        wallet_id: str,
        algorithm: str = "ecdsa-secp256k1",
    ) -> Dict[str, Any]:
        """Create a new signing key."""
        ...

    async def get_public_key(self, key_reference: str) -> bytes:
        """Get public key for a key reference."""
        ...

    async def rotate_key(
        self,
        old_key_reference: str,
        new_key_reference: str,
    ) -> Dict[str, Any]:
        """Rotate from old key to new key."""
        ...

    async def revoke_key(self, key_reference: str) -> bool:
        """Revoke a key."""
        ...


class KeyRotationCallback(Protocol):
    """Callback protocol for rotation events."""

    async def on_rotation_started(
        self,
        event: KeyRotationEvent,
    ) -> None:
        """Called when rotation starts."""
        ...

    async def on_rotation_completed(
        self,
        event: KeyRotationEvent,
    ) -> None:
        """Called when rotation completes."""
        ...

    async def on_rotation_failed(
        self,
        event: KeyRotationEvent,
        error: Exception,
    ) -> None:
        """Called when rotation fails."""
        ...


class MPCKeyRotationManager:
    """
    Manages MPC wallet key rotation with security best practices.

    Features:
    - Automatic scheduled rotation
    - Emergency rotation for security incidents
    - Grace periods for seamless transitions
    - Full audit trail
    - Multi-provider support (Turnkey, Fireblocks)
    """

    def __init__(
        self,
        policy: Optional[MPCKeyRotationPolicy] = None,
        mpc_signer: Optional[MPCSignerPort] = None,
        callback: Optional[KeyRotationCallback] = None,
    ):
        self._policy = policy or MPCKeyRotationPolicy()
        self._mpc_signer = mpc_signer
        self._callback = callback

        # Storage (in production, use database)
        self._keys: Dict[str, Dict[str, MPCKeyInfo]] = {}  # wallet_id -> key_id -> key
        self._active_keys: Dict[str, str] = {}  # wallet_id -> active_key_id
        self._rotation_events: List[KeyRotationEvent] = []
        self._pending_rotations: Dict[str, KeyRotationEvent] = {}  # wallet_id -> event

        # Lock for concurrent operations
        self._rotation_lock = asyncio.Lock()

    async def register_key(
        self,
        wallet_id: str,
        mpc_provider: str,
        mpc_key_reference: str,
        algorithm: str = "ecdsa-secp256k1",
        expires_at: Optional[datetime] = None,
        public_key: Optional[bytes] = None,
    ) -> MPCKeyInfo:
        """
        Register a new MPC key for a wallet.

        Args:
            wallet_id: Wallet identifier
            mpc_provider: MPC provider name
            mpc_key_reference: Provider-specific key reference
            algorithm: Signing algorithm
            expires_at: Optional expiration time
            public_key: Optional public key for fingerprint

        Returns:
            MPCKeyInfo for the registered key
        """
        now = datetime.now(timezone.utc)

        # Generate key ID
        key_id = f"mpckey_{secrets.token_hex(12)}"

        # Set expiration based on policy if not provided
        if expires_at is None:
            expires_at = now + timedelta(days=self._policy.rotation_interval_days)

        # Calculate fingerprint if public key provided
        fingerprint = None
        if public_key:
            fingerprint = hashlib.sha256(public_key).hexdigest()[:16]

        # Check for existing active key
        current_active_id = self._active_keys.get(wallet_id)
        previous_key_id = None

        if current_active_id:
            # Put current key into rotation mode
            current_key = self._keys[wallet_id][current_active_id]
            current_key.status = MPCKeyStatus.ROTATING
            current_key.rotation_started_at = now
            previous_key_id = current_active_id

            logger.info(
                f"Key {current_active_id} for wallet {wallet_id} entering grace period"
            )

        # Create new key
        new_key = MPCKeyInfo(
            key_id=key_id,
            wallet_id=wallet_id,
            mpc_provider=mpc_provider,
            mpc_key_reference=mpc_key_reference,
            algorithm=algorithm,
            created_at=now,
            expires_at=expires_at,
            status=MPCKeyStatus.ACTIVE,
            previous_key_id=previous_key_id,
            key_fingerprint=fingerprint,
        )

        # Store key
        if wallet_id not in self._keys:
            self._keys[wallet_id] = {}
        self._keys[wallet_id][key_id] = new_key
        self._active_keys[wallet_id] = key_id

        logger.info(f"Registered new MPC key {key_id} for wallet {wallet_id}")

        return new_key

    def get_active_key(self, wallet_id: str) -> Optional[MPCKeyInfo]:
        """Get the currently active key for a wallet."""
        key_id = self._active_keys.get(wallet_id)
        if not key_id:
            return None

        wallet_keys = self._keys.get(wallet_id, {})
        key = wallet_keys.get(key_id)

        if key and key.is_valid:
            return key
        return None

    def get_valid_keys(self, wallet_id: str) -> List[MPCKeyInfo]:
        """Get all valid keys for a wallet (including grace period keys)."""
        wallet_keys = self._keys.get(wallet_id, {})
        return [k for k in wallet_keys.values() if k.is_valid]

    async def rotate_key(
        self,
        wallet_id: str,
        reason: RotationReason = RotationReason.SCHEDULED,
        initiated_by: str = "system",
        force: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KeyRotationEvent:
        """
        Perform a key rotation for a wallet.

        Args:
            wallet_id: Wallet identifier
            reason: Reason for rotation
            initiated_by: Who initiated the rotation
            force: Force rotation even if concurrent rotation exists
            metadata: Additional metadata for the event

        Returns:
            KeyRotationEvent for the rotation

        Raises:
            ValueError: If wallet has no active key or rotation already in progress
        """
        async with self._rotation_lock:
            # Check for existing rotation
            if wallet_id in self._pending_rotations and not force:
                raise ValueError(
                    f"Rotation already in progress for wallet {wallet_id}"
                )

            # Get current active key
            current_key = self.get_active_key(wallet_id)
            if not current_key:
                raise ValueError(f"No active key found for wallet {wallet_id}")

            now = datetime.now(timezone.utc)

            # Create rotation event
            event = KeyRotationEvent(
                event_id=f"rot_{secrets.token_hex(8)}",
                wallet_id=wallet_id,
                old_key_id=current_key.key_id,
                new_key_id="pending",
                reason=reason,
                initiated_at=now,
                initiated_by=initiated_by,
                metadata=metadata or {},
            )

            self._pending_rotations[wallet_id] = event

            # Notify callback
            if self._callback:
                try:
                    await self._callback.on_rotation_started(event)
                except Exception as e:
                    logger.warning(f"Callback error on rotation start: {e}")

            try:
                # Create new key via MPC provider
                if self._mpc_signer:
                    new_key_data = await self._mpc_signer.create_key(
                        wallet_id=wallet_id,
                        algorithm=current_key.algorithm,
                    )
                    new_key_reference = new_key_data.get("key_reference", f"ref_{secrets.token_hex(8)}")
                    public_key = new_key_data.get("public_key")
                else:
                    # For testing without MPC provider
                    new_key_reference = f"ref_{secrets.token_hex(8)}"
                    public_key = None

                # Register new key
                new_key = await self.register_key(
                    wallet_id=wallet_id,
                    mpc_provider=current_key.mpc_provider,
                    mpc_key_reference=new_key_reference,
                    algorithm=current_key.algorithm,
                    public_key=public_key,
                )

                # Update event
                event.new_key_id = new_key.key_id
                event.completed_at = datetime.now(timezone.utc)
                event.status = "completed"

                # Store event
                self._rotation_events.append(event)

                # Notify callback
                if self._callback:
                    try:
                        await self._callback.on_rotation_completed(event)
                    except Exception as e:
                        logger.warning(f"Callback error on rotation complete: {e}")

                logger.info(
                    f"Key rotation completed for wallet {wallet_id}: "
                    f"{current_key.key_id} -> {new_key.key_id}"
                )

                return event

            except Exception as e:
                event.status = "failed"
                event.error_message = str(e)
                event.completed_at = datetime.now(timezone.utc)
                self._rotation_events.append(event)

                # Notify callback
                if self._callback:
                    try:
                        await self._callback.on_rotation_failed(event, e)
                    except Exception as cb_error:
                        logger.warning(f"Callback error on rotation failure: {cb_error}")

                logger.error(f"Key rotation failed for wallet {wallet_id}: {e}")
                raise

            finally:
                del self._pending_rotations[wallet_id]

    async def emergency_rotate(
        self,
        wallet_id: str,
        reason: str = "security_incident",
        initiated_by: str = "security",
    ) -> KeyRotationEvent:
        """
        Perform emergency key rotation with immediate revocation.

        This immediately revokes the old key without grace period.
        """
        if not self._policy.allow_emergency_rotation:
            raise ValueError("Emergency rotation not allowed by policy")

        # Perform rotation
        event = await self.rotate_key(
            wallet_id=wallet_id,
            reason=RotationReason.SECURITY_INCIDENT,
            initiated_by=initiated_by,
            force=True,
            metadata={"emergency": True, "reason": reason},
        )

        # Immediately revoke old key
        if event.old_key_id:
            await self.revoke_key(wallet_id, event.old_key_id, reason="emergency_revocation")

        return event

    async def revoke_key(
        self,
        wallet_id: str,
        key_id: str,
        reason: str = "manual",
    ) -> bool:
        """Revoke a specific key."""
        wallet_keys = self._keys.get(wallet_id, {})
        key = wallet_keys.get(key_id)

        if not key:
            return False

        key.status = MPCKeyStatus.REVOKED

        # Revoke in MPC provider
        if self._mpc_signer:
            try:
                await self._mpc_signer.revoke_key(key.mpc_key_reference)
            except Exception as e:
                logger.warning(f"Failed to revoke key in MPC provider: {e}")

        # If this was the active key, clear active status
        if self._active_keys.get(wallet_id) == key_id:
            del self._active_keys[wallet_id]

        logger.info(f"Revoked key {key_id} for wallet {wallet_id}: {reason}")
        return True

    async def cleanup_expired_keys(self) -> int:
        """
        Clean up expired keys and finalize rotation grace periods.

        Returns the number of keys affected.
        """
        now = datetime.now(timezone.utc)
        count = 0
        grace_period = timedelta(hours=self._policy.grace_period_hours)

        for wallet_id, wallet_keys in self._keys.items():
            for key_id, key in list(wallet_keys.items()):
                # Check expiration
                if key.expires_at and now > key.expires_at:
                    if key.status not in (MPCKeyStatus.REVOKED, MPCKeyStatus.EXPIRED):
                        key.status = MPCKeyStatus.EXPIRED
                        count += 1
                        logger.info(f"Key {key_id} for wallet {wallet_id} expired")

                # Check grace period end
                if key.status == MPCKeyStatus.ROTATING:
                    if key.rotation_started_at:
                        if now > key.rotation_started_at + grace_period:
                            key.status = MPCKeyStatus.REVOKED
                            count += 1
                            logger.info(
                                f"Key {key_id} for wallet {wallet_id} grace period ended"
                            )

        return count

    def get_keys_needing_rotation(self) -> List[tuple]:
        """Get list of (wallet_id, key_id, expires_at) that should be rotated soon."""
        now = datetime.now(timezone.utc)
        threshold = timedelta(days=self._policy.notification_threshold_days)
        result = []

        for wallet_id, key_id in self._active_keys.items():
            key = self._keys[wallet_id][key_id]
            if key.expires_at:
                if key.expires_at - now <= threshold:
                    result.append((wallet_id, key_id, key.expires_at))

        return result

    def get_rotation_history(
        self,
        wallet_id: str,
        limit: int = 100,
    ) -> List[KeyRotationEvent]:
        """Get rotation event history for a wallet."""
        events = [e for e in self._rotation_events if e.wallet_id == wallet_id]
        return sorted(events, key=lambda e: e.initiated_at, reverse=True)[:limit]

    def get_key_usage_stats(self, wallet_id: str) -> Dict[str, Any]:
        """Get key usage statistics for a wallet."""
        wallet_keys = self._keys.get(wallet_id, {})

        stats = {
            "total_keys": len(wallet_keys),
            "active_keys": 0,
            "rotating_keys": 0,
            "revoked_keys": 0,
            "expired_keys": 0,
            "total_uses": 0,
        }

        for key in wallet_keys.values():
            stats["total_uses"] += key.use_count
            if key.status == MPCKeyStatus.ACTIVE:
                stats["active_keys"] += 1
            elif key.status == MPCKeyStatus.ROTATING:
                stats["rotating_keys"] += 1
            elif key.status == MPCKeyStatus.REVOKED:
                stats["revoked_keys"] += 1
            elif key.status == MPCKeyStatus.EXPIRED:
                stats["expired_keys"] += 1

        return stats


# Singleton instance
_mpc_key_rotation_manager: Optional[MPCKeyRotationManager] = None


def get_mpc_key_rotation_manager(
    policy: Optional[MPCKeyRotationPolicy] = None,
    mpc_signer: Optional[MPCSignerPort] = None,
) -> MPCKeyRotationManager:
    """Get the global MPC key rotation manager instance."""
    global _mpc_key_rotation_manager

    if _mpc_key_rotation_manager is None:
        _mpc_key_rotation_manager = MPCKeyRotationManager(policy, mpc_signer)

    return _mpc_key_rotation_manager


__all__ = [
    "MPCKeyStatus",
    "RotationReason",
    "MPCKeyInfo",
    "KeyRotationEvent",
    "MPCKeyRotationPolicy",
    "MPCSignerPort",
    "KeyRotationCallback",
    "MPCKeyRotationManager",
    "get_mpc_key_rotation_manager",
]
