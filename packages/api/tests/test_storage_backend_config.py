from types import SimpleNamespace

import pytest

from sardis_server.dependencies import (
    initialize_turnkey_client,
    resolve_cache_backend,
    resolve_storage_backend,
    validate_live_execution_config,
)


def _settings(**overrides):
    defaults = {
        "database_url": "",
        "ledger_dsn": "memory://",
        "redis_url": None,
        "is_production": False,
        "chain_mode": "simulated",
        "mpc": SimpleNamespace(name="simulated"),
        "turnkey": SimpleNamespace(
            api_public_key="",
            api_private_key="",
            organization_id="",
        ),
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


def test_validate_live_execution_requires_live_chain_mode_in_production() -> None:
    with pytest.raises(RuntimeError, match="Production requires SARDIS_CHAIN_MODE=live"):
        validate_live_execution_config(
            _settings(is_production=True, chain_mode="simulated"),
            turnkey_client=None,
            environ={},
        )


def test_validate_live_execution_rejects_simulated_signer_in_live_mode() -> None:
    with pytest.raises(RuntimeError, match="Simulated signer is not allowed"):
        validate_live_execution_config(
            _settings(chain_mode="live", mpc=SimpleNamespace(name="simulated")),
            turnkey_client=None,
            environ={},
        )


def test_validate_live_execution_requires_turnkey_client_for_turnkey_mpc() -> None:
    with pytest.raises(RuntimeError, match="Turnkey MPC provider required"):
        validate_live_execution_config(
            _settings(chain_mode="live", mpc=SimpleNamespace(name="turnkey")),
            turnkey_client=None,
            environ={},
        )


def test_validate_live_execution_accepts_configured_turnkey_mpc() -> None:
    config = validate_live_execution_config(
        _settings(chain_mode="live", mpc=SimpleNamespace(name="turnkey")),
        turnkey_client=object(),
        environ={},
    )

    assert config.chain_mode == "live"
    assert config.mpc_name == "turnkey"


def test_validate_live_execution_requires_fireblocks_key() -> None:
    with pytest.raises(RuntimeError, match="Fireblocks MPC provider required"):
        validate_live_execution_config(
            _settings(chain_mode="live", mpc=SimpleNamespace(name="fireblocks")),
            turnkey_client=None,
            environ={},
        )


def test_validate_live_execution_accepts_configured_fireblocks_mpc() -> None:
    config = validate_live_execution_config(
        _settings(chain_mode="live", mpc=SimpleNamespace(name="fireblocks")),
        turnkey_client=None,
        environ={"FIREBLOCKS_API_KEY": "fb_key"},
    )

    assert config.mpc_name == "fireblocks"


def test_validate_live_execution_rejects_local_signer_in_production() -> None:
    with pytest.raises(RuntimeError, match="Local signer is custodial"):
        validate_live_execution_config(
            _settings(
                is_production=True,
                chain_mode="live",
                mpc=SimpleNamespace(name="local"),
            ),
            turnkey_client=None,
            environ={"SARDIS_EOA_PRIVATE_KEY": "0xkey"},
        )


def test_validate_live_execution_requires_local_private_key() -> None:
    with pytest.raises(RuntimeError, match="SARDIS_MPC__NAME=local requires"):
        validate_live_execution_config(
            _settings(chain_mode="live", mpc=SimpleNamespace(name="local")),
            turnkey_client=None,
            environ={},
        )


def test_validate_live_execution_accepts_local_signer_outside_production() -> None:
    config = validate_live_execution_config(
        _settings(chain_mode="live", mpc=SimpleNamespace(name="local")),
        turnkey_client=None,
        environ={"SARDIS_EOA_PRIVATE_KEY": "0xkey"},
    )

    assert config.mpc_name == "local"


def test_validate_live_execution_env_mpc_overrides_settings() -> None:
    config = validate_live_execution_config(
        _settings(chain_mode="live", mpc=SimpleNamespace(name="simulated")),
        turnkey_client=object(),
        environ={"SARDIS_MPC__NAME": "turnkey"},
    )

    assert config.mpc_name == "turnkey"


class FakeTurnkeyClient:
    def __init__(self, *, api_key: str, api_private_key: str, organization_id: str) -> None:
        self.api_key = api_key
        self.api_private_key = api_private_key
        self.organization_id = organization_id


def test_initialize_turnkey_client_returns_none_without_complete_credentials() -> None:
    assert (
        initialize_turnkey_client(
            _settings(),
            environ={"TURNKEY_API_PUBLIC_KEY": "tk_public"},
            client_cls=FakeTurnkeyClient,
        )
        is None
    )


def test_initialize_turnkey_client_prefers_env_credentials() -> None:
    client = initialize_turnkey_client(
        _settings(
            turnkey=SimpleNamespace(
                api_public_key="settings_public",
                api_private_key="settings_private",
                organization_id="settings_org",
            )
        ),
        environ={
            "TURNKEY_API_PUBLIC_KEY": "env_public",
            "TURNKEY_API_PRIVATE_KEY": "env_private",
            "TURNKEY_ORGANIZATION_ID": "env_org",
        },
        client_cls=FakeTurnkeyClient,
    )

    assert isinstance(client, FakeTurnkeyClient)
    assert client.api_key == "env_public"
    assert client.api_private_key == "env_private"
    assert client.organization_id == "env_org"


def test_initialize_turnkey_client_falls_back_to_legacy_api_key_env() -> None:
    client = initialize_turnkey_client(
        _settings(),
        environ={
            "TURNKEY_API_KEY": "legacy_key",
            "TURNKEY_API_PRIVATE_KEY": "env_private",
            "TURNKEY_ORGANIZATION_ID": "env_org",
        },
        client_cls=FakeTurnkeyClient,
    )

    assert isinstance(client, FakeTurnkeyClient)
    assert client.api_key == "legacy_key"


def test_initialize_turnkey_client_uses_settings_credentials() -> None:
    client = initialize_turnkey_client(
        _settings(
            turnkey=SimpleNamespace(
                api_public_key="settings_public",
                api_private_key="settings_private",
                organization_id="settings_org",
            )
        ),
        environ={},
        client_cls=FakeTurnkeyClient,
    )

    assert isinstance(client, FakeTurnkeyClient)
    assert client.api_key == "settings_public"
    assert client.api_private_key == "settings_private"
    assert client.organization_id == "settings_org"
