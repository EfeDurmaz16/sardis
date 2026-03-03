from __future__ import annotations

import pytest

from sardis_v2_core.config import MPCProvider, SardisSettings, validate_production_config


def _set_prod_baseline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "prod")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SARDIS_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PERSONA_API_KEY", "persona-key")
    monkeypatch.setenv("ELLIPTIC_API_KEY", "elliptic-key")
    monkeypatch.delenv("FIREBLOCKS_API_KEY", raising=False)
    monkeypatch.delenv("TURNKEY_ORGANIZATION_ID", raising=False)
    monkeypatch.delenv("TURNKEY_API_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("TURNKEY_API_PRIVATE_KEY", raising=False)


def _build_live_circle_settings() -> SardisSettings:
    return SardisSettings(
        environment="prod",
        secret_key="s" * 32,
        database_url="postgresql://localhost/sardis",
        chain_mode="live",
        mpc=MPCProvider(name="circle"),
    )


def test_circle_live_requires_explicit_enable_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_prod_baseline_env(monkeypatch)
    monkeypatch.setenv("SARDIS_CIRCLE_WALLET_API_KEY", "circle-api-key")
    monkeypatch.delenv("SARDIS_CIRCLE_LIVE_SIGNER_ENABLED", raising=False)
    monkeypatch.delenv("SARDIS_CIRCLE_DEFAULT_WALLET_ID", raising=False)
    monkeypatch.delenv("SARDIS_CIRCLE_DEFAULT_ADDRESS", raising=False)

    settings = _build_live_circle_settings()
    errors = validate_production_config(settings)

    assert any("SARDIS_CIRCLE_LIVE_SIGNER_ENABLED" in item for item in errors)


def test_circle_live_requires_default_wallet_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_prod_baseline_env(monkeypatch)
    monkeypatch.setenv("SARDIS_CIRCLE_WALLET_API_KEY", "circle-api-key")
    monkeypatch.setenv("SARDIS_CIRCLE_LIVE_SIGNER_ENABLED", "true")
    monkeypatch.delenv("SARDIS_CIRCLE_DEFAULT_WALLET_ID", raising=False)
    monkeypatch.delenv("SARDIS_CIRCLE_DEFAULT_ADDRESS", raising=False)

    settings = _build_live_circle_settings()
    errors = validate_production_config(settings)

    assert any("SARDIS_CIRCLE_DEFAULT_WALLET_ID" in item for item in errors)


def test_circle_live_with_explicit_binding_passes_circle_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_prod_baseline_env(monkeypatch)
    monkeypatch.setenv("SARDIS_CIRCLE_WALLET_API_KEY", "circle-api-key")
    monkeypatch.setenv("SARDIS_CIRCLE_LIVE_SIGNER_ENABLED", "true")
    monkeypatch.setenv("SARDIS_CIRCLE_DEFAULT_WALLET_ID", "wallet_123")
    monkeypatch.setenv("SARDIS_CIRCLE_DEFAULT_ADDRESS", "0x1111111111111111111111111111111111111111")

    settings = _build_live_circle_settings()
    errors = validate_production_config(settings)

    assert not any("SARDIS_CIRCLE_WALLET_API_KEY" in item for item in errors)
    assert not any("SARDIS_CIRCLE_LIVE_SIGNER_ENABLED" in item for item in errors)
    assert not any("SARDIS_CIRCLE_DEFAULT_WALLET_ID" in item for item in errors)
