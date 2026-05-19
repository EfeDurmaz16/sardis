from types import SimpleNamespace

from server.checkout_runtime import (
    configure_checkout_orchestrator,
    configure_merchant_checkout_runtime,
)


class FakeCheckoutOrchestrator:
    def __init__(self) -> None:
        self.connectors = {}

    def register_connector(self, name: str, connector: object) -> None:
        self.connectors[name] = connector


class FakeStripeConnector:
    def __init__(self, *, api_key: str, webhook_secret: str) -> None:
        self.api_key = api_key
        self.webhook_secret = webhook_secret


def test_configure_checkout_orchestrator_registers_stripe_when_configured() -> None:
    runtime = configure_checkout_orchestrator(
        environ={
            "STRIPE_SECRET_KEY": "stripe_secret_fixture",
            "STRIPE_WEBHOOK_SECRET": "stripe_webhook_fixture",
        },
        checkout_orchestrator_cls=FakeCheckoutOrchestrator,
        stripe_connector_cls=FakeStripeConnector,
    )

    assert isinstance(runtime.orchestrator, FakeCheckoutOrchestrator)
    assert isinstance(runtime.stripe_connector, FakeStripeConnector)
    assert runtime.stripe_connector.api_key == "stripe_secret_fixture"
    assert runtime.stripe_connector.webhook_secret == "stripe_webhook_fixture"
    assert runtime.orchestrator.connectors == {
        "stripe": runtime.stripe_connector,
    }


def test_configure_checkout_orchestrator_skips_stripe_without_secret_key() -> None:
    runtime = configure_checkout_orchestrator(
        environ={},
        checkout_orchestrator_cls=FakeCheckoutOrchestrator,
        stripe_connector_cls=FakeStripeConnector,
    )

    assert runtime.stripe_connector is None
    assert runtime.orchestrator.connectors == {}


class FakeMerchantRepository:
    pass


class FakeMerchantWebhookService:
    def __init__(self, *, merchant_repo: object) -> None:
        self.merchant_repo = merchant_repo


class FakeSettlementService:
    def __init__(
        self,
        *,
        merchant_repo: object,
        offramp_service: object | None,
        merchant_webhook_service: object,
        stripe_connect_provider: object | None,
    ) -> None:
        self.merchant_repo = merchant_repo
        self.offramp_service = offramp_service
        self.merchant_webhook_service = merchant_webhook_service
        self.stripe_connect_provider = stripe_connect_provider


class FakeSardisNativeConnector:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeStripeConnectProvider:
    pass


class FailingStripeConnectProvider:
    def __init__(self) -> None:
        raise ValueError("stripe not configured")


def test_configure_merchant_checkout_runtime_wires_dependencies() -> None:
    chain_executor = object()
    wallet_manager = object()
    compliance_engine = object()
    ledger_store = object()

    runtime = configure_merchant_checkout_runtime(
        chain_executor=chain_executor,
        wallet_manager=wallet_manager,
        compliance_engine=compliance_engine,
        ledger_store=ledger_store,
        environ={"SARDIS_CHECKOUT_BASE_URL": "https://checkout.example"},
        merchant_repository_cls=FakeMerchantRepository,
        merchant_webhook_service_cls=FakeMerchantWebhookService,
        settlement_service_cls=FakeSettlementService,
        sardis_native_connector_cls=FakeSardisNativeConnector,
        stripe_connect_provider_cls=FakeStripeConnectProvider,
    )

    assert isinstance(runtime.merchant_repository, FakeMerchantRepository)
    assert runtime.merchant_webhook_service.merchant_repo is runtime.merchant_repository
    assert runtime.settlement_service.merchant_repo is runtime.merchant_repository
    assert runtime.settlement_service.offramp_service is None
    assert runtime.settlement_service.merchant_webhook_service is runtime.merchant_webhook_service
    assert isinstance(runtime.settlement_service.stripe_connect_provider, FakeStripeConnectProvider)
    assert runtime.stripe_connect_provider is runtime.settlement_service.stripe_connect_provider
    assert runtime.sardis_native_connector.kwargs == {
        "chain_executor": chain_executor,
        "wallet_manager": wallet_manager,
        "compliance_engine": compliance_engine,
        "ledger_store": ledger_store,
        "merchant_repo": runtime.merchant_repository,
        "settlement_service": runtime.settlement_service,
        "merchant_webhook_service": runtime.merchant_webhook_service,
    }
    assert runtime.checkout_base_url == "https://checkout.example"


def test_configure_merchant_checkout_runtime_uses_defaults_and_skips_stripe_connect_failure() -> None:
    runtime = configure_merchant_checkout_runtime(
        chain_executor=SimpleNamespace(name="chain"),
        wallet_manager=SimpleNamespace(name="wallet"),
        compliance_engine=SimpleNamespace(name="compliance"),
        ledger_store=SimpleNamespace(name="ledger"),
        environ={},
        merchant_repository_cls=FakeMerchantRepository,
        merchant_webhook_service_cls=FakeMerchantWebhookService,
        settlement_service_cls=FakeSettlementService,
        sardis_native_connector_cls=FakeSardisNativeConnector,
        stripe_connect_provider_cls=FailingStripeConnectProvider,
    )

    assert runtime.settlement_service.stripe_connect_provider is None
    assert runtime.stripe_connect_provider is None
    assert runtime.checkout_base_url == "https://checkout.sardis.sh"
