from __future__ import annotations

from sardis_v2_core.config import SardisSettings, validate_production_config


def _set_required_env(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "prod")
    monkeypatch.setenv("JWT_SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SARDIS_ADMIN_PASSWORD", "admin-password")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PERSONA_API_KEY", "persona_key")
    monkeypatch.setenv("ELLIPTIC_API_KEY", "elliptic_key")


def _base_settings(allowed_origins: str) -> SardisSettings:
    return SardisSettings(
        environment="prod",
        secret_key="s" * 32,
        database_url="postgresql://localhost/sardis",
        ledger_dsn="postgresql://localhost/sardis",
        allowed_origins=allowed_origins,
        chain_mode="simulated",
    )


def test_production_rejects_wildcard_origin(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    settings = _base_settings("*")
    errors = validate_production_config(settings)
    assert any("Wildcard '*'" in e for e in errors)


def test_production_rejects_localhost_origin(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    settings = _base_settings("http://localhost:3000,https://app.sardis.sh")
    errors = validate_production_config(settings)
    assert any("Localhost origin not allowed" in e for e in errors)


def test_production_rejects_non_https_origin(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    settings = _base_settings("http://app.sardis.sh")
    errors = validate_production_config(settings)
    assert any("Non-HTTPS origin not allowed" in e for e in errors)


def test_production_accepts_explicit_https_origins(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    settings = _base_settings("https://app.sardis.sh,https://dashboard.sardis.sh")
    errors = validate_production_config(settings)
    assert not any("SARDIS_ALLOWED_ORIGINS" in e for e in errors)


def test_production_accepts_json_array_origins(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    settings = _base_settings('["https://app.sardis.sh","https://www.sardis.sh"]')
    errors = validate_production_config(settings)
    assert not any("SARDIS_ALLOWED_ORIGINS" in e for e in errors)


def test_production_requires_live_chain_mode(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    settings = _base_settings("https://app.sardis.sh")
    errors = validate_production_config(settings)
    assert any("SARDIS_CHAIN_MODE: Must be 'live' in production" in e for e in errors)


def test_production_live_chain_mode_passes_chain_mode_guard(monkeypatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "live")
    settings = SardisSettings(
        environment="prod",
        secret_key="s" * 32,
        database_url="postgresql://localhost/sardis",
        ledger_dsn="postgresql://localhost/sardis",
        allowed_origins="https://app.sardis.sh",
        chain_mode="live",
    )
    errors = validate_production_config(settings)
    assert not any("SARDIS_CHAIN_MODE: Must be 'live' in production" in e for e in errors)
