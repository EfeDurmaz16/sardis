"""Lightspark Grid transfers — quote→execute→status lifecycle."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from .client import GridClient
from .exceptions import GridQuoteExpiredError
from .models import GridPaymentRail, GridQuote, GridTransfer, GridTransferStatus

logger = logging.getLogger(__name__)


class GridTransferService:
    """
    Cross-currency transfers via Lightspark Grid.

    Implements the quote→execute→status flow:
    1. get_quote() — get pricing with FX rate
    2. execute_transfer() — execute with quote_id
    3. get_transfer_status() — poll for completion
    """

    def __init__(self, client: GridClient):
        self._client = client

    async def get_quote(
        self,
        source_currency: str,
        target_currency: str,
        amount_cents: int,
        rail: GridPaymentRail | None = None,
    ) -> GridQuote:
        """
        Get a transfer quote with FX rate.

        Args:
            source_currency: Source currency (USD, EUR, etc.)
            target_currency: Target currency
            amount_cents: Amount in source currency cents
            rail: Preferred payment rail

        Returns:
            GridQuote with exchange rate, fees, and expiration
        """
        body: dict[str, Any] = {
            "sourceCurrency": source_currency.upper(),
            "targetCurrency": target_currency.upper(),
            "sourceAmount": amount_cents,
        }
        if rail:
            body["rail"] = rail.value

        result = await self._client.request("POST", "/quotes", body)

        return GridQuote(
            quote_id=result.get("quoteId", ""),
            source_currency=source_currency.upper(),
            source_amount_cents=amount_cents,
            target_currency=target_currency.upper(),
            target_amount_cents=int(result.get("targetAmount", 0)),
            exchange_rate=Decimal(result.get("exchangeRate", "1.0")),
            fee_cents=int(result.get("fee", 0)),
            rail=rail,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    async def execute_transfer(
        self,
        quote: GridQuote,
        destination: str,
        reference: str | None = None,
    ) -> GridTransfer:
        """
        Execute a transfer using a quote.

        Args:
            quote: Valid (non-expired) GridQuote
            destination: Destination (bank account ID, UMA address, etc.)
            reference: Optional payment reference

        Returns:
            GridTransfer with status tracking

        Raises:
            GridQuoteExpiredError: If quote has expired
        """
        if quote.is_expired:
            raise GridQuoteExpiredError(f"Quote {quote.quote_id} has expired")

        body: dict[str, Any] = {
            "quoteId": quote.quote_id,
            "destination": destination,
        }
        if reference:
            body["reference"] = reference

        result = await self._client.request("POST", "/transfers", body)

        return GridTransfer(
            transfer_id=result.get("transferId", ""),
            quote_id=quote.quote_id,
            source_currency=quote.source_currency,
            source_amount_cents=quote.source_amount_cents,
            target_currency=quote.target_currency,
            target_amount_cents=quote.target_amount_cents,
            rail=quote.rail or GridPaymentRail.ACH,
            status=GridTransferStatus.PROCESSING,
            destination=destination,
            reference=reference,
            created_at=datetime.now(UTC),
        )

    async def get_transfer_status(self, transfer_id: str) -> GridTransfer:
        """Get current status of a transfer."""
        result = await self._client.request("GET", f"/transfers/{transfer_id}")

        status_map = {
            "quoted": GridTransferStatus.QUOTED,
            "pending": GridTransferStatus.PENDING,
            "processing": GridTransferStatus.PROCESSING,
            "completed": GridTransferStatus.COMPLETED,
            "failed": GridTransferStatus.FAILED,
            "cancelled": GridTransferStatus.CANCELLED,
            "refunded": GridTransferStatus.REFUNDED,
        }

        rail_map = {
            "ach": GridPaymentRail.ACH,
            "ach_same_day": GridPaymentRail.ACH_SAME_DAY,
            "rtp": GridPaymentRail.RTP,
            "fednow": GridPaymentRail.FEDNOW,
            "wire": GridPaymentRail.WIRE,
        }

        return GridTransfer(
            transfer_id=result.get("transferId", transfer_id),
            quote_id=result.get("quoteId"),
            source_currency=result.get("sourceCurrency", "USD"),
            source_amount_cents=int(result.get("sourceAmount", 0)),
            target_currency=result.get("targetCurrency", "USD"),
            target_amount_cents=int(result.get("targetAmount", 0)),
            rail=rail_map.get(result.get("rail", "ach"), GridPaymentRail.ACH),
            status=status_map.get(result.get("status", "pending"), GridTransferStatus.PENDING),
            destination=result.get("destination", ""),
            reference=result.get("reference"),
            failure_reason=result.get("failureReason"),
        )
