"""
Comprehensive tests for sardis_wallet.key_rotation module.

Tests cover:
- MPCKeyInfo management
- Key rotation policies
- Key rotation events and audit
- Rotation state transitions
- Grace period handling
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch

import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
packages_dir = Path(__file__).parent.parent.parent
for pkg in ["sardis-core"]:
    pkg_path = packages_dir / pkg / "src"
    if pkg_path.exists():
        sys.path.insert(0, str(pkg_path))

from sardis_wallet.key_rotation import (
    MPCKeyStatus,
    RotationReason,
    MPCKeyInfo,
    KeyRotationEvent,
    MPCKeyRotationPolicy,
)


class TestMPCKeyStatus:
    """Tests for MPCKeyStatus enum."""

    def test_status_values(self):
        """Should have correct status values."""
        assert MPCKeyStatus.ACTIVE.value == "active"
        assert MPCKeyStatus.ROTATING.value == "rotating"
        assert MPCKeyStatus.PENDING_ACTIVATION.value == "pending_activation"
        assert MPCKeyStatus.REVOKED.value == "revoked"
        assert MPCKeyStatus.COMPROMISED.value == "compromised"
        assert MPCKeyStatus.EXPIRED.value == "expired"


class TestRotationReason:
    """Tests for RotationReason enum."""

    def test_reason_values(self):
        """Should have correct reason values."""
        assert RotationReason.SCHEDULED.value == "scheduled"
        assert RotationReason.MANUAL.value == "manual"
        assert RotationReason.SECURITY_INCIDENT.value == "security_incident"
        assert RotationReason.COMPLIANCE.value == "compliance"
        assert RotationReason.KEY_EXPIRY.value == "key_expiry"
        assert RotationReason.PROVIDER_MIGRATION.value == "provider_migration"


class TestMPCKeyInfo:
    """Tests for MPCKeyInfo class."""

    def test_create_key_info(self):
        """Should create key info with all fields."""
        key = MPCKeyInfo(
            key_id="key_123",
            wallet_id="wallet_456",
            mpc_provider="turnkey",
            mpc_key_reference="tk_key_ref",
            algorithm="ecdsa-secp256k1",
        )

        assert key.key_id == "key_123"
        assert key.wallet_id == "wallet_456"
        assert key.mpc_provider == "turnkey"
        assert key.status == MPCKeyStatus.ACTIVE

    def test_is_valid_active_key(self):
        """Should validate active key."""
        key = MPCKeyInfo(
            key_id="key_1",
            wallet_id="wallet_1",
            mpc_provider="turnkey",
            mpc_key_reference="ref_1",
            status=MPCKeyStatus.ACTIVE,
        )

        assert key.is_valid is True

    def test_is_valid_expired_key(self):
        """Should invalidate expired key."""
        past_time = datetime.now(timezone.utc) - timedelta(days=1)

        key = MPCKeyInfo(
            key_id="key_2",
            wallet_id="wallet_2",
            mpc_provider="turnkey",
            mpc_key_reference="ref_2",
            status=MPCKeyStatus.ACTIVE,
            expires_at=past_time,
        )

        assert key.is_valid is False

    def test_is_valid_revoked_key(self):
        """Should invalidate revoked key."""
        key = MPCKeyInfo(
            key_id="key_3",
            wallet_id="wallet_3",
            mpc_provider="turnkey",
            mpc_key_reference="ref_3",
            status=MPCKeyStatus.REVOKED,
        )

        assert key.is_valid is False

    def test_is_in_grace_period(self):
        """Should detect grace period status."""
        key = MPCKeyInfo(
            key_id="key_4",
            wallet_id="wallet_4",
            mpc_provider="turnkey",
            mpc_key_reference="ref_4",
            status=MPCKeyStatus.ROTATING,
        )

        assert key.is_in_grace_period is True

    def test_days_until_expiry(self):
        """Should calculate days until expiry."""
        future_time = datetime.now(timezone.utc) + timedelta(days=30)

        key = MPCKeyInfo(
            key_id="key_5",
            wallet_id="wallet_5",
            mpc_provider="turnkey",
            mpc_key_reference="ref_5",
            expires_at=future_time,
        )

        days = key.days_until_expiry
        assert days is not None
        assert 29 <= days <= 30

    def test_days_until_expiry_no_expiry(self):
        """Should return None if no expiry set."""
        key = MPCKeyInfo(
            key_id="key_6",
            wallet_id="wallet_6",
            mpc_provider="turnkey",
            mpc_key_reference="ref_6",
        )

        assert key.days_until_expiry is None

    def test_record_use(self):
        """Should track key usage."""
        key = MPCKeyInfo(
            key_id="key_7",
            wallet_id="wallet_7",
            mpc_provider="turnkey",
            mpc_key_reference="ref_7",
        )

        assert key.use_count == 0
        assert key.last_used_at is None

        key.record_use()

        assert key.use_count == 1
        assert key.last_used_at is not None

        key.record_use()
        assert key.use_count == 2

    def test_to_dict(self):
        """Should convert to dictionary."""
        key = MPCKeyInfo(
            key_id="key_8",
            wallet_id="wallet_8",
            mpc_provider="turnkey",
            mpc_key_reference="ref_8",
        )

        result = key.to_dict()

        assert result["key_id"] == "key_8"
        assert result["wallet_id"] == "wallet_8"
        assert result["mpc_provider"] == "turnkey"
        assert result["status"] == "active"
        assert "created_at" in result


class TestKeyRotationEvent:
    """Tests for KeyRotationEvent class."""

    def test_create_rotation_event(self):
        """Should create rotation event."""
        event = KeyRotationEvent(
            event_id="event_123",
            wallet_id="wallet_456",
            old_key_id="old_key",
            new_key_id="new_key",
            reason=RotationReason.SCHEDULED,
            initiated_at=datetime.now(timezone.utc),
            initiated_by="system",
        )

        assert event.event_id == "event_123"
        assert event.reason == RotationReason.SCHEDULED
        assert event.status == "in_progress"

    def test_event_to_dict(self):
        """Should convert event to dictionary."""
        event = KeyRotationEvent(
            event_id="event_456",
            wallet_id="wallet_789",
            old_key_id="key_old",
            new_key_id="key_new",
            reason=RotationReason.SECURITY_INCIDENT,
            initiated_at=datetime.now(timezone.utc),
            initiated_by="security",
        )

        result = event.to_dict()

        assert result["event_id"] == "event_456"
        assert result["reason"] == "security_incident"
        assert result["initiated_by"] == "security"

    def test_event_with_completion(self):
        """Should track completion."""
        event = KeyRotationEvent(
            event_id="event_789",
            wallet_id="wallet_abc",
            old_key_id="old",
            new_key_id="new",
            reason=RotationReason.MANUAL,
            initiated_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            initiated_by="user",
            completed_at=datetime.now(timezone.utc),
            status="completed",
        )

        result = event.to_dict()
        assert result["status"] == "completed"
        assert result["completed_at"] is not None


class TestMPCKeyRotationPolicy:
    """Tests for MPCKeyRotationPolicy class."""

    def test_create_policy(self):
        """Should create rotation policy."""
        policy = MPCKeyRotationPolicy(
            auto_rotate=True,
            rotation_interval_days=90,
            grace_period_hours=24,
            warn_before_days=7,
        )

        assert policy.auto_rotate is True
        assert policy.rotation_interval_days == 90
        assert policy.grace_period_hours == 24
        assert policy.warn_before_days == 7


class TestKeyRotationIntegration:
    """Integration tests for key rotation."""

    def test_key_lifecycle(self):
        """Should support full key lifecycle."""
        # Create active key
        key = MPCKeyInfo(
            key_id="lifecycle_key",
            wallet_id="wallet_1",
            mpc_provider="turnkey",
            mpc_key_reference="ref_1",
            status=MPCKeyStatus.ACTIVE,
        )

        assert key.is_valid is True

        # Start rotation
        key.status = MPCKeyStatus.ROTATING
        key.rotation_started_at = datetime.now(timezone.utc)

        assert key.is_valid is True  # Still valid during rotation
        assert key.is_in_grace_period is True

        # Complete rotation
        key.status = MPCKeyStatus.EXPIRED
        key.rotation_completed_at = datetime.now(timezone.utc)

        assert key.is_valid is False

    def test_emergency_rotation_event(self):
        """Should create emergency rotation event."""
        event = KeyRotationEvent(
            event_id="emergency_1",
            wallet_id="wallet_compromised",
            old_key_id="compromised_key",
            new_key_id="new_secure_key",
            reason=RotationReason.SECURITY_INCIDENT,
            initiated_at=datetime.now(timezone.utc),
            initiated_by="security",
            metadata={"incident_id": "INC-001", "severity": "high"},
        )

        result = event.to_dict()
        assert result["metadata"]["incident_id"] == "INC-001"


class TestKeyRotationEdgeCases:
    """Edge case tests for key rotation."""

    def test_key_with_no_uses(self):
        """Should handle key that was never used."""
        key = MPCKeyInfo(
            key_id="unused_key",
            wallet_id="wallet_1",
            mpc_provider="turnkey",
            mpc_key_reference="ref_1",
        )

        assert key.use_count == 0
        assert key.last_used_at is None
        assert key.is_valid is True

    def test_key_expiry_boundary(self):
        """Should handle key at expiry boundary."""
        # Key expiring right now
        now = datetime.now(timezone.utc)

        key = MPCKeyInfo(
            key_id="expiring_key",
            wallet_id="wallet_1",
            mpc_provider="turnkey",
            mpc_key_reference="ref_1",
            expires_at=now - timedelta(seconds=1),
        )

        assert key.is_valid is False
        assert key.days_until_expiry == 0

    def test_multiple_rotation_events_same_wallet(self):
        """Should handle multiple rotation events."""
        events = [
            KeyRotationEvent(
                event_id=f"event_{i}",
                wallet_id="same_wallet",
                old_key_id=f"key_{i}",
                new_key_id=f"key_{i+1}",
                reason=RotationReason.SCHEDULED,
                initiated_at=datetime.now(timezone.utc),
                initiated_by="system",
            )
            for i in range(5)
        ]

        assert len(events) == 5
        assert all(e.wallet_id == "same_wallet" for e in events)
