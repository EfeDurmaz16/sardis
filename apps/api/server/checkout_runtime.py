"""Checkout runtime bootstrap helpers."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_DEFAULT_PROVIDER = object()


@dataclass(frozen=True)
class CheckoutOrchestratorRuntime:
    """Resolved checkout orchestrator and optional PSP connectors."""

    orchestrator: Any
    stripe_connector: Any | None


@dataclass(frozen=True)
class MerchantCheckoutRuntime:
    """Resolved merchant checkout repositories, settlement, and connectors."""

    merchant_repository: Any
    merchant_webhook_service: Any
    settlement_service: Any
    sardis_native_connector: Any
    stripe_connect_provider: Any | None
    checkout_base_url: str


def configure_checkout_orchestrator(
    *,
    environ: Mapping[str, str] | None = None,
    checkout_orchestrator_cls: Any = _DEFAULT_PROVIDER,
    stripe_connector_cls: Any = _DEFAULT_PROVIDER,
) -> CheckoutOrchestratorRuntime:
    """Create the checkout orchestrator and register configured PSP connectors."""
    env = environ if environ is not None else os.environ
    if checkout_orchestrator_cls is _DEFAULT_PROVIDER:
        from sardis.checkout.orchestrator import CheckoutOrchestrator

        checkout_orchestrator_cls = CheckoutOrchestrator
    if stripe_connector_cls is _DEFAULT_PROVIDER:
        from sardis.checkout.connectors.stripe import StripeConnector

        stripe_connector_cls = StripeConnector

    stripe_secret_key = env.get("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret = env.get("STRIPE_WEBHOOK_SECRET", "")
    stripe_connector = (
        stripe_connector_cls(
            api_key=stripe_secret_key,
            webhook_secret=stripe_webhook_secret,
        )
        if stripe_secret_key
        else None
    )
    orchestrator = checkout_orchestrator_cls()
    if stripe_connector:
        orchestrator.register_connector("stripe", stripe_connector)

    return CheckoutOrchestratorRuntime(
        orchestrator=orchestrator,
        stripe_connector=stripe_connector,
    )


def configure_merchant_checkout_runtime(
    *,
    chain_executor: Any,
    wallet_manager: Any,
    compliance_engine: Any,
    ledger_store: Any,
    environ: Mapping[str, str] | None = None,
    merchant_repository_cls: Any = _DEFAULT_PROVIDER,
    merchant_webhook_service_cls: Any = _DEFAULT_PROVIDER,
    settlement_service_cls: Any = _DEFAULT_PROVIDER,
    sardis_native_connector_cls: Any = _DEFAULT_PROVIDER,
    stripe_connect_provider_cls: Any = _DEFAULT_PROVIDER,
) -> MerchantCheckoutRuntime:
    """Create Pay with Sardis merchant checkout dependencies."""
    env = environ if environ is not None else os.environ
    if merchant_repository_cls is _DEFAULT_PROVIDER:
        from sardis.core.merchant import MerchantRepository

        merchant_repository_cls = MerchantRepository
    if merchant_webhook_service_cls is _DEFAULT_PROVIDER:
        from sardis.checkout.merchant_webhooks import MerchantWebhookService

        merchant_webhook_service_cls = MerchantWebhookService
    if settlement_service_cls is _DEFAULT_PROVIDER:
        from sardis.checkout.settlement import SettlementService

        settlement_service_cls = SettlementService
    if sardis_native_connector_cls is _DEFAULT_PROVIDER:
        from sardis.checkout.connectors.sardis_native import SardisNativeConnector

        sardis_native_connector_cls = SardisNativeConnector

    merchant_repository = merchant_repository_cls()
    merchant_webhook_service = merchant_webhook_service_cls(
        merchant_repo=merchant_repository,
    )
    stripe_connect_provider = _build_stripe_connect_provider(
        stripe_connect_provider_cls,
    )
    settlement_service = settlement_service_cls(
        merchant_repo=merchant_repository,
        offramp_service=None,
        merchant_webhook_service=merchant_webhook_service,
        stripe_connect_provider=stripe_connect_provider,
    )
    sardis_native_connector = sardis_native_connector_cls(
        chain_executor=chain_executor,
        wallet_manager=wallet_manager,
        compliance_engine=compliance_engine,
        ledger_store=ledger_store,
        merchant_repo=merchant_repository,
        settlement_service=settlement_service,
        merchant_webhook_service=merchant_webhook_service,
    )

    return MerchantCheckoutRuntime(
        merchant_repository=merchant_repository,
        merchant_webhook_service=merchant_webhook_service,
        settlement_service=settlement_service,
        sardis_native_connector=sardis_native_connector,
        stripe_connect_provider=stripe_connect_provider,
        checkout_base_url=env.get(
            "SARDIS_CHECKOUT_BASE_URL",
            "https://checkout.sardis.sh",
        ),
    )


def _build_stripe_connect_provider(stripe_connect_provider_cls: Any) -> Any | None:
    if stripe_connect_provider_cls is _DEFAULT_PROVIDER:
        try:
            from sardis.core.stripe_connect import StripeConnectProvider

            stripe_connect_provider_cls = StripeConnectProvider
        except ImportError:
            return None

    try:
        return stripe_connect_provider_cls()
    except (ImportError, ValueError):
        return None
