from types import SimpleNamespace

from server.card_runtime import configure_card_runtime


def _settings(**overrides):
    defaults = {
        "cards": SimpleNamespace(
            on_chain_provider="",
            primary_provider="mock",
            fallback_provider="",
            org_provider_overrides_json="",
        ),
        "lithic": SimpleNamespace(
            api_key="",
            environment="sandbox",
            webhook_secret="",
            asa_enabled=False,
            asa_webhook_secret="",
        ),
        "stripe": SimpleNamespace(
            api_key="",
            webhook_secret="",
        ),
        "rain": SimpleNamespace(
            api_key="",
            base_url="",
            program_id="",
            cards_path_map_json="",
            cards_method_map_json="",
            webhook_secret="",
        ),
        "bridge_cards": SimpleNamespace(
            api_key="",
            api_secret="",
            cards_base_url="",
            program_id="",
            cards_path_map_json="",
            cards_method_map_json="",
            webhook_secret="",
        ),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FakeCardRepository:
    def __init__(self, *, dsn=None) -> None:
        self.dsn = dsn


class FakeCardProviderAdapter:
    def __init__(self, provider: object, repository: object) -> None:
        self.provider = provider
        self.repository = repository


class FakeMockCardProvider:
    pass


class FakeLithicCardProvider:
    def __init__(self, *, api_key: str, environment: str) -> None:
        self.api_key = api_key
        self.environment = environment


class FakeStripeIssuingProvider:
    def __init__(self, *, api_key: str, webhook_secret: str | None, policy_evaluator) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.policy_evaluator = policy_evaluator


class FakeCardProviderRouter:
    def __init__(self, *, primary: object, fallback: object) -> None:
        self.primary = primary
        self.fallback = fallback


class FakeOrganizationCardProviderRouter:
    def __init__(
        self,
        *,
        default_provider: object,
        providers_by_org: dict[str, object],
        wallet_org_resolver,
    ) -> None:
        self.default_provider = default_provider
        self.providers_by_org = providers_by_org
        self.wallet_org_resolver = wallet_org_resolver


class FakeCardWebhookHandler:
    def __init__(self, *, secret: str, provider: str) -> None:
        self.secret = secret
        self.provider = provider


class FakeASAHandler:
    def __init__(self, *, webhook_handler: object, card_lookup) -> None:
        self.webhook_handler = webhook_handler
        self.card_lookup = card_lookup


def _configure_card(settings=None, environ=None, *, use_postgres=True):
    return configure_card_runtime(
        settings or _settings(),
        database_url="postgresql://localhost/sardis",
        use_postgres=use_postgres,
        policy_store=object(),
        wallet_repository=object(),
        agent_repository=object(),
        environ=environ or {},
        card_repository_cls=FakeCardRepository,
        card_provider_adapter_cls=FakeCardProviderAdapter,
        mock_provider_cls=FakeMockCardProvider,
        lithic_provider_cls=FakeLithicCardProvider,
        stripe_issuing_provider_cls=FakeStripeIssuingProvider,
        card_provider_router_cls=FakeCardProviderRouter,
        organization_card_provider_router_cls=FakeOrganizationCardProviderRouter,
        asa_handler_cls=FakeASAHandler,
        card_webhook_handler_cls=FakeCardWebhookHandler,
    )


def test_configure_card_runtime_returns_disabled_dependencies_without_feature_flag() -> None:
    config = _configure_card()

    assert config.cards_enabled is False
    assert config.card_repository is None
    assert config.card_provider is None
    assert config.webhook_secret is None
    assert config.asa_handler is None


def test_configure_card_runtime_builds_mock_provider_when_enabled() -> None:
    config = _configure_card(environ={"SARDIS_ENABLE_CARDS": "true"})

    assert config.cards_enabled is True
    assert isinstance(config.card_repository, FakeCardRepository)
    assert config.card_repository.dsn == "postgresql://localhost/sardis"
    assert isinstance(config.card_provider, FakeCardProviderAdapter)
    assert isinstance(config.card_provider.provider, FakeMockCardProvider)
    assert config.card_provider.repository is config.card_repository


def test_configure_card_runtime_builds_primary_fallback_router() -> None:
    config = _configure_card(
        settings=_settings(
            cards=SimpleNamespace(
                on_chain_provider="",
                primary_provider="mock",
                fallback_provider="lithic",
                org_provider_overrides_json="",
            )
        ),
        environ={
            "SARDIS_ENABLE_CARDS": "1",
            "LITHIC_API_KEY": "lithic_key",
        },
    )

    assert isinstance(config.card_provider.provider, FakeCardProviderRouter)
    assert isinstance(config.card_provider.provider.primary, FakeMockCardProvider)
    assert isinstance(config.card_provider.provider.fallback, FakeLithicCardProvider)
    assert config.card_provider.provider.fallback.api_key == "lithic_key"


def test_configure_card_runtime_enables_lithic_asa_handler() -> None:
    config = _configure_card(
        settings=_settings(
            cards=SimpleNamespace(
                on_chain_provider="",
                primary_provider="lithic",
                fallback_provider="",
                org_provider_overrides_json="",
            ),
            lithic=SimpleNamespace(
                api_key="settings_lithic",
                environment="sandbox",
                webhook_secret="",
                asa_enabled=True,
                asa_webhook_secret="asa_secret",
            ),
        ),
        environ={"SARDIS_ENABLE_CARDS": "yes"},
    )

    assert isinstance(config.asa_handler, FakeASAHandler)
    assert isinstance(config.asa_handler.webhook_handler, FakeCardWebhookHandler)
    assert config.asa_handler.webhook_handler.secret == "asa_secret"
    assert config.asa_handler.webhook_handler.provider == "lithic"


def test_configure_card_runtime_uses_partner_webhook_env_values() -> None:
    config = _configure_card(
        environ={
            "SARDIS_ENABLE_CARDS": "true",
            "RAIN_WEBHOOK_SECRET": "rain_webhook",
            "BRIDGE_CARDS_WEBHOOK_SECRET": "bridge_webhook",
        }
    )

    assert config.rain_webhook_secret == "rain_webhook"
    assert config.bridge_webhook_secret == "bridge_webhook"
