"""Money movement route registration helpers."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from sardis_v2_core.orchestrator import PaymentOrchestrator

from server.routes.money_movement import (
    batch_payments,
    bridge,
    fx,
    holds,
    ledger,
    pay,
    payment_objects,
    payments_refund,
    receipts,
    settlements,
    streaming_payments,
    swap,
    transactions,
)


def register_pay_endpoint(
    app: FastAPI,
    *,
    orchestrator: PaymentOrchestrator,
    chain_mode: str,
) -> None:
    """Register the unified payment execution endpoint."""
    app.dependency_overrides[pay.get_deps] = lambda: pay.PayDependencies(  # type: ignore[arg-type]
        orchestrator=orchestrator,
        chain_mode=chain_mode,
    )
    app.include_router(pay.router, prefix="/api/v2/pay", tags=["pay"])


def register_ledger_routes(app: FastAPI, *, ledger_store: Any) -> None:
    """Register ledger routes."""
    app.dependency_overrides[ledger.get_deps] = lambda: ledger.LedgerDependencies(  # type: ignore[arg-type]
        ledger=ledger_store,
    )
    app.include_router(ledger.router, prefix="/api/v2/ledger")


def register_hold_routes(
    app: FastAPI,
    *,
    database_url: str,
    use_postgres: bool,
) -> None:
    """Register hold routes and expose hold dependencies on app state."""
    from sardis_v2_core.holds import HoldsRepository

    holds_repo = HoldsRepository(dsn=database_url if use_postgres else "memory://")
    app.state.holds_deps = holds.HoldsDependencies(holds_repo=holds_repo)
    app.state.holds_repo = holds_repo
    app.dependency_overrides[holds.get_deps] = lambda: holds.HoldsDependencies(  # type: ignore[arg-type]
        holds_repo=holds_repo,
    )
    app.include_router(holds.router, prefix="/api/v2/holds")


def register_transaction_routes(
    app: FastAPI,
    *,
    chain_executor: Any,
    canonical_repo: Any,
) -> None:
    """Register transaction routes."""
    app.dependency_overrides[transactions.get_deps] = lambda: transactions.TransactionDependencies(  # type: ignore[arg-type]
        chain_executor=chain_executor,
        canonical_repo=canonical_repo,
    )
    app.include_router(transactions.router, prefix="/api/v2/transactions")


def register_bridge_routes(
    app: FastAPI,
    *,
    wallet_repo: Any,
    chain_executor: Any,
) -> None:
    """Register cross-chain bridge routes."""
    app.dependency_overrides[bridge.get_deps] = lambda: bridge.BridgeDependencies(
        wallet_repo=wallet_repo,
        chain_executor=chain_executor,
    )
    app.include_router(bridge.router, prefix="/api/v2/bridge", tags=["bridge"])


def register_refund_routes(app: FastAPI) -> None:
    """Register payment refund routes."""
    app.include_router(payments_refund.router, prefix="/api/v2/payments", tags=["payments", "refunds"])


def register_settlement_routes(app: FastAPI) -> None:
    """Register settlement routes."""
    app.include_router(settlements.router)


def register_receipt_routes(app: FastAPI) -> None:
    """Register receipt routes."""
    app.include_router(receipts.router, prefix="/api/v2/receipts", tags=["receipts"])


def register_payment_object_routes(app: FastAPI) -> None:
    """Register payment object routes."""
    app.include_router(payment_objects.router, prefix="/api/v2", tags=["payment-objects"])


def register_fx_routes(app: FastAPI) -> None:
    """Register FX quote routes."""
    app.include_router(fx.router, prefix="/api/v2", tags=["fx"])


def register_batch_payment_routes(app: FastAPI) -> None:
    """Register batch payment routes."""
    app.include_router(batch_payments.router, prefix="/api/v2", tags=["batch-payments"])


def register_streaming_payment_routes(app: FastAPI) -> None:
    """Register streaming payment routes."""
    app.include_router(streaming_payments.router, prefix="/api/v2", tags=["streaming-payments"])


def register_swap_routes(app: FastAPI) -> None:
    """Register swap, bridge quote, and verification helper routes."""
    app.include_router(swap.router, prefix="/api/v2", tags=["swap", "bridge", "verifications"])
