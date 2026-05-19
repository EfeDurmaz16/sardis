"""Wallet, ramp, and card route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from sardis_server.routes.wallets import (
    cards,
    cpn,
    funding,
    funding_capabilities,
    offramp,
    onchain_payments,
    onramp,
    ramp,
    treasury,
    treasury_ops,
    virtual_cards,
    wallets,
)


def register_card_routes(
    app: FastAPI,
    *,
    card_repo: Any,
    card_provider: Any,
    webhook_secret: str | None,
    environment: str,
    offramp_service: Any,
    chain_executor: Any,
    wallet_repo: Any,
    policy_store: Any,
    treasury_repo: Any,
    agent_repo: Any,
    canonical_repo: Any,
    asa_handler: Any = None,
) -> None:
    """Register card routes with provider-injected dependencies when available."""
    if card_provider:
        injected_router = cards.create_cards_router(
            card_repo,
            card_provider,
            webhook_secret,
            environment=environment,
            offramp_service=offramp_service,
            chain_executor=chain_executor,
            wallet_repo=wallet_repo,
            policy_store=policy_store,
            treasury_repo=treasury_repo,
            agent_repo=agent_repo,
            canonical_repo=canonical_repo,
            asa_handler=asa_handler,
        )
        app.include_router(injected_router, prefix="/api/v2/cards", tags=["cards"])
        return

    app.include_router(cards.router, prefix="/api/v2/cards", tags=["cards"])


def register_wallet_core_routes(
    app: FastAPI,
    *,
    wallet_repo: Any,
    agent_repo: Any,
    chain_executor: Any,
    wallet_manager: Any,
    ledger: Any,
    settings: Any,
    compliance: Any,
    inbound_payment_service: Any,
    circle_nanopayments_client: Any,
) -> None:
    """Register core wallet and receive routes."""
    def get_wallet_deps() -> wallets.WalletDependencies:
        return wallets.WalletDependencies(  # type: ignore[arg-type]
            wallet_repo=wallet_repo,
            agent_repo=agent_repo,
            chain_executor=chain_executor,
            wallet_manager=wallet_manager,
            ledger=ledger,
            settings=settings,
            canonical_repo=getattr(app.state, "canonical_ledger_repo", None),
            compliance=compliance,
            inbound_payment_service=inbound_payment_service,
            circle_nanopayments_client=circle_nanopayments_client,
        )

    app.dependency_overrides[wallets.get_deps] = get_wallet_deps
    app.include_router(wallets.router, prefix="/api/v2/wallets", tags=["wallets"])


def register_onchain_payment_routes(
    app: FastAPI,
    *,
    wallet_repo: Any,
    agent_repo: Any,
    policy_store: Any,
    approval_service: Any,
    sanctions_service: Any,
    kya_service: Any,
    coinbase_cdp_provider: Any,
    default_on_chain_provider: Any,
    audit_store: Any,
    settings: Any,
    payment_orchestrator: Any,
) -> None:
    """Register on-chain payment routes under the wallet API surface."""
    app.dependency_overrides[onchain_payments.get_deps] = (
        lambda: onchain_payments.OnChainPaymentDependencies(
            wallet_repo=wallet_repo,
            agent_repo=agent_repo,
            policy_store=policy_store,
            approval_service=approval_service,
            sanctions_service=sanctions_service,
            kya_service=kya_service,
            coinbase_cdp_provider=coinbase_cdp_provider,
            default_on_chain_provider=default_on_chain_provider,
            audit_store=audit_store,
            settings=settings,
            payment_orchestrator=payment_orchestrator,
        )
    )
    app.include_router(onchain_payments.router, prefix="/api/v2/wallets", tags=["wallets"])


def register_ramp_routes(
    app: FastAPI,
    *,
    wallet_repo: Any,
    agent_repo: Any,
    offramp_service: Any,
    onramper_api_key: str,
    onramper_webhook_secret: str,
    bridge_webhook_secret: str,
    fiat_ramp: Any,
) -> None:
    """Register fiat on-ramp and off-ramp routes."""
    app.dependency_overrides[ramp.get_deps] = lambda: ramp.RampDependencies(
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        offramp_service=offramp_service,
        onramper_api_key=onramper_api_key,
        onramper_webhook_secret=onramper_webhook_secret,
        bridge_webhook_secret=bridge_webhook_secret,
        fiat_ramp=fiat_ramp,
    )
    app.include_router(ramp.router, prefix="/api/v2/ramp", tags=["ramp"])
    if hasattr(ramp, "public_router"):
        app.include_router(ramp.public_router, prefix="/api/v2/ramp", tags=["ramp"])


def register_treasury_routes(
    app: FastAPI,
    *,
    treasury_repo: Any,
    lithic_treasury_client: Any,
    lithic_webhook_secret: str,
    canonical_ledger_repo: Any,
) -> None:
    """Register treasury and treasury ops routes."""
    app.dependency_overrides[treasury.get_deps] = lambda: treasury.TreasuryDependencies(
        treasury_repo=treasury_repo,
        lithic_client=lithic_treasury_client,
        lithic_webhook_secret=lithic_webhook_secret,
        canonical_repo=canonical_ledger_repo,
    )
    app.include_router(treasury.router, prefix="/api/v2/treasury", tags=["treasury"])
    if hasattr(treasury, "public_router"):
        app.include_router(
            treasury.public_router,
            prefix="/api/v2/webhooks/lithic",
            tags=["treasury-webhooks"],
        )

    app.dependency_overrides[treasury_ops.get_deps] = lambda: treasury_ops.TreasuryOpsDependencies(
        canonical_repo=canonical_ledger_repo,
    )
    app.include_router(
        treasury_ops.router,
        prefix="/api/v2/treasury/ops",
        tags=["treasury-ops"],
    )


def register_cpn_routes(
    app: FastAPI,
    *,
    treasury_repo: Any,
    cpn_client: Any,
    webhook_secret: str,
    environment: str,
) -> None:
    """Register Circle CPN routes and webhooks."""
    app.dependency_overrides[cpn.get_deps] = lambda: cpn.CPNDependencies(
        treasury_repo=treasury_repo,
        cpn_client=cpn_client,
        webhook_secret=webhook_secret,
        environment=environment,
    )
    app.include_router(cpn.router, prefix="/api/v2")
    app.include_router(cpn.public_router, prefix="/api/v2")


def register_funding_capability_routes(app: FastAPI, *, settings: Any) -> None:
    """Register funding capability discovery routes."""
    app.dependency_overrides[funding_capabilities.get_deps] = (
        lambda: funding_capabilities.FundingCapabilitiesDeps(settings=settings)
    )
    app.include_router(funding_capabilities.router, prefix="/api/v2")


def register_funding_routes(app: FastAPI) -> None:
    """Register protocol funding commitment and funding cell routes."""
    app.include_router(funding.router, prefix="/api/v2", tags=["funding"])


def register_ramp_edge_routes(app: FastAPI) -> None:
    """Register simple fiat ramp and virtual-card edge routes."""
    app.include_router(offramp.router, prefix="/api/v2", tags=["offramp"])
    app.include_router(onramp.router, prefix="/api/v2", tags=["onramp"])
    app.include_router(
        onramp.webhook_router,
        prefix="/api/v2",
        tags=["stripe-onramp-webhooks"],
    )
    app.include_router(virtual_cards.router, prefix="/api/v2", tags=["virtual-cards"])
