"""
Session Management for Sardis Wallets.

Provides secure session management for wallet access with:
- Time-limited sessions
- Device binding
- IP restrictions
- Multi-factor authentication support
- Session revocation
- Concurrent session limits
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


class SessionStatus(str, Enum):
    """Status of a session."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    PENDING_MFA = "pending_mfa"


class SessionAction(str, Enum):
    """Actions that can be performed in a session."""
    READ = "read"
    SIGN = "sign"
    TRANSFER = "transfer"
    SETTINGS = "settings"
    ADMIN = "admin"


class MFAMethod(str, Enum):
    """Multi-factor authentication methods."""
    TOTP = "totp"  # Time-based OTP (Google Authenticator)
    SMS = "sms"
    EMAIL = "email"
    HARDWARE_KEY = "hardware_key"  # FIDO2/WebAuthn
    BIOMETRIC = "biometric"


@dataclass
class DeviceInfo:
    """Information about a device."""
    device_id: str
    device_type: str  # "mobile", "desktop", "browser"
    user_agent: str = ""
    fingerprint: Optional[str] = None  # Browser/device fingerprint
    push_token: Optional[str] = None  # For push notifications
    is_trusted: bool = False
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "is_trusted": self.is_trusted,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
        }


@dataclass
class Session:
    """A wallet access session."""
    session_id: str
    wallet_id: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24)
    )
    last_activity_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: SessionStatus = SessionStatus.ACTIVE

    # Device and location info
    device_info: Optional[DeviceInfo] = None
    ip_address: Optional[str] = None
    geo_location: Optional[str] = None

    # Authentication info
    mfa_verified: bool = False
    mfa_method: Optional[MFAMethod] = None
    mfa_verified_at: Optional[datetime] = None

    # Permissions
    allowed_actions: Set[SessionAction] = field(
        default_factory=lambda: {SessionAction.READ}
    )
    max_transaction_amount: Optional[str] = None

    # Session metadata
    refresh_token: Optional[str] = None
    refresh_count: int = 0
    max_refreshes: int = 10
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if session is valid."""
        if self.status != SessionStatus.ACTIVE:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def is_mfa_required(self, action: SessionAction) -> bool:
        """Check if MFA is required for an action."""
        mfa_required_actions = {SessionAction.SIGN, SessionAction.TRANSFER, SessionAction.ADMIN}
        return action in mfa_required_actions and not self.mfa_verified

    def can_perform(self, action: SessionAction) -> Tuple[bool, str]:
        """Check if session can perform an action."""
        if not self.is_valid():
            return False, "Session is not valid"

        if action not in self.allowed_actions:
            return False, f"Action {action.value} not allowed in this session"

        if self.is_mfa_required(action):
            return False, "MFA verification required"

        return True, "OK"

    def record_activity(self) -> None:
        """Record session activity."""
        self.last_activity_at = datetime.now(timezone.utc)

    def extend(self, hours: int = 24) -> None:
        """Extend session expiration."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.refresh_count += 1

    def revoke(self, reason: str = "") -> None:
        """Revoke the session."""
        self.status = SessionStatus.REVOKED
        self.metadata["revocation_reason"] = reason
        self.metadata["revoked_at"] = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "wallet_id": self.wallet_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "status": self.status.value,
            "device": self.device_info.to_dict() if self.device_info else None,
            "ip_address": self.ip_address,
            "mfa_verified": self.mfa_verified,
            "allowed_actions": [a.value for a in self.allowed_actions],
        }


@dataclass
class MFAChallenge:
    """An MFA challenge for session verification."""
    challenge_id: str
    session_id: str
    method: MFAMethod
    challenge_data: str  # TOTP code, OTP, or challenge nonce
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=5)
    )
    attempts: int = 0
    max_attempts: int = 3
    verified: bool = False

    def is_valid(self) -> bool:
        """Check if challenge is still valid."""
        if self.verified:
            return False
        if self.attempts >= self.max_attempts:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class SessionPolicy:
    """Policy configuration for sessions."""
    # Session duration
    default_session_hours: int = 24
    max_session_hours: int = 168  # 7 days
    idle_timeout_minutes: int = 30

    # MFA requirements
    require_mfa_for_sign: bool = True
    require_mfa_for_transfer: bool = True
    require_mfa_for_settings: bool = True
    mfa_validity_hours: int = 24

    # Device settings
    trust_device_after_mfa: bool = True
    max_trusted_devices: int = 5

    # Concurrent session limits
    max_concurrent_sessions: int = 3
    allow_same_device_sessions: bool = False

    # IP restrictions
    allowed_ips: Optional[List[str]] = None
    blocked_ips: List[str] = field(default_factory=list)
    allow_ip_change: bool = True

    # Security settings
    rotate_tokens_on_refresh: bool = True
    invalidate_on_password_change: bool = True


@dataclass
class SessionAuditEvent:
    """Audit event for session activities."""
    event_id: str
    session_id: str
    wallet_id: str
    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    action: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "wallet_id": self.wallet_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "action": self.action,
            "success": self.success,
        }


class MFAProvider(Protocol):
    """Protocol for MFA providers."""

    async def send_challenge(
        self,
        method: MFAMethod,
        user_id: str,
        destination: str,  # Email, phone, etc.
    ) -> str:
        """Send MFA challenge, returns challenge data."""
        ...

    async def verify_challenge(
        self,
        method: MFAMethod,
        challenge_data: str,
        response: str,
    ) -> bool:
        """Verify MFA response."""
        ...


class SessionManager:
    """
    Manages wallet access sessions.

    Features:
    - Secure session creation and validation
    - MFA integration
    - Device management
    - IP restrictions
    - Concurrent session limits
    - Session audit logging
    """

    def __init__(
        self,
        policy: Optional[SessionPolicy] = None,
        mfa_provider: Optional[MFAProvider] = None,
    ):
        self._policy = policy or SessionPolicy()
        self._mfa_provider = mfa_provider

        # Storage (in production, use database/Redis)
        self._sessions: Dict[str, Session] = {}  # session_id -> session
        self._wallet_sessions: Dict[str, List[str]] = {}  # wallet_id -> [session_ids]
        self._devices: Dict[str, Dict[str, DeviceInfo]] = {}  # wallet_id -> device_id -> device
        self._mfa_challenges: Dict[str, MFAChallenge] = {}  # challenge_id -> challenge
        self._audit_log: List[SessionAuditEvent] = []

        # Token storage
        self._refresh_tokens: Dict[str, str] = {}  # refresh_token -> session_id

        # Lock for concurrent operations
        self._lock = asyncio.Lock()

    def _generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return f"sess_{secrets.token_urlsafe(32)}"

    def _generate_refresh_token(self) -> str:
        """Generate a secure refresh token."""
        return secrets.token_urlsafe(64)

    async def create_session(
        self,
        wallet_id: str,
        user_id: str,
        device_info: Optional[DeviceInfo] = None,
        ip_address: Optional[str] = None,
        allowed_actions: Optional[Set[SessionAction]] = None,
        duration_hours: Optional[int] = None,
    ) -> Session:
        """
        Create a new session for wallet access.

        Args:
            wallet_id: Wallet identifier
            user_id: User identifier
            device_info: Device information
            ip_address: Client IP address
            allowed_actions: Actions allowed in session
            duration_hours: Session duration

        Returns:
            New Session object
        """
        async with self._lock:
            # Check IP restrictions
            if not self._check_ip_allowed(ip_address):
                raise ValueError("IP address not allowed")

            # Check concurrent session limits
            await self._enforce_session_limits(wallet_id, device_info)

            # Create session
            session_id = self._generate_session_id()
            duration = duration_hours or self._policy.default_session_hours
            duration = min(duration, self._policy.max_session_hours)

            session = Session(
                session_id=session_id,
                wallet_id=wallet_id,
                user_id=user_id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=duration),
                device_info=device_info,
                ip_address=ip_address,
                allowed_actions=allowed_actions or {SessionAction.READ},
                refresh_token=self._generate_refresh_token(),
            )

            # Check if device is trusted (with fingerprint cross-check)
            if device_info:
                trusted_device = self._get_trusted_device(
                    wallet_id,
                    device_info.device_id,
                    presented_fingerprint=device_info.fingerprint,
                )
                if trusted_device:
                    session.mfa_verified = True
                    session.mfa_verified_at = datetime.now(timezone.utc)

            # Store session
            self._sessions[session_id] = session
            if wallet_id not in self._wallet_sessions:
                self._wallet_sessions[wallet_id] = []
            self._wallet_sessions[wallet_id].append(session_id)

            # Store refresh token
            if session.refresh_token:
                self._refresh_tokens[session.refresh_token] = session_id

            # Update device info
            if device_info:
                self._update_device(wallet_id, device_info)

            # Audit log
            self._log_event(
                session_id=session_id,
                wallet_id=wallet_id,
                event_type="session_created",
                ip_address=ip_address,
                device_id=device_info.device_id if device_info else None,
            )

            logger.info(f"Created session {session_id} for wallet {wallet_id}")
            return session

    def _check_ip_allowed(self, ip_address: Optional[str]) -> bool:
        """Check if IP address is allowed."""
        if not ip_address:
            return True

        # Check blocked IPs
        if ip_address in self._policy.blocked_ips:
            return False

        # Check allowed IPs (if whitelist configured)
        if self._policy.allowed_ips:
            return ip_address in self._policy.allowed_ips

        return True

    async def _enforce_session_limits(
        self,
        wallet_id: str,
        device_info: Optional[DeviceInfo],
    ) -> None:
        """Enforce concurrent session limits."""
        existing_sessions = self._wallet_sessions.get(wallet_id, [])
        active_sessions = [
            self._sessions[sid] for sid in existing_sessions
            if sid in self._sessions and self._sessions[sid].is_valid()
        ]

        # Check same device
        if device_info and not self._policy.allow_same_device_sessions:
            for session in active_sessions:
                if (session.device_info and
                    session.device_info.device_id == device_info.device_id):
                    await self.revoke_session(session.session_id, "new_session_same_device")

        # Enforce max concurrent sessions
        while len(active_sessions) >= self._policy.max_concurrent_sessions:
            # Revoke oldest session
            oldest = min(active_sessions, key=lambda s: s.created_at)
            await self.revoke_session(oldest.session_id, "max_sessions_exceeded")
            active_sessions.remove(oldest)

    def _get_trusted_device(
        self,
        wallet_id: str,
        device_id: str,
        presented_fingerprint: Optional[str] = None,
    ) -> Optional[DeviceInfo]:
        """Get a trusted device with additional security checks.

        SECURITY: A device_id alone is a client-provided string that can be
        replayed from logs or API responses. We add:
        1. Fingerprint cross-check (if the stored device has one)
        2. Trust expiry (devices trusted > 90 days ago must re-verify MFA)
        """
        devices = self._devices.get(wallet_id, {})
        device = devices.get(device_id)
        if not device or not device.is_trusted:
            return None

        # Check trust expiry: devices trusted more than 90 days ago must re-MFA
        trust_age = datetime.now(timezone.utc) - device.first_seen_at
        if trust_age > timedelta(days=90):
            logger.info(
                "Trusted device %s for wallet %s expired (age=%s days), requiring re-MFA",
                device_id, wallet_id, trust_age.days,
            )
            device.is_trusted = False
            return None

        # Cross-check fingerprint if the stored device has one
        if device.fingerprint and presented_fingerprint:
            if not hmac.compare_digest(device.fingerprint, presented_fingerprint):
                logger.warning(
                    "Device fingerprint mismatch for device %s on wallet %s - "
                    "possible device_id replay attack",
                    device_id, wallet_id,
                )
                return None

        return device

    def _update_device(
        self,
        wallet_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Update device information."""
        if wallet_id not in self._devices:
            self._devices[wallet_id] = {}

        device_info.last_seen_at = datetime.now(timezone.utc)
        self._devices[wallet_id][device_info.device_id] = device_info

    async def validate_session(
        self,
        session_id: str,
        action: Optional[SessionAction] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Session]]:
        """
        Validate a session and optionally check action permission.

        Args:
            session_id: Session identifier
            action: Action to validate
            ip_address: Current IP address

        Returns:
            Tuple of (is_valid, reason, session)
        """
        session = self._sessions.get(session_id)

        if not session:
            return False, "Session not found", None

        if not session.is_valid():
            return False, f"Session is {session.status.value}", session

        # Check IP change
        if ip_address and session.ip_address:
            if ip_address != session.ip_address and not self._policy.allow_ip_change:
                await self.revoke_session(session_id, "ip_address_changed")
                return False, "IP address changed", session

        # Check idle timeout
        idle_time = datetime.now(timezone.utc) - session.last_activity_at
        if idle_time > timedelta(minutes=self._policy.idle_timeout_minutes):
            session.status = SessionStatus.EXPIRED
            return False, "Session expired due to inactivity", session

        # Check action permission
        if action:
            can_perform, reason = session.can_perform(action)
            if not can_perform:
                return False, reason, session

        # Record activity
        session.record_activity()

        return True, "OK", session

    async def refresh_session(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[Optional[Session], Optional[str]]:
        """
        Refresh a session using refresh token.

        Args:
            refresh_token: Refresh token
            ip_address: Current IP address

        Returns:
            Tuple of (new_session, new_refresh_token)
        """
        async with self._lock:
            session_id = self._refresh_tokens.get(refresh_token)
            if not session_id:
                return None, None

            session = self._sessions.get(session_id)
            if not session:
                return None, None

            if session.status != SessionStatus.ACTIVE:
                return None, None

            # Check refresh limit
            if session.refresh_count >= session.max_refreshes:
                await self.revoke_session(session_id, "max_refreshes_exceeded")
                return None, None

            # Extend session
            session.extend(self._policy.default_session_hours)

            # Rotate refresh token if configured
            new_refresh_token = refresh_token
            if self._policy.rotate_tokens_on_refresh:
                new_refresh_token = self._generate_refresh_token()
                del self._refresh_tokens[refresh_token]
                self._refresh_tokens[new_refresh_token] = session_id
                session.refresh_token = new_refresh_token

            self._log_event(
                session_id=session_id,
                wallet_id=session.wallet_id,
                event_type="session_refreshed",
                ip_address=ip_address,
            )

            return session, new_refresh_token

    async def initiate_mfa(
        self,
        session_id: str,
        method: MFAMethod,
        destination: Optional[str] = None,
    ) -> MFAChallenge:
        """
        Initiate MFA verification for a session.

        Args:
            session_id: Session identifier
            method: MFA method to use
            destination: Destination for OTP (email/phone)

        Returns:
            MFAChallenge object
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")

        if not session.is_valid():
            raise ValueError("Session is not valid")

        # Generate challenge
        challenge_id = f"mfa_{secrets.token_hex(16)}"

        if self._mfa_provider:
            challenge_data = await self._mfa_provider.send_challenge(
                method=method,
                user_id=session.user_id,
                destination=destination or "",
            )
        else:
            # Mock challenge for testing
            challenge_data = secrets.token_hex(3).upper()  # 6 digit code

        challenge = MFAChallenge(
            challenge_id=challenge_id,
            session_id=session_id,
            method=method,
            challenge_data=challenge_data,
        )

        self._mfa_challenges[challenge_id] = challenge

        # Update session status
        session.status = SessionStatus.PENDING_MFA

        self._log_event(
            session_id=session_id,
            wallet_id=session.wallet_id,
            event_type="mfa_initiated",
            metadata={"method": method.value},
        )

        return challenge

    async def verify_mfa(
        self,
        challenge_id: str,
        response: str,
    ) -> Tuple[bool, Optional[Session]]:
        """
        Verify MFA challenge response.

        Args:
            challenge_id: Challenge identifier
            response: User's response

        Returns:
            Tuple of (success, session)
        """
        challenge = self._mfa_challenges.get(challenge_id)
        if not challenge:
            return False, None

        if not challenge.is_valid():
            return False, None

        challenge.attempts += 1

        # Verify response
        verified = False
        if self._mfa_provider:
            verified = await self._mfa_provider.verify_challenge(
                method=challenge.method,
                challenge_data=challenge.challenge_data,
                response=response,
            )
        else:
            # Mock verification for testing
            verified = response.upper() == challenge.challenge_data.upper()

        session = self._sessions.get(challenge.session_id)

        if verified:
            challenge.verified = True

            if session:
                session.mfa_verified = True
                session.mfa_method = challenge.method
                session.mfa_verified_at = datetime.now(timezone.utc)
                session.status = SessionStatus.ACTIVE

                # Grant elevated permissions
                session.allowed_actions.add(SessionAction.SIGN)
                session.allowed_actions.add(SessionAction.TRANSFER)

                # Trust device if configured
                if (self._policy.trust_device_after_mfa and
                    session.device_info):
                    await self._trust_device(session.wallet_id, session.device_info)

            self._log_event(
                session_id=challenge.session_id,
                wallet_id=session.wallet_id if session else "",
                event_type="mfa_verified",
                metadata={"method": challenge.method.value},
            )

            return True, session

        self._log_event(
            session_id=challenge.session_id,
            wallet_id=session.wallet_id if session else "",
            event_type="mfa_failed",
            success=False,
            metadata={"method": challenge.method.value, "attempts": challenge.attempts},
        )

        return False, session

    async def _trust_device(
        self,
        wallet_id: str,
        device_info: DeviceInfo,
    ) -> None:
        """Mark a device as trusted."""
        # Check max trusted devices
        devices = self._devices.get(wallet_id, {})
        trusted_devices = [d for d in devices.values() if d.is_trusted]

        if len(trusted_devices) >= self._policy.max_trusted_devices:
            # Remove oldest trusted device
            oldest = min(trusted_devices, key=lambda d: d.first_seen_at)
            oldest.is_trusted = False

        device_info.is_trusted = True
        self._update_device(wallet_id, device_info)

        logger.info(f"Trusted device {device_info.device_id} for wallet {wallet_id}")

    async def revoke_session(
        self,
        session_id: str,
        reason: str = "",
    ) -> bool:
        """Revoke a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.revoke(reason)

        # Cleanup refresh token
        if session.refresh_token:
            self._refresh_tokens.pop(session.refresh_token, None)

        self._log_event(
            session_id=session_id,
            wallet_id=session.wallet_id,
            event_type="session_revoked",
            metadata={"reason": reason},
        )

        logger.info(f"Revoked session {session_id}: {reason}")
        return True

    async def revoke_all_sessions(
        self,
        wallet_id: str,
        reason: str = "",
        exclude_session_id: Optional[str] = None,
    ) -> int:
        """Revoke all sessions for a wallet."""
        session_ids = self._wallet_sessions.get(wallet_id, [])
        revoked = 0

        for session_id in session_ids:
            if session_id == exclude_session_id:
                continue
            if await self.revoke_session(session_id, reason):
                revoked += 1

        return revoked

    def get_active_sessions(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a wallet."""
        session_ids = self._wallet_sessions.get(wallet_id, [])
        sessions = []

        for session_id in session_ids:
            session = self._sessions.get(session_id)
            if session and session.is_valid():
                sessions.append(session.to_dict())

        return sessions

    def get_trusted_devices(self, wallet_id: str) -> List[Dict[str, Any]]:
        """Get all trusted devices for a wallet."""
        devices = self._devices.get(wallet_id, {})
        return [d.to_dict() for d in devices.values() if d.is_trusted]

    def _log_event(
        self,
        session_id: str,
        wallet_id: str,
        event_type: str,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        action: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a session audit event."""
        event = SessionAuditEvent(
            event_id=f"event_{secrets.token_hex(8)}",
            session_id=session_id,
            wallet_id=wallet_id,
            event_type=event_type,
            ip_address=ip_address,
            device_id=device_id,
            action=action,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )

        self._audit_log.append(event)

        # Keep only last 10000 events
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]

    def get_audit_log(
        self,
        wallet_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit log for a wallet."""
        events = [e for e in self._audit_log if e.wallet_id == wallet_id]
        return [e.to_dict() for e in sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]]


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(
    policy: Optional[SessionPolicy] = None,
) -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager(policy)

    return _session_manager


__all__ = [
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
]
