"""API composition root."""
from __future__ import annotations

from fastapi import FastAPI

from sardis_v2_core import SardisSettings, load_settings
from sardis_wallet.manager import WalletManager
from sardis_protocol.verifier import MandateVerifier
from sardis_chain.executor import ChainExecutor
from sardis_ledger.records import LedgerStore
from sardis_compliance.checks import ComplianceEngine
from sardis_v2_core.orchestrator import PaymentOrchestrator
from .routers import mandates, ap2


def create_app(settings: SardisSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(
        title="Sardis Stablecoin Execution API",
        version="0.1.0",
        openapi_url="/api/v2/openapi.json",
        docs_url="/api/v2/docs",
    )

    wallet_mgr = WalletManager(settings=settings)
    chain_exec = ChainExecutor(settings=settings)
    ledger = LedgerStore(dsn=settings.ledger_dsn)
    compliance = ComplianceEngine(settings=settings)
    verifier = MandateVerifier(settings=settings)
    orchestrator = PaymentOrchestrator(
        wallet_manager=wallet_mgr,
        compliance=compliance,
        chain_executor=chain_exec,
        ledger=ledger,
    )

    app.dependency_overrides[mandates.get_deps] = lambda: mandates.Dependencies(  # type: ignore[arg-type]
        wallet_manager=wallet_mgr,
        chain_executor=chain_exec,
        verifier=verifier,
        ledger=ledger,
        compliance=compliance,
    )
    app.include_router(mandates.router, prefix="/api/v2/mandates")

    app.dependency_overrides[ap2.get_deps] = lambda: ap2.Dependencies(  # type: ignore[arg-type]
        verifier=verifier,
        orchestrator=orchestrator,
    )
    app.include_router(ap2.router, prefix="/api/v2/ap2")

    return app
