from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sardis_v2_core.key_rotation import KeyRotationManager, KeyRotationPolicy, KeyStatus


def _pub(seed: int) -> bytes:
    return bytes([seed]) * 32


def test_rotate_key_marks_previous_key_rotating():
    manager = KeyRotationManager(
        KeyRotationPolicy(
            rotation_interval_days=90,
            grace_period_hours=24,
            allow_multiple_active=False,
        )
    )

    first = manager.register_key("agent_1", "key_1", _pub(1), "ed25519")
    second = manager.rotate_key("agent_1", _pub(2), "ed25519", reason="manual")

    assert second.key_id != first.key_id
    assert manager.get_active_key("agent_1").key_id == second.key_id
    valid_ids = {k.key_id for k in manager.get_valid_keys("agent_1")}
    assert first.key_id in valid_ids  # grace period
    assert second.key_id in valid_ids


def test_cleanup_expired_keys_moves_rotating_key_to_revoked():
    manager = KeyRotationManager(
        KeyRotationPolicy(
            grace_period_hours=1,
            allow_multiple_active=False,
        )
    )

    first = manager.register_key("agent_1", "key_1", _pub(1), "ed25519")
    manager.rotate_key("agent_1", _pub(2), "ed25519")

    # Force old key out of grace period.
    first.rotation_started_at = datetime.now(timezone.utc) - timedelta(hours=2)
    first.status = KeyStatus.ROTATING

    affected = manager.cleanup_expired_keys()
    assert affected >= 1
    assert first.status == KeyStatus.REVOKED


def test_get_keys_needing_rotation_returns_threshold_matches():
    manager = KeyRotationManager(
        KeyRotationPolicy(
            rotation_interval_days=90,
            notification_threshold_days=7,
        )
    )
    soon = datetime.now(timezone.utc) + timedelta(days=2)
    later = datetime.now(timezone.utc) + timedelta(days=30)

    manager.register_key("agent_soon", "key_soon", _pub(3), "ed25519", expires_at=soon)
    manager.register_key("agent_later", "key_later", _pub(4), "ed25519", expires_at=later)

    needing = manager.get_keys_needing_rotation()
    agent_ids = {agent_id for agent_id, _, _ in needing}

    assert "agent_soon" in agent_ids
    assert "agent_later" not in agent_ids
