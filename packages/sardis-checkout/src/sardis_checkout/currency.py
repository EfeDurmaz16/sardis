"""
Multi-currency support for checkout sessions.

This module provides currency conversion, rate management, and
multi-currency checkout capabilities.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sardis_checkout.models import (
    CurrencyConversion,
    SupportedCurrency,
)

logger = logging.getLogger(__name__)


class CurrencyError(Exception):
    """Base exception for currency errors."""
    pass


class UnsupportedCurrency(CurrencyError):
    """Raised when a currency is not supported."""
    pass


class ConversionError(CurrencyError):
    """Raised when currency conversion fails."""
    pass


class RateNotAvailable(CurrencyError):
    """Raised when exchange rate is not available."""
    pass


# Default supported currencies
DEFAULT_CURRENCIES: Dict[str, SupportedCurrency] = {
    "USD": SupportedCurrency(
        code="USD", name="US Dollar", symbol="$", decimal_places=2
    ),
    "EUR": SupportedCurrency(
        code="EUR", name="Euro", symbol="\u20ac", decimal_places=2
    ),
    "GBP": SupportedCurrency(
        code="GBP", name="British Pound", symbol="\u00a3", decimal_places=2
    ),
    "JPY": SupportedCurrency(
        code="JPY", name="Japanese Yen", symbol="\u00a5", decimal_places=0
    ),
    "CAD": SupportedCurrency(
        code="CAD", name="Canadian Dollar", symbol="C$", decimal_places=2
    ),
    "AUD": SupportedCurrency(
        code="AUD", name="Australian Dollar", symbol="A$", decimal_places=2
    ),
    "CHF": SupportedCurrency(
        code="CHF", name="Swiss Franc", symbol="CHF", decimal_places=2
    ),
    "CNY": SupportedCurrency(
        code="CNY", name="Chinese Yuan", symbol="\u00a5", decimal_places=2
    ),
    "INR": SupportedCurrency(
        code="INR", name="Indian Rupee", symbol="\u20b9", decimal_places=2
    ),
    "MXN": SupportedCurrency(
        code="MXN", name="Mexican Peso", symbol="$", decimal_places=2
    ),
    "BRL": SupportedCurrency(
        code="BRL", name="Brazilian Real", symbol="R$", decimal_places=2
    ),
    "SGD": SupportedCurrency(
        code="SGD", name="Singapore Dollar", symbol="S$", decimal_places=2
    ),
    "HKD": SupportedCurrency(
        code="HKD", name="Hong Kong Dollar", symbol="HK$", decimal_places=2
    ),
    "KRW": SupportedCurrency(
        code="KRW", name="South Korean Won", symbol="\u20a9", decimal_places=0
    ),
}


@dataclass
class ExchangeRate:
    """Exchange rate between two currencies."""
    from_currency: str
    to_currency: str
    rate: Decimal
    source: str
    timestamp: datetime
    bid: Optional[Decimal] = None  # Best buy rate
    ask: Optional[Decimal] = None  # Best sell rate
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if the rate has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class ExchangeRateProvider(ABC):
    """Abstract interface for exchange rate providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        """Get exchange rate between two currencies."""
        pass

    @abstractmethod
    async def get_rates(
        self,
        base_currency: str,
        target_currencies: List[str],
    ) -> Dict[str, ExchangeRate]:
        """Get exchange rates from base currency to multiple targets."""
        pass


class StaticExchangeRateProvider(ExchangeRateProvider):
    """
    Static exchange rate provider for development and testing.

    Uses fixed rates that don't change.
    """

    # Static rates relative to USD (for demo/testing purposes)
    _RATES_TO_USD = {
        "USD": Decimal("1.0"),
        "EUR": Decimal("0.92"),
        "GBP": Decimal("0.79"),
        "JPY": Decimal("149.50"),
        "CAD": Decimal("1.36"),
        "AUD": Decimal("1.53"),
        "CHF": Decimal("0.88"),
        "CNY": Decimal("7.24"),
        "INR": Decimal("83.12"),
        "MXN": Decimal("17.15"),
        "BRL": Decimal("4.97"),
        "SGD": Decimal("1.34"),
        "HKD": Decimal("7.82"),
        "KRW": Decimal("1320.0"),
    }

    @property
    def name(self) -> str:
        return "static"

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        if from_currency not in self._RATES_TO_USD:
            raise UnsupportedCurrency(f"Currency {from_currency} not supported")
        if to_currency not in self._RATES_TO_USD:
            raise UnsupportedCurrency(f"Currency {to_currency} not supported")

        # Convert through USD
        from_to_usd = self._RATES_TO_USD[from_currency]
        usd_to_target = self._RATES_TO_USD[to_currency]

        # Rate is (1/from_to_usd) * usd_to_target
        rate = usd_to_target / from_to_usd

        return ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            source=self.name,
            timestamp=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

    async def get_rates(
        self,
        base_currency: str,
        target_currencies: List[str],
    ) -> Dict[str, ExchangeRate]:
        rates = {}
        for target in target_currencies:
            if target != base_currency:
                rates[target] = await self.get_rate(base_currency, target)
        return rates


class CachedExchangeRateProvider(ExchangeRateProvider):
    """
    Caching wrapper for exchange rate providers.

    Caches rates to reduce API calls and improve performance.
    """

    def __init__(
        self,
        provider: ExchangeRateProvider,
        cache_ttl_seconds: int = 300,  # 5 minutes default
    ):
        self._provider = provider
        self._cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, ExchangeRate] = {}

    @property
    def name(self) -> str:
        return f"cached_{self._provider.name}"

    def _cache_key(self, from_currency: str, to_currency: str) -> str:
        return f"{from_currency}_{to_currency}"

    async def get_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        key = self._cache_key(from_currency, to_currency)
        cached = self._cache.get(key)

        if cached and not cached.is_expired():
            return cached

        rate = await self._provider.get_rate(from_currency, to_currency)
        rate.expires_at = datetime.utcnow() + timedelta(seconds=self._cache_ttl)
        self._cache[key] = rate

        return rate

    async def get_rates(
        self,
        base_currency: str,
        target_currencies: List[str],
    ) -> Dict[str, ExchangeRate]:
        # Check cache first
        uncached = []
        rates = {}

        for target in target_currencies:
            if target == base_currency:
                continue
            key = self._cache_key(base_currency, target)
            cached = self._cache.get(key)
            if cached and not cached.is_expired():
                rates[target] = cached
            else:
                uncached.append(target)

        # Fetch uncached rates
        if uncached:
            new_rates = await self._provider.get_rates(base_currency, uncached)
            for currency, rate in new_rates.items():
                rate.expires_at = datetime.utcnow() + timedelta(seconds=self._cache_ttl)
                key = self._cache_key(base_currency, currency)
                self._cache[key] = rate
                rates[currency] = rate

        return rates

    def clear_cache(self) -> None:
        """Clear the rate cache."""
        self._cache.clear()


class CurrencyConverter:
    """
    Handles currency conversion with support for multiple rate providers.
    """

    def __init__(
        self,
        rate_provider: Optional[ExchangeRateProvider] = None,
        supported_currencies: Optional[Dict[str, SupportedCurrency]] = None,
        conversion_fee_percentage: Decimal = Decimal("0.0"),  # No fee by default
    ):
        self._rate_provider = rate_provider or StaticExchangeRateProvider()
        self._currencies = supported_currencies or DEFAULT_CURRENCIES
        self._conversion_fee = conversion_fee_percentage

    def is_currency_supported(self, currency_code: str) -> bool:
        """Check if a currency is supported."""
        return currency_code.upper() in self._currencies

    def get_supported_currencies(self) -> List[SupportedCurrency]:
        """Get list of supported currencies."""
        return list(self._currencies.values())

    def get_currency_info(self, currency_code: str) -> Optional[SupportedCurrency]:
        """Get information about a currency."""
        return self._currencies.get(currency_code.upper())

    def _round_amount(
        self,
        amount: Decimal,
        currency_code: str,
    ) -> Decimal:
        """Round amount to the correct decimal places for the currency."""
        currency = self._currencies.get(currency_code.upper())
        decimal_places = currency.decimal_places if currency else 2
        quantize_str = "0." + "0" * decimal_places if decimal_places > 0 else "1"
        return amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        """
        Get the exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            ExchangeRate object

        Raises:
            UnsupportedCurrency: If either currency is not supported
            RateNotAvailable: If rate cannot be fetched
        """
        from_code = from_currency.upper()
        to_code = to_currency.upper()

        if not self.is_currency_supported(from_code):
            raise UnsupportedCurrency(f"Currency {from_code} not supported")
        if not self.is_currency_supported(to_code):
            raise UnsupportedCurrency(f"Currency {to_code} not supported")

        if from_code == to_code:
            return ExchangeRate(
                from_currency=from_code,
                to_currency=to_code,
                rate=Decimal("1"),
                source="identity",
                timestamp=datetime.utcnow(),
            )

        try:
            return await self._rate_provider.get_rate(from_code, to_code)
        except Exception as e:
            raise RateNotAvailable(
                f"Could not get rate for {from_code}/{to_code}: {e}"
            )

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        include_fee: bool = True,
    ) -> CurrencyConversion:
        """
        Convert an amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            include_fee: Whether to include conversion fee

        Returns:
            CurrencyConversion with conversion details
        """
        rate = await self.get_exchange_rate(from_currency, to_currency)

        # Calculate converted amount
        converted = amount * rate.rate

        # Calculate fee
        fee_amount = Decimal("0")
        if include_fee and self._conversion_fee > 0:
            fee_amount = self._round_amount(
                converted * (self._conversion_fee / 100),
                to_currency,
            )
            converted = converted - fee_amount

        # Round to currency precision
        converted = self._round_amount(converted, to_currency)

        return CurrencyConversion(
            conversion_id=str(uuid.uuid4()),
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            from_amount=amount,
            to_amount=converted,
            exchange_rate=rate.rate,
            rate_source=rate.source,
            rate_timestamp=rate.timestamp,
            fee_amount=fee_amount,
            fee_currency=to_currency.upper(),
        )

    async def convert_for_display(
        self,
        amount: Decimal,
        from_currency: str,
        to_currencies: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Convert an amount to multiple currencies for display purposes.

        Returns a dict mapping currency codes to converted amounts and formatting.
        """
        results = {}

        for to_currency in to_currencies:
            to_code = to_currency.upper()
            if not self.is_currency_supported(to_code):
                continue

            currency_info = self._currencies[to_code]

            if to_code == from_currency.upper():
                converted_amount = amount
                rate = Decimal("1")
            else:
                conversion = await self.convert(
                    amount, from_currency, to_code, include_fee=False
                )
                converted_amount = conversion.to_amount
                rate = conversion.exchange_rate

            results[to_code] = {
                "amount": converted_amount,
                "formatted": self.format_amount(converted_amount, to_code),
                "symbol": currency_info.symbol,
                "exchange_rate": rate,
            }

        return results

    def format_amount(
        self,
        amount: Decimal,
        currency_code: str,
    ) -> str:
        """Format an amount with the currency symbol."""
        currency = self._currencies.get(currency_code.upper())
        if not currency:
            return f"{amount} {currency_code}"

        rounded = self._round_amount(amount, currency_code)

        # Format based on decimal places
        if currency.decimal_places == 0:
            formatted = f"{int(rounded):,}"
        else:
            formatted = f"{rounded:,.{currency.decimal_places}f}"

        return f"{currency.symbol}{formatted}"

    def validate_amount(
        self,
        amount: Decimal,
        currency_code: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an amount for a currency.

        Returns (is_valid, error_message).
        """
        currency = self._currencies.get(currency_code.upper())

        if not currency:
            return False, f"Currency {currency_code} not supported"

        if not currency.enabled:
            return False, f"Currency {currency_code} is currently disabled"

        if amount < currency.min_amount:
            return False, f"Amount below minimum ({currency.min_amount} {currency_code})"

        if amount > currency.max_amount:
            return False, f"Amount exceeds maximum ({currency.max_amount} {currency_code})"

        return True, None


class MultiCurrencyCheckout:
    """
    Manages multi-currency checkout sessions.

    Features:
    - Accept payments in multiple currencies
    - Automatic currency conversion
    - Currency preference management
    - Rate locking for checkout sessions
    """

    def __init__(
        self,
        converter: CurrencyConverter,
        default_currency: str = "USD",
        lock_rate_seconds: int = 900,  # 15 minutes
    ):
        self.converter = converter
        self.default_currency = default_currency
        self.lock_rate_seconds = lock_rate_seconds
        self._locked_rates: Dict[str, Tuple[ExchangeRate, datetime]] = {}

    async def get_checkout_currencies(
        self,
        amount: Decimal,
        base_currency: str,
        accepted_currencies: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get available currencies for checkout with converted amounts.

        Args:
            amount: Checkout amount
            base_currency: Original currency
            accepted_currencies: List of accepted currency codes

        Returns:
            Dict mapping currency codes to checkout details
        """
        return await self.converter.convert_for_display(
            amount, base_currency, accepted_currencies
        )

    async def lock_rate(
        self,
        checkout_id: str,
        from_currency: str,
        to_currency: str,
    ) -> ExchangeRate:
        """
        Lock an exchange rate for a checkout session.

        The locked rate will be used for the checkout until it expires.
        """
        rate = await self.converter.get_exchange_rate(from_currency, to_currency)

        lock_key = f"{checkout_id}:{from_currency}:{to_currency}"
        self._locked_rates[lock_key] = (
            rate,
            datetime.utcnow() + timedelta(seconds=self.lock_rate_seconds),
        )

        logger.info(
            f"Locked rate for checkout {checkout_id}: "
            f"{from_currency}/{to_currency} = {rate.rate}"
        )

        return rate

    async def get_locked_rate(
        self,
        checkout_id: str,
        from_currency: str,
        to_currency: str,
    ) -> Optional[ExchangeRate]:
        """
        Get the locked rate for a checkout session.

        Returns None if no rate is locked or the lock has expired.
        """
        lock_key = f"{checkout_id}:{from_currency}:{to_currency}"
        locked = self._locked_rates.get(lock_key)

        if locked is None:
            return None

        rate, expires_at = locked
        if datetime.utcnow() > expires_at:
            del self._locked_rates[lock_key]
            return None

        return rate

    async def convert_payment(
        self,
        checkout_id: str,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> CurrencyConversion:
        """
        Convert a payment amount, using locked rate if available.
        """
        # Try to use locked rate
        locked_rate = await self.get_locked_rate(
            checkout_id, from_currency, to_currency
        )

        if locked_rate:
            # Use locked rate for conversion
            converted = amount * locked_rate.rate
            converted = self.converter._round_amount(converted, to_currency)

            # Calculate fee if applicable
            fee_amount = Decimal("0")
            if self.converter._conversion_fee > 0:
                fee_amount = self.converter._round_amount(
                    converted * (self.converter._conversion_fee / 100),
                    to_currency,
                )
                converted = converted - fee_amount

            return CurrencyConversion(
                conversion_id=str(uuid.uuid4()),
                from_currency=from_currency.upper(),
                to_currency=to_currency.upper(),
                from_amount=amount,
                to_amount=converted,
                exchange_rate=locked_rate.rate,
                rate_source=f"locked:{locked_rate.source}",
                rate_timestamp=locked_rate.timestamp,
                fee_amount=fee_amount,
                fee_currency=to_currency.upper(),
            )

        # Fall back to current rate
        return await self.converter.convert(
            amount, from_currency, to_currency, include_fee=True
        )

    def release_locked_rate(self, checkout_id: str) -> None:
        """Release all locked rates for a checkout session."""
        to_remove = [
            key for key in self._locked_rates
            if key.startswith(f"{checkout_id}:")
        ]
        for key in to_remove:
            del self._locked_rates[key]

    def cleanup_expired_locks(self) -> int:
        """Clean up expired rate locks. Returns count of removed locks."""
        now = datetime.utcnow()
        expired = [
            key for key, (_, expires_at) in self._locked_rates.items()
            if now > expires_at
        ]
        for key in expired:
            del self._locked_rates[key]
        return len(expired)
