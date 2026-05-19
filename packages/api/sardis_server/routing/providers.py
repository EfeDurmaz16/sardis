"""Provider integration and webhook route registration helpers."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from sardis_server.routes.providers import mastercard_webhooks, stripe_funding

logger = logging.getLogger("sardis_server.api.routing.providers")


def register_mastercard_webhook_routes(app: FastAPI) -> None:
    """Register Mastercard Agent Pay inbound webhook routes."""
    app.include_router(mastercard_webhooks.router)
    logger.info("Mastercard webhook router enabled at /mastercard/webhooks")


def register_stripe_funding_routes(
    app: FastAPI,
    *,
    treasury_provider,
    funding_adapter,
    fallback_funding_adapter,
    treasury_repo,
    canonical_repo,
    default_connected_account_id: str,
    connected_account_map: dict[str, str],
    funding_strategy: str,
    stablecoin_prefund_enabled: bool,
    require_connected_account: bool,
) -> None:
    """Register Stripe Issuing funding routes."""
    app.dependency_overrides[stripe_funding.get_deps] = (
        lambda: stripe_funding.StripeFundingDeps(
            treasury_provider=treasury_provider,
            funding_adapter=funding_adapter,
            fallback_funding_adapter=fallback_funding_adapter,
            treasury_repo=treasury_repo,
            canonical_repo=canonical_repo,
            default_connected_account_id=default_connected_account_id,
            connected_account_map=connected_account_map,
            funding_strategy=funding_strategy,
            stablecoin_prefund_enabled=stablecoin_prefund_enabled,
            require_connected_account=require_connected_account,
        )
    )
    app.include_router(stripe_funding.router, prefix="/api/v2")
    logger.info("Stripe funding router enabled at /api/v2/stripe/funding")
