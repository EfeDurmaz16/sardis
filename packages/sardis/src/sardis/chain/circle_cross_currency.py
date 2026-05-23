"""Circle Cross-Currency API integration (USDC ↔ EURC, Fiat ↔ USDC).

Provides FX swap functionality via Circle Mint's Cross-Currency API:
- USDC ↔ EURC stablecoin swap (instant settlement)
- Fiat → USDC onramp via local payment rails (MXN, BRL, etc.)
- Quote with locked rate (3-second expiry)
- Trade execution with settlement tracking

Requirements:
- Circle Mint API key with Cross-Currency access
- For fiat swaps: linked fiat account on Circle Mint

API Reference: https://developers.circle.com/circle-mint/cross-currency
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────────────


CIRCLE_MINT_API_BASE = "https://api.circle.com"
CIRCLE_MINT_SANDBOX_BASE = "https://api-sandbox.circle.com"

# Supported currency pairs
SUPPORTED_CRYPTO_PAIRS = [
    ("USDC", "EURC"),
    ("EURC", "USDC"),
]

SUPPORTED_FIAT_CURRENCIES = [
    "MXN", "BRL", "COP", "HKD", "INR", "SGD", "CNY",
]


class TradeStatus(str, Enum):
    """Circle trade execution status."""
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QuoteType(str, Enum):
    """Quote type — tradable means locked rate."""
    TRADABLE = "tradable"
    INDICATIVE = "indicative"


class SettlementStatus(str, Enum):
    """Settlement batch status."""
    PENDING = "pending"
    SETTLED = "settled"
    FAILED = "failed"


# ── Data Models ────────────────────────────────────────────────────────


@dataclass
class CrossCurrencyQuote:
    """Quote for a cross-currency swap."""
    quote_id: str
    from_currency: str
    from_amount: Decimal
    to_currency: str
    to_amount: Decimal
    rate: Decimal
    quote_type: QuoteType = QuoteType.TRADABLE
    expires_at: str | None = None

    @property
    def is_crypto_to_crypto(self) -> bool:
        return self.from_currency in ("USDC", "EURC") and self.to_currency in ("USDC", "EURC")


@dataclass
class CrossCurrencyTrade:
    """Executed trade from a quote."""
    trade_id: str
    quote_id: str
    from_currency: str
    from_amount: Decimal
    to_currency: str
    to_amount: Decimal
    status: TradeStatus = TradeStatus.PENDING
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class SettlementDetail:
    """A single settlement detail (payable or receivable)."""
    detail_id: str
    detail_type: str  # "payable" or "receivable"
    status: str
    currency: str
    amount: Decimal
    reference: str | None = None
    expected_payment_due_at: str | None = None


@dataclass
class SettlementBatch:
    """Settlement batch from Circle."""
    batch_id: str
    entity_id: str
    status: SettlementStatus = SettlementStatus.PENDING
    details: list[SettlementDetail] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class FiatAccount:
    """Linked fiat account on Circle Mint."""
    account_id: str
    account_type: str  # "wire", "pix", etc.
    status: str
    description: str
    currency: str | None = None
    bank_name: str | None = None


class CircleCrossCurrencyError(Exception):
    """Error from Circle Cross-Currency API."""
    pass


# ── Client ─────────────────────────────────────────────────────────────


class CircleCrossCurrencyClient:
    """Client for Circle Mint Cross-Currency API.

    Supports:
    - USDC ↔ EURC instant stablecoin swaps
    - Fiat → USDC onramp via local payment rails
    - Settlement batch tracking

    Usage:
        client = CircleCrossCurrencyClient(api_key="...", sandbox=True)
        quote = await client.get_quote("EURC", Decimal("100"), "USDC")
        trade = await client.execute_trade(quote.quote_id)
    """

    def __init__(
        self,
        api_key: str,
        *,
        sandbox: bool = False,
        timeout_seconds: float = 15.0,
    ):
        base_url = CIRCLE_MINT_SANDBOX_BASE if sandbox else CIRCLE_MINT_API_BASE
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    # ── Fiat Accounts ──────────────────────────────────────────────

    async def list_fiat_accounts(self) -> list[FiatAccount]:
        """List linked fiat accounts on Circle Mint.

        Required for fiat → USDC swaps. Each account represents a
        bank account linked via PIX, WIRE, SPEI, etc.
        """
        resp = await self._client.get(
            f"{self._base_url}/v1/businessAccount/banks/wires"
        )
        resp.raise_for_status()
        data = resp.json()

        accounts = []
        for item in data.get("data", []):
            accounts.append(FiatAccount(
                account_id=item.get("id", ""),
                account_type=item.get("type", "wire"),
                status=item.get("status", ""),
                description=item.get("description", ""),
                bank_name=item.get("bankAddress", {}).get("bankName"),
            ))
        return accounts

    async def register_fiat_account_for_fx(
        self,
        fiat_account_id: str,
        currency: str,
    ) -> dict[str, Any]:
        """Register a fiat account for cross-currency trading.

        Must be called once per currency before requesting fiat quotes.
        """
        resp = await self._client.put(
            f"{self._base_url}/v1/exchange/fxConfigs/accounts",
            json={
                "fiatAccountId": fiat_account_id,
                "currency": currency,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    # ── Quotes ─────────────────────────────────────────────────────

    async def get_quote(
        self,
        from_currency: str,
        from_amount: Decimal | None = None,
        to_currency: str = "USDC",
        to_amount: Decimal | None = None,
        quote_type: QuoteType = QuoteType.TRADABLE,
    ) -> CrossCurrencyQuote:
        """Get a cross-currency quote with locked rate.

        Must specify amount on either from or to side, not both.
        Tradable quotes are valid for 3 seconds.

        Args:
            from_currency: Source currency (USDC, EURC, MXN, BRL, etc.)
            from_amount: Amount to sell (mutually exclusive with to_amount)
            to_currency: Destination currency (USDC, EURC)
            to_amount: Amount to buy (mutually exclusive with from_amount)
            quote_type: "tradable" for locked rate, "indicative" for estimate

        Returns:
            CrossCurrencyQuote with locked rate and amounts
        """
        if not from_amount and not to_amount:
            raise CircleCrossCurrencyError("Must specify from_amount or to_amount")
        if from_amount and to_amount:
            raise CircleCrossCurrencyError("Cannot specify both from_amount and to_amount")

        idempotency_key = str(uuid.uuid4())

        payload: dict[str, Any] = {
            "type": quote_type.value,
            "idempotencyKey": idempotency_key,
            "from": {
                "currency": from_currency,
                "amount": float(from_amount) if from_amount else None,
            },
            "to": {
                "currency": to_currency,
                "amount": float(to_amount) if to_amount else None,
            },
        }

        try:
            resp = await self._client.post(
                f"{self._base_url}/v1/exchange/quotes",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        except httpx.HTTPStatusError as e:
            raise CircleCrossCurrencyError(
                f"Quote request failed: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise CircleCrossCurrencyError(f"Quote request failed: {e}") from e

        return CrossCurrencyQuote(
            quote_id=data.get("id", ""),
            from_currency=data.get("from", {}).get("currency", from_currency),
            from_amount=Decimal(str(data.get("from", {}).get("amount", 0))),
            to_currency=data.get("to", {}).get("currency", to_currency),
            to_amount=Decimal(str(data.get("to", {}).get("amount", 0))),
            rate=Decimal(str(data.get("rate", 0))),
            quote_type=quote_type,
            expires_at=data.get("expiry"),
        )

    # ── Trades ─────────────────────────────────────────────────────

    async def execute_trade(self, quote_id: str) -> CrossCurrencyTrade:
        """Execute a trade from a previously obtained quote.

        Must be called within 3 seconds of quote creation.
        For crypto-to-crypto (USDC↔EURC), settlement is instant.
        For fiat swaps, settlement follows the configured fiat account rails.

        Args:
            quote_id: Quote ID from get_quote()

        Returns:
            CrossCurrencyTrade with execution details
        """
        idempotency_key = str(uuid.uuid4())

        try:
            resp = await self._client.post(
                f"{self._base_url}/v1/exchange/trades",
                json={
                    "idempotencyKey": idempotency_key,
                    "quoteId": quote_id,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        except httpx.HTTPStatusError as e:
            raise CircleCrossCurrencyError(
                f"Trade execution failed: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise CircleCrossCurrencyError(f"Trade execution failed: {e}") from e

        status_str = data.get("status", "pending")
        try:
            trade_status = TradeStatus(status_str)
        except ValueError:
            trade_status = TradeStatus.PENDING

        return CrossCurrencyTrade(
            trade_id=data.get("id", ""),
            quote_id=data.get("quoteId", quote_id),
            from_currency=data.get("from", {}).get("currency", ""),
            from_amount=Decimal(str(data.get("from", {}).get("amount", 0))),
            to_currency=data.get("to", {}).get("currency", ""),
            to_amount=Decimal(str(data.get("to", {}).get("amount", 0))),
            status=trade_status,
            created_at=data.get("createDate"),
            updated_at=data.get("updateDate"),
        )

    # ── Settlements ────────────────────────────────────────────────

    async def get_settlements(self) -> list[SettlementBatch]:
        """Get settlement batches for pending and completed trades.

        For fiat swaps, this shows payment instructions and settlement status.
        For crypto swaps, settlement is typically instant.
        """
        try:
            resp = await self._client.get(
                f"{self._base_url}/v1/exchange/trades/settlements"
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise CircleCrossCurrencyError(f"Settlement query failed: {e}") from e

        batches = []
        for item in data.get("data", []):
            details = []
            for d in item.get("details", []):
                amount_data = d.get("amount", {})
                details.append(SettlementDetail(
                    detail_id=d.get("id", ""),
                    detail_type=d.get("type", ""),
                    status=d.get("status", ""),
                    currency=amount_data.get("currency", ""),
                    amount=Decimal(str(amount_data.get("amount", 0))),
                    reference=d.get("reference"),
                    expected_payment_due_at=d.get("expectedPaymentDueAt"),
                ))

            status_str = item.get("status", "pending")
            try:
                batch_status = SettlementStatus(status_str)
            except ValueError:
                batch_status = SettlementStatus.PENDING

            batches.append(SettlementBatch(
                batch_id=item.get("id", ""),
                entity_id=item.get("entityId", ""),
                status=batch_status,
                details=details,
                created_at=item.get("createDate"),
                updated_at=item.get("updateDate"),
            ))

        return batches

    async def get_settlement_instructions(self, currency: str) -> dict[str, Any]:
        """Get settlement payment instructions for a fiat currency.

        Returns bank details where fiat must be sent for fiat → USDC swaps.
        These are static and can be cached.
        """
        resp = await self._client.get(
            f"{self._base_url}/v1/exchange/trades/settlements/instructions/{currency}"
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


# ── High-Level Service ─────────────────────────────────────────────────


class CrossCurrencyService:
    """High-level service for cross-currency operations.

    Provides simplified interface for common operations:
    - swap_usdc_eurc(): USDC ↔ EURC instant swap
    - swap_fiat_to_usdc(): Fiat → USDC with settlement tracking
    """

    def __init__(self, client: CircleCrossCurrencyClient):
        self._client = client

    async def swap_usdc_to_eurc(
        self,
        amount: Decimal,
    ) -> CrossCurrencyTrade:
        """Swap USDC → EURC. Settlement is instant."""
        quote = await self._client.get_quote(
            from_currency="USDC",
            from_amount=amount,
            to_currency="EURC",
        )
        return await self._client.execute_trade(quote.quote_id)

    async def swap_eurc_to_usdc(
        self,
        amount: Decimal,
    ) -> CrossCurrencyTrade:
        """Swap EURC → USDC. Settlement is instant."""
        quote = await self._client.get_quote(
            from_currency="EURC",
            from_amount=amount,
            to_currency="USDC",
        )
        return await self._client.execute_trade(quote.quote_id)

    async def get_indicative_rate(
        self,
        from_currency: str,
        to_currency: str,
        amount: Decimal,
    ) -> CrossCurrencyQuote:
        """Get an indicative (non-binding) exchange rate."""
        return await self._client.get_quote(
            from_currency=from_currency,
            from_amount=amount,
            to_currency=to_currency,
            quote_type=QuoteType.INDICATIVE,
        )

    async def close(self) -> None:
        await self._client.close()
