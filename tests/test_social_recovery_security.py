from __future__ import annotations

import pytest

from sardis_wallet.social_recovery import SocialRecoveryManager


def test_social_recovery_share_generation_disabled_in_production(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "prod")
    manager = SocialRecoveryManager()

    with pytest.raises(RuntimeError, match="Secure SSS backend is required in production"):
        manager._generate_sss_shares(b"secret", num_shares=3, threshold=2)


def test_social_recovery_reconstruction_disabled_in_production(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "prod")
    manager = SocialRecoveryManager()
    shares = [(1, b"a" * 32), (2, b"b" * 32)]

    with pytest.raises(RuntimeError, match="Secure SSS backend is required in production"):
        manager._reconstruct_secret(shares, threshold=2)
