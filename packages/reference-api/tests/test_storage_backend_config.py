from types import SimpleNamespace

import pytest

from sardis_server.dependencies import (
    configure_api_support_services,
    configure_compliance_services,
    configure_core_services,
    configure_facility_gate_services,
    configure_kyc_service,
    configure_payment_runtime,
    configure_sanctions_service,
    expose_runtime_state,
    expose_support_services_state,
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


class FakeComplianceEngine:
    def __init__(
        self,
        *,
        settings: object,
        audit_store: object,
        kyc_service: object,
        sanctions_service: object,
        kya_service: object,
    ) -> None:
        self.settings = settings
        self.audit_store = audit_store
        self.kyc_service = kyc_service
        self.sanctions_service = sanctions_service
        self.kya_service = kya_service


def test_configure_compliance_services_wires_audit_kya_and_engine() -> None:
    calls = []
    settings = _settings()
    kyc_service = object()
    sanctions_service = object()

    def fake_create_audit_store(*, dsn: str):
        calls.append(("audit", dsn))
        return SimpleNamespace(name="audit", dsn=dsn)

    def fake_create_kya_service(*, liveness_timeout: int, dsn: str):
        calls.append(("kya", liveness_timeout, dsn))
        return SimpleNamespace(name="kya", liveness_timeout=liveness_timeout, dsn=dsn)

    config = configure_compliance_services(
        settings,
        database_url="postgresql://localhost/sardis",
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
        environ={"SARDIS_KYA_LIVENESS_TIMEOUT_SECONDS": "45"},
        create_audit_store_fn=fake_create_audit_store,
        create_kya_service_fn=fake_create_kya_service,
        compliance_engine_cls=FakeComplianceEngine,
    )

    assert calls == [
        ("audit", "postgresql://localhost/sardis"),
        ("kya", 45, "postgresql://localhost/sardis"),
    ]
    assert config.kya_liveness_timeout == 45
    assert config.audit_store.name == "audit"
    assert config.kya_service.name == "kya"
    assert isinstance(config.compliance_engine, FakeComplianceEngine)
    assert config.compliance_engine.settings is settings
    assert config.compliance_engine.audit_store is config.audit_store
    assert config.compliance_engine.kyc_service is kyc_service
    assert config.compliance_engine.sanctions_service is sanctions_service
    assert config.compliance_engine.kya_service is config.kya_service


def test_configure_compliance_services_uses_default_kya_liveness_timeout() -> None:
    config = configure_compliance_services(
        _settings(),
        database_url="memory://",
        kyc_service=object(),
        sanctions_service=object(),
        environ={},
        create_audit_store_fn=lambda *, dsn: SimpleNamespace(dsn=dsn),
        create_kya_service_fn=lambda *, liveness_timeout, dsn: SimpleNamespace(
            liveness_timeout=liveness_timeout,
            dsn=dsn,
        ),
        compliance_engine_cls=FakeComplianceEngine,
    )

    assert config.kya_liveness_timeout == 300
    assert config.kya_service.liveness_timeout == 300
    assert config.kya_service.dsn == "memory://"


class FakePostgresPolicyStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url


class FakeInMemoryPolicyStore:
    pass


class FakePostgresWalletRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url


class FakeWalletRepository:
    def __init__(self, *, dsn: str) -> None:
        self.dsn = dsn


class FakePostgresAgentRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url


class FakeAgentRepository:
    def __init__(self, *, dsn: str) -> None:
        self.dsn = dsn


class FakeWalletManager:
    def __init__(self, *, settings: object, turnkey_client: object, async_policy_store: object) -> None:
        self.settings = settings
        self.turnkey_client = turnkey_client
        self.async_policy_store = async_policy_store


class FakeChainExecutor:
    def __init__(self, *, settings: object, turnkey_client: object) -> None:
        self.settings = settings
        self.turnkey_client = turnkey_client


class FakeLedgerStore:
    def __init__(self, *, dsn: str) -> None:
        self.dsn = dsn


def _configure_core_services(settings=None, database_url="postgresql://localhost/sardis", use_postgres=True):
    return configure_core_services(
        settings or _settings(ledger_dsn="sqlite:///ledger.db"),
        database_url=database_url,
        use_postgres=use_postgres,
        turnkey_client=SimpleNamespace(name="turnkey"),
        postgres_policy_store_cls=FakePostgresPolicyStore,
        in_memory_policy_store_cls=FakeInMemoryPolicyStore,
        postgres_wallet_repository_cls=FakePostgresWalletRepository,
        wallet_repository_cls=FakeWalletRepository,
        postgres_agent_repository_cls=FakePostgresAgentRepository,
        agent_repository_cls=FakeAgentRepository,
        wallet_manager_cls=FakeWalletManager,
        chain_executor_cls=FakeChainExecutor,
        ledger_store_cls=FakeLedgerStore,
    )


def test_configure_core_services_uses_postgres_backends() -> None:
    config = _configure_core_services()

    assert isinstance(config.policy_store, FakePostgresPolicyStore)
    assert config.policy_store.database_url == "postgresql://localhost/sardis"
    assert isinstance(config.wallet_repository, FakePostgresWalletRepository)
    assert config.wallet_repository.database_url == "postgresql://localhost/sardis"
    assert isinstance(config.agent_repository, FakePostgresAgentRepository)
    assert config.agent_repository.database_url == "postgresql://localhost/sardis"
    assert isinstance(config.wallet_manager, FakeWalletManager)
    assert config.wallet_manager.async_policy_store is config.policy_store
    assert config.wallet_manager.turnkey_client.name == "turnkey"
    assert isinstance(config.chain_executor, FakeChainExecutor)
    assert config.chain_executor.turnkey_client.name == "turnkey"
    assert isinstance(config.ledger_store, FakeLedgerStore)
    assert config.ledger_store.dsn == "postgresql://localhost/sardis"


def test_configure_core_services_uses_memory_backends_outside_postgres() -> None:
    config = _configure_core_services(
        settings=_settings(ledger_dsn="sqlite:///ledger.db"),
        database_url="sqlite:///api.db",
        use_postgres=False,
    )

    assert isinstance(config.policy_store, FakeInMemoryPolicyStore)
    assert isinstance(config.wallet_repository, FakeWalletRepository)
    assert config.wallet_repository.dsn == "memory://"
    assert isinstance(config.agent_repository, FakeAgentRepository)
    assert config.agent_repository.dsn == "memory://"
    assert config.ledger_store.dsn == "sqlite:///ledger.db"


class FakeMandateArchive:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn


class FakePostgresReplayCache:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn


class FakeSqliteReplayCache:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn


class FakeReplayCache:
    def __init__(self) -> None:
        self.dsn = "memory://"


class FakeMandateVerifier:
    def __init__(
        self,
        *,
        settings: object,
        replay_cache: object,
        archive: object,
        identity_registry: object,
    ) -> None:
        self.settings = settings
        self.replay_cache = replay_cache
        self.archive = archive
        self.identity_registry = identity_registry


class FakePaymentOrchestrator:
    def __init__(
        self,
        *,
        wallet_manager: object,
        compliance: object,
        chain_executor: object,
        ledger: object,
    ) -> None:
        self.wallet_manager = wallet_manager
        self.compliance = compliance
        self.chain_executor = chain_executor
        self.ledger = ledger


def _configure_payment_runtime(settings=None, use_postgres=True):
    return configure_payment_runtime(
        settings or _settings(
            mandate_archive_dsn="sqlite:///mandates.db",
            replay_cache_dsn="sqlite:///replay.db",
        ),
        database_url="postgresql://localhost/sardis",
        use_postgres=use_postgres,
        identity_registry=SimpleNamespace(name="identity"),
        wallet_manager=SimpleNamespace(name="wallet_manager"),
        compliance_engine=SimpleNamespace(name="compliance"),
        chain_executor=SimpleNamespace(name="chain_executor"),
        ledger_store=SimpleNamespace(name="ledger"),
        mandate_archive_cls=FakeMandateArchive,
        postgres_replay_cache_cls=FakePostgresReplayCache,
        sqlite_replay_cache_cls=FakeSqliteReplayCache,
        replay_cache_cls=FakeReplayCache,
        mandate_verifier_cls=FakeMandateVerifier,
        payment_orchestrator_cls=FakePaymentOrchestrator,
    )


def test_configure_payment_runtime_uses_postgres_archive_and_replay_cache() -> None:
    config = _configure_payment_runtime(use_postgres=True)

    assert isinstance(config.archive, FakeMandateArchive)
    assert config.archive.dsn == "postgresql://localhost/sardis"
    assert isinstance(config.replay_cache, FakePostgresReplayCache)
    assert config.replay_cache.dsn == "postgresql://localhost/sardis"
    assert isinstance(config.verifier, FakeMandateVerifier)
    assert config.verifier.archive is config.archive
    assert config.verifier.replay_cache is config.replay_cache
    assert config.verifier.identity_registry.name == "identity"
    assert isinstance(config.orchestrator, FakePaymentOrchestrator)
    assert config.orchestrator.wallet_manager.name == "wallet_manager"
    assert config.orchestrator.compliance.name == "compliance"
    assert config.orchestrator.chain_executor.name == "chain_executor"
    assert config.orchestrator.ledger.name == "ledger"


def test_configure_payment_runtime_uses_sqlite_replay_cache_for_sqlite_dsn() -> None:
    config = _configure_payment_runtime(
        settings=_settings(
            mandate_archive_dsn="sqlite:///mandates.db",
            replay_cache_dsn="sqlite:///replay.db",
        ),
        use_postgres=False,
    )

    assert config.archive.dsn == "sqlite:///mandates.db"
    assert isinstance(config.replay_cache, FakeSqliteReplayCache)
    assert config.replay_cache.dsn == "sqlite:///replay.db"


def test_configure_payment_runtime_uses_memory_replay_cache_for_non_sqlite_dsn() -> None:
    config = _configure_payment_runtime(
        settings=_settings(
            mandate_archive_dsn="memory://mandates",
            replay_cache_dsn="memory://replay",
        ),
        use_postgres=False,
    )

    assert config.archive.dsn == "memory://mandates"
    assert isinstance(config.replay_cache, FakeReplayCache)
    assert config.replay_cache.dsn == "memory://"


class FakeAPIKeyManager:
    def __init__(self, *, dsn: str) -> None:
        self.dsn = dsn


def test_configure_api_support_services_wires_redis_cache_and_postgres_api_keys() -> None:
    installed = []

    def fake_create_cache_service(redis_url):
        return SimpleNamespace(redis_url=redis_url)

    def fake_set_api_key_manager(manager):
        installed.append(manager)

    config = configure_api_support_services(
        _settings(redis_url="redis://settings"),
        database_url="postgresql://localhost/sardis",
        use_postgres=True,
        environ={"SARDIS_REDIS_URL": "redis://env"},
        create_cache_service_fn=fake_create_cache_service,
        api_key_manager_cls=FakeAPIKeyManager,
        set_api_key_manager_fn=fake_set_api_key_manager,
    )

    assert config.redis_url == "redis://env"
    assert config.cache_service.redis_url == "redis://env"
    assert isinstance(config.api_key_manager, FakeAPIKeyManager)
    assert config.api_key_manager.dsn == "postgresql://localhost/sardis"
    assert config.api_key_manager_dsn == "postgresql://localhost/sardis"
    assert installed == [config.api_key_manager]


def test_configure_api_support_services_uses_memory_api_key_manager_without_postgres() -> None:
    installed = []

    config = configure_api_support_services(
        _settings(redis_url=None),
        database_url="sqlite:///api.db",
        use_postgres=False,
        environ={},
        create_cache_service_fn=lambda redis_url: SimpleNamespace(redis_url=redis_url),
        api_key_manager_cls=FakeAPIKeyManager,
        set_api_key_manager_fn=installed.append,
    )

    assert config.redis_url is None
    assert config.cache_service.redis_url is None
    assert config.api_key_manager.dsn == "memory://"
    assert config.api_key_manager_dsn == "memory://"
    assert installed == [config.api_key_manager]


def test_configure_api_support_services_keeps_production_redis_requirement() -> None:
    with pytest.raises(RuntimeError, match="Redis is required in production"):
        configure_api_support_services(
            _settings(is_production=True),
            database_url="postgresql://localhost/sardis",
            use_postgres=True,
            environ={},
            create_cache_service_fn=lambda redis_url: SimpleNamespace(redis_url=redis_url),
            api_key_manager_cls=FakeAPIKeyManager,
            set_api_key_manager_fn=lambda manager: None,
        )


class FakeFacilityGateRepository:
    def __init__(self, *, dsn: str) -> None:
        self.dsn = dsn


class FakeFacilityGateAdapter:
    pass


def test_configure_facility_gate_services_uses_postgres_dsn() -> None:
    config = configure_facility_gate_services(
        database_url="postgresql://localhost/sardis",
        use_postgres=True,
        repository_cls=FakeFacilityGateRepository,
        adapter_cls=FakeFacilityGateAdapter,
    )

    assert config.dsn == "postgresql://localhost/sardis"
    assert isinstance(config.repository, FakeFacilityGateRepository)
    assert config.repository.dsn == "postgresql://localhost/sardis"
    assert isinstance(config.adapter, FakeFacilityGateAdapter)


def test_configure_facility_gate_services_uses_memory_dsn_without_postgres() -> None:
    config = configure_facility_gate_services(
        database_url="sqlite:///api.db",
        use_postgres=False,
        repository_cls=FakeFacilityGateRepository,
        adapter_cls=FakeFacilityGateAdapter,
    )

    assert config.dsn == "memory://"
    assert config.repository.dsn == "memory://"


def test_expose_runtime_state_sets_route_dependency_state() -> None:
    app = SimpleNamespace(state=SimpleNamespace())
    settings = _settings()
    turnkey_client = object()
    policy_store = object()
    chain_executor = object()
    wallet_repository = object()
    compliance_engine = object()
    facility_gate_repository = object()

    expose_runtime_state(
        app,
        settings=settings,
        database_url="postgresql://localhost/sardis",
        use_postgres=True,
        turnkey_client=turnkey_client,
        policy_store=policy_store,
        chain_executor=chain_executor,
        wallet_repository=wallet_repository,
        compliance_engine=compliance_engine,
        facility_gate_repository=facility_gate_repository,
    )

    assert app.state.settings is settings
    assert app.state.database_url == "postgresql://localhost/sardis"
    assert app.state.use_postgres is True
    assert app.state.turnkey_client is turnkey_client
    assert app.state.policy_store is policy_store
    assert app.state.chain_executor is chain_executor
    assert app.state.wallet_repo is wallet_repository
    assert app.state.compliance_engine is compliance_engine
    assert app.state.facility_gate_repo is facility_gate_repository


def test_expose_support_services_state_sets_late_bound_services() -> None:
    app = SimpleNamespace(state=SimpleNamespace())
    cache_service = object()
    api_key_manager = object()

    expose_support_services_state(
        app,
        cache_service=cache_service,
        api_key_manager=api_key_manager,
    )

    assert app.state.cache_service is cache_service
    assert app.state.api_key_manager is api_key_manager
