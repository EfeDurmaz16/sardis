"""Data retention engine — auto-purge expired data, tenant export/deletion.

Implements GDPR-aligned data governance:
- Purge or anonymize data past retention windows
- Tenant data export (right to portability)
- Tenant data deletion (right to erasure)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetentionResult:
    """Result of a retention enforcement run."""
    table_name: str
    rows_purged: int = 0
    rows_anonymized: int = 0
    retention_days: int = 0
    duration_ms: int = 0
    error: str | None = None


@dataclass
class ClassifiedColumn:
    """A column with its data classification."""
    table_name: str
    column_name: str
    classification: str  # public, internal, confidential, restricted
    pii_type: str | None
    retention_days: int
    anonymize_on_expiry: bool


_ALLOWED_RETENTION_TABLES = frozenset({
    "agents",
    "wallets",
    "ledger_entries",
    "transactions",
    "holds",
    "webhook_deliveries",
    "webhook_subscriptions",
    "policy_decisions",
    "execution_intents",
    "execution_side_effects",
    "idempotency_records",
    "access_audit_log",
    "compliance_checks",
    "invoices",
    "checkouts",
})

_ALLOWED_TIMESTAMP_COLUMNS = frozenset({
    "created_at",
    "executed_at",
    "timestamp",
    "updated_at",
})


def _validate_identifier(name: str, allowed: frozenset[str], kind: str) -> str:
    """Validate that a SQL identifier is in the allowlist."""
    if name not in allowed:
        raise ValueError(f"{kind} '{name}' is not in the allowed list")
    return name


class DataRetentionEngine:
    """Enforce data retention policies across all classified tables."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    async def get_classifications(self) -> list[ClassifiedColumn]:
        """Load all data classification entries."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT table_name, column_name, classification, pii_type, "
                "retention_days, anonymize_on_expiry FROM data_classification"
            )
            return [
                ClassifiedColumn(
                    table_name=r["table_name"],
                    column_name=r["column_name"],
                    classification=r["classification"],
                    pii_type=r["pii_type"],
                    retention_days=r["retention_days"],
                    anonymize_on_expiry=r["anonymize_on_expiry"],
                )
                for r in rows
            ]

    async def enforce_retention(self) -> list[RetentionResult]:
        """Run retention enforcement across all classified tables.

        Groups columns by table, then either anonymizes PII columns
        or deletes rows past their retention window.
        """
        classifications = await self.get_classifications()
        results: list[RetentionResult] = []

        # Group by table
        tables: dict[str, list[ClassifiedColumn]] = {}
        for c in classifications:
            tables.setdefault(c.table_name, []).append(c)

        for table_name, columns in tables.items():
            result = await self._enforce_table(table_name, columns)
            results.append(result)

        return results

    async def _enforce_table(
        self, table_name: str, columns: list[ClassifiedColumn]
    ) -> RetentionResult:
        """Enforce retention for a single table."""
        import re
        import time

        start = time.monotonic()
        result = RetentionResult(table_name=table_name)

        try:
            # Validate table name against allowlist (I1 fix)
            _validate_identifier(table_name, _ALLOWED_RETENTION_TABLES, "Table")

            # Find the minimum retention window for this table
            min_retention = min(c.retention_days for c in columns)
            result.retention_days = min_retention

            # Validate column names: must be simple identifiers
            _ident_re = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
            for c in columns:
                if not _ident_re.match(c.column_name):
                    raise ValueError(f"Invalid column name: {c.column_name}")

            # Check which columns should be anonymized vs deleted
            anonymize_cols = [c for c in columns if c.anonymize_on_expiry]
            delete_cols = [c for c in columns if not c.anonymize_on_expiry]

            async with self._pool.acquire() as conn:
                # Determine the timestamp column (created_at or executed_at)
                ts_col = await self._find_timestamp_column(conn, table_name)
                if ts_col is None:
                    result.error = f"No timestamp column found in {table_name}"
                    return result

                if anonymize_cols:
                    # Anonymize PII columns for expired rows
                    set_clauses = ", ".join(
                        f"{c.column_name} = '***REDACTED***'"
                        for c in anonymize_cols
                    )
                    query = (
                        f"UPDATE {table_name} SET {set_clauses} "  # noqa: S608
                        f"WHERE {ts_col} < NOW() - INTERVAL '{min_retention} days' "
                        f"AND {anonymize_cols[0].column_name} != '***REDACTED***'"
                    )
                    tag = await conn.execute(query)
                    result.rows_anonymized = int(tag.split()[-1]) if tag else 0

                if delete_cols and not anonymize_cols:
                    # Delete rows past retention (only if no anonymization needed)
                    query = (
                        f"DELETE FROM {table_name} "  # noqa: S608
                        f"WHERE {ts_col} < NOW() - INTERVAL '{min_retention} days'"
                    )
                    tag = await conn.execute(query)
                    result.rows_purged = int(tag.split()[-1]) if tag else 0

                # Log the retention run
                duration_ms = int((time.monotonic() - start) * 1000)
                result.duration_ms = duration_ms
                await conn.execute(
                    "INSERT INTO data_retention_log "
                    "(table_name, rows_purged, rows_anonymized, retention_days, duration_ms) "
                    "VALUES ($1, $2, $3, $4, $5)",
                    table_name, result.rows_purged, result.rows_anonymized,
                    min_retention, duration_ms,
                )

        except Exception as e:
            result.error = str(e)
            logger.warning("Retention enforcement failed for %s: %s", table_name, e)

        return result

    async def _find_timestamp_column(self, conn: Any, table_name: str) -> str | None:
        """Find the timestamp column for a table (validated against allowlist)."""
        for candidate in _ALLOWED_TIMESTAMP_COLUMNS:
            exists = await conn.fetchval(
                "SELECT EXISTS("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = $1 AND column_name = $2"
                ")",
                table_name, candidate,
            )
            if exists:
                return candidate
        return None

    async def export_tenant_data(
        self, org_id: str, requested_by: str, format: str = "json"
    ) -> dict[str, Any]:
        """Export all data for a tenant (GDPR data portability).

        Returns a dict of table_name -> list of row dicts.
        """
        async with self._pool.acquire() as conn:
            # Record the export request
            export_id = await conn.fetchval(
                "INSERT INTO tenant_data_exports (org_id, requested_by, status, export_format) "
                "VALUES ($1, $2, 'processing', $3) RETURNING id",
                org_id, requested_by, format,
            )

            try:
                export_data: dict[str, list[dict]] = {}

                # Tables that have org-scoped data
                org_tables = [
                    ("agents", "owner_id"),
                    ("wallets", "organization_id"),
                    ("execution_intents", "org_id"),
                    ("access_audit_log", "user_id"),
                ]

                for table_name, org_column in org_tables:
                    table_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = $1)",
                        table_name,
                    )
                    if not table_exists:
                        continue

                    rows = await conn.fetch(
                        f"SELECT * FROM {table_name} WHERE {org_column} = $1",  # noqa: S608
                        org_id,
                    )
                    export_data[table_name] = [dict(r) for r in rows]

                await conn.execute(
                    "UPDATE tenant_data_exports SET status = 'completed', "
                    "completed_at = NOW() WHERE id = $1",
                    export_id,
                )

                logger.info(
                    "Tenant data export completed: org=%s tables=%d",
                    org_id, len(export_data),
                )
                return {"export_id": export_id, "data": export_data}

            except Exception:
                await conn.execute(
                    "UPDATE tenant_data_exports SET status = 'failed' WHERE id = $1",
                    export_id,
                )
                raise

    async def delete_tenant_data(
        self, org_id: str, requested_by: str
    ) -> dict[str, Any]:
        """Delete all data for a tenant (GDPR right to erasure).

        WARNING: This is irreversible. Audit log entries are anonymized, not deleted.
        """
        async with self._pool.acquire() as conn:
            deletion_id = await conn.fetchval(
                "INSERT INTO tenant_data_deletions (org_id, requested_by, status) "
                "VALUES ($1, $2, 'processing') RETURNING id",
                org_id, requested_by,
            )

            try:
                tables_processed = []
                total_deleted = 0

                # Delete in dependency order (children first)
                delete_tables = [
                    ("execution_intents", "org_id"),
                    ("wallets", "organization_id"),
                    ("agents", "owner_id"),
                ]

                for table_name, org_column in delete_tables:
                    table_exists = await conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                        "WHERE table_name = $1)",
                        table_name,
                    )
                    if not table_exists:
                        continue

                    tag = await conn.execute(
                        f"DELETE FROM {table_name} WHERE {org_column} = $1",  # noqa: S608
                        org_id,
                    )
                    count = int(tag.split()[-1]) if tag else 0
                    total_deleted += count
                    tables_processed.append(table_name)

                # Anonymize audit logs (don't delete — compliance requires retention)
                await conn.execute(
                    "UPDATE access_audit_log SET ip_address = '***REDACTED***', "
                    "user_agent = '***REDACTED***' WHERE user_id = $1",
                    org_id,
                )

                await conn.execute(
                    "UPDATE tenant_data_deletions SET status = 'completed', "
                    "tables_processed = $1, rows_deleted = $2, completed_at = NOW() "
                    "WHERE id = $3",
                    tables_processed, total_deleted, deletion_id,
                )

                logger.info(
                    "Tenant data deletion completed: org=%s tables=%s rows=%d",
                    org_id, tables_processed, total_deleted,
                )
                return {
                    "deletion_id": deletion_id,
                    "tables_processed": tables_processed,
                    "rows_deleted": total_deleted,
                }

            except Exception:
                await conn.execute(
                    "UPDATE tenant_data_deletions SET status = 'failed' WHERE id = $1",
                    deletion_id,
                )
                raise
