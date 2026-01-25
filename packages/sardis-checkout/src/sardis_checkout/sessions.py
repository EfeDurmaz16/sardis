"""
Customer session management for checkout.

This module provides functionality to manage customer checkout sessions,
including session creation, tracking, expiration, and activity monitoring.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
import hashlib

from sardis_checkout.models import (
    CustomerSession,
    DEFAULT_SESSION_TIMEOUT_MINUTES,
)

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Base exception for session errors."""
    pass


class SessionNotFound(SessionError):
    """Raised when a session is not found."""
    pass


class SessionExpired(SessionError):
    """Raised when a session has expired."""
    pass


class SessionInvalid(SessionError):
    """Raised when a session is invalid."""
    pass


class SessionStore(ABC):
    """Abstract interface for session storage."""

    @abstractmethod
    async def create(self, session: CustomerSession) -> CustomerSession:
        """Create a new session."""
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[CustomerSession]:
        """Get a session by ID."""
        pass

    @abstractmethod
    async def get_by_customer(self, customer_id: str) -> List[CustomerSession]:
        """Get all sessions for a customer."""
        pass

    @abstractmethod
    async def update(self, session: CustomerSession) -> CustomerSession:
        """Update a session."""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        pass


class InMemorySessionStore(SessionStore):
    """
    In-memory session store for development and testing.

    Note: This store is not suitable for production use.
    Use a persistent store like Redis or a database.
    """

    def __init__(self):
        self._sessions: Dict[str, CustomerSession] = {}
        self._customer_sessions: Dict[str, List[str]] = {}  # customer_id -> session_ids

    async def create(self, session: CustomerSession) -> CustomerSession:
        self._sessions[session.session_id] = session
        if session.customer_id:
            if session.customer_id not in self._customer_sessions:
                self._customer_sessions[session.customer_id] = []
            self._customer_sessions[session.customer_id].append(session.session_id)
        return session

    async def get(self, session_id: str) -> Optional[CustomerSession]:
        return self._sessions.get(session_id)

    async def get_by_customer(self, customer_id: str) -> List[CustomerSession]:
        session_ids = self._customer_sessions.get(customer_id, [])
        return [
            self._sessions[sid] for sid in session_ids
            if sid in self._sessions
        ]

    async def update(self, session: CustomerSession) -> CustomerSession:
        if session.session_id in self._sessions:
            self._sessions[session.session_id] = session
        return session

    async def delete(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            del self._sessions[session_id]
            if session.customer_id and session.customer_id in self._customer_sessions:
                self._customer_sessions[session.customer_id] = [
                    sid for sid in self._customer_sessions[session.customer_id]
                    if sid != session_id
                ]
            return True
        return False

    async def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self._sessions.items()
            if session.expires_at < now
        ]
        for sid in expired:
            await self.delete(sid)
        return len(expired)


class SessionManager:
    """
    Manages customer checkout sessions.

    Features:
    - Session creation and lifecycle management
    - Session timeout handling (15 minutes by default)
    - Activity tracking
    - Device fingerprinting
    - Multi-checkout session support
    """

    def __init__(
        self,
        store: SessionStore,
        session_timeout_minutes: int = DEFAULT_SESSION_TIMEOUT_MINUTES,
        max_sessions_per_customer: int = 5,
        extend_on_activity: bool = True,
    ):
        self.store = store
        self.session_timeout_minutes = session_timeout_minutes
        self.max_sessions_per_customer = max_sessions_per_customer
        self.extend_on_activity = extend_on_activity

    def _generate_session_token(self) -> str:
        """Generate a secure session token."""
        return hashlib.sha256(uuid.uuid4().bytes).hexdigest()

    async def create_session(
        self,
        agent_id: str,
        customer_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CustomerSession:
        """
        Create a new customer checkout session.

        Args:
            agent_id: Agent ID for the session
            customer_id: Optional customer identifier
            customer_email: Optional customer email
            ip_address: Client IP address
            user_agent: Client user agent string
            device_fingerprint: Device fingerprint for fraud detection
            metadata: Additional session metadata

        Returns:
            The created CustomerSession
        """
        # Clean up old sessions for this customer
        if customer_id:
            existing = await self.store.get_by_customer(customer_id)
            active_count = sum(
                1 for s in existing
                if s.status == "active" and s.expires_at > datetime.utcnow()
            )

            # Expire oldest sessions if over limit
            if active_count >= self.max_sessions_per_customer:
                sorted_sessions = sorted(existing, key=lambda s: s.created_at)
                for old_session in sorted_sessions[:active_count - self.max_sessions_per_customer + 1]:
                    if old_session.status == "active":
                        old_session.status = "expired"
                        await self.store.update(old_session)

        session = CustomerSession(
            session_id=str(uuid.uuid4()),
            customer_id=customer_id,
            customer_email=customer_email,
            agent_id=agent_id,
            status="active",
            expires_at=datetime.utcnow() + timedelta(minutes=self.session_timeout_minutes),
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            metadata=metadata or {},
        )

        await self.store.create(session)
        logger.info(
            f"Created session {session.session_id} for agent {agent_id}"
            f"{f', customer {customer_id}' if customer_id else ''}"
        )

        return session

    async def get_session(self, session_id: str) -> CustomerSession:
        """
        Get a session by ID.

        Raises:
            SessionNotFound: If session doesn't exist
            SessionExpired: If session has expired
        """
        session = await self.store.get(session_id)

        if not session:
            raise SessionNotFound(f"Session {session_id} not found")

        # Check expiration
        if session.expires_at < datetime.utcnow():
            session.status = "expired"
            await self.store.update(session)
            raise SessionExpired(f"Session {session_id} has expired")

        if session.status != "active":
            raise SessionInvalid(f"Session {session_id} is {session.status}")

        return session

    async def validate_session(self, session_id: str) -> bool:
        """
        Validate a session is active and not expired.

        Returns True if valid, False otherwise.
        """
        try:
            await self.get_session(session_id)
            return True
        except SessionError:
            return False

    async def update_activity(
        self,
        session_id: str,
        extend_expiration: Optional[bool] = None,
    ) -> CustomerSession:
        """
        Update the last activity timestamp for a session.

        Args:
            session_id: Session ID
            extend_expiration: Whether to extend expiration (defaults to extend_on_activity setting)

        Returns:
            Updated CustomerSession
        """
        session = await self.get_session(session_id)

        session.last_activity_at = datetime.utcnow()

        # Extend expiration if enabled
        should_extend = extend_expiration if extend_expiration is not None else self.extend_on_activity
        if should_extend:
            session.expires_at = datetime.utcnow() + timedelta(
                minutes=self.session_timeout_minutes
            )

        await self.store.update(session)
        return session

    async def add_checkout_to_session(
        self,
        session_id: str,
        checkout_id: str,
    ) -> CustomerSession:
        """
        Associate a checkout with a session.
        """
        session = await self.get_session(session_id)

        if checkout_id not in session.checkout_ids:
            session.checkout_ids.append(checkout_id)
            session.last_activity_at = datetime.utcnow()
            await self.store.update(session)

        logger.debug(f"Added checkout {checkout_id} to session {session_id}")
        return session

    async def get_session_checkouts(self, session_id: str) -> List[str]:
        """Get all checkout IDs associated with a session."""
        session = await self.get_session(session_id)
        return session.checkout_ids.copy()

    async def complete_session(
        self,
        session_id: str,
    ) -> CustomerSession:
        """
        Mark a session as completed.

        This should be called when all checkouts in the session are complete.
        """
        session = await self.store.get(session_id)
        if not session:
            raise SessionNotFound(f"Session {session_id} not found")

        session.status = "completed"
        session.last_activity_at = datetime.utcnow()
        await self.store.update(session)

        logger.info(f"Session {session_id} marked as completed")
        return session

    async def abandon_session(
        self,
        session_id: str,
        reason: Optional[str] = None,
    ) -> CustomerSession:
        """
        Mark a session as abandoned.

        This should be called when a session is abandoned without completing.
        """
        session = await self.store.get(session_id)
        if not session:
            raise SessionNotFound(f"Session {session_id} not found")

        session.status = "abandoned"
        session.last_activity_at = datetime.utcnow()
        if reason:
            session.metadata["abandon_reason"] = reason

        await self.store.update(session)

        logger.info(f"Session {session_id} marked as abandoned")
        return session

    async def expire_session(
        self,
        session_id: str,
    ) -> CustomerSession:
        """
        Force-expire a session.
        """
        session = await self.store.get(session_id)
        if not session:
            raise SessionNotFound(f"Session {session_id} not found")

        session.status = "expired"
        session.expires_at = datetime.utcnow()
        await self.store.update(session)

        logger.info(f"Session {session_id} force-expired")
        return session

    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a session.
        """
        session = await self.store.get(session_id)
        if not session:
            raise SessionNotFound(f"Session {session_id} not found")

        now = datetime.utcnow()
        is_expired = session.expires_at < now
        seconds_until_expiry = max(
            0,
            int((session.expires_at - now).total_seconds())
        ) if not is_expired else 0

        return {
            "session_id": session.session_id,
            "customer_id": session.customer_id,
            "customer_email": session.customer_email,
            "agent_id": session.agent_id,
            "status": session.status,
            "is_active": session.status == "active" and not is_expired,
            "is_expired": is_expired,
            "checkout_count": len(session.checkout_ids),
            "checkout_ids": session.checkout_ids,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "last_activity_at": session.last_activity_at.isoformat(),
            "seconds_until_expiry": seconds_until_expiry,
            "ip_address": session.ip_address,
            "device_fingerprint": session.device_fingerprint,
            "metadata": session.metadata,
        }

    async def get_customer_sessions(
        self,
        customer_id: str,
        active_only: bool = False,
    ) -> List[CustomerSession]:
        """
        Get all sessions for a customer.

        Args:
            customer_id: Customer identifier
            active_only: Only return active sessions
        """
        sessions = await self.store.get_by_customer(customer_id)

        if active_only:
            now = datetime.utcnow()
            sessions = [
                s for s in sessions
                if s.status == "active" and s.expires_at > now
            ]

        return sessions

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns the number of sessions cleaned up.
        """
        count = await self.store.cleanup_expired()
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")
        return count

    async def get_active_session_count(self, agent_id: Optional[str] = None) -> int:
        """
        Get count of active sessions, optionally filtered by agent.

        Note: This is a simplified implementation. Production systems
        should use database queries for better performance.
        """
        # This would need to be implemented properly with database support
        # For the in-memory store, we'd need to iterate all sessions
        return 0
