"""PostgreSQL-backed auto-conversion service.

Replaces the in-memory ``_conversions`` dict in
``AutoConversionService`` with the ``card_conversions`` table.

Pattern follows ``policy_store_postgres.py``.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, List, Optional

from .auto_conversion import (
    ConversionDirection,
    ConversionRecord,
    ConversionStatus,
    OfframpProvider,
    OnrampProvider,
    UnifiedBalance,
)

logger = logging.getLogger(__name__)


class PostgresAutoConversionService:
    """
    DB-backed conversion service.

    Conversion records are persisted in ``card_conversions``.
    Balance operations delegate to the balance service (memory or DB).
    """

    def __init__(
        self,
        balance_service,  # UnifiedBalanceService or PostgresUnifiedBalanceService
        dsn: str,
        offramp_provider: Optional[OfframpProvider] = None,
        onramp_provider: Optional[OnrampProvider] = None,
        on_conversion_complete: Optional[Callable[[ConversionRecord], None]] = None,
    ) -> None:
        self._balance_service = balance_service
        self._dsn = dsn
        self._offramp_provider = offramp_provider
        self._onramp_provider = onramp_provider
        self._on_conversion_complete = on_conversion_complete
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg

            dsn = self._dsn
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        return self._pool

    async def _persist_record(self, record: ConversionRecord) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO card_conversions (id, wallet_id, direction, amount_cents, status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE
                SET status = $5
                """,
                record.conversion_id,
                record.wallet_id,
                record.direction.value,
                record.output_amount_cents,
                record.status.value,
                record.created_at,
            )

    async def convert_for_card_payment(
        self,
        wallet_id: str,
        amount_cents: int,
        card_transaction_id: Optional[str] = None,
        chain: str = "base",
    ) -> ConversionRecord:
        """Convert USDC to USD for a card payment (DB-persisted)."""
        conversion_id = f"conv_{uuid.uuid4().hex[:16]}"
        usdc_amount_minor = amount_cents * 10_000

        record = ConversionRecord(
            conversion_id=conversion_id,
            wallet_id=wallet_id,
            direction=ConversionDirection.USDC_TO_USD,
            input_amount_minor=usdc_amount_minor,
            output_amount_cents=amount_cents,
            exchange_rate=Decimal("1.0"),
            fee_cents=0,
            status=ConversionStatus.PENDING,
            trigger="card_payment",
            card_transaction_id=card_transaction_id,
        )

        await self._persist_record(record)

        logger.info(
            "Initiating auto-conversion (DB): wallet=%s, amount=$%.2f",
            wallet_id,
            amount_cents / 100,
        )

        try:
            balance = await self._balance_service.get_unified_balance(wallet_id, chain)

            if balance.usdc_balance_minor < usdc_amount_minor:
                record.status = ConversionStatus.FAILED
                record.error_message = (
                    f"Insufficient USDC: have {balance.usdc_balance_minor}, "
                    f"need {usdc_amount_minor}"
                )
                await self._persist_record(record)
                return record

            if self._offramp_provider:
                record.status = ConversionStatus.PROCESSING
                provider_tx_id = await self._offramp_provider.convert_to_fiat(
                    wallet_id=wallet_id,
                    usdc_amount_minor=usdc_amount_minor,
                    destination="card_funding",
                    chain=chain,
                )
                record.provider_tx_id = provider_tx_id
            else:
                record.provider_tx_id = f"mock_{conversion_id}"

            record.status = ConversionStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)

            # Use async add if available (DB-backed service), sync otherwise
            if hasattr(self._balance_service, "add_usd_balance"):
                result = self._balance_service.add_usd_balance(wallet_id, amount_cents)
                if hasattr(result, "__await__"):
                    await result

            await self._persist_record(record)

            if self._on_conversion_complete:
                self._on_conversion_complete(record)

        except Exception as e:
            record.status = ConversionStatus.FAILED
            record.error_message = str(e)
            await self._persist_record(record)
            logger.error("Auto-conversion failed: %s", e)

        return record

    async def convert_for_crypto_payment(
        self,
        wallet_id: str,
        usdc_amount_minor: int,
        chain: str = "base",
    ) -> ConversionRecord:
        """Convert USD to USDC for a crypto payment (DB-persisted)."""
        conversion_id = f"conv_{uuid.uuid4().hex[:16]}"
        usd_amount_cents = usdc_amount_minor // 10_000

        record = ConversionRecord(
            conversion_id=conversion_id,
            wallet_id=wallet_id,
            direction=ConversionDirection.USD_TO_USDC,
            input_amount_minor=usd_amount_cents * 10_000,
            output_amount_cents=usd_amount_cents,
            exchange_rate=Decimal("1.0"),
            fee_cents=0,
            status=ConversionStatus.PENDING,
            trigger="crypto_payment",
        )

        await self._persist_record(record)

        try:
            balance = await self._balance_service.get_unified_balance(wallet_id, chain)

            if balance.usd_balance_cents < usd_amount_cents:
                record.status = ConversionStatus.FAILED
                record.error_message = (
                    f"Insufficient USD: have {balance.usd_balance_cents}, "
                    f"need {usd_amount_cents}"
                )
                await self._persist_record(record)
                return record

            deduct_result = self._balance_service.deduct_usd_balance(
                wallet_id, usd_amount_cents
            )
            if hasattr(deduct_result, "__await__"):
                success = await deduct_result
            else:
                success = deduct_result
            if not success:
                record.status = ConversionStatus.FAILED
                record.error_message = "Failed to deduct USD balance"
                await self._persist_record(record)
                return record

            if self._onramp_provider:
                record.status = ConversionStatus.PROCESSING
                wallet_address = await self._balance_service._wallet_provider.get_wallet_address(wallet_id)
                provider_tx_id = await self._onramp_provider.convert_to_crypto(
                    wallet_id=wallet_id,
                    usd_amount_cents=usd_amount_cents,
                    destination_address=wallet_address,
                    chain=chain,
                )
                record.provider_tx_id = provider_tx_id
            else:
                record.provider_tx_id = f"mock_{conversion_id}"

            record.status = ConversionStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            await self._persist_record(record)

            if self._on_conversion_complete:
                self._on_conversion_complete(record)

        except Exception as e:
            record.status = ConversionStatus.FAILED
            record.error_message = str(e)
            await self._persist_record(record)
            logger.error("Auto-conversion failed: %s", e)

        return record

    async def get_conversion(self, conversion_id: str) -> Optional[ConversionRecord]:
        """Get conversion record by ID from DB."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM card_conversions WHERE id = $1",
                conversion_id,
            )
            if not row:
                return None
            return ConversionRecord(
                conversion_id=row["id"],
                wallet_id=row["wallet_id"],
                direction=ConversionDirection(row["direction"]),
                input_amount_minor=int(row["amount_cents"]) * 10_000,
                output_amount_cents=int(row["amount_cents"]),
                status=ConversionStatus(row["status"]),
                created_at=row["created_at"],
            )

    async def list_conversions(
        self,
        wallet_id: Optional[str] = None,
        status: Optional[ConversionStatus] = None,
        limit: int = 50,
    ) -> List[ConversionRecord]:
        """List conversion records from DB."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = "SELECT * FROM card_conversions WHERE 1=1"
            params: list = []
            idx = 1

            if wallet_id:
                query += f" AND wallet_id = ${idx}"
                params.append(wallet_id)
                idx += 1

            if status:
                query += f" AND status = ${idx}"
                params.append(status.value)
                idx += 1

            query += f" ORDER BY created_at DESC LIMIT ${idx}"
            params.append(limit)

            rows = await conn.fetch(query, *params)
            return [
                ConversionRecord(
                    conversion_id=r["id"],
                    wallet_id=r["wallet_id"],
                    direction=ConversionDirection(r["direction"]),
                    input_amount_minor=int(r["amount_cents"]) * 10_000,
                    output_amount_cents=int(r["amount_cents"]),
                    status=ConversionStatus(r["status"]),
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
