from types import SimpleNamespace

import pytest

from sardis_server.dependencies import resolve_cache_backend, resolve_storage_backend


def _settings(**overrides):
    defaults = {
        "database_url": "",
        "ledger_dsn": "memory://",
        "redis_url": None,
        "is_production": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_resolve_storage_backend_prefers_database_url_env() -> None:
    config = resolve_storage_backend(
        _settings(database_url="sqlite:///settings.db", ledger_dsn="sqlite:///ledger.db"),
        environ={"DATABASE_URL": "postgresql://user:pass@localhost/sardis"},
    )

    assert config.database_url == "postgresql://user:pass@localhost/sardis"
    assert config.use_postgres is True


def test_resolve_storage_backend_falls_back_to_settings_then_ledger() -> None:
    settings_config = resolve_storage_backend(
        _settings(database_url="postgres://localhost/settings", ledger_dsn="sqlite:///ledger.db"),
        environ={},
    )
    ledger_config = resolve_storage_backend(
        _settings(database_url="", ledger_dsn="sqlite:///ledger.db"),
        environ={},
    )

    assert settings_config.database_url == "postgres://localhost/settings"
    assert settings_config.use_postgres is True
    assert ledger_config.database_url == "sqlite:///ledger.db"
    assert ledger_config.use_postgres is False


def test_resolve_storage_backend_requires_database_url_in_production() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL is required in production"):
        resolve_storage_backend(
            _settings(database_url="", ledger_dsn="", is_production=True),
            environ={},
        )


def test_resolve_storage_backend_requires_postgres_in_production() -> None:
    with pytest.raises(RuntimeError, match="Production requires PostgreSQL"):
        resolve_storage_backend(
            _settings(database_url="sqlite:///prod.db", is_production=True),
            environ={},
        )


def test_resolve_cache_backend_prefers_sardis_redis_url() -> None:
    config = resolve_cache_backend(
        _settings(redis_url="redis://settings"),
        environ={
            "SARDIS_REDIS_URL": "redis://sardis",
            "REDIS_URL": "redis://generic",
            "UPSTASH_REDIS_URL": "redis://upstash",
        },
    )

    assert config.redis_url == "redis://sardis"


def test_resolve_cache_backend_falls_back_to_generic_urls_then_settings() -> None:
    generic_config = resolve_cache_backend(
        _settings(redis_url="redis://settings"),
        environ={"REDIS_URL": "redis://generic"},
    )
    upstash_config = resolve_cache_backend(
        _settings(redis_url="redis://settings"),
        environ={"UPSTASH_REDIS_URL": "redis://upstash"},
    )
    settings_config = resolve_cache_backend(
        _settings(redis_url="redis://settings"),
        environ={},
    )

    assert generic_config.redis_url == "redis://generic"
    assert upstash_config.redis_url == "redis://upstash"
    assert settings_config.redis_url == "redis://settings"


def test_resolve_cache_backend_requires_redis_in_production() -> None:
    with pytest.raises(RuntimeError, match="Redis is required in production"):
        resolve_cache_backend(_settings(is_production=True), environ={})
