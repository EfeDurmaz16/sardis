"""Wallet, ramp, and card route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from sardis_server.routes.wallets import offramp, onchain_payments, onramp, virtual_cards, wallets


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
