"""Database-backed lookup for active spending mandates.

This adapter implements the :class:`SpendingMandateLookupPort` protocol used by
:class:`~sardis.core.orchestrator.PaymentOrchestrator` during the
``MANDATE_VALIDATION`` phase.  It loads the active spending mandate governing a
given agent/wallet from the ``spending_mandates`` table (migration 071) and
hydrates it into a :class:`~sardis.core.spending_mandate.SpendingMandate` so the
orchestrator can enforce scope, amount limits, rail/chain/token permissions and
approval thresholds — and, crucially, so that **revocation/suspension/expiry
take effect** (only ``status = 'active'`` rows are returned).

In dev / non-Postgres environments the lookup returns ``None`` (no mandate),
which the orchestrator treats as "no mandate configured — pass through for
backward compatibility".  This keeps local development and the in-memory test
suite working without a database.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .spending_mandate import ApprovalMode, MandateStatus, SpendingMandate

logger = logging.getLogger(__name__)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


class SpendingMandateLookup:
    """Loads the active :class:`SpendingMandate` for an agent or wallet.

    Args:
        dsn: Database connection string.  Postgres DSNs use the shared
            :class:`~sardis.core.database.Database` pool; any other value
            (e.g. ``memory://``) puts the lookup in no-op mode.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pg_pool: Any | None = None
        self._use_postgres = dsn.startswith(("postgresql://", "postgres://"))

    async def _get_pool(self) -> Any | None:
        """Lazily resolve the shared asyncpg pool (Postgres only)."""
        if self._pg_pool is None and self._use_postgres:
            from sardis.core.database import Database

            self._pg_pool = await Database.get_pool()
        return self._pg_pool

    async def get_active_mandate(
        self,
        agent_id: str | None = None,
        wallet_id: str | None = None,
    ) -> SpendingMandate | None:
        """Return the active spending mandate for the agent/wallet, or ``None``.

        Only rows with ``status = 'active'`` are returned, so revoked,
        suspended, expired and consumed mandates correctly fail closed (the
        agent loses authority).  When both ``agent_id`` and ``wallet_id`` are
        provided, the agent-scoped mandate is preferred.
        """
        if not self._use_postgres:
            return None
        if not agent_id and not wallet_id:
            return None

        pool = await self._get_pool()
        if pool is None:
            return None

        conditions: list[str] = []
        params: list[Any] = []
        if agent_id:
            params.append(agent_id)
            conditions.append(f"agent_id = ${len(params)}")
        if wallet_id:
            params.append(wallet_id)
            conditions.append(f"wallet_id = ${len(params)}")

        where = " OR ".join(conditions)
        # Prefer agent-scoped mandates, then most recently created.
        query = (
            "SELECT * FROM spending_mandates "
            f"WHERE status = 'active' AND ({where}) "
            "ORDER BY (agent_id IS NOT NULL) DESC, created_at DESC "
            "LIMIT 1"
        )

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)
        except Exception:
            # Fail closed: if we cannot confirm the mandate state we must not
            # silently grant authority.  Re-raise so the orchestrator rejects.
            logger.exception(
                "Spending mandate lookup failed (agent=%s wallet=%s)",
                agent_id,
                wallet_id,
            )
            raise

        if row is None:
            return None

        return self._row_to_mandate(row)

    @staticmethod
    def _row_to_mandate(row: Any) -> SpendingMandate:
        """Hydrate a DB row into a :class:`SpendingMandate` domain object."""
        data = dict(row)

        approval_mode_raw = (data.get("approval_mode") or "auto").lower()
        try:
            approval_mode = ApprovalMode(approval_mode_raw)
        except ValueError:
            approval_mode = ApprovalMode.AUTO

        status_raw = (data.get("status") or "active").lower()
        try:
            status = MandateStatus(status_raw)
        except ValueError:
            status = MandateStatus.ACTIVE

        return SpendingMandate(
            principal_id=data.get("principal_id") or "",
            issuer_id=data.get("issuer_id") or "",
            org_id=data.get("org_id") or "",
            agent_id=data.get("agent_id"),
            wallet_id=data.get("wallet_id"),
            id=data.get("id") or "",
            merchant_scope=data.get("merchant_scope") or {},
            purpose_scope=data.get("purpose_scope"),
            amount_per_tx=_to_decimal(data.get("amount_per_tx")),
            amount_daily=_to_decimal(data.get("amount_daily")),
            amount_weekly=_to_decimal(data.get("amount_weekly")),
            amount_monthly=_to_decimal(data.get("amount_monthly")),
            amount_total=_to_decimal(data.get("amount_total")),
            currency=data.get("currency") or "USDC",
            spent_total=_to_decimal(data.get("spent_total")) or Decimal("0"),
            allowed_rails=list(data.get("allowed_rails") or ["card", "usdc", "bank"]),
            allowed_chains=list(data["allowed_chains"]) if data.get("allowed_chains") else None,
            allowed_tokens=list(data["allowed_tokens"]) if data.get("allowed_tokens") else None,
            valid_from=data.get("valid_from") or datetime.now(UTC),
            expires_at=data.get("expires_at"),
            approval_threshold=_to_decimal(data.get("approval_threshold")),
            approval_mode=approval_mode,
            status=status,
            revoked_at=data.get("revoked_at"),
            revoked_by=data.get("revoked_by"),
            revocation_reason=data.get("revocation_reason"),
            version=data.get("version") or 1,
            metadata=data.get("metadata") or {},
            created_at=data.get("created_at") or datetime.now(UTC),
            updated_at=data.get("updated_at") or datetime.now(UTC),
        )
