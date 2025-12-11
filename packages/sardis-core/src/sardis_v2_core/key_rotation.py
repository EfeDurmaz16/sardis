"""
Agent key rotation mechanism for Sardis.

Provides secure key rotation with grace periods for agent identities.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KeyStatus(str, Enum):
    """Status of an agent key."""
    ACTIVE = "active"
    ROTATING = "rotating"  # Grace period
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class AgentKey:
    """An agent's signing key."""
    key_id: str
    public_key: bytes
    algorithm: str  # "ed25519" or "ecdsa-p256"
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: KeyStatus = KeyStatus.ACTIVE
    
    # For rotation tracking
    previous_key_id: Optional[str] = None
    rotation_started_at: Optional[datetime] = None
    rotation_grace_period_hours: int = 24
    
    @property
    def is_valid(self) -> bool:
        """Check if key is valid for signing."""
        if self.status not in (KeyStatus.ACTIVE, KeyStatus.ROTATING):
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True
    
    @property
    def is_in_grace_period(self) -> bool:
        """Check if key is in rotation grace period."""
        if self.status != KeyStatus.ROTATING:
            return False
        if not self.rotation_started_at:
            return False
        grace_end = self.rotation_started_at + timedelta(hours=self.rotation_grace_period_hours)
        return datetime.now(timezone.utc) < grace_end
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "key_id": self.key_id,
            "public_key": self.public_key.hex(),
            "algorithm": self.algorithm,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "previous_key_id": self.previous_key_id,
            "rotation_started_at": self.rotation_started_at.isoformat() if self.rotation_started_at else None,
        }


@dataclass
class RotationEvent:
    """A key rotation event for audit logging."""
    event_id: str
    agent_id: str
    old_key_id: str
    new_key_id: str
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    reason: str = "scheduled"
    initiated_by: str = "system"


@dataclass
class KeyRotationPolicy:
    """Key rotation policy configuration."""
    # Automatic rotation interval
    rotation_interval_days: int = 90
    
    # Grace period for old keys
    grace_period_hours: int = 24
    
    # Maximum key age before forced rotation
    max_key_age_days: int = 180
    
    # Whether to allow multiple active keys
    allow_multiple_active: bool = False
    
    # Notification threshold (days before rotation)
    notification_threshold_days: int = 7


class KeyRotationManager:
    """
    Manages agent key rotation with grace periods.
    
    Features:
    - Automatic rotation scheduling
    - Grace period support for old keys
    - Rotation event logging
    - Policy-based rotation
    """
    
    def __init__(
        self,
        policy: Optional[KeyRotationPolicy] = None,
    ):
        self._policy = policy or KeyRotationPolicy()
        self._keys: Dict[str, Dict[str, AgentKey]] = {}  # agent_id -> key_id -> key
        self._active_keys: Dict[str, str] = {}  # agent_id -> active_key_id
        self._rotation_events: List[RotationEvent] = []
    
    def register_key(
        self,
        agent_id: str,
        key_id: str,
        public_key: bytes,
        algorithm: str = "ed25519",
        expires_at: Optional[datetime] = None,
    ) -> AgentKey:
        """
        Register a new key for an agent.
        
        If the agent has an existing active key and allow_multiple_active is False,
        the old key will be put into rotation mode.
        """
        now = datetime.now(timezone.utc)
        
        # Set expiration based on policy if not provided
        if expires_at is None:
            expires_at = now + timedelta(days=self._policy.rotation_interval_days)
        
        # Check if agent has existing active key
        current_active_id = self._active_keys.get(agent_id)
        previous_key_id = None
        
        if current_active_id and not self._policy.allow_multiple_active:
            # Put current key into rotation mode
            current_key = self._keys[agent_id][current_active_id]
            current_key.status = KeyStatus.ROTATING
            current_key.rotation_started_at = now
            previous_key_id = current_active_id
            
            logger.info(f"Key {current_active_id} for agent {agent_id} entering grace period")
        
        # Create new key
        new_key = AgentKey(
            key_id=key_id,
            public_key=public_key,
            algorithm=algorithm,
            created_at=now,
            expires_at=expires_at,
            status=KeyStatus.ACTIVE,
            previous_key_id=previous_key_id,
            rotation_grace_period_hours=self._policy.grace_period_hours,
        )
        
        # Store key
        if agent_id not in self._keys:
            self._keys[agent_id] = {}
        self._keys[agent_id][key_id] = new_key
        self._active_keys[agent_id] = key_id
        
        logger.info(f"Registered new key {key_id} for agent {agent_id}")
        
        # Log rotation event if replacing
        if previous_key_id:
            event = RotationEvent(
                event_id=f"rot_{agent_id}_{now.timestamp()}",
                agent_id=agent_id,
                old_key_id=previous_key_id,
                new_key_id=key_id,
                initiated_at=now,
                reason="registration",
            )
            self._rotation_events.append(event)
        
        return new_key
    
    def get_active_key(self, agent_id: str) -> Optional[AgentKey]:
        """Get the currently active key for an agent."""
        key_id = self._active_keys.get(agent_id)
        if not key_id:
            return None
        
        agent_keys = self._keys.get(agent_id, {})
        key = agent_keys.get(key_id)
        
        if key and key.is_valid:
            return key
        return None
    
    def get_valid_keys(self, agent_id: str) -> List[AgentKey]:
        """Get all valid keys for an agent (including grace period keys)."""
        agent_keys = self._keys.get(agent_id, {})
        return [k for k in agent_keys.values() if k.is_valid]
    
    def verify_with_any_valid_key(
        self,
        agent_id: str,
        message: bytes,
        signature: bytes,
    ) -> Optional[AgentKey]:
        """
        Attempt to verify a signature with any valid key.
        
        Returns the key that successfully verified, or None.
        """
        from .identity import AgentIdentity
        
        valid_keys = self.get_valid_keys(agent_id)
        
        for key in valid_keys:
            identity = AgentIdentity(
                agent_id=agent_id,
                public_key=key.public_key,
                algorithm=key.algorithm,
            )
            try:
                # Simple verification without domain/nonce (caller should handle full verification)
                if self._verify_raw(key, message, signature):
                    return key
            except Exception:
                continue
        
        return None
    
    def _verify_raw(self, key: AgentKey, message: bytes, signature: bytes) -> bool:
        """Raw signature verification."""
        try:
            if key.algorithm == "ed25519":
                from nacl.signing import VerifyKey
                verify_key = VerifyKey(key.public_key)
                verify_key.verify(message, signature)
                return True
            elif key.algorithm == "ecdsa-p256":
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import ec
                from cryptography.hazmat.primitives.serialization import load_der_public_key
                
                public_key = load_der_public_key(key.public_key)
                public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
                return True
        except Exception:
            return False
        return False
    
    def rotate_key(
        self,
        agent_id: str,
        new_public_key: bytes,
        new_algorithm: str = "ed25519",
        reason: str = "scheduled",
        initiated_by: str = "system",
    ) -> AgentKey:
        """
        Perform a key rotation for an agent.
        
        Returns the new key.
        """
        import secrets
        
        new_key_id = f"key_{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc)
        
        old_key_id = self._active_keys.get(agent_id)
        
        # Register new key (this handles grace period for old key)
        new_key = self.register_key(
            agent_id=agent_id,
            key_id=new_key_id,
            public_key=new_public_key,
            algorithm=new_algorithm,
        )
        
        # Update rotation event
        if old_key_id:
            event = RotationEvent(
                event_id=f"rot_{agent_id}_{now.timestamp()}",
                agent_id=agent_id,
                old_key_id=old_key_id,
                new_key_id=new_key_id,
                initiated_at=now,
                reason=reason,
                initiated_by=initiated_by,
            )
            self._rotation_events.append(event)
        
        return new_key
    
    def revoke_key(self, agent_id: str, key_id: str, reason: str = "manual") -> bool:
        """Revoke a specific key."""
        agent_keys = self._keys.get(agent_id, {})
        key = agent_keys.get(key_id)
        
        if not key:
            return False
        
        key.status = KeyStatus.REVOKED
        
        # If this was the active key, clear active status
        if self._active_keys.get(agent_id) == key_id:
            del self._active_keys[agent_id]
        
        logger.info(f"Revoked key {key_id} for agent {agent_id}: {reason}")
        return True
    
    def cleanup_expired_keys(self) -> int:
        """
        Clean up expired keys and finalize rotation grace periods.
        
        Returns the number of keys affected.
        """
        now = datetime.now(timezone.utc)
        count = 0
        
        for agent_id, agent_keys in self._keys.items():
            for key_id, key in list(agent_keys.items()):
                # Check expiration
                if key.expires_at and now > key.expires_at:
                    if key.status not in (KeyStatus.REVOKED, KeyStatus.EXPIRED):
                        key.status = KeyStatus.EXPIRED
                        count += 1
                        logger.info(f"Key {key_id} for agent {agent_id} expired")
                
                # Check grace period end
                if key.status == KeyStatus.ROTATING:
                    if not key.is_in_grace_period:
                        key.status = KeyStatus.REVOKED
                        count += 1
                        logger.info(f"Key {key_id} for agent {agent_id} grace period ended")
        
        return count
    
    def get_keys_needing_rotation(self) -> List[tuple]:
        """Get list of (agent_id, key_id) pairs that should be rotated soon."""
        now = datetime.now(timezone.utc)
        threshold = timedelta(days=self._policy.notification_threshold_days)
        result = []
        
        for agent_id, key_id in self._active_keys.items():
            key = self._keys[agent_id][key_id]
            if key.expires_at:
                if key.expires_at - now <= threshold:
                    result.append((agent_id, key_id, key.expires_at))
        
        return result
    
    def get_rotation_history(self, agent_id: str) -> List[RotationEvent]:
        """Get rotation event history for an agent."""
        return [e for e in self._rotation_events if e.agent_id == agent_id]


# Singleton instance
_key_rotation_manager: Optional[KeyRotationManager] = None


def get_key_rotation_manager(
    policy: Optional[KeyRotationPolicy] = None,
) -> KeyRotationManager:
    """Get the global key rotation manager instance."""
    global _key_rotation_manager
    
    if _key_rotation_manager is None:
        _key_rotation_manager = KeyRotationManager(policy)
    
    return _key_rotation_manager


