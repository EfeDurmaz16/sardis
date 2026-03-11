"""Striga EURC → EUR swap — implements OfframpProviderBase for EUR off-ramp."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sardis_cards.offramp import (
    OfframpProvider,
    OfframpProviderBase,
    OfframpQuote,
    OfframpStatus,
    OfframpTransaction,
)

from .client import StrigaClient

logger = logging.getLogger(__name__)


class StrigaSwapProvider(OfframpProviderBase):
    """
    Striga EURC→EUR swap provider.

    Implements OfframpProviderBase ABC with output_currency="EUR".
    Uses Striga's crypto-to-fiat wallet swap API.
    """

    def __init__(self, client: StrigaClient, default_user_id: str = ""):
        self._client = client
        self._default_user_id = default_user_id

    async def get_quote(
        self,
        input_token: str,
        input_amount_minor: int,
        input_chain: str,
        output_currency: str = "EUR",
    ) -> OfframpQuote:
        """Get EURC→EUR swap quote from Striga."""
        result = await self._client.request(
            "POST",
            "/wallets/swap/quote",
            {
                "userId": self._default_user_id,
                "sourceCurrency": input_token.upper(),
                "targetCurrency": output_currency.upper(),
                "amount": str(input_amount_minor),
            },
        )

        # Striga swap fees (~0.3% for stablecoin-to-fiat)
        fee_cents = int(result.get("fee", 0))
        output_amount = int(result.get("targetAmount", input_amount_minor // 10_000 - fee_cents))

        return OfframpQuote(
            quote_id=result.get("quoteId", f"striga_quote_{input_amount_minor}"),
            provider=OfframpProvider.MOCK,  # Will add STRIGA to enum
            input_token=input_token,
            input_amount_minor=input_amount_minor,
            input_chain=input_chain,
            output_currency=output_currency,
            output_amount_cents=output_amount,
            exchange_rate=Decimal(result.get("exchangeRate", "1.0")),
            fee_cents=fee_cents,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    async def execute_offramp(
        self,
        quote: OfframpQuote,
        source_address: str,
        destination_account: str,
    ) -> OfframpTransaction:
        """Execute EURC→EUR swap via Striga."""
        result = await self._client.request(
            "POST",
            "/wallets/swap/execute",
            {
                "userId": self._default_user_id,
                "quoteId": quote.quote_id,
                "sourceAddress": source_address,
                "destinationAccount": destination_account,
            },
        )

        return OfframpTransaction(
            transaction_id=result.get("transactionId", ""),
            quote_id=quote.quote_id,
            provider=OfframpProvider.MOCK,  # Will add STRIGA to enum
            input_token=quote.input_token,
            input_amount_minor=quote.input_amount_minor,
            input_chain=quote.input_chain,
            output_currency=quote.output_currency,
            output_amount_cents=quote.output_amount_cents,
            destination_account=destination_account,
            status=OfframpStatus.PROCESSING,
            provider_reference=result.get("reference"),
        )

    async def get_transaction_status(
        self,
        transaction_id: str,
    ) -> OfframpTransaction:
        """Get Striga swap transaction status."""
        result = await self._client.request(
            "GET", f"/wallets/swap/{transaction_id}"
        )

        status_map = {
            "pending": OfframpStatus.PENDING,
            "processing": OfframpStatus.PROCESSING,
            "completed": OfframpStatus.COMPLETED,
            "failed": OfframpStatus.FAILED,
        }

        return OfframpTransaction(
            transaction_id=result.get("transactionId", transaction_id),
            quote_id=result.get("quoteId", ""),
            provider=OfframpProvider.MOCK,
            input_token=result.get("sourceCurrency", "EURC"),
            input_amount_minor=int(result.get("sourceAmount", 0)),
            input_chain=result.get("chain", ""),
            output_currency=result.get("targetCurrency", "EUR"),
            output_amount_cents=int(result.get("targetAmount", 0)),
            destination_account=result.get("destinationAccount", ""),
            status=status_map.get(result.get("status", "pending"), OfframpStatus.PENDING),
            provider_reference=result.get("reference"),
        )

    async def get_deposit_address(
        self,
        chain: str,
        token: str,
    ) -> str:
        """Get Striga deposit address for EURC."""
        result = await self._client.request(
            "POST",
            "/wallets/deposit-address",
            {
                "userId": self._default_user_id,
                "chain": chain,
                "currency": token.upper(),
            },
        )
        return result.get("address", "")
