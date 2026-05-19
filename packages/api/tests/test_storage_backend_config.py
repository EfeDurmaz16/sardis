from types import SimpleNamespace

import pytest

from sardis_server.dependencies import (
    configure_kyc_service,
    configure_sanctions_service,
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


class FakeKYCService:
    def __init__(self, *, provider: object) -> None:
        self.provider = provider


class FakeFailoverKYCProvider:
    def __init__(self, primary: object, fallback: object) -> None:
        self.primary = primary
        self.fallback = fallback


class FakePersonaKYCProvider:
    def __init__(
        self,
        *,
        api_key: str,
        template_id: str,
        webhook_secret: str | None,
        environment: str,
    ) -> None:
        self.api_key = api_key
        self.template_id = template_id
        self.webhook_secret = webhook_secret
        self.environment = environment


class FakeMockKYCProvider:
    pass


def _configure_kyc(settings=None, environ=None, create_kyc_service_fn=None):
    return configure_kyc_service(
        settings or _settings(),
        environ=environ or {},
        kyc_service_cls=FakeKYCService,
        failover_provider_cls=FakeFailoverKYCProvider,
        persona_provider_cls=FakePersonaKYCProvider,
        mock_provider_cls=FakeMockKYCProvider,
        create_kyc_service_fn=create_kyc_service_fn or (lambda **kwargs: SimpleNamespace(**kwargs)),
    )


def test_configure_kyc_service_uses_persona_primary() -> None:
    config = _configure_kyc(
        environ={
            "PERSONA_API_KEY": "persona_key",
            "PERSONA_TEMPLATE_ID": "template_123",
            "PERSONA_WEBHOOK_SECRET": "secret",
        }
    )

    assert config.mode == "primary"
    assert config.primary_name == "persona"
    assert isinstance(config.service, FakeKYCService)
    assert isinstance(config.service.provider, FakePersonaKYCProvider)
    assert config.service.provider.api_key == "persona_key"
    assert config.service.provider.template_id == "template_123"
    assert config.service.provider.webhook_secret == "secret"
    assert config.service.provider.environment == "sandbox"


def test_configure_kyc_service_uses_production_persona_environment() -> None:
    config = _configure_kyc(
        settings=_settings(is_production=True),
        environ={
            "PERSONA_API_KEY": "persona_key",
            "PERSONA_TEMPLATE_ID": "template_123",
        },
    )

    assert config.service.provider.environment == "production"


def test_configure_kyc_service_builds_failover_provider() -> None:
    config = _configure_kyc(
        environ={
            "SARDIS_KYC_PRIMARY_PROVIDER": "persona",
            "SARDIS_KYC_FALLBACK_PROVIDER": "mock",
            "PERSONA_API_KEY": "persona_key",
            "PERSONA_TEMPLATE_ID": "template_123",
        }
    )

    assert config.mode == "failover"
    assert isinstance(config.service.provider, FakeFailoverKYCProvider)
    assert isinstance(config.service.provider.primary, FakePersonaKYCProvider)
    assert isinstance(config.service.provider.fallback, FakeMockKYCProvider)


def test_configure_kyc_service_uses_fallback_when_primary_unavailable() -> None:
    config = _configure_kyc(
        environ={
            "SARDIS_KYC_PRIMARY_PROVIDER": "persona",
            "SARDIS_KYC_FALLBACK_PROVIDER": "mock",
        }
    )

    assert config.mode == "fallback"
    assert isinstance(config.service.provider, FakeMockKYCProvider)


def test_configure_kyc_service_ignores_duplicate_fallback_provider() -> None:
    config = _configure_kyc(
        environ={
            "SARDIS_KYC_PRIMARY_PROVIDER": "mock",
            "SARDIS_KYC_FALLBACK_PROVIDER": "mock",
        }
    )

    assert config.mode == "primary"
    assert config.fallback_name == "mock"
    assert isinstance(config.service.provider, FakeMockKYCProvider)


def test_configure_kyc_service_requires_provider_in_production() -> None:
    with pytest.raises(RuntimeError, match="Production requires at least one KYC provider"):
        _configure_kyc(settings=_settings(is_production=True), environ={})


def test_configure_kyc_service_uses_factory_outside_production_without_provider() -> None:
    captured = {}

    def fake_create_kyc_service(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="factory")

    config = _configure_kyc(
        environ={"PERSONA_WEBHOOK_SECRET": "secret"},
        create_kyc_service_fn=fake_create_kyc_service,
    )

    assert config.mode == "factory"
    assert config.service.name == "factory"
    assert captured == {
        "api_key": None,
        "template_id": None,
        "webhook_secret": "secret",
        "environment": "sandbox",
    }


class FakeSanctionsService:
    def __init__(self, *, provider: object) -> None:
        self.provider = provider


class FakeFailoverSanctionsProvider:
    def __init__(self, primary: object, fallback: object) -> None:
        self.primary = primary
        self.fallback = fallback


class FakeEllipticProvider:
    def __init__(self, *, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret


class FakeScorechainProvider:
    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key


class FakeMockSanctionsProvider:
    pass


def _configure_sanctions(
    settings=None,
    environ=None,
    scorechain_provider_cls=FakeScorechainProvider,
    create_sanctions_service_fn=None,
):
    return configure_sanctions_service(
        settings or _settings(),
        environ=environ or {},
        sanctions_service_cls=FakeSanctionsService,
        failover_provider_cls=FakeFailoverSanctionsProvider,
        elliptic_provider_cls=FakeEllipticProvider,
        scorechain_provider_cls=scorechain_provider_cls,
        mock_provider_cls=FakeMockSanctionsProvider,
        create_sanctions_service_fn=(
            create_sanctions_service_fn or (lambda **kwargs: SimpleNamespace(**kwargs))
        ),
    )


def test_configure_sanctions_service_uses_elliptic_primary() -> None:
    config = _configure_sanctions(
        environ={
            "ELLIPTIC_API_KEY": "elliptic_key",
            "ELLIPTIC_API_SECRET": "elliptic_secret",
        }
    )

    assert config.mode == "primary"
    assert config.primary_name == "elliptic"
    assert isinstance(config.service, FakeSanctionsService)
    assert isinstance(config.service.provider, FakeEllipticProvider)
    assert config.service.provider.api_key == "elliptic_key"
    assert config.service.provider.api_secret == "elliptic_secret"


def test_configure_sanctions_service_requires_complete_elliptic_credentials() -> None:
    config = _configure_sanctions(
        environ={
            "ELLIPTIC_API_KEY": "elliptic_key",
            "SARDIS_SANCTIONS_FALLBACK_PROVIDER": "mock",
        }
    )

    assert config.mode == "fallback"
    assert isinstance(config.service.provider, FakeMockSanctionsProvider)


def test_configure_sanctions_service_uses_scorechain_primary() -> None:
    config = _configure_sanctions(
        environ={
            "SARDIS_SANCTIONS_PRIMARY_PROVIDER": "scorechain",
            "SCORECHAIN_API_KEY": "scorechain_key",
        }
    )

    assert config.mode == "primary"
    assert isinstance(config.service.provider, FakeScorechainProvider)
    assert config.service.provider.api_key == "scorechain_key"


def test_configure_sanctions_service_skips_scorechain_when_provider_unavailable() -> None:
    config = _configure_sanctions(
        environ={
            "SARDIS_SANCTIONS_PRIMARY_PROVIDER": "scorechain",
            "SARDIS_SANCTIONS_FALLBACK_PROVIDER": "mock",
            "SCORECHAIN_API_KEY": "scorechain_key",
        },
        scorechain_provider_cls=None,
    )

    assert config.mode == "fallback"
    assert isinstance(config.service.provider, FakeMockSanctionsProvider)


def test_configure_sanctions_service_builds_failover_provider() -> None:
    config = _configure_sanctions(
        environ={
            "SARDIS_SANCTIONS_PRIMARY_PROVIDER": "elliptic",
            "SARDIS_SANCTIONS_FALLBACK_PROVIDER": "scorechain",
            "ELLIPTIC_API_KEY": "elliptic_key",
            "ELLIPTIC_API_SECRET": "elliptic_secret",
            "SCORECHAIN_API_KEY": "scorechain_key",
        }
    )

    assert config.mode == "failover"
    assert isinstance(config.service.provider, FakeFailoverSanctionsProvider)
    assert isinstance(config.service.provider.primary, FakeEllipticProvider)
    assert isinstance(config.service.provider.fallback, FakeScorechainProvider)


def test_configure_sanctions_service_ignores_duplicate_fallback_provider() -> None:
    config = _configure_sanctions(
        environ={
            "SARDIS_SANCTIONS_PRIMARY_PROVIDER": "mock",
            "SARDIS_SANCTIONS_FALLBACK_PROVIDER": "mock",
        }
    )

    assert config.mode == "primary"
    assert config.fallback_name == "mock"
    assert isinstance(config.service.provider, FakeMockSanctionsProvider)


def test_configure_sanctions_service_requires_provider_in_production() -> None:
    with pytest.raises(RuntimeError, match="Production requires at least one sanctions provider"):
        _configure_sanctions(settings=_settings(is_production=True), environ={})


def test_configure_sanctions_service_uses_factory_outside_production_without_provider() -> None:
    captured = {}

    def fake_create_sanctions_service(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="factory")

    config = _configure_sanctions(
        environ={"ELLIPTIC_API_KEY": "partial_key"},
        create_sanctions_service_fn=fake_create_sanctions_service,
    )

    assert config.mode == "factory"
    assert config.service.name == "factory"
    assert captured == {
        "api_key": "partial_key",
        "api_secret": None,
    }
